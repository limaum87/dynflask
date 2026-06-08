
import os
import secrets
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
from models import db, Host, User, Setting
from provider_factory import get_provider, get_configured_providers, ProviderNotFoundError, ProviderNotConfiguredError
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from security import encrypt_value, decrypt_value
from werkzeug.middleware.proxy_fix import ProxyFix

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

# --- Rotas da Aplicação ---

@app.route('/')
@login_required
def index():
    """Página principal que lista todos os hosts."""
    hosts = Host.query.all()
    configured_providers = get_configured_providers()
    return render_template('index.html', hosts=hosts, configured_providers=configured_providers)


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


# --- Rotas CRUD de Hosts ---

@app.route('/add', methods=['POST'])
@login_required
def add_host():
    """Adiciona um novo host."""
    hostname = request.form.get('hostname')
    record_type = request.form.get('record_type', 'A')
    ttl = int(request.form.get('ttl', 300))
    provider = request.form.get('provider', 'cloudflare')

    if not hostname:
        flash('O nome do host é obrigatório.', 'error')
        return redirect(url_for('index'))

    # Validar provider
    configured = get_configured_providers()
    if provider not in configured:
        flash(f'O provider "{provider}" não está configurado. Configure as credenciais em Configurações.', 'error')
        return redirect(url_for('index'))

    # Gera um token de autenticação seguro
    auth_token = secrets.token_hex(16)

    new_host = Host(
        hostname=hostname,
        record_type=record_type,
        ttl=ttl,
        auth_token=auth_token,
        provider=provider,
    )
    db.session.add(new_host)
    db.session.commit()

    flash(f'Host {hostname} adicionado com sucesso (provider: {provider})!', 'success')
    return redirect(url_for('index'))


@app.route('/edit/<int:host_id>', methods=['POST'])
@login_required
def edit_host(host_id):
    """Edita um host existente."""
    host = Host.query.get_or_404(host_id)

    host.hostname = request.form.get('hostname')
    host.record_type = request.form.get('record_type')
    host.ttl = int(request.form.get('ttl'))
    host.provider = request.form.get('provider', host.provider)

    # Validar provider
    configured = get_configured_providers()
    if host.provider not in configured:
        flash(f'O provider "{host.provider}" não está configurado. Configure as credenciais em Configurações.', 'warning')

    db.session.commit()

    flash(f'Host {host.hostname} atualizado com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/delete/<int:host_id>', methods=['POST'])
@login_required
def delete_host(host_id):
    """Exclui um host."""
    host = Host.query.get_or_404(host_id)
    db.session.delete(host)
    db.session.commit()

    flash(f'Host {host.hostname} excluído com sucesso!', 'success')
    return redirect(url_for('index'))


# --- API Endpoints ---

@app.route('/update', methods=['POST'])
def update_ip():
    """
    Endpoint da API para atualizar o endereço IP de um host.
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

    try:
        # Instancia o provider correto via fábrica
        provider = get_provider(host.provider)

        # Verifica se o registro DNS já existe
        record = provider.get_dns_record(hostname, host.record_type)

        if record:
            # Se o IP não mudou, não faz nada
            if record['content'] == ip_address:
                return jsonify({"status": "success", "message": "IP já está atualizado.", "provider": host.provider}), 200

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
            "message": f"IP do host {hostname} {action} para {ip_address} via {host.provider}.",
            "provider": host.provider,
        }), 200

    except ProviderNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except ProviderNotConfiguredError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Retorna o status de todos os hosts configurados."""
    hosts = Host.query.all()
    status_data = [
        {
            "hostname": host.hostname,
            "provider": host.provider,
            "record_type": host.record_type,
            "current_ip": host.current_ip,
            "last_updated": host.last_updated.isoformat() if host.last_updated else None
        }
        for host in hosts
    ]
    return jsonify(status_data), 200


def run_migration():
    """Executa migrations pendentes (adicionar coluna provider)."""
    try:
        result = db.session.execute(db.text("SHOW COLUMNS FROM hosts LIKE 'provider'"))
        if not result.fetchone():
            db.session.execute(db.text(
                "ALTER TABLE hosts ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'cloudflare' AFTER auth_token"
            ))
            db.session.commit()
            print("Migration: coluna 'provider' adicionada à tabela 'hosts'.")
    except Exception as e:
        print(f"Migration: erro ou não necessária — {e}")


def create_initial_user():
    """Cria o usuário admin inicial se nenhum usuário existir."""
    if User.query.first() is None:
        admin_user = User(username='admin')
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário 'admin' criado com a senha 'admin'.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        run_migration()
        create_initial_user()
    app.run(host='0.0.0.0', port=5000, debug=True)
