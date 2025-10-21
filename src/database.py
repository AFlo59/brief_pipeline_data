from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuration de la base de données depuis les variables d'environnement
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "nyc_taxi")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Construction de l'URL de connexion PostgreSQL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Création du moteur SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Vérifie la connexion avant chaque requête
    pool_recycle=300,    # Recycle les connexions après 5 minutes
    echo=False           # Mettre à True pour voir les requêtes SQL
)

# Factory pour créer des sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles SQLAlchemy
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dépendance FastAPI pour obtenir une session de base de données.
    
    Cette fonction est utilisée comme dépendance dans les endpoints FastAPI
    pour obtenir une session de base de données. Elle s'assure que la session
    est fermée après utilisation.
    
    Yields:
        Session: Session SQLAlchemy active
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialise la base de données en créant toutes les tables définies.
    
    Cette fonction doit être appelée au démarrage de l'application pour
    s'assurer que toutes les tables existent dans la base de données.
    """
    # Import des modèles pour qu'ils soient enregistrés avec Base
    from src.models import YellowTaxiTrip, ImportLog  # noqa: F401
    
    # Création de toutes les tables
    Base.metadata.create_all(bind=engine)
    print(f"[INFO] Base de données initialisée: {POSTGRES_DB}")


def check_db_connection() -> bool:
    """
    Vérifie si la connexion à la base de données fonctionne.
    
    Returns:
        bool: True si la connexion fonctionne, False sinon
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERROR] Impossible de se connecter à la base de données: {e}")
        return False


if __name__ == "__main__":
    # Test de connexion
    if check_db_connection():
        print("[SUCCESS] Connexion à la base de données réussie")
        init_db()
    else:
        print("[ERROR] Échec de la connexion à la base de données")
