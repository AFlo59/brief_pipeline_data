from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.database import get_db, init_db, check_db_connection
from src.models import YellowTaxiTrip, ImportLog


# Création de l'application FastAPI
app = FastAPI(
    title="NYC Taxi Data Pipeline API",
    description="API pour l'analyse des données de taxis de New York",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/")
async def root():
    """
    Point d'entrée principal de l'API.
    
    Returns:
        dict: Message de bienvenue et informations sur l'API
    """
    return {
        "message": "NYC Taxi Data Pipeline API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de santé pour vérifier le statut de l'application.
    
    Returns:
        dict: Statut de l'application et de la base de données
    """
    db_status = check_db_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_status else "disconnected",
        "environment": os.getenv("APP_ENV", "development")
    }


@app.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """
    Récupère les statistiques générales de la base de données.
    
    Args:
        db: Session de base de données
        
    Returns:
        dict: Statistiques des trajets et imports
    """
    try:
        # Statistiques des trajets
        total_trips = db.query(YellowTaxiTrip).count()
        
        # Statistiques des imports
        total_imports = db.query(ImportLog).count()
        
        # Plage de dates
        date_range = db.query(
            func.min(YellowTaxiTrip.tpep_pickup_datetime),
            func.max(YellowTaxiTrip.tpep_dropoff_datetime)
        ).first()
        
        # Statistiques financières
        financial_stats = db.query(
            func.sum(YellowTaxiTrip.total_amount),
            func.avg(YellowTaxiTrip.trip_distance),
            func.avg(YellowTaxiTrip.passenger_count)
        ).first()
        
        return {
            "total_trips": total_trips,
            "total_imports": total_imports,
            "date_range": {
                "earliest_pickup": date_range[0].isoformat() if date_range[0] else None,
                "latest_dropoff": date_range[1].isoformat() if date_range[1] else None
            },
            "financial_stats": {
                "total_fare_amount": float(financial_stats[0] or 0),
                "avg_trip_distance": float(financial_stats[1] or 0),
                "avg_passenger_count": float(financial_stats[2] or 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")


@app.get("/trips")
async def get_trips(
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de trajets à retourner"),
    offset: int = Query(0, ge=0, description="Nombre de trajets à ignorer"),
    db: Session = Depends(get_db)
):
    """
    Récupère une liste paginée des trajets de taxi.
    
    Args:
        limit: Nombre maximum de trajets à retourner
        offset: Nombre de trajets à ignorer
        db: Session de base de données
        
    Returns:
        dict: Liste des trajets et métadonnées de pagination
    """
    try:
        # Compter le total pour la pagination
        total_count = db.query(YellowTaxiTrip).count()
        
        # Récupérer les trajets avec pagination
        trips = db.query(YellowTaxiTrip)\
            .order_by(desc(YellowTaxiTrip.tpep_pickup_datetime))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        return {
            "trips": [
                {
                    "id": trip.id,
                    "pickup_datetime": trip.tpep_pickup_datetime.isoformat() if trip.tpep_pickup_datetime else None,
                    "dropoff_datetime": trip.tpep_dropoff_datetime.isoformat() if trip.tpep_dropoff_datetime else None,
                    "passenger_count": trip.passenger_count,
                    "trip_distance": trip.trip_distance,
                    "fare_amount": trip.fare_amount,
                    "tip_amount": trip.tip_amount,
                    "total_amount": trip.total_amount,
                    "payment_type": trip.payment_type,
                    "pu_location_id": trip.pu_location_id,
                    "do_location_id": trip.do_location_id
                }
                for trip in trips
            ],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des trajets: {str(e)}")


@app.get("/trips/{trip_id}")
async def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """
    Récupère un trajet spécifique par son ID.
    
    Args:
        trip_id: ID du trajet à récupérer
        db: Session de base de données
        
    Returns:
        dict: Détails du trajet
    """
    trip = db.query(YellowTaxiTrip).filter(YellowTaxiTrip.id == trip_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trajet non trouvé")
    
    return {
        "id": trip.id,
        "vendor_id": trip.vendor_id,
        "pickup_datetime": trip.tpep_pickup_datetime.isoformat() if trip.tpep_pickup_datetime else None,
        "dropoff_datetime": trip.tpep_dropoff_datetime.isoformat() if trip.tpep_dropoff_datetime else None,
        "passenger_count": trip.passenger_count,
        "trip_distance": trip.trip_distance,
        "ratecode_id": trip.ratecode_id,
        "store_and_fwd_flag": trip.store_and_fwd_flag,
        "pu_location_id": trip.pu_location_id,
        "do_location_id": trip.do_location_id,
        "payment_type": trip.payment_type,
        "fare_amount": trip.fare_amount,
        "extra": trip.extra,
        "mta_tax": trip.mta_tax,
        "tip_amount": trip.tip_amount,
        "tolls_amount": trip.tolls_amount,
        "improvement_surcharge": trip.improvement_surcharge,
        "total_amount": trip.total_amount,
        "congestion_surcharge": trip.congestion_surcharge,
        "airport_fee": trip.airport_fee,
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
        "updated_at": trip.updated_at.isoformat() if trip.updated_at else None
    }


@app.get("/imports")
async def get_imports(db: Session = Depends(get_db)):
    """
    Récupère l'historique des imports de fichiers.
    
    Args:
        db: Session de base de données
        
    Returns:
        dict: Liste des imports effectués
    """
    try:
        imports = db.query(ImportLog)\
            .order_by(desc(ImportLog.import_date))\
            .all()
        
        return {
            "imports": [
                {
                    "file_name": imp.file_name,
                    "import_date": imp.import_date.isoformat() if imp.import_date else None,
                    "rows_imported": imp.rows_imported,
                    "file_size_bytes": imp.file_size_bytes,
                    "import_duration_seconds": imp.import_duration_seconds
                }
                for imp in imports
            ],
            "total_imports": len(imports)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des imports: {str(e)}")


@app.get("/analytics/daily")
async def get_daily_analytics(
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Récupère les statistiques quotidiennes des trajets.
    
    Args:
        start_date: Date de début pour le filtre
        end_date: Date de fin pour le filtre
        db: Session de base de données
        
    Returns:
        dict: Statistiques quotidiennes
    """
    try:
        query = db.query(
            func.date(YellowTaxiTrip.tpep_pickup_datetime).label('date'),
            func.count(YellowTaxiTrip.id).label('trip_count'),
            func.sum(YellowTaxiTrip.total_amount).label('total_fare'),
            func.avg(YellowTaxiTrip.trip_distance).label('avg_distance'),
            func.avg(YellowTaxiTrip.passenger_count).label('avg_passengers')
        ).group_by(func.date(YellowTaxiTrip.tpep_pickup_datetime))
        
        # Appliquer les filtres de date si fournis
        if start_date:
            query = query.filter(YellowTaxiTrip.tpep_pickup_datetime >= start_date)
        if end_date:
            query = query.filter(YellowTaxiTrip.tpep_pickup_datetime <= end_date)
        
        results = query.order_by(desc('date')).limit(30).all()
        
        return {
            "daily_stats": [
                {
                    "date": str(result.date),
                    "trip_count": result.trip_count,
                    "total_fare": float(result.total_fare or 0),
                    "avg_distance": float(result.avg_distance or 0),
                    "avg_passengers": float(result.avg_passengers or 0)
                }
                for result in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des statistiques quotidiennes: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Configuration pour le développement local
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
