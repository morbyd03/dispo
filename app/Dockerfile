FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system dispo \
    && useradd --system --gid dispo \
       --no-create-home dispo

COPY requirements.txt requirements.lock ./

RUN pip install --no-cache-dir -r requirements.lock

COPY . .

# Garantir la lecture des sources, meme lorsque
# le depot a ete clone avec un umask restrictif.
RUN chmod -R a+rX /app

RUN mkdir -p /app/staticfiles /data \
    && chown dispo:dispo /app/staticfiles /data \
    && chmod 755 /app/entrypoint.sh

USER dispo

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
