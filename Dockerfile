# Use a imagem oficial do Python
FROM python:3.9-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY ./app /app

# Expõe a porta que o Flask irá rodar
EXPOSE 5000

# Comando para rodar a aplicação
CMD ["python", "main.py"]
