import os
from cryptography.fernet import Fernet

# É crucial que esta chave seja mantida em segredo e não mude.
# Vamos lê-la da variável de ambiente SECRET_KEY que já usamos para o Flask.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("A SECRET_KEY não foi definida nas variáveis de ambiente.")

# O Fernet requer uma chave de 32 bytes, codificada em URL-safe base64.
# Vamos derivar uma chave a partir da SECRET_KEY do Flask.
# ATENÇÃO: Em um ambiente de produção real, seria melhor gerar e armazenar
# uma chave de criptografia totalmente separada e gerenciá-la com cuidado.
# Para este projeto, derivar da SECRET_KEY é uma simplificação aceitável.
from hashlib import sha256
import base64

key = base64.urlsafe_b64encode(sha256(SECRET_KEY.encode()).digest())

fernet = Fernet(key)

def encrypt_value(value: str) -> str:
    """Criptografa um valor string."""
    if not value:
        return ""
    return fernet.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Descriptografa um valor."""
    if not encrypted_value:
        return ""
    return fernet.decrypt(encrypted_value.encode()).decode()
