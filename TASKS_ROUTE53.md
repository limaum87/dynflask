# Tasks: Suporte a Múltiplos DNS Providers (Cloudflare + Route53)

## Objetivo

Refatorar o DynFlask para suportar múltiplos providers de DNS, adicionando o **AWS Route53** como alternativa ao **Cloudflare**, usando o padrão **Strategy (Provider)**.

---

## Fase 1 — Fundação (Interface e Modelo)

### Task 1.1 — Criar interface `DNSProvider`

- [ ] Criar arquivo `app/dns_provider.py`
- [ ] Definir classe abstrata `DNSProvider` com métodos:
  - `get_dns_record(hostname, record_type) -> dict | None`
  - `create_dns_record(hostname, ip, record_type, ttl)`
  - `update_dns_record(record_id, hostname, ip, record_type, ttl)`
- [ ] Adicionar docstrings em cada método

### Task 1.2 — Refatorar `cloudflare.py` para implementar a interface

- [ ] Criar classe `CloudflareProvider(DNSProvider)` em `app/cloudflare.py`
- [ ] Mover as funções existentes (`get_dns_record`, `create_dns_record`, `update_dns_record`) como métodos da classe
- [ ] Receber `zone_id` e `api_token` no `__init__` em vez de parâmetros soltos
- [ ] Garantir que o comportamento existente não quebre (compatibilidade retroativa)

### Task 1.3 — Criar `Route53Provider`

- [ ] Criar arquivo `app/route53_provider.py`
- [ ] Criar classe `Route53Provider(DNSProvider)`
- [ ] Receber no `__init__`: `hosted_zone_id`, `aws_access_key_id`, `aws_secret_access_key`, `region` (default: `us-east-1`)
- [ ] Implementar `get_dns_record` usando `boto3.client.list_resource_record_sets`
- [ ] Implementar `create_dns_record` usando `boto3.client.change_resource_record_sets` com `Action: CREATE`
- [ ] Implementar `update_dns_record` usando `boto3.client.change_resource_record_sets` com `Action: UPSERT`
- [ ] Adicionar tratamento de erros (exceções do boto3 → mensagens amigáveis)
- [ ] Adicionar logs para debug

### Task 1.4 — Atualizar `models.py`

- [ ] Adicionar coluna `provider` na model `Host`:
  ```python
  provider = db.Column(db.String(50), nullable=False, default='cloudflare')
  ```
- [ ] Valor padrão `cloudflare` para manter compatibilidade com hosts existentes
- [ ] Atualizar o `__repr__` para incluir o provider

### Task 1.5 — Script de migration

- [ ] Criar migration SQL para adicionar a coluna `provider` na tabela `hosts`
  ```sql
  ALTER TABLE hosts ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'cloudflare';
  ```
- [ ] Adicionar as novas chaves de configuração do Route53 na tabela `settings` (seeding)

---

## Fase 2 — Configurações e Credenciais

### Task 2.1 — Configurações do Route53 no banco

- [ ] Adicionar suporte às novas chaves na model `Setting`:
  - `ROUTE53_HOSTED_ZONE_ID`
  - `ROUTE53_AWS_ACCESS_KEY_ID`
  - `ROUTE53_AWS_SECRET_ACCESS_KEY`
  - `ROUTE53_AWS_REGION` (default: `us-east-1`)
- [ ] Garantir que `ROUTE53_AWS_SECRET_ACCESS_KEY` seja armazenada criptografada (usar `encrypt_value`/`decrypt_value` existente)

### Task 2.2 — Atualizar arquivo `.env.example`

- [ ] Adicionar bloco de variáveis do Route53:
  ```env
  # Route53 (opcional)
  ROUTE53_HOSTED_ZONE_ID=
  ROUTE53_AWS_ACCESS_KEY_ID=
  ROUTE53_AWS_SECRET_ACCESS_KEY=
  ROUTE53_AWS_REGION=us-east-1
  ```

### Task 2.3 — Atualizar página de Settings

- [ ] Criar seções separadas na tela de configurações: "Cloudflare" e "Route53"
- [ ] Exibir/ocultar campos conforme o provider selecionado
- [ ] Validar credenciais antes de salvar (opcional: botão "Testar Conexão")

---

## Fase 3 — Fábrica de Providers e Rotas

### Task 3.1 — Criar fábrica de providers

- [ ] Criar função `get_provider(provider_name: str) -> DNSProvider` em `app/main.py` ou novo arquivo `app/provider_factory.py`
- [ ] Buscar credenciais do banco de dados conforme o provider
- [ ] Retornar instância correta: `CloudflareProvider` ou `Route53Provider`
- [ ] Levantar erro claro se provider não existir ou credenciais não configuradas

### Task 3.2 — Atualizar rota `/update` no `main.py`

- [ ] Substituir chamadas diretas ao `cloudflare.py` pela fábrica de providers
- [ ] Fluxo:
  1. Buscar host no banco
  2. Obter provider do host (`host.provider`)
  3. Instanciar provider via fábrica
  4. Chamar `get_dns_record` → `create_dns_record` ou `update_dns_record`
- [ ] Manter o contrato de resposta da API inalterado

### Task 3.3 — Atualizar rota `/add`

- [ ] Adicionar campo `provider` no formulário de adicionar host
- [ ] Salvar o provider escolhido no banco de dados
- [ ] Validar se as credenciais do provider selecionado estão configuradas antes de salvar

### Task 3.4 — Atualizar rota `/edit`

- [ ] Permitir trocar o provider de um host existente
- [ ] Validação: se trocar de provider, verificar se as credenciais do novo estão configuradas

---

## Fase 4 — Interface Web (Templates)

### Task 4.1 — Atualizar `index.html` (listagem de hosts)

- [ ] Adicionar coluna "Provider" na tabela de hosts
- [ ] Exibir badge/label com o nome do provider (Cloudflare / Route53)

### Task 4.2 — Atualizar formulário de adicionar host

- [ ] Adicionar campo select para escolher o provider
- [ ] Opções: Cloudflare, Route53
- [ ] Default: Cloudflare (mantém comportamento atual)

### Task 4.3 — Atualizar formulário de editar host

- [ ] Exibir o provider atual
- [ ] Permitir alteração (com aviso sobre troca de provider)

### Task 4.4 — Atualizar página de `settings.html`

- [ ] Dividir em abas ou seções: Cloudflare | Route53
- [ ] Campos do Route53:
  - Hosted Zone ID
  - AWS Access Key ID
  - AWS Secret Access Key (mascarado)
  - AWS Region (select com regiões)
- [ ] Botão "Testar Conexão" para cada provider (opcional, mas recomendado)

---

## Fase 5 — Dependências e Infra

### Task 5.1 — Atualizar `requirements.txt`

- [ ] Adicionar `boto3` como dependência
  ```
  boto3>=1.34.0
  ```

### Task 5.2 — Atualizar `docker-compose.yml`

- [ ] Adicionar variáveis de ambiente do Route53 (opcionais)
- [ ] Documentar no compose as novas variáveis

### Task 5.3 — Atualizar `Dockerfile`

- [ ] Garantir que o `boto3` será instalado no build (já coberto pelo `requirements.txt`)

---

## Fase 6 — Testes

### Task 6.1 — Testes unitários do `Route53Provider`

- [ ] Testar `get_dns_record` (registro existe / não existe)
- [ ] Testar `create_dns_record`
- [ ] Testar `update_dns_record` (UPSERT)
- [ ] Mockear chamadas do boto3 com `moto` (library de mock AWS)

### Task 6.2 — Testes unitários do `CloudflareProvider` (refatorado)

- [ ] Garantir que a refatoração não quebrou o comportamento existente
- [ ] Testar `get_dns_record`, `create_dns_record`, `update_dns_record`

### Task 6.3 — Testes de integração da API `/update`

- [ ] Testar update com provider Cloudflare
- [ ] Testar update com provider Route53
- [ ] Testar erro quando credenciais não estão configuradas
- [ ] Testar erro quando provider é inválido

### Task 6.4 — Testes manuais

- [ ] Adicionar host Cloudflare e verificar funcionamento
- [ ] Adicionar host Route53 e verificar funcionamento
- [ ] Trocar provider de um host existente e verificar
- [ ] Verificar migration em banco existente com dados

---

## Fase 7 — Documentação

### Task 7.1 — Atualizar `README.md`

- [ ] Adicionar seção sobre suporte a múltiplos providers
- [ ] Documentar configuração do Route53 (criar IAM, Hosted Zone, etc.)
- [ ] Atualizar exemplos da API com campo `provider`

### Task 7.2 — Criar guia de configuração do Route53

- [ ] Passo a passo para criar IAM User com permissão `route53:ChangeResourceRecordSets`
- [ ] Como obter o Hosted Zone ID
- [ ] Política IAM mínima recomendada:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "route53:ChangeResourceRecordSets",
          "route53:ListResourceRecordSets"
        ],
        "Resource": "arn:aws:route53:::hostedzone/HOSTED_ZONE_ID"
      }
    ]
  }
  ```

---

## Resumo de Arquivos Novos/Modificados

| Arquivo | Ação |
|---|---|
| `app/dns_provider.py` | 🆕 Novo |
| `app/route53_provider.py` | 🆕 Novo |
| `app/cloudflare.py` | ✏️ Refatorar |
| `app/main.py` | ✏️ Refatorar |
| `app/models.py` | ✏️ Alterar |
| `app/templates/index.html` | ✏️ Alterar |
| `app/templates/settings.html` | ✏️ Alterar |
| `app/templates/add_host.html` | ✏️ Alterar (se existir separado) |
| `requirements.txt` | ✏️ Adicionar `boto3` |
| `.env.example` | ✏️ Adicionar vars Route53 |
| `docker-compose.yml` | ✏️ Adicionar vars Route53 |
| `db/migration_route53.sql` | 🆕 Novo |
| `README.md` | ✏️ Atualizar |
| `docs/route53-setup.md` | 🆕 Novo |
| `tests/test_route53_provider.py` | 🆕 Novo |
| `tests/test_cloudflare_provider.py` | 🆕 Novo |
