# DynFlask: Sistema de DNS Dinâmico Auto-Hospedado

DynFlask é um sistema de DNS dinâmico completo, construído com Flask, MySQL e Docker Compose, que permite a você gerenciar e atualizar registros DNS no Cloudflare através de uma interface web e uma API REST segura.

## Funcionalidades

-   **Interface Web de Administração:** Gerencie (crie, liste, edite, exclua) os registros de host que o sistema pode atualizar.
-   **API REST Segura:** Um endpoint `/update` para atualizar o IP de um host, autenticado por um token secreto único por host.
-   **Integração com Cloudflare:** Adiciona ou atualiza automaticamente os registros DNS (tipo A ou AAAA) na sua zona do Cloudflare.
-   **Orquestração com Docker Compose:** Setup simplificado com contêineres para a aplicação Flask e o banco de dados MySQL.
-   **Segurança:** Autenticação baseada em token para atualizações de IP.

## Estrutura do Projeto

```
/
├── app/                # Código-fonte da aplicação Flask
│   ├── static/         # Arquivos estáticos (CSS, JS)
│   ├── templates/      # Templates HTML (Jinja2)
│   ├── main.py         # Lógica principal do Flask (rotas, API)
│   ├── models.py       # Modelos de dados (SQLAlchemy)
│   └── cloudflare.py   # Funções de integração com a API do Cloudflare
├── db/
│   └── init.sql        # Script de inicialização do banco de dados
├── .env                # Arquivo para variáveis de ambiente (NÃO versionar)
├── docker-compose.yml  # Orquestração dos serviços Docker
├── Dockerfile          # Definição do contêiner da aplicação
├── requirements.txt    # Dependências Python
└── README.md           # Esta documentação
```

## Como Rodar o Projeto

### Pré-requisitos

-   Docker e Docker Compose instalados.
-   Uma conta no Cloudflare com um domínio configurado.

### 1. Configurar o Cloudflare

Você precisará de duas informações da sua conta Cloudflare:

-   **Zone ID:** O ID da zona (domínio) que você quer gerenciar.
    1.  Vá para o painel do seu domínio no Cloudflare.
    2.  Na página "Overview" (Visão Geral), role para baixo e você encontrará o **Zone ID** no lado direito. Copie-o.

-   **API Token:** Um token de API com permissão para editar registros DNS.
    1.  Acesse a página [API Tokens](https://dash.cloudflare.com/profile/api-tokens).
    2.  Clique em "Create Token".
    3.  Use o template "Edit zone DNS" ou crie um token customizado.
    4.  Em "Permissions", selecione:
        -   `Zone` - `DNS` - `Edit`
    5.  Em "Zone Resources", selecione sua zona específica.
    6.  Continue e crie o token. Copie o token gerado.

### 2. Configurar as Variáveis de Ambiente

1.  Renomeie ou copie o arquivo `.env.example` para `.env`.
2.  Abra o arquivo `.env` e preencha as variáveis:

    ```env
    # Configurações do Banco de Dados
    MYSQL_DATABASE=dynflaskdb
    MYSQL_USER=dynflaskuser
    MYSQL_PASSWORD=your_strong_password       # Use uma senha forte
    MYSQL_ROOT_PASSWORD=your_very_strong_root_password # Use uma senha forte

    # Credenciais da API do Cloudflare
    CLOUDFLARE_API_TOKEN=your_cloudflare_api_token # Token que você criou
    CLOUDFLARE_ZONE_ID=your_cloudflare_zone_id     # Zone ID que você copiou

    # Chave secreta para as sessões do Flask
    SECRET_KEY=a_very_secret_key_for_flask_sessions # Pode gerar com: openssl rand -hex 32
    ```

### 3. Iniciar os Contêineres

Com o Docker em execução, rode o seguinte comando na raiz do projeto:

```bash
docker-compose up --build -d
```

-   `--build`: Reconstrói a imagem do Flask caso haja mudanças no `Dockerfile` ou `requirements.txt`.
-   `-d`: Roda os contêineres em modo "detached" (em segundo plano).

A aplicação estará disponível em `http://localhost:5000`.

## Como Usar

### Interface de Administração

1.  Acesse `http://localhost:5000` no seu navegador.
2.  Use o formulário para adicionar os hostnames que você deseja gerenciar (ex: `home.seudominio.com`, `server.seudominio.com`).
3.  Para cada host, um **token de autenticação** será gerado. Este token é necessário para usar a API de atualização.

### API de Atualização de IP

Para atualizar o endereço IP de um host, envie uma requisição `POST` para o endpoint `/update`.

-   **URL:** `http://localhost:5000/update`
-   **Método:** `POST`
-   **Cabeçalho:** `Content-Type: application/json`
-   **Corpo (JSON):**

    ```json
    {
        "hostname": "home.seudominio.com",
        "token": "seu_token_de_autenticacao_gerado_na_interface"
    }
    ```

    -   **`hostname`**: O nome de host completo a ser atualizado.
    -   **`token`**: O token secreto associado a este host.
    -   **`ip` (opcional)**: Você pode enviar o IP no corpo da requisição. Se não for fornecido, o sistema usará o endereço IP de origem da requisição.

#### Exemplo com `curl`

```bash
curl -X POST http://localhost:5000/update \
-H "Content-Type: application/json" \
-d \'{
    "hostname": "home.seudominio.com",
    "token": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
}\'
```

Esta chamada pode ser configurada em um script `cron` em um servidor ou em um cliente de DNS dinâmico para automatizar a atualização do IP.

### Outros Endpoints

-   **`GET /status`**: Retorna um JSON com o status de todos os hosts configurados, incluindo o último IP registrado e a data da última atualização.

## Parando o Projeto

Para parar os contêineres, execute:

```bash
docker-compose down
```

Se quiser remover também os volumes (isso apagará os dados do banco de dados), use:

```bash
docker-compose down -v
```
