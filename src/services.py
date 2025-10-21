from __future__ import annotations

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from src.models import YellowTaxiTrip, ImportLog
from src.schemas import TaxiTripCreate, TaxiTripUpdate, Statistics


class TaxiTripService:
    """Service pour la gestion des trajets de taxi."""
    
    @staticmethod
    def get_trip(db: Session, trip_id: int) -> Optional[YellowTaxiTrip]:
        """
        Récupérer un trajet par ID.
        
        Args:
            db: Session de base de données
            trip_id: ID du trajet
            
        Returns:
            Le trajet ou None si non trouvé
        """
        return db.query(YellowTaxiTrip).filter(YellowTaxiTrip.id == trip_id).first()
    
    @staticmethod
    def get_trips(db: Session, skip: int = 0, limit: int = 100) -> Tuple[list[YellowTaxiTrip], int]:
        """
        Récupérer une liste de trajets avec pagination.
        
        Args:
            db: Session de base de données
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            
        Returns:
            Tuple (trips, total_count)
        """
        # Compter le total
        total = db.query(func.count(YellowTaxiTrip.id)).scalar()
        
        # Récupérer les trajets avec pagination
        trips = (
            db.query(YellowTaxiTrip)
            .order_by(YellowTaxiTrip.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return trips, total
    
    @staticmethod
    def create_trip(db: Session, trip: TaxiTripCreate) -> YellowTaxiTrip:
        """
        Créer un nouveau trajet.
        
        Args:
            db: Session de base de données
            trip: Données du trajet à créer
            
        Returns:
            Le trajet créé
        """
        db_trip = YellowTaxiTrip(**trip.model_dump())
        db.add(db_trip)
        db.commit()
        db.refresh(db_trip)
        return db_trip
    
    @staticmethod
    def update_trip(db: Session, trip_id: int, trip: TaxiTripUpdate) -> Optional[YellowTaxiTrip]:
        """
        Mettre à jour un trajet existant.
        
        Args:
            db: Session de base de données
            trip_id: ID du trajet à mettre à jour
            trip: Nouvelles données du trajet
            
        Returns:
            Le trajet mis à jour ou None si non trouvé
        """
        db_trip = db.query(YellowTaxiTrip).filter(YellowTaxiTrip.id == trip_id).first()
        if not db_trip:
            return None
        
        # Mettre à jour seulement les champs fournis
        update_data = trip.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_trip, field, value)
        
        db.commit()
        db.refresh(db_trip)
        return db_trip
    
    @staticmethod
    def delete_trip(db: Session, trip_id: int) -> bool:
        """
        Supprimer un trajet.
        
        Args:
            db: Session de base de données
            trip_id: ID du trajet à supprimer
            
        Returns:
            True si supprimé, False si non trouvé
        """
        db_trip = db.query(YellowTaxiTrip).filter(YellowTaxiTrip.id == trip_id).first()
        if not db_trip:
            return False
        
        db.delete(db_trip)
        db.commit()
        return True
    
    @staticmethod
    def get_statistics(db: Session) -> Statistics:
        """
        Calculer les statistiques des trajets.
        
        Args:
            db: Session de base de données
            
        Returns:
            Objet Statistics avec toutes les statistiques
        """
        # Nombre total de trajets
        total_trips = db.query(func.count(YellowTaxiTrip.id)).scalar()
        
        # Nombre de fichiers importés
        files_imported = db.query(func.count(ImportLog.file_name)).scalar()
        
        # Plage de dates
        date_result = db.query(
            func.min(YellowTaxiTrip.tpep_pickup_datetime),
            func.max(YellowTaxiTrip.tpep_dropoff_datetime)
        ).first()
        
        pickup_min = None
        dropoff_max = None
        if date_result and date_result[0]:
            pickup_min = date_result[0].isoformat()
            dropoff_max = date_result[1].isoformat()
        
        # Statistiques financières et de distance
        fare_stats = db.query(
            func.sum(YellowTaxiTrip.total_amount),
            func.avg(YellowTaxiTrip.trip_distance),
            func.avg(YellowTaxiTrip.fare_amount),
            func.avg(YellowTaxiTrip.tip_amount),
            func.avg(YellowTaxiTrip.passenger_count)
        ).first()
        
        total_fare_amount = float(fare_stats[0] or 0) if fare_stats[0] else 0.0
        avg_trip_distance = float(fare_stats[1] or 0) if fare_stats[1] else 0.0
        avg_fare_amount = float(fare_stats[2] or 0) if fare_stats[2] else None
        avg_tip_amount = float(fare_stats[3] or 0) if fare_stats[3] else None
        avg_passenger_count = float(fare_stats[4] or 0) if fare_stats[4] else None
        
        return Statistics(
            total_trips=total_trips,
            files_imported=files_imported,
            pickup_min=pickup_min,
            dropoff_max=dropoff_max,
            total_fare_amount=total_fare_amount,
            avg_trip_distance=avg_trip_distance,
            avg_fare_amount=avg_fare_amount,
            avg_tip_amount=avg_tip_amount,
            avg_passenger_count=avg_passenger_count
        )


class ImportLogService:
    """Service pour la gestion des logs d'import."""
    
    @staticmethod
    def get_import_logs(db: Session, skip: int = 0, limit: int = 100) -> Tuple[list[ImportLog], int]:
        """
        Récupérer les logs d'import avec pagination.
        
        Args:
            db: Session de base de données
            skip: Nombre d'éléments à ignorer
            limit: Nombre maximum d'éléments à retourner
            
        Returns:
            Tuple (logs, total_count)
        """
        # Compter le total
        total = db.query(func.count(ImportLog.file_name)).scalar()
        
        # Récupérer les logs avec pagination
        logs = (
            db.query(ImportLog)
            .order_by(ImportLog.import_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return logs, total
    
    @staticmethod
    def get_import_log(db: Session, file_name: str) -> Optional[ImportLog]:
        """
        Récupérer un log d'import par nom de fichier.
        
        Args:
            db: Session de base de données
            file_name: Nom du fichier
            
        Returns:
            Le log d'import ou None si non trouvé
        """
        return db.query(ImportLog).filter(ImportLog.file_name == file_name).first()
