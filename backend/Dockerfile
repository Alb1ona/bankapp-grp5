# Backend-image til senere deployment på bankapplikations-VM'en (VLAN 50).
FROM python:3.12-slim

WORKDIR /app

# Systemafhængigheder til psycopg og argon2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# API_SURFACE vælger kunde- eller intern-listener (API-02).
# Overstyres ved kørsel: -e API_SURFACE=customer / internal
ENV API_SURFACE=all
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
