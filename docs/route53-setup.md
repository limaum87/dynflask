# Configuração do AWS Route53 — Guia Passo a Passo

Este guia mostra como configurar o AWS Route53 como provider de DNS dinâmico no DynFlask.

---

## Pré-requisitos

- Uma conta AWS ativa
- Um domínio registrado e uma Hosted Zone configurada no Route53

---

## Passo 1 — Obter o Hosted Zone ID

1. Acesse o [Console do Route53](https://console.aws.amazon.com/route53/)
2. Clique em **Hosted zones** no menu lateral
3. Clique no nome do seu domínio
4. No painel à direita, copie o **Hosted Zone ID** (ex: `Z1ABC2DEF3GHIJ`)

---

## Passo 2 — Criar um IAM User com permissões mínimas

### 2.1 Criar a política IAM

1. Acesse [IAM → Policies](https://console.aws.amazon.com/iam/home#/policies)
2. Clique em **Create policy**
3. Selecione a aba **JSON** e cole:

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
      "Resource": "arn:aws:route53:::hostedzone/SEU_HOSTED_ZONE_ID"
    }
  ]
}
```

4. Substitua `SEU_HOSTED_ZONE_ID` pelo ID do Passo 1
5. Clique em **Next**
6. Nome da política: `DynFlaskRoute53Policy`
7. Clique em **Create policy**

### 2.2 Criar o usuário IAM

1. Acesse [IAM → Users](https://console.aws.amazon.com/iam/home#/users)
2. Clique em **Create user**
3. Nome: `dynflask-ddns`
4. Marque **Provide user access to the AWS Management Console** — *opcional, não necessário*
5. Clique em **Next**
6. Selecione **Attach policies directly**
7. Busque e selecione `DynFlaskRoute53Policy`
8. Clique em **Next** → **Create user**

### 2.3 Criar Access Key

1. Clique no usuário `dynflask-ddns` criado
2. Vá na aba **Security credentials**
3. Clique em **Create access key**
4. Selecione **Application running outside AWS**
5. Clique em **Next**
6. Adicione uma descrição: `DynFlask DDNS`
7. Clique em **Create access key**
8. **Copie o Access Key ID e Secret Access Key** (não será possível ver novamente!)

---

## Passo 3 — Configurar no DynFlask

1. Acesse `https://seu-dominio/settings`
2. Na seção **AWS Route53**, preencha:
   - **Hosted Zone ID**: O ID copiado no Passo 1
   - **AWS Access Key ID**: O Access Key ID do Passo 2.3
   - **AWS Secret Access Key**: A Secret Access Key do Passo 2.3
   - **Região AWS**: Selecione a região mais próxima (Route53 é global, mas a autenticação usa a região)
3. Clique em **Salvar Route53**

---

## Passo 4 — Adicionar um host com Route53

1. No Dashboard, preencha:
   - **Hostname**: `home.seudominio.com`
   - **Tipo**: `A (IPv4)`
   - **TTL**: `300`
   - **Provider**: `AWS Route53`
2. Clique em **Adicionar Host**
3. Use o token gerado para atualizar o IP via API:

```bash
curl -X POST https://seu-dominio/update \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "home.seudominio.com",
    "token": "seu_token_gerado"
  }'
```

---

## Segurança

- A **Secret Access Key** é armazenada de forma **criptografada** no banco de dados
- O IAM User tem permissão **mínima** — apenas criar/atualizar/listar registros na zona específica
- Não é necessário acesso ao console AWS para o DynFlask funcionar
- Recomenda-se **rotacionar** as Access Keys periodicamente

---

## Troubleshooting

| Erro | Causa | Solução |
|---|---|---|
| `Credenciais AWS inválidas` | Access Key ou Secret incorretas | Verifique se copiou corretamente |
| `Erro Route53 (NoSuchHostedZone)` | Hosted Zone ID incorreto | Verifique o ID no console AWS |
| `Erro Route53 (AccessDenied)` | IAM sem permissão | Verifique se a política está anexada ao usuário |
| `Erro Route53 (InvalidChangeBatch)` | Registro já existe com valor diferente | O DynFlask usa UPSERT automaticamente |
