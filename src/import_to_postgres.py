from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd
from fastparquet import ParquetFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import SessionLocal, init_db, check_db_connection
from src.models import YellowTaxiTrip, ImportLog


class PostgresImporter:
    """
    Importeur NYC Yellow Taxi pour PostgreSQL.
    
    Cette classe gère l'import des fichiers Parquet vers PostgreSQL en utilisant
    SQLAlchemy. Elle évite les imports en double grâce à une table de log
    et fournit des statistiques sur les données importées.
    """

    def __init__(self) -> None:
        """
        Initialise l'importeur PostgreSQL.
        
        Vérifie la connexion à la base de données et initialise les tables
        si nécessaire.
        """
        if not check_db_connection():
            raise ConnectionError("Impossible de se connecter à PostgreSQL")
        
        # Initialiser les tables
        init_db()
        print("[INFO] Importeur PostgreSQL initialisé")

    def is_file_imported(self, filename: str) -> bool:
        """
        Vérifie si un fichier a déjà été importé.
        
        Args:
            filename: Nom du fichier à vérifier
            
        Returns:
            bool: True si le fichier est déjà importé, False sinon
        """
        with SessionLocal() as db:
            result = db.query(ImportLog).filter(ImportLog.file_name == filename).first()
            return result is not None

    def import_parquet(self, file_path: Path) -> bool:
        """
        Importe un fichier Parquet dans PostgreSQL.
        
        Args:
            file_path: Chemin vers le fichier Parquet
            
        Returns:
            bool: True si l'import a réussi, False sinon
        """
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"[WARN] Fichier introuvable: {file_path}")
            return False

        filename = file_path.name
        if self.is_file_imported(filename):
            print(f"[SKIP] Déjà importé: {filename}")
            return True

        try:
            start_time = time.time()
            print(f"[INFO] Lecture du fichier: {filename}")

            # Prépare mapping insensible à la casse similaire à la logique DuckDB
            column_mapping = {
                'VendorID': 'vendor_id',
                'tpep_pickup_datetime': 'tpep_pickup_datetime',
                'tpep_dropoff_datetime': 'tpep_dropoff_datetime',
                'passenger_count': 'passenger_count',
                'trip_distance': 'trip_distance',
                'RatecodeID': 'ratecode_id',
                'store_and_fwd_flag': 'store_and_fwd_flag',
                'PULocationID': 'pu_location_id',
                'DOLocationID': 'do_location_id',
                'payment_type': 'payment_type',
                'fare_amount': 'fare_amount',
                'extra': 'extra',
                'mta_tax': 'mta_tax',
                'tip_amount': 'tip_amount',
                'tolls_amount': 'tolls_amount',
                'improvement_surcharge': 'improvement_surcharge',
                'total_amount': 'total_amount',
                'congestion_surcharge': 'congestion_surcharge',
                'Airport_fee': 'airport_fee'
            }

            # Colonnes cibles de la table (on n'impose pas id/created_at/updated_at)
            target_columns = [
                'vendor_id', 'tpep_pickup_datetime', 'tpep_dropoff_datetime', 'passenger_count',
                'trip_distance', 'ratecode_id', 'store_and_fwd_flag', 'pu_location_id',
                'do_location_id', 'payment_type', 'fare_amount', 'extra', 'mta_tax',
                'tip_amount', 'tolls_amount', 'improvement_surcharge', 'total_amount',
                'congestion_surcharge', 'airport_fee'
            ]

            # Lecture par groupes de lignes pour éviter de charger tout en mémoire
            pf = ParquetFile(str(file_path))
            total_rows_imported = 0

            with SessionLocal() as db:
                engine = db.bind
                for rg_index, df in enumerate(pf.iter_row_groups()):
                    # Renommer selon mapping si présent
                    rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
                    df = df.rename(columns=rename_map)

                    # Harmoniser colonnes: ne garder que les cibles et ajouter les manquantes à NaN
                    for col in target_columns:
                        if col not in df.columns:
                            df[col] = pd.NA
                    df = df[target_columns]

                    # Ecrire en base par chunks
                    chunk_rows = len(df)
                    if chunk_rows == 0:
                        continue
                    df.to_sql(
                        name='yellow_taxi_trips',
                        con=engine,
                        if_exists='append',
                        index=False,
                        method='multi',
                        chunksize=50000,
                    )
                    total_rows_imported += chunk_rows
                    if (rg_index + 1) % 1 == 0:
                        print(f"[PROGRESS] {filename}: +{chunk_rows} lignes (cumul {total_rows_imported:,})")

                # Enregistrer l'import si au moins 1 ligne écrite
                import_log = ImportLog(
                    file_name=filename,
                    rows_imported=total_rows_imported,
                    file_size_bytes=file_path.stat().st_size,
                    import_duration_seconds=time.time() - start_time,
                )
                db.add(import_log)
                db.commit()

            print(f"[OK] {filename} importé ({total_rows_imported:,} lignes en {time.time() - start_time:.2f}s)")
            return True

        except Exception as e:
            print(f"[ERROR] Échec import {filename}: {e}")
            return False

    def import_all_parquet_files(self, data_dir: Path) -> int:
        """
        Importe tous les fichiers Parquet d'un répertoire.
        
        Args:
            data_dir: Répertoire contenant les fichiers Parquet
            
        Returns:
            int: Nombre de fichiers importés avec succès
        """
        data_dir = Path(data_dir)
        if not data_dir.exists():
            print(f"[WARN] Dossier introuvable: {data_dir}")
            return 0

        parquet_files = list(data_dir.glob("*.parquet"))
        if not parquet_files:
            print(f"[WARN] Aucun fichier Parquet trouvé dans: {data_dir}")
            return 0

        print(f"[INFO] {len(parquet_files)} fichiers Parquet trouvés")
        
        imported_count = 0
        for file_path in sorted(parquet_files):
            if self.import_parquet(file_path):
                imported_count += 1
        
        print(f"[INFO] Fichiers importés: {imported_count}/{len(parquet_files)}")
        return imported_count

    def get_statistics(self) -> dict:
        """
        Récupère les statistiques de la base de données.
        
        Returns:
            dict: Dictionnaire contenant les statistiques
        """
        stats = {
            "total_trips": 0,
            "files_imported": 0,
            "pickup_min": None,
            "dropoff_max": None,
            "total_fare_amount": 0.0,
            "avg_trip_distance": 0.0,
        }

        with SessionLocal() as db:
            # Total des trajets
            stats["total_trips"] = db.query(YellowTaxiTrip).count()
            
            # Fichiers importés
            stats["files_imported"] = db.query(ImportLog).count()
            
            # Plage de dates
            result = db.query(
                func.min(YellowTaxiTrip.tpep_pickup_datetime),
                func.max(YellowTaxiTrip.tpep_dropoff_datetime)
            ).first()
            
            if result and result[0]:
                stats["pickup_min"] = result[0].isoformat()
                stats["dropoff_max"] = result[1].isoformat()
            
            # Statistiques financières
            fare_stats = db.query(
                func.sum(YellowTaxiTrip.total_amount),
                func.avg(YellowTaxiTrip.trip_distance)
            ).first()
            
            if fare_stats:
                stats["total_fare_amount"] = float(fare_stats[0] or 0)
                stats["avg_trip_distance"] = float(fare_stats[1] or 0)

        # Affichage des statistiques
        print("=== STATISTIQUES POSTGRESQL ===")
        print(f"Total trips           : {stats['total_trips']:,}")
        print(f"Fichiers importés     : {stats['files_imported']}")
        print(f"Pickup min            : {stats['pickup_min']}")
        print(f"Dropoff max           : {stats['dropoff_max']}")
        print(f"Total fare amount     : ${stats['total_fare_amount']:,.2f}")
        print(f"Avg trip distance     : {stats['avg_trip_distance']:.2f} miles")
        print("===============================")
        
        return stats


if __name__ == "__main__":
    # Exemple d'utilisation
    try:
        importer = PostgresImporter()
        
        # Importer tous les fichiers Parquet
        data_dir = Path("data/raw")
        imported_count = importer.import_all_parquet_files(data_dir)
        
        # Afficher les statistiques
        if imported_count > 0:
            importer.get_statistics()
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'import: {e}")
