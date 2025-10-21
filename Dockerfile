# Utiliser Python 3.12 slim comme image de base
FROM python:3.12-slim

# Définir les métadonnées de l'image
LABEL maintainer="AFlo59"
LABEL description="NYC Taxi Data Pipeline - FastAPI Application"
LABEL version="1.0.0"

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    # Compilateur C pour certaines dépendances Python
    gcc \
    g++ \
    # Client PostgreSQL pour les tests de connexion
    postgresql-client \
    # Outils de développement
    curl \
    # Nettoyage pour réduire la taille de l'image
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer un utilisateur non-root pour la sécurité
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copier le fichier des dépendances Python
COPY requirements.txt .

# Installer les dépendances Python
# Utiliser --no-cache-dir pour réduire la taille de l'image
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY src/ ./src/
COPY scripts/ ./scripts/

# Copier le fichier .env.example et le renommer en .env
COPY .env.example .env

# Créer le répertoire pour les données et donner les permissions
RUN mkdir -p /app/data/raw && \
    chown -R appuser:appuser /app

# Changer vers l'utilisateur non-root
USER appuser

# Exposer le port sur lequel l'application va écouter
EXPOSE 8000

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Commande de santé pour vérifier que l'application fonctionne
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande par défaut pour démarrer l'application
# Utiliser uvicorn avec des options optimisées pour la production
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
