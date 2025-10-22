from __future__ import annotations

import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.database import get_db, init_db, check_db_connection
from src.routes import router
from src.schemas import HealthResponse, ApiInfoResponse


# Création de l'application FastAPI
app = FastAPI(
    title="NYC Taxi Data Pipeline API",
    description="""
    API REST pour l'analyse des données de taxis de New York.
    
    Cette API permet de :
    - Consulter les données de trajets de taxi (CRUD complet)
    - Obtenir des statistiques détaillées
    - Gérer les imports de données depuis NYC Open Data
    - Exécuter la pipeline de données complète
    
    ## Architecture
    
    L'API suit une architecture MVC (Model-View-Controller) :
    - **Models** : Modèles SQLAlchemy pour la base de données
    - **Services** : Logique métier et accès aux données
    - **Routes** : Endpoints REST et validation des données
    
    ## Données
    
    Les données proviennent de NYC Open Data et incluent :
    - Trajets de taxi jaune de 2025
    - Informations détaillées (dates, montants, distances, etc.)
    - Import automatique avec déduplication
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure le router principal avec le préfixe /api/v1
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """
    Événement de démarrage de l'application.
    
    Initialise la base de données et vérifie la connexion.
    """
    print("[INFO] Démarrage de l'application NYC Taxi Data Pipeline")
    
    if check_db_connection():
        init_db()
        print("[SUCCESS] Base de données initialisée")
    else:
        print("[WARNING] Impossible de se connecter à la base de données")


@app.get("/", response_model=ApiInfoResponse, tags=["Info"])
def get_api_info():
    """
    Informations générales sur l'API.
    
    Retourne les informations de base sur l'API, sa version,
    et la liste des endpoints disponibles.
    """
    return ApiInfoResponse(
        name="NYC Taxi Data Pipeline API",
        description="API REST pour l'analyse des données de taxis de New York",
        version="1.0.0",
        documentation_url="/docs",
        endpoints=[
            "GET / - Informations API",
            "GET /health - Health check",
            "GET /api/v1/trips - Liste des trajets (paginée)",
            "GET /api/v1/trips/{id} - Détails d'un trajet",
            "POST /api/v1/trips - Créer un trajet",
            "PUT /api/v1/trips/{id} - Modifier un trajet",
            "DELETE /api/v1/trips/{id} - Supprimer un trajet",
            "GET /api/v1/statistics - Statistiques des trajets",
            "GET /api/v1/import-logs - Logs d'import",
            "POST /api/v1/pipeline/run - Exécuter la pipeline complète",
            "POST /api/v1/pipeline/download - Télécharger les données",
            "POST /api/v1/pipeline/import - Importer les données"
        ]
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Vérification de l'état de santé de l'API.
    
    Retourne le statut de l'API, la connexion à la base de données
    et d'autres informations de diagnostic.
    """
    # Vérifier la connexion à la base de données
    db_connected = check_db_connection()
    
    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        timestamp=datetime.now(),
        database_connected=db_connected,
        version="1.0.0"
    )


# Point d'entrée pour le développement
if __name__ == "__main__":
    import uvicorn
    
    # Configuration pour le développement
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )