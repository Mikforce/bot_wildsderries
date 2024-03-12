FROM python:3.9

# Установка PostgreSQL и необходимых пакетов
RUN apt-get update \
    && apt-get install -y postgresql \
    && apt-get clean

# Копирование кода приложения в контейнер
WORKDIR /app
COPY . /app

# Установка зависимостей Python
RUN pip install aiogram==2.23.1 requests SQLAlchemy psycopg2 asyncio

# Открываем порт для веб-хука Telegram (если используется)
EXPOSE 80

CMD ["python", "main.py"]