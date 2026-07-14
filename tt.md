Voici une configuration Docker Compose complète, prête à l’emploi, incluant :

🐬 MariaDB (10.11)
🐍 FastAPI (via uvicorn)
🔁 Migrations automatiques au démarrage (via script d'initialisation)
📦 Variables d’environnement sécurisées via .env
📁 Structure ajoutée
sdn-api/
├── docker-compose.yml
├── Dockerfile.api
├── init-db.sh               # Script de setup DB + migrations
├── .env                     # Variables sensibles (à créer)
└── app/                     # [déjà vu précédemment]
🔐 1. .env (à créer à la racine)
# Base de données MariaDB
DATABASE_URL=mysql+pymysql://sdn_user:securepass@db:3306/sdn_db

# JWT & sécurité
JWT_SECRET_KEY=supersecretkey_2025_sdn_api_v1
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Back directory (chemin relatif dans le conteneur)
BACK_DIR=/app/back

# FastAPI
APP_HOST=0.0.0.0
APP_PORT=8000
Important : Ne jamais committer ce fichier ! Ajoutez-le à .gitignore.

2. docker-compose.yml
version: '3.8'

services:
  db:
    image: mariadb:10.11
    container_name: sdn-mariadb
    restart: unless-stopped
    environment:
      MARIADB_ROOT_PASSWORD: rootpass
      MARIADB_DATABASE: sdn_db
      MARIADB_USER: sdn_user
      MARIADB_PASSWORD: securepass
    volumes:
      - ./init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
      - mariadb_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mariadb-admin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: sdn-api
    restart: unless-stopped
    env_file:
      - .env
    environment:
      # Override BACK_DIR pour pointer vers le dossier monté dans le conteneur
      - BACK_DIR=/app/back
    volumes:
      - ./back:/app/back:ro  # Lire-only (pas de modification des scripts métier)
      - ./app:/app/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "
        echo 'Waiting for DB...' &&
        sleep 5 &&
        alembic upgrade head || { echo 'Migration skipped (first run?)'; } &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000
      "

volumes:
  mariadb_data:
3. init-db.sh (script d’initialisation de la DB)
#!/bin/bash
set -e

echo "Creating database and user..."

mariadb -u root -p"$MARIADB_ROOT_PASSWORD" <<SQL
CREATE DATABASE IF NOT EXISTS sdn_db;
CREATE USER IF NOT EXISTS 'sdn_user'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';
GRANT ALL PRIVILEGES ON sdn_db.* TO 'sdn_user'@'%';
FLUSH PRIVILEGES;
SQL

echo "Database and user ready."
Rendre exécutable :

chmod +x init-db.sh
4. Dockerfile.api
# Build stage (pour installer les dépendances)
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.7.1

WORKDIR /app

# Install system deps for PyMySQL & netmiko
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project files
COPY . .

# Ensure back/ is readable (readonly via docker-compose)
RUN chmod -R a+r /app/back

# Expose port
EXPOSE 8000

# Entrypoint : lancer uvicorn après migration
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
💡 Note : On utilise un multi-stage build pour garder une image légère.

🚀 Lancement
1. Démarrer tout le stack
docker-compose up -d --build
2. Vérifier les logs
docker-compose logs -f api
# Attendre : "INFO:     Application startup complete."
3. Tester l’API
curl http://localhost:8000/
# → {"message":"Welcome to SDN Topology API"}
4. Créer un utilisateur admin (via /api/users)
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123", "is_admin": true}'
5. Se connecter
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)

echo $TOKEN
🧪 Bonus : Test complet de découverte
curl -X POST http://localhost:8000/api/discovery/start \
  -H "Content-Type: application/json" \
  -d '{
    "host": "192.168.1.2",
    "username": "admin",
    "password": "azeAZE123-",
    "device_type": "cisco_ios"
  }'