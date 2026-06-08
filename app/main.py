
import os
import secrets
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
from models import db, DnsZone, Host, User, Setting
from provider_factory import get_provider, get_configured_providers, ProviderNotFoundError, ProviderNotConfiguredError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from security import encrypt_value, decrypt_value
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.exc import IntegrityError

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Adiciona o middleware ProxyFix para que o Flask confie nos cabeçalhos do Nginx
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configurações do Banco de Dados
db_user = os.getenv("MYSQL_USER")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DATABASE")
db_host = 'mysql-db'  # Nome do serviço no docker-compose

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

# Endurecimento dos cookies de sessão (mitiga CSRF/roubo de sessão).
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Cookie só trafega via HTTPS. Desative apenas para testes locais em HTTP
# definindo SESSION_COOKIE_SECURE=False no ambiente.
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('1', 'true', 'yes')

# Proteção CSRF para todos os formulários POST/PUT/PATCH/DELETE.
csrf = CSRFProtect(app)

# Inicializa o app com o banco de dados
db.init_app(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Rota para a página de login

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Rotas de Autenticação ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Rotas de Zonas ---

@app.route('/')
@login_required
def index():
    """Página principal — lista todas as zonas DNS."""
    zones = DnsZone.query.order_by(DnsZone.name).all()
    configured_providers = get_configured_providers()
    return render_template('index.html', zones=zones, configured_providers=configured_providers)


@app.route('/zones/add', methods=['POST'])
@login_required
def add_zone():
    """Adiciona uma nova zona DNS e importa registros automaticamente."""
    name = request.form.get('name', '').strip().lower()
    provider = request.form.get('provider', 'cloudflare')
    auto_sync = request.form.get('auto_sync') == 'on'

    if not name:
        flash('O nome da zona é obrigatório.', 'error')
        return redirect(url_for('index'))

    # Validar provider
    configured = get_configured_providers()
    if provider not in configured:
        flash(f'O provider "{provider}" não está configurado. Configure as credenciais em Configurações.', 'error')
        return redirect(url_for('index'))

    # Verificar duplicata
    existing = DnsZone.query.filter_by(name=name).first()
    if existing:
        flash(f'A zona "{name}" já existe.', 'error')
        return redirect(url_for('index'))

    # Validar zona contra o provider (bloquear se não bater)
    try:
        dns_provider = get_provider(provider)
        zone_info = dns_provider.get_zone_info()
        provider_zone_name = zone_info.get('name', '').rstrip('.').lower()
        zone_name_clean = name.rstrip('.').lower()

        if provider_zone_name:
            # Verifica se bate exatamente OU é subdomínio da Hosted Zone
            is_match = zone_name_clean == provider_zone_name
            is_subdomain = zone_name_clean.endswith('.' + provider_zone_name)

            if not is_match and not is_subdomain:
                flash(
                    f'❌ A zona "{name}" não corresponde à Hosted Zone configurada "{provider_zone_name}" '
                    f'(ID: {zone_info.get("id", "?")}). Verifique as credenciais em Configurações — '
                    f'você pode estar usando o Zone ID errado.',
                    'error'
                )
                return redirect(url_for('index'))
    except ProviderNotConfiguredError:
        flash(f'O provider "{provider}" não está configurado.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        # get_zone_info pode falhar se o IAM não tiver permissão GetHostedZone
        # Mostra warning e permite continuar
        logging.warning(f"Não foi possível validar zona contra o provider: {e}")
        flash(f'⚠️ Não foi possível validar a zona contra o provider ({e}). '
              f'Verifique se o IAM tem permissão route53:GetHostedZone.', 'warning')

    zone = DnsZone(name=name, provider=provider)
    db.session.add(zone)
    db.session.commit()

    # Auto-import registros se solicitado
    imported = 0
    if auto_sync:
        try:
            imported = _sync_zone_records(zone)
        except Exception as e:
            flash(f'Zona "{name}" criada, mas falha ao importar registros: {e}', 'warning')
            return redirect(url_for('zone_detail', zone_id=zone.id))

    if imported > 0:
        flash(f'Zona "{name}" criada com sucesso! {imported} registro(s) importado(s) automaticamente.', 'success')
    else:
        flash(f'Zona "{name}" criada com sucesso!', 'success')

    return redirect(url_for('zone_detail', zone_id=zone.id))


@app.route('/zones/edit/<int:zone_id>', methods=['POST'])
@login_required
def edit_zone(zone_id):
    """Edita uma zona existente."""
    zone = DnsZone.query.get_or_404(zone_id)

    zone.name = request.form.get('name', '').strip().lower()
    zone.provider = request.form.get('provider', zone.provider)

    # Validar provider
    configured = get_configured_providers()
    if zone.provider not in configured:
        flash(f'O provider "{zone.provider}" não está configurado.', 'warning')

    db.session.commit()
    flash(f'Zona "{zone.name}" atualizada com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/zones/delete/<int:zone_id>', methods=['POST'])
@login_required
def delete_zone(zone_id):
    """Exclui uma zona e todos os seus hosts."""
    zone = DnsZone.query.get_or_404(zone_id)
    zone_name = zone.name
    db.session.delete(zone)
    db.session.commit()

    flash(f'Zona "{zone_name}" excluída com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/zone/<int:zone_id>/sync')
@login_required
def sync_zone(zone_id):
    """Sincroniza os registros de uma zona com o provider DNS."""
    zone = DnsZone.query.get_or_404(zone_id)

    try:
        imported = _sync_zone_records(zone)
        flash(f'Sincronização concluída! {imported} registro(s) importado(s).', 'success')
    except Exception as e:
        flash(f'Erro ao sincronizar: {e}', 'error')

    return redirect(url_for('zone_detail', zone_id=zone.id))


def _sync_zone_records(zone: DnsZone) -> int:
    """
    Importa registros DNS do provider para a zona.
    Cria hosts apenas para registros que ainda não existem localmente.
    Retorna o número de registros importados.

    A lógica de matching é flexível: como o Route53 lista TODOS os registros
    da Hosted Zone, e a Hosted Zone pode cobrir 'accept.inf.br' enquanto
    o usuário registrou a zona como 'accept.inf.br' ou até 'dyn.accept.inf.br',
    nós importamos todos os registros que pertencem à Hosted Zone do provider
    e associamos à zona do DynFlask.
    """
    provider = get_provider(zone.provider)

    imported = 0
    skipped = 0
    for record_type in ('A', 'AAAA'):
        try:
            records = provider.list_dns_records(record_type=record_type)
        except Exception as e:
            logging.warning(f"Falha ao listar registros {record_type} para {zone.name}: {e}")
            continue

        for record in records:
            hostname = record['hostname'].lower().rstrip('.').strip()

            if not hostname:
                continue

            # Detectar o domínio base da Hosted Zone a partir dos registros.
            # Se a zona é 'dyn.accept.inf.br' mas os registros são 'foo.accept.inf.br',
            # significa que a Hosted Zone é 'accept.inf.br' — importar tudo.
            # Se os registros terminam com o nome da zona exato, filtrar normalmente.
            zone_name = zone.name.rstrip('.').lower()
            hostname_matches_zone = hostname == zone_name or hostname.endswith('.' + zone_name)

            if not hostname_matches_zone:
                # Tentar matching reverso: verificar se algum sufixo do hostname
                # corresponde à zona (ex: zona='dyn.accept.inf.br' e hostname='foo.accept.inf.br')
                # Neste caso, o domínio base é 'accept.inf.br' — importar todos
                # que terminam com esse domínio base
                parts = zone_name.split('.')
                matched_parent = False
                for i in range(len(parts)):
                    parent = '.'.join(parts[i:])
                    if hostname.endswith('.' + parent) or hostname == parent:
                        matched_parent = True
                        break
                if not matched_parent:
                    skipped += 1
                    continue

            # Verificar se já existe
            existing = Host.query.filter_by(hostname=hostname, zone_id=zone.id).first()
            if existing:
                # Atualizar IP se diferente
                if record.get('content') and existing.current_ip != record['content']:
                    existing.current_ip = record['content']
                continue

            logging.info(f"[Sync] Importando: {hostname} -> {record.get('content')} ({record_type})")

            # Criar novo host com token
            host = Host(
                zone_id=zone.id,
                hostname=hostname,
                record_type=record.get('type', record_type),
                ttl=record.get('ttl', 300),
                auth_token=secrets.token_hex(16),
                current_ip=record.get('content'),
            )
            db.session.add(host)
            imported += 1

    db.session.commit()
    logging.info(f"[Sync] Zona {zone.name}: {imported} importados, {skipped} ignorados")
    return imported


# --- Rotas de Hosts (dentro de uma zona) ---

@app.route('/zone/<int:zone_id>')
@login_required
def zone_detail(zone_id):
    """Página de detalhes de uma zona — lista seus hosts/registros."""
    zone = DnsZone.query.get_or_404(zone_id)
    hosts = zone.hosts.all()
    return render_template('zone_detail.html', zone=zone, hosts=hosts)


@app.route('/zone/<int:zone_id>/add', methods=['POST'])
@login_required
def add_host(zone_id):
    """Adiciona um novo host a uma zona."""
    zone = DnsZone.query.get_or_404(zone_id)

    hostname = request.form.get('hostname', '').strip().lower()
    record_type = request.form.get('record_type', 'A')
    ttl = int(request.form.get('ttl', 300))
    ip = request.form.get('ip', '').strip() or None

    if not hostname:
        flash('O hostname é obrigatório.', 'error')
        return redirect(url_for('zone_detail', zone_id=zone.id))

    # Se o hostname não termina com o nome da zona, adiciona automaticamente
    if not hostname.endswith(zone.name):
        hostname = f"{hostname}.{zone.name}"

    # Verificar duplicata
    existing = Host.query.filter_by(hostname=hostname, zone_id=zone.id).first()
    if existing:
        flash(f'O host "{hostname}" já existe nesta zona.', 'error')
        return redirect(url_for('zone_detail', zone_id=zone.id))

    auth_token = secrets.token_hex(16)

    host = Host(
        zone_id=zone.id,
        hostname=hostname,
        record_type=record_type,
        ttl=ttl,
        auth_token=auth_token,
        current_ip=ip,
    )
    db.session.add(host)
    db.session.commit()

    flash(f'Host "{hostname}" adicionado com sucesso!', 'success')
    return redirect(url_for('zone_detail', zone_id=zone.id))


@app.route('/host/edit/<int:host_id>', methods=['POST'])
@login_required
def edit_host(host_id):
    """Edita um host existente."""
    host = Host.query.get_or_404(host_id)

    host.hostname = request.form.get('hostname', '').strip().lower()
    host.record_type = request.form.get('record_type')
    host.ttl = int(request.form.get('ttl'))

    db.session.commit()

    flash(f'Host "{host.hostname}" atualizado com sucesso!', 'success')
    return redirect(url_for('zone_detail', zone_id=host.zone_id))


@app.route('/host/delete/<int:host_id>', methods=['POST'])
@login_required
def delete_host(host_id):
    """Exclui um host."""
    host = Host.query.get_or_404(host_id)
    zone_id = host.zone_id
    hostname = host.hostname

    db.session.delete(host)
    db.session.commit()

    flash(f'Host "{hostname}" excluído com sucesso!', 'success')
    return redirect(url_for('zone_detail', zone_id=zone_id))


# --- Rotas de Configurações ---

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # --- Cloudflare ---
        zone_id = request.form.get('cloudflare_zone_id', '').strip()
        if zone_id:
            setting = Setting.query.filter_by(key='CLOUDFLARE_ZONE_ID').first()
            if not setting:
                setting = Setting(key='CLOUDFLARE_ZONE_ID')
            setting.value = zone_id
            db.session.add(setting)

        api_token = request.form.get('cloudflare_api_token', '').strip()
        if api_token:
            setting = Setting.query.filter_by(key='CLOUDFLARE_API_TOKEN').first()
            if not setting:
                setting = Setting(key='CLOUDFLARE_API_TOKEN')
            setting.value = encrypt_value(api_token)
            db.session.add(setting)

        # --- Route53 ---
        hosted_zone_id = request.form.get('route53_hosted_zone_id', '').strip()
        if hosted_zone_id:
            setting = Setting.query.filter_by(key='ROUTE53_HOSTED_ZONE_ID').first()
            if not setting:
                setting = Setting(key='ROUTE53_HOSTED_ZONE_ID')
            setting.value = hosted_zone_id
            db.session.add(setting)

        aws_access_key = request.form.get('route53_aws_access_key_id', '').strip()
        if aws_access_key:
            setting = Setting.query.filter_by(key='ROUTE53_AWS_ACCESS_KEY_ID').first()
            if not setting:
                setting = Setting(key='ROUTE53_AWS_ACCESS_KEY_ID')
            setting.value = aws_access_key
            db.session.add(setting)

        aws_secret_key = request.form.get('route53_aws_secret_access_key', '').strip()
        if aws_secret_key:
            setting = Setting.query.filter_by(key='ROUTE53_AWS_SECRET_ACCESS_KEY').first()
            if not setting:
                setting = Setting(key='ROUTE53_AWS_SECRET_ACCESS_KEY')
            setting.value = encrypt_value(aws_secret_key)
            db.session.add(setting)

        aws_region = request.form.get('route53_aws_region', '').strip()
        if aws_region:
            setting = Setting.query.filter_by(key='ROUTE53_AWS_REGION').first()
            if not setting:
                setting = Setting(key='ROUTE53_AWS_REGION')
            setting.value = aws_region
            db.session.add(setting)

        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('settings'))

    # GET — carregar valores para o formulário
    def get_setting(key):
        s = Setting.query.filter_by(key=key).first()
        return s.value if s else ''

    return render_template('settings.html',
        cloudflare_zone_id=get_setting('CLOUDFLARE_ZONE_ID'),
        route53_hosted_zone_id=get_setting('ROUTE53_HOSTED_ZONE_ID'),
        route53_aws_access_key_id=get_setting('ROUTE53_AWS_ACCESS_KEY_ID'),
        route53_aws_region=get_setting('ROUTE53_AWS_REGION') or 'us-east-1',
        configured_providers=get_configured_providers(),
    )


# --- API Endpoints ---

@app.route('/update', methods=['POST'])
@csrf.exempt
def update_ip():
    """
    Endpoint da API para atualizar o endereço IP de um host.
    Isento de CSRF: é uma API máquina-a-máquina autenticada por token
    (não usa cookie de sessão), consumida por clientes DynDNS externos.
    Requer 'hostname' e 'token' no corpo da requisição (JSON).
    Opcionalmente, pode receber 'ip' (se não for recebido, usa o IP de origem da requisição).
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Corpo da requisição deve ser JSON."}), 400

    hostname = data.get('hostname')
    token = data.get('token')
    ip_address = data.get('ip', request.remote_addr)

    if not all([hostname, token]):
        return jsonify({"status": "error", "message": "Parâmetros 'hostname' e 'token' são obrigatórios."}), 400

    # Busca o host no banco de dados
    host = Host.query.filter_by(hostname=hostname).first()

    if not host or not secrets.compare_digest(host.auth_token, token):
        return jsonify({"status": "error", "message": "Host não encontrado ou token inválido."}), 403

    # Provider vem da zona
    zone = host.zone

    try:
        # Instancia o provider correto via fábrica
        provider = get_provider(zone.provider)

        # Verifica se o registro DNS já existe
        record = provider.get_dns_record(hostname, host.record_type)

        if record:
            # Se o IP não mudou, não faz nada
            if record['content'] == ip_address:
                return jsonify({"status": "success", "message": "IP já está atualizado.", "provider": zone.provider}), 200

            # Atualiza o registro existente
            provider.update_dns_record(record['id'], host.hostname, ip_address, host.record_type, host.ttl)
            action = "atualizado"
        else:
            # Cria um novo registro
            provider.create_dns_record(host.hostname, ip_address, host.record_type, host.ttl)
            action = "criado"

        # Atualiza o IP no banco de dados local
        host.current_ip = ip_address
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"IP do host {hostname} {action} para {ip_address} via {zone.provider}.",
            "provider": zone.provider,
        }), 200

    except ProviderNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except ProviderNotConfiguredError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- API de Teste de Conexão ---

@app.route('/api/test-provider/<provider_name>')
@login_required
def test_provider(provider_name):
    """Testa a conexão com um provider de DNS e retorna info da zona."""
    try:
        provider = get_provider(provider_name)
        zone_info = provider.get_zone_info()
        return jsonify({
            'status': 'success',
            'provider': provider_name,
            'zone_name': zone_info.get('name', ''),
            'zone_id': zone_info.get('id', ''),
            'record_count': zone_info.get('record_count', 0),
            'comment': zone_info.get('comment', ''),
        }), 200
    except ProviderNotFoundError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except ProviderNotConfiguredError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/status', methods=['GET'])
@login_required
def get_status():
    """Retorna o status de todos os hosts configurados."""
    hosts = Host.query.all()
    status_data = [
        {
            "hostname": host.hostname,
            "zone": host.zone.name,
            "provider": host.zone.provider,
            "record_type": host.record_type,
            "current_ip": host.current_ip,
            "last_updated": host.last_updated.isoformat() if host.last_updated else None
        }
        for host in hosts
    ]
    return jsonify(status_data), 200


def run_migration():
    """Executa migrations pendentes."""
    try:
        # Create dns_zones table if not exists
        db.session.execute(db.text("""
            CREATE TABLE IF NOT EXISTS dns_zones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                provider VARCHAR(50) NOT NULL DEFAULT 'cloudflare',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Add zone_id column to hosts if not exists
        result = db.session.execute(db.text("SHOW COLUMNS FROM hosts LIKE 'zone_id'"))
        if not result.fetchone():
            db.session.execute(db.text(
                "ALTER TABLE hosts ADD COLUMN zone_id INT AFTER id"
            ))

            # Migrate existing data
            try:
                providers = db.session.execute(db.text(
                    "SELECT DISTINCT provider FROM hosts WHERE provider IS NOT NULL"
                )).fetchall()

                for (prov,) in providers:
                    zone_name = f"migrated-{prov}-zone"
                    db.session.execute(db.text(
                        f"INSERT IGNORE INTO dns_zones (name, provider) VALUES ('{zone_name}', '{prov}')"
                    ))
                    zone_row = db.session.execute(db.text(
                        f"SELECT id FROM dns_zones WHERE name = '{zone_name}'"
                    )).fetchone()
                    if zone_row:
                        db.session.execute(db.text(
                            f"UPDATE hosts SET zone_id = {zone_row[0]} WHERE provider = '{prov}' AND zone_id IS NULL"
                        ))
            except Exception:
                pass

            try:
                db.session.execute(db.text("ALTER TABLE hosts MODIFY COLUMN zone_id INT NOT NULL"))
                db.session.execute(db.text(
                    "ALTER TABLE hosts ADD CONSTRAINT fk_hosts_zone FOREIGN KEY (zone_id) REFERENCES dns_zones(id)"
                ))
            except Exception:
                pass

            try:
                db.session.execute(db.text("ALTER TABLE hosts DROP COLUMN provider"))
            except Exception:
                pass

        db.session.commit()
        print("Migration: zonas verificadas/criadas com sucesso.")
    except Exception as e:
        print(f"Migration: {e}")


def create_initial_user():
    """
    Cria o usuário admin inicial se nenhum usuário existir.

    A senha NUNCA é um valor fixo: ela vem da variável de ambiente
    ADMIN_PASSWORD. Se não for definida, uma senha forte aleatória é
    gerada e exibida UMA ÚNICA VEZ no log de inicialização — anote-a
    e troque após o primeiro login.
    """
    if User.query.first() is not None:
        return

    username = os.getenv('ADMIN_USERNAME', 'admin')
    password = os.getenv('ADMIN_PASSWORD')

    generated = False
    if not password:
        password = secrets.token_urlsafe(16)
        generated = True

    admin_user = User(username=username)
    admin_user.set_password(password)
    db.session.add(admin_user)
    try:
        db.session.commit()
    except IntegrityError:
        # Corrida entre workers do Gunicorn: outro processo já criou o usuário.
        db.session.rollback()
        return

    if generated:
        logging.warning(
            "\n" + "=" * 70 +
            f"\n  Usuário inicial '{username}' criado com SENHA ALEATÓRIA:"
            f"\n      {password}"
            "\n  Anote agora — ela NÃO será exibida novamente."
            "\n  Defina ADMIN_PASSWORD no .env para controlar a senha inicial."
            "\n" + "=" * 70
        )
    else:
        logging.info(f"Usuário inicial '{username}' criado com a senha definida em ADMIN_PASSWORD.")


def initialize():
    """Prepara o banco (schema, migrations, usuário inicial). Idempotente."""
    with app.app_context():
        db.create_all()
        run_migration()
        create_initial_user()


# Executa a inicialização ao carregar o módulo, para que também funcione
# sob um servidor WSGI de produção (Gunicorn), não só com `python main.py`.
initialize()


if __name__ == '__main__':
    # Apenas para desenvolvimento local. Em produção use Gunicorn (ver Dockerfile).
    debug_enabled = os.getenv('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=5000, debug=debug_enabled)
