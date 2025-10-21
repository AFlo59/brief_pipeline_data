from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.services import TaxiTripService, ImportLogService
from src.schemas import (
    TaxiTrip, TaxiTripCreate, TaxiTripUpdate, TaxiTripList,
    Statistics, ImportLog, PipelineResponse, HealthResponse, ApiInfoResponse
)
from src.import_to_postgres import PostgresImporter
from src.download_data import NYCTaxiDataDownloader
from src.database import check_db_connection

# Créer le router principal
router = APIRouter()


# ============================================================================
# ENDPOINTS CRUD POUR LES TRAJETS DE TAXI
# ============================================================================

@router.get("/trips", response_model=TaxiTripList, tags=["Trips"])
def get_trips(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des trajets de taxi avec pagination.
    
    - **skip**: Nombre d'éléments à ignorer (défaut: 0)
    - **limit**: Nombre maximum d'éléments à retourner (défaut: 100, max: 1000)
    """
    if limit > 1000:
        limit = 1000
    
    trips, total = TaxiTripService.get_trips(db, skip=skip, limit=limit)
    
    return TaxiTripList(
        total=total,
        trips=trips,
        skip=skip,
        limit=limit
    )


@router.get("/trips/{trip_id}", response_model=TaxiTrip, tags=["Trips"])
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    """
    Récupérer un trajet de taxi par son ID.
    
    - **trip_id**: ID du trajet à récupérer
    """
    trip = TaxiTripService.get_trip(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trajet avec l'ID {trip_id} non trouvé"
        )
    return trip


@router.post("/trips", response_model=TaxiTrip, status_code=status.HTTP_201_CREATED, tags=["Trips"])
def create_trip(trip: TaxiTripCreate, db: Session = Depends(get_db)):
    """
    Créer un nouveau trajet de taxi.
    
    - **trip**: Données du trajet à créer
    """
    return TaxiTripService.create_trip(db, trip)


@router.put("/trips/{trip_id}", response_model=TaxiTrip, tags=["Trips"])
def update_trip(trip_id: int, trip: TaxiTripUpdate, db: Session = Depends(get_db)):
    """
    Mettre à jour un trajet de taxi existant.
    
    - **trip_id**: ID du trajet à mettre à jour
    - **trip**: Nouvelles données du trajet
    """
    updated_trip = TaxiTripService.update_trip(db, trip_id, trip)
    if not updated_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trajet avec l'ID {trip_id} non trouvé"
        )
    return updated_trip


@router.delete("/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Trips"])
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    """
    Supprimer un trajet de taxi.
    
    - **trip_id**: ID du trajet à supprimer
    """
    success = TaxiTripService.delete_trip(db, trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trajet avec l'ID {trip_id} non trouvé"
        )


# ============================================================================
# ENDPOINTS POUR LES STATISTIQUES
# ============================================================================

@router.get("/statistics", response_model=Statistics, tags=["Statistics"])
def get_statistics(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques des trajets de taxi.
    
    Retourne des statistiques complètes incluant :
    - Nombre total de trajets
    - Nombre de fichiers importés
    - Plage de dates (min/max)
    - Montants totaux et moyens
    - Distances moyennes
    """
    return TaxiTripService.get_statistics(db)


# ============================================================================
# ENDPOINTS POUR LES LOGS D'IMPORT
# ============================================================================

@router.get("/import-logs", response_model=List[ImportLog], tags=["Import Logs"])
def get_import_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des logs d'import avec pagination.
    
    - **skip**: Nombre d'éléments à ignorer (défaut: 0)
    - **limit**: Nombre maximum d'éléments à retourner (défaut: 100)
    """
    logs, _ = ImportLogService.get_import_logs(db, skip=skip, limit=limit)
    return logs


@router.get("/import-logs/{file_name}", response_model=ImportLog, tags=["Import Logs"])
def get_import_log(file_name: str, db: Session = Depends(get_db)):
    """
    Récupérer un log d'import par nom de fichier.
    
    - **file_name**: Nom du fichier importé
    """
    log = ImportLogService.get_import_log(db, file_name)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log d'import pour le fichier '{file_name}' non trouvé"
        )
    return log


# ============================================================================
# ENDPOINTS POUR LA PIPELINE
# ============================================================================

@router.post("/pipeline/run", response_model=PipelineResponse, tags=["Pipeline"])
def run_pipeline(db: Session = Depends(get_db)):
    """
    Exécuter la pipeline complète : téléchargement + import des données.
    
    Cette opération peut prendre du temps selon la quantité de données.
    Les fichiers déjà téléchargés/importés seront ignorés.
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    errors = []
    
    try:
        # Vérifier la connexion à la base de données
        if not check_db_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de données non disponible"
            )
        
        # Étape 1: Téléchargement des données
        print("[PIPELINE] Début du téléchargement des données...")
        downloader = NYCTaxiDataDownloader()
        downloader.download_all_available()
        
        # Étape 2: Import des données
        print("[PIPELINE] Début de l'import des données...")
        importer = PostgresImporter()
        data_dir_path = importer.raw_data_dir
        imported_files = importer.import_all_parquet_files(data_dir_path)
        
        # Calculer la durée
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=True,
            message=f"Pipeline exécutée avec succès. {imported_files} fichier(s) traité(s).",
            files_processed=imported_files,
            duration_seconds=round(duration, 2)
        )
        
    except Exception as e:
        errors.append(str(e))
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=False,
            message=f"Erreur lors de l'exécution de la pipeline: {str(e)}",
            duration_seconds=round(duration, 2),
            errors=errors
        )


@router.post("/pipeline/download", response_model=PipelineResponse, tags=["Pipeline"])
def download_data():
    """
    Télécharger uniquement les données Parquet (sans import).
    
    Cette opération télécharge les fichiers depuis NYC Open Data
    vers le répertoire local data/raw.
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    errors = []
    
    try:
        print("[PIPELINE] Début du téléchargement des données...")
        downloader = NYCTaxiDataDownloader()
        downloader.download_all_available()
        
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=True,
            message="Téléchargement des données terminé avec succès.",
            duration_seconds=round(duration, 2)
        )
        
    except Exception as e:
        errors.append(str(e))
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=False,
            message=f"Erreur lors du téléchargement: {str(e)}",
            duration_seconds=round(duration, 2),
            errors=errors
        )


@router.post("/pipeline/import", response_model=PipelineResponse, tags=["Pipeline"])
def import_data(db: Session = Depends(get_db)):
    """
    Importer uniquement les données Parquet existantes (sans téléchargement).
    
    Cette opération importe les fichiers Parquet du répertoire data/raw
    vers la base de données PostgreSQL.
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    errors = []
    
    try:
        # Vérifier la connexion à la base de données
        if not check_db_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de données non disponible"
            )
        
        print("[PIPELINE] Début de l'import des données...")
        importer = PostgresImporter()
        data_dir_path = importer.raw_data_dir
        imported_files = importer.import_all_parquet_files(data_dir_path)
        
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=True,
            message=f"Import des données terminé avec succès. {imported_files} fichier(s) traité(s).",
            files_processed=imported_files,
            duration_seconds=round(duration, 2)
        )
        
    except Exception as e:
        errors.append(str(e))
        duration = time.time() - start_time
        
        return PipelineResponse(
            success=False,
            message=f"Erreur lors de l'import: {str(e)}",
            duration_seconds=round(duration, 2),
            errors=errors
        )
