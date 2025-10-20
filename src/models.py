from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Float, BigInteger
from sqlalchemy.sql import func

from src.database import Base


class YellowTaxiTrip(Base):
    """
    Modèle SQLAlchemy pour les trajets de taxi jaune NYC.
    
    Cette table stocke les données brutes des trajets de taxi téléchargées
    depuis NYC Open Data. Les colonnes correspondent exactement au schéma
    des fichiers Parquet fournis par la TLC.
    """
    __tablename__ = "yellow_taxi_trips"

    # Clé primaire auto-incrémentée
    id = Column(Integer, primary_key=True, index=True)
    
    # Données du trajet
    vendor_id = Column(Integer, nullable=True, comment="Identifiant du fournisseur")
    tpep_pickup_datetime = Column(DateTime, nullable=True, comment="Date/heure de prise en charge")
    tpep_dropoff_datetime = Column(DateTime, nullable=True, comment="Date/heure de dépose")
    passenger_count = Column(Float, nullable=True, comment="Nombre de passagers")
    trip_distance = Column(Float, nullable=True, comment="Distance du trajet (miles)")
    ratecode_id = Column(Float, nullable=True, comment="Code de tarification")
    store_and_fwd_flag = Column(String(1), nullable=True, comment="Flag stockage et transfert")
    pu_location_id = Column(BigInteger, nullable=True, comment="ID zone de prise en charge")
    do_location_id = Column(BigInteger, nullable=True, comment="ID zone de dépose")
    payment_type = Column(BigInteger, nullable=True, comment="Type de paiement")
    fare_amount = Column(Float, nullable=True, comment="Montant du tarif")
    extra = Column(Float, nullable=True, comment="Supplément")
    mta_tax = Column(Float, nullable=True, comment="Taxe MTA")
    tip_amount = Column(Float, nullable=True, comment="Montant du pourboire")
    tolls_amount = Column(Float, nullable=True, comment="Montant des péages")
    improvement_surcharge = Column(Float, nullable=True, comment="Supplément d'amélioration")
    total_amount = Column(Float, nullable=True, comment="Montant total")
    congestion_surcharge = Column(Float, nullable=True, comment="Supplément d'embouteillage")
    airport_fee = Column(Float, nullable=True, comment="Frais d'aéroport")
    
    # Métadonnées
    created_at = Column(DateTime, default=func.now(), comment="Date de création de l'enregistrement")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="Date de dernière mise à jour")

    def __repr__(self) -> str:
        return f"<YellowTaxiTrip(id={self.id}, pickup={self.tpep_pickup_datetime}, amount={self.total_amount})>"


class ImportLog(Base):
    """
    Modèle SQLAlchemy pour le journal des imports.
    
    Cette table track les fichiers Parquet qui ont été importés dans la base
    de données, évitant ainsi les imports en double.
    """
    __tablename__ = "import_log"

    # Clé primaire basée sur le nom du fichier
    file_name = Column(String(255), primary_key=True, comment="Nom du fichier importé")
    
    # Métadonnées de l'import
    import_date = Column(DateTime, default=func.now(), comment="Date/heure de l'import")
    rows_imported = Column(BigInteger, nullable=False, comment="Nombre de lignes importées")
    
    # Informations supplémentaires
    file_size_bytes = Column(BigInteger, nullable=True, comment="Taille du fichier en bytes")
    import_duration_seconds = Column(Float, nullable=True, comment="Durée de l'import en secondes")
    
    # Métadonnées
    created_at = Column(DateTime, default=func.now(), comment="Date de création de l'enregistrement")

    def __repr__(self) -> str:
        return f"<ImportLog(file={self.file_name}, rows={self.rows_imported}, date={self.import_date})>"
