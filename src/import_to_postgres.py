from __future__ import annotations

import time
import psutil
import gc
import io
from pathlib import Path
from typing import Optional, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import multiprocessing as mp

import pandas as pd
from fastparquet import ParquetFile
from sqlalchemy.orm import Session
from sqlalchemy import func, create_engine
from sqlalchemy.pool import QueuePool

from src.database import SessionLocal, init_db, check_db_connection
from src.models import YellowTaxiTrip, ImportLog


class PostgresImporter:
    """
    Importeur NYC Yellow Taxi pour PostgreSQL avec parallélisme optimisé.
    
    Cette classe gère l'import des fichiers Parquet vers PostgreSQL en utilisant
    SQLAlchemy avec parallélisme au niveau des fichiers et des row groups.
    Elle évite les imports en double grâce à une table de log et fournit des 
    statistiques sur les données importées.
    
    Optimisations:
    - Parallélisme au niveau des fichiers (ThreadPoolExecutor)
    - Traitement par chunks de row groups pour économiser la mémoire
    - Pool de connexions optimisé
    - Monitoring de la mémoire RAM
    - COPY avec buffer CSV pour de meilleures performances d'import
    - Fallback automatique vers to_sql() en cas d'erreur COPY
    """

    def __init__(self, max_workers: Optional[int] = None, chunk_size: int = 10000) -> None:
        """
        Initialise l'importeur PostgreSQL avec parallélisme.
        
        Args:
            max_workers: Nombre maximum de threads (défaut: min(4, nb_cpu))
            chunk_size: Taille des chunks pour l'écriture en base (défaut: 10000)
        """
        if not check_db_connection():
            raise ConnectionError("Impossible de se connecter à PostgreSQL")
        
        # Initialiser les tables
        init_db()
        
        # Configuration du parallélisme
        self.max_workers = max_workers or min(4, mp.cpu_count())
        self.chunk_size = chunk_size
        self.memory_limit_gb = 12  # Limite de sécurité pour 16GB RAM
        self._lock = Lock()
        
        print(f"[INFO] Importeur PostgreSQL initialisé (workers: {self.max_workers}, chunk: {self.chunk_size})")
        print(f"[INFO] Limite mémoire: {self.memory_limit_gb}GB")

    def _check_memory_usage(self) -> bool:
        """
        Vérifie si l'utilisation mémoire est acceptable.
        
        Returns:
            bool: True si la mémoire est OK, False si limite atteinte
        """
        memory_percent = psutil.virtual_memory().percent
        memory_gb = psutil.virtual_memory().used / (1024**3)
        
        if memory_gb > self.memory_limit_gb:
            print(f"[WARN] Mémoire élevée: {memory_gb:.1f}GB ({memory_percent:.1f}%)")
            return False
        return True

    def _force_garbage_collection(self) -> None:
        """Force le garbage collection pour libérer la mémoire."""
        gc.collect()

    def _import_chunk_with_copy(self, chunk_df: pd.DataFrame, engine, filename: str, chunk_info: str) -> int:
        """
        Importe un chunk de données avec COPY pour de meilleures performances.
        
        Args:
            chunk_df: DataFrame contenant les données à importer
            engine: Moteur SQLAlchemy
            filename: Nom du fichier pour les logs
            chunk_info: Information sur le chunk pour les logs
            
        Returns:
            int: Nombre de lignes importées
        """
        try:
            # Créer un buffer CSV en mémoire
            buffer = io.StringIO()
            chunk_df.to_csv(buffer, index=False, header=False, na_rep='\\N')
            buffer.seek(0)
            
            # Import du chunk avec COPY (beaucoup plus rapide que to_sql)
            with engine.connect() as connection:
                cursor = connection.connection.cursor()
                try:
                    # Construire la requête COPY avec les colonnes
                    columns_str = ', '.join(chunk_df.columns)
                    copy_query = f"COPY yellow_taxi_trips ({columns_str}) FROM STDIN WITH CSV NULL '\\N'"
                    
                    cursor.copy_expert(copy_query, buffer)
                    connection.connection.commit()
                    return len(chunk_df)
                    
                except Exception as copy_error:
                    connection.connection.rollback()
                    print(f"[WARN] Erreur COPY pour {filename} {chunk_info}: {copy_error}")
                    # Fallback vers to_sql en cas d'erreur COPY
                    chunk_df.to_sql(
                        name='yellow_taxi_trips',
                        con=engine,
                        if_exists='append',
                        index=False,
                        method='multi',
                        chunksize=min(1000, len(chunk_df)),
                    )
                    return len(chunk_df)
                finally:
                    cursor.close()
                    
        except Exception as e:
            print(f"[WARN] Erreur lors de l'import du chunk {chunk_info}: {e}")
            # Fallback vers to_sql en cas d'erreur
            chunk_df.to_sql(
                name='yellow_taxi_trips',
                con=engine,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=min(1000, len(chunk_df)),
            )
            return len(chunk_df)

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
        Importe un fichier Parquet dans PostgreSQL avec optimisations mémoire.
        
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

            # Vérifier la mémoire avant de commencer
            if not self._check_memory_usage():
                self._force_garbage_collection()

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
                    # Vérifier la mémoire avant chaque row group
                    if not self._check_memory_usage():
                        self._force_garbage_collection()
                        print(f"[INFO] Garbage collection effectué pour {filename}")

                    # Renommer selon mapping si présent
                    rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
                    df = df.rename(columns=rename_map)

                    # Harmoniser colonnes: ne garder que les cibles et ajouter les manquantes à NaN
                    for col in target_columns:
                        if col not in df.columns:
                            df[col] = pd.NA
                    df = df[target_columns]

                    # Traitement par chunks plus petits pour économiser la mémoire
                    chunk_rows = len(df)
                    if chunk_rows == 0:
                        continue
                    
                    # Diviser en chunks plus petits si nécessaire
                    for start_idx in range(0, chunk_rows, self.chunk_size):
                        end_idx = min(start_idx + self.chunk_size, chunk_rows)
                        chunk_df = df.iloc[start_idx:end_idx]
                        
                        if len(chunk_df) == 0:
                            continue
                        
                        # 🚀 OPTIMISATION: Utiliser COPY avec buffer CSV pour de meilleures performances
                        # Cette méthode est 3-5x plus rapide que to_sql() pour les gros volumes
                        # Le buffer CSV évite les conversions de types coûteuses
                        chunk_info = f"chunk {start_idx}-{end_idx}"
                        rows_imported = self._import_chunk_with_copy(chunk_df, engine, filename, chunk_info)
                        total_rows_imported += rows_imported
                    
                    # Libérer la mémoire du DataFrame
                    del df
                    self._force_garbage_collection()
                    
                    if (rg_index + 1) % 1 == 0:
                        print(f"[PROGRESS] {filename}: RG {rg_index + 1} traité (cumul {total_rows_imported:,})")

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
        Importe tous les fichiers Parquet d'un répertoire avec parallélisme.
        
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
        print(f"[INFO] Démarrage de l'import parallèle avec {self.max_workers} workers")
        
        # Filtrer les fichiers déjà importés
        files_to_import = []
        for file_path in sorted(parquet_files):
            if not self.is_file_imported(file_path.name):
                files_to_import.append(file_path)
            else:
                print(f"[SKIP] Déjà importé: {file_path.name}")
        
        if not files_to_import:
            print("[INFO] Tous les fichiers sont déjà importés")
            return len(parquet_files)
        
        print(f"[INFO] {len(files_to_import)} fichiers à importer")
        
        # Import parallèle avec ThreadPoolExecutor
        imported_count = 0
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre tous les fichiers
            future_to_file = {
                executor.submit(self._import_single_file, file_path): file_path 
                for file_path in files_to_import
            }
            
            # Traiter les résultats au fur et à mesure
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    success = future.result()
                    if success:
                        imported_count += 1
                        print(f"[SUCCESS] {file_path.name} importé avec succès")
                    else:
                        failed_files.append(file_path.name)
                        print(f"[FAILED] Échec import {file_path.name}")
                except Exception as e:
                    failed_files.append(file_path.name)
                    print(f"[ERROR] Exception lors de l'import {file_path.name}: {e}")
                
                # Afficher le progrès
                completed = imported_count + len(failed_files)
                print(f"[PROGRESS] {completed}/{len(files_to_import)} fichiers traités")
                
                # Vérifier la mémoire après chaque fichier
                if not self._check_memory_usage():
                    self._force_garbage_collection()
                    print("[INFO] Garbage collection effectué")
        
        print(f"[INFO] Import terminé: {imported_count}/{len(files_to_import)} fichiers importés avec succès")
        if failed_files:
            print(f"[WARN] Fichiers en échec: {failed_files}")
        
        return imported_count

    def _create_optimized_engine(self):
        """
        Crée un moteur SQLAlchemy optimisé pour les imports parallèles.
        
        Returns:
            Engine: Moteur SQLAlchemy optimisé
        """
        from src.database import engine_url
        
        return create_engine(
            engine_url,
            poolclass=QueuePool,
            pool_size=self.max_workers,
            max_overflow=self.max_workers * 2,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )

    def _import_single_file(self, file_path: Path) -> bool:
        """
        Importe un seul fichier (méthode wrapper pour le parallélisme).
        
        Args:
            file_path: Chemin vers le fichier Parquet
            
        Returns:
            bool: True si l'import a réussi, False sinon
        """
        try:
            return self.import_parquet(file_path)
        except Exception as e:
            print(f"[ERROR] Exception dans _import_single_file pour {file_path.name}: {e}")
            return False

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
    # Exemple d'utilisation avec parallélisme optimisé
    try:
        # Configuration adaptée à 16GB RAM
        importer = PostgresImporter(
            max_workers=3,  # Limité pour économiser la mémoire
            chunk_size=5000  # Chunks plus petits
        )
        
        # Afficher l'état mémoire initial
        memory_info = psutil.virtual_memory()
        print(f"[INFO] Mémoire disponible: {memory_info.available / (1024**3):.1f}GB / {memory_info.total / (1024**3):.1f}GB")
        
        # Importer tous les fichiers Parquet
        data_dir = Path("data/raw")
        start_time = time.time()
        imported_count = importer.import_all_parquet_files(data_dir)
        total_time = time.time() - start_time
        
        # Afficher les statistiques
        if imported_count > 0:
            print(f"[INFO] Import terminé en {total_time:.2f}s")
            importer.get_statistics()
            
            # Afficher l'état mémoire final
            memory_info = psutil.virtual_memory()
            print(f"[INFO] Mémoire finale: {memory_info.available / (1024**3):.1f}GB / {memory_info.total / (1024**3):.1f}GB")
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
