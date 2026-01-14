FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY tgbot_standalone/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY tgbot_standalone/ /app/tgbot_standalone/

WORKDIR /app/tgbot_standalone

CMD ["python", "main.py"]
