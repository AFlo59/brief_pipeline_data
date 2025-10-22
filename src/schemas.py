from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class TaxiTripBase(BaseModel):
    """Schéma de base pour les trajets de taxi avec tous les champs optionnels."""
    
    vendor_id: Optional[int] = None
    tpep_pickup_datetime: Optional[datetime] = None
    tpep_dropoff_datetime: Optional[datetime] = None
    passenger_count: Optional[float] = None
    trip_distance: Optional[float] = None
    ratecode_id: Optional[float] = None
    store_and_fwd_flag: Optional[str] = None
    pu_location_id: Optional[int] = None
    do_location_id: Optional[int] = None
    payment_type: Optional[int] = None
    fare_amount: Optional[float] = None
    extra: Optional[float] = None
    mta_tax: Optional[float] = None
    tip_amount: Optional[float] = None
    tolls_amount: Optional[float] = None
    improvement_surcharge: Optional[float] = None
    total_amount: Optional[float] = None
    congestion_surcharge: Optional[float] = None
    airport_fee: Optional[float] = None


class TaxiTripCreate(TaxiTripBase):
    """Schéma pour la création d'un trajet de taxi."""
    pass


class TaxiTripUpdate(TaxiTripBase):
    """Schéma pour la mise à jour d'un trajet de taxi."""
    pass


class TaxiTrip(TaxiTripBase):
    """Schéma pour la réponse d'un trajet de taxi avec l'ID."""
    
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaxiTripList(BaseModel):
    """Schéma pour la liste paginée des trajets de taxi."""
    
    total: int
    trips: List[TaxiTrip]
    skip: int
    limit: int


class Statistics(BaseModel):
    """Schéma pour les statistiques des trajets de taxi."""
    
    total_trips: int
    files_imported: int
    pickup_min: Optional[str] = None
    dropoff_max: Optional[str] = None
    total_fare_amount: float
    avg_trip_distance: float
    avg_fare_amount: Optional[float] = None
    avg_tip_amount: Optional[float] = None
    avg_passenger_count: Optional[float] = None


class ImportLogBase(BaseModel):
    """Schéma de base pour les logs d'import."""
    
    file_name: str
    rows_imported: int
    file_size_bytes: Optional[int] = None
    import_duration_seconds: Optional[float] = None


class ImportLog(ImportLogBase):
    """Schéma pour la réponse d'un log d'import."""
    
    import_date: datetime
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class PipelineResponse(BaseModel):
    """Schéma pour les réponses de la pipeline."""
    
    success: bool
    message: str
    files_processed: Optional[int] = None
    rows_imported: Optional[int] = None
    duration_seconds: Optional[float] = None
    errors: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Schéma pour la réponse de health check."""
    
    status: str
    timestamp: datetime
    database_connected: bool
    version: str = "1.0.0"


class ApiInfoResponse(BaseModel):
    """Schéma pour les informations de l'API."""
    
    name: str
    description: str
    version: str
    documentation_url: str
    endpoints: List[str]
