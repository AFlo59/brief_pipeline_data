"""
Data Cleaner for NYC Taxi Data Pipeline

This module provides data cleaning functionality for the NYC taxi dataset.
It extracts data from PostgreSQL, analyzes and cleans it, then saves the
cleaned data to MongoDB.

Author: AFlo59
Version: 1.0.0
"""

from __future__ import annotations

import os
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import gc

from sqlalchemy import create_engine, text
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Classe pour le nettoyage des données NYC Taxi.
    
    Cette classe gère l'extraction des données depuis PostgreSQL,
    l'analyse et le nettoyage des données, puis la sauvegarde
    dans MongoDB.
    """

    def __init__(self, chunk_size: int = 50000) -> None:
        """
        Initialise le nettoyeur de données avec les connexions aux bases de données.
        
        Args:
            chunk_size: Taille des chunks pour le traitement par lots (défaut: 50000)
        """
        self.chunk_size = chunk_size
        self.postgres_engine = self._get_postgres_engine()
        self.mongo_client = self._get_mongo_client()
        self.mongo_db = self.mongo_client[os.getenv("MONGO_DB", "nyc_taxi_clean")]
        self.cleaned_trips_collection = self.mongo_db["cleaned_trips"]
        
        logger.info(f"DataCleaner initialisé avec succès (chunk_size: {chunk_size:,})")

    def _get_postgres_engine(self):
        """
        Crée et retourne le moteur SQLAlchemy pour PostgreSQL.
        
        Returns:
            Engine: Moteur SQLAlchemy configuré
        """
        # Configuration PostgreSQL depuis les variables d'environnement
        postgres_user = os.getenv("POSTGRES_USER", "postgres")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        postgres_db = os.getenv("POSTGRES_DB", "nyc_taxi")
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        
        # Construction de l'URL de connexion
        database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        
        # Création du moteur avec configuration optimisée
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
            pool_size=5,  # Réduire la taille du pool
            max_overflow=10
        )
        
        logger.info(f"Connexion PostgreSQL configurée: {postgres_host}:{postgres_port}/{postgres_db}")
        return engine

    def _get_mongo_client(self):
        """
        Crée et retourne le client MongoDB.
        
        Returns:
            MongoClient: Client MongoDB configuré
        """
        # Configuration MongoDB depuis les variables d'environnement
        mongo_user = os.getenv("MONGO_USER", "admin")
        mongo_password = os.getenv("MONGO_PASSWORD", "admin")
        mongo_host = os.getenv("MONGO_HOST", "mongodb")
        mongo_port = os.getenv("MONGO_PORT", "27017")
        mongo_db = os.getenv("MONGO_DB", "nyc_taxi_clean")
        
        # Construction de l'URL de connexion MongoDB
        mongo_url = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/"
        
        try:
            client = MongoClient(
                mongo_url, 
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,  # Limiter le pool de connexions
                minPoolSize=1
            )
            # Test de connexion
            client.admin.command('ping')
            logger.info(f"Connexion MongoDB configurée: {mongo_host}:{mongo_port}/{mongo_db}")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Impossible de se connecter à MongoDB: {e}")
            raise

    def get_total_count(self) -> int:
        """
        Obtient le nombre total de lignes dans la table PostgreSQL.
        
        Returns:
            int: Nombre total de lignes
        """
        try:
            with self.postgres_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM yellow_taxi_trips"))
                count = result.scalar()
                logger.info(f"📊 Total des lignes à traiter: {count:,}")
                return count
        except Exception as e:
            logger.error(f"Erreur lors du comptage des lignes: {e}")
            raise

    def load_data_chunk(self, offset: int, limit: int) -> pd.DataFrame:
        """
        Charge un chunk de données depuis PostgreSQL.
        
        Args:
            offset: Décalage pour la pagination
            limit: Nombre de lignes à charger
            
        Returns:
            pd.DataFrame: DataFrame contenant le chunk de données
        """
        try:
            # Requête SQL pour récupérer un chunk de données
            query = f"""
            SELECT 
                id,
                vendor_id,
                tpep_pickup_datetime,
                tpep_dropoff_datetime,
                passenger_count,
                trip_distance,
                ratecode_id,
                store_and_fwd_flag,
                pu_location_id,
                do_location_id,
                payment_type,
                fare_amount,
                extra,
                mta_tax,
                tip_amount,
                tolls_amount,
                improvement_surcharge,
                total_amount,
                congestion_surcharge,
                airport_fee
            FROM yellow_taxi_trips
            ORDER BY id
            LIMIT {limit} OFFSET {offset}
            """
            
            # Chargement des données avec pandas
            df = pd.read_sql(query, self.postgres_engine)
            
            logger.info(f"✅ Chunk chargé: {len(df):,} lignes (offset: {offset:,})")
            return df
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du chunk: {e}")
            raise

    def analyze_data_chunk(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse un chunk de données pour détecter les anomalies.
        
        Args:
            df: DataFrame contenant les données à analyser
            
        Returns:
            Dict: Dictionnaire contenant les statistiques d'analyse
        """
        analysis = {
            "total_rows": len(df),
            "negative_values": {},
            "null_values": {},
            "outliers": {}
        }
        
        # Colonnes à analyser pour les valeurs négatives
        negative_columns = [
            'passenger_count', 'trip_distance', 'fare_amount', 
            'tip_amount', 'tolls_amount', 'total_amount'
        ]
        
        # Détection des valeurs négatives
        for col in negative_columns:
            if col in df.columns:
                negative_count = (df[col] < 0).sum()
                analysis["negative_values"][col] = int(negative_count)
        
        # Détection des valeurs nulles
        for col in df.columns:
            null_count = df[col].isnull().sum()
            analysis["null_values"][col] = int(null_count)
        
        # Détection des outliers
        if 'passenger_count' in df.columns:
            invalid_passengers = ((df['passenger_count'] < 1) | (df['passenger_count'] > 8)).sum()
            analysis["outliers"]["passenger_count"] = int(invalid_passengers)
        
        if 'trip_distance' in df.columns:
            long_trips = (df['trip_distance'] > 100).sum()
            analysis["outliers"]["trip_distance"] = int(long_trips)
        
        if 'fare_amount' in df.columns:
            high_fares = (df['fare_amount'] > 500).sum()
            analysis["outliers"]["fare_amount"] = int(high_fares)
        
        return analysis

    def clean_data_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Nettoie un chunk de données en supprimant les lignes problématiques.
        
        Args:
            df: DataFrame contenant les données à nettoyer
            
        Returns:
            pd.DataFrame: DataFrame nettoyé
        """
        original_count = len(df)
        df_cleaned = df.copy()
        
        # 1. Supprimer les lignes avec valeurs négatives
        negative_columns = [
            'passenger_count', 'trip_distance', 'fare_amount', 
            'tip_amount', 'tolls_amount', 'total_amount'
        ]
        
        for col in negative_columns:
            if col in df_cleaned.columns:
                before = len(df_cleaned)
                df_cleaned = df_cleaned[df_cleaned[col] >= 0]
                removed = before - len(df_cleaned)
        
        # 2. Supprimer les lignes avec passenger_count invalide
        if 'passenger_count' in df_cleaned.columns:
            before = len(df_cleaned)
            df_cleaned = df_cleaned[(df_cleaned['passenger_count'] >= 1) & (df_cleaned['passenger_count'] <= 8)]
            removed = before - len(df_cleaned)
        
        # 3. Supprimer les lignes avec trip_distance > 100 miles
        if 'trip_distance' in df_cleaned.columns:
            before = len(df_cleaned)
            df_cleaned = df_cleaned[df_cleaned['trip_distance'] <= 100]
            removed = before - len(df_cleaned)
        
        # 4. Supprimer les lignes avec fare_amount > $500
        if 'fare_amount' in df_cleaned.columns:
            before = len(df_cleaned)
            df_cleaned = df_cleaned[df_cleaned['fare_amount'] <= 500]
            removed = before - len(df_cleaned)
        
        # 5. Supprimer les lignes avec dates manquantes
        date_columns = ['tpep_pickup_datetime', 'tpep_dropoff_datetime']
        before = len(df_cleaned)
        df_cleaned = df_cleaned.dropna(subset=date_columns)
        removed = before - len(df_cleaned)
        
        return df_cleaned

    def save_chunk_to_mongodb(self, df: pd.DataFrame) -> int:
        """
        Sauvegarde un chunk de données nettoyées dans MongoDB.
        
        Args:
            df: DataFrame contenant les données nettoyées
            
        Returns:
            int: Nombre de documents insérés
        """
        try:
            # Convertir le DataFrame en liste de dictionnaires
            records = df.to_dict('records')
            
            # Convertir les Timestamp Pandas en datetime Python
            for record in records:
                for key, value in record.items():
                    if isinstance(value, pd.Timestamp):
                        record[key] = value.to_pydatetime()
            
            # Supprimer l'ID PostgreSQL
            for record in records:
                if 'id' in record:
                    del record['id']
            
            # Insérer les données
            if records:
                result = self.cleaned_trips_collection.insert_many(records)
                inserted_count = len(result.inserted_ids)
                return inserted_count
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du chunk: {e}")
            raise

    def process_data_in_chunks(self) -> Dict[str, Any]:
        """
        Traite toutes les données par chunks pour optimiser la mémoire.
        
        Returns:
            Dict: Statistiques globales du traitement
        """
        logger.info("🚀 Début du traitement par chunks...")
        
        # Obtenir le nombre total de lignes
        total_count = self.get_total_count()
        
        # Vider la collection MongoDB existante
        existing_count = self.cleaned_trips_collection.count_documents({})
        if existing_count > 0:
            logger.info(f"🗑️ Suppression de {existing_count:,} documents existants...")
            self.cleaned_trips_collection.delete_many({})
        
        # Statistiques globales
        global_stats = {
            "total_processed": 0,
            "total_cleaned": 0,
            "total_inserted": 0,
            "chunks_processed": 0,
            "negative_values": {},
            "null_values": {},
            "outliers": {}
        }
        
        # Traitement par chunks
        offset = 0
        while offset < total_count:
            logger.info(f"📦 Traitement du chunk {offset//self.chunk_size + 1} (offset: {offset:,})")
            
            # Charger le chunk
            df_chunk = self.load_data_chunk(offset, self.chunk_size)
            
            if df_chunk.empty:
                break
            
            # Analyser le chunk
            chunk_analysis = self.analyze_data_chunk(df_chunk)
            
            # Nettoyer le chunk
            cleaned_chunk = self.clean_data_chunk(df_chunk)
            
            # Sauvegarder le chunk
            inserted_count = self.save_chunk_to_mongodb(cleaned_chunk)
            
            # Mettre à jour les statistiques globales
            global_stats["total_processed"] += len(df_chunk)
            global_stats["total_cleaned"] += len(cleaned_chunk)
            global_stats["total_inserted"] += inserted_count
            global_stats["chunks_processed"] += 1
            
            # Fusionner les statistiques d'analyse
            for key in ["negative_values", "null_values", "outliers"]:
                for col, count in chunk_analysis[key].items():
                    if col not in global_stats[key]:
                        global_stats[key][col] = 0
                    global_stats[key][col] += count
            
            # Libérer la mémoire
            del df_chunk, cleaned_chunk
            gc.collect()
            
            # Afficher le progrès
            progress = (offset + self.chunk_size) / total_count * 100
            logger.info(f"📈 Progrès: {progress:.1f}% - {global_stats['total_processed']:,} lignes traitées")
            
            offset += self.chunk_size
        
        # Afficher les statistiques finales
        logger.info("📊 Statistiques finales:")
        logger.info(f"  • Chunks traités: {global_stats['chunks_processed']}")
        logger.info(f"  • Lignes traitées: {global_stats['total_processed']:,}")
        logger.info(f"  • Lignes nettoyées: {global_stats['total_cleaned']:,}")
        logger.info(f"  • Documents insérés: {global_stats['total_inserted']:,}")
        
        # Afficher les anomalies détectées
        for key, values in global_stats.items():
            if key in ["negative_values", "null_values", "outliers"] and values:
                logger.warning(f"⚠️  {key}: {values}")
        
        return global_stats

    def close(self) -> None:
        """
        Ferme les connexions aux bases de données.
        """
        try:
            if hasattr(self, 'mongo_client'):
                self.mongo_client.close()
                logger.info("Connexion MongoDB fermée")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de MongoDB: {e}")


def main():
    """
    Fonction principale pour exécuter le pipeline de nettoyage des données.
    """
    # Utiliser un chunk size plus petit pour réduire la consommation mémoire
    chunk_size = int(os.getenv("CHUNK_SIZE", "25000"))
    
    cleaner = DataCleaner(chunk_size=chunk_size)
    
    try:
        # Traiter les données par chunks
        stats = cleaner.process_data_in_chunks()
        
        logger.info("🎉 Pipeline de nettoyage terminé avec succès!")
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline de nettoyage: {e}")
        raise
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
