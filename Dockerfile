# Use a imagem oficial do Python
FROM python:3.9-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY ./app /app

# Expõe a porta que a aplicação irá rodar
EXPOSE 5000

# Comando para rodar a aplicação em produção via Gunicorn (servidor WSGI).
# NÃO use `python main.py` (servidor de desenvolvimento do Flask) em produção.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "main:app"]
