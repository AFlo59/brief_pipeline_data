from __future__ import annotations
from pathlib import Path
from typing import Optional
import duckdb
import datetime as dt


class DuckDBImporter:
    """
    Importeur NYC Yellow Taxi pour DuckDB.
    - Connecte/initialise la base
    - Crée tables yellow_taxi_trips & import_log
    - Permet d'importer un .parquet ou tout un dossier
    - Expose des statistiques simples
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Connexion
        if str(self.db_path) == ":memory:":
            self.con = duckdb.connect()
        else:
            self.con = duckdb.connect(database=str(self.db_path))
        # Init DB
        self._initialize_database()

    # -------------------------------------------------------------------------
    # Initialisation
    # -------------------------------------------------------------------------
    def _initialize_database(self) -> None:
        # Schéma cible (par défaut main)
        # Créer la table trips si elle n'existe pas.
        # Schéma compatible NYC TLC (2019+) ; ajuste si besoin pour d'autres millésimes.
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS yellow_taxi_trips (
                VendorID                 INTEGER,
                tpep_pickup_datetime     TIMESTAMP,
                tpep_dropoff_datetime    TIMESTAMP,
                passenger_count          INTEGER,
                trip_distance            DOUBLE,
                RatecodeID               INTEGER,
                store_and_fwd_flag       VARCHAR,
                PULocationID             INTEGER,
                DOLocationID             INTEGER,
                payment_type             INTEGER,
                fare_amount              DOUBLE,
                extra                    DOUBLE,
                mta_tax                  DOUBLE,
                tip_amount               DOUBLE,
                tolls_amount             DOUBLE,
                improvement_surcharge    DOUBLE,
                total_amount             DOUBLE,
                congestion_surcharge     DOUBLE,
                airport_fee              DOUBLE
            );
            """
        )

        # Journal des imports
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS import_log (
                file_name      VARCHAR,
                import_date    TIMESTAMP,
                rows_imported  BIGINT
            );
            """
        )

    # -------------------------------------------------------------------------
    # Utilitaires
    # -------------------------------------------------------------------------
    def is_file_imported(self, filename: str) -> bool:
        res = self.con.execute(
            "SELECT 1 FROM import_log WHERE file_name = ? LIMIT 1;", [filename]
        ).fetchone()
        return res is not None

    # -------------------------------------------------------------------------
    # Import d'un fichier Parquet
    # -------------------------------------------------------------------------
    def import_parquet(self, file_path: Path) -> bool:
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"[WARN] Fichier introuvable: {file_path}")
            return False

        filename = file_path.name
        if self.is_file_imported(filename):
            print(f"[SKIP] Déjà importé: {filename}")
            return True

        try:
            before = self.con.execute("SELECT COUNT(*) FROM yellow_taxi_trips;").fetchone()[0]

            # Colonnes de la table (ordre cible)
            table_cols = self._get_table_columns("yellow_taxi_trips")

            # Colonnes du parquet (on construit un lookup insensible à la casse)
            pq_cols = self._get_parquet_columns(file_path)
            pq_lookup = {c: c for c in pq_cols} | {c.lower(): c for c in pq_cols}

            select_items = []
            for col in table_cols:
                # préféré: correspondance exacte, sinon insensible à la casse
                if col in pq_lookup:
                    src = pq_lookup[col]
                    select_items.append(f'{self._ident(src)}')
                elif col.lower() in pq_lookup:
                    src = pq_lookup[col.lower()]
                    select_items.append(f'{self._ident(src)}')
                else:
                    select_items.append(f'NULL AS {self._ident(col)}')

            select_sql = ", ".join(select_items)
            target_cols_sql = ", ".join(self._ident(c) for c in table_cols)

            self.con.execute(
                f"INSERT INTO yellow_taxi_trips ({target_cols_sql}) "
                f"SELECT {select_sql} FROM read_parquet(?);",
                [str(file_path)]
            )

            after = self.con.execute("SELECT COUNT(*) FROM yellow_taxi_trips;").fetchone()[0]
            delta = after - before

            self.con.execute(
                "INSERT INTO import_log (file_name, import_date, rows_imported) "
                "VALUES (?, CURRENT_TIMESTAMP, ?);",
                [filename, delta]
            )
            print(f"[OK] {filename} importé ({delta} lignes)")
            return True

        except Exception as e:
            print(f"[ERROR] Echec import {filename}: {e}")
            return False



    # -------------------------------------------------------------------------
    # Import de tous les .parquet d'un répertoire
    # -------------------------------------------------------------------------
    def import_all_parquet_files(self, data_dir: Path) -> int:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            print(f"[WARN] Dossier introuvable: {data_dir}")
            return 0

        count = 0
        for fp in sorted(data_dir.glob("*.parquet")):
            ok = self.import_parquet(fp)
            if ok:
                count += 1
        print(f"[INFO] Fichiers importés: {count}")
        return count

    # -------------------------------------------------------------------------
    # Statistiques
    # -------------------------------------------------------------------------
    def get_statistics(self) -> dict:
        stats: dict[str, Optional[str | int | float]] = {
            "total_trips": 0,
            "files_imported": 0,
            "pickup_min": None,
            "dropoff_max": None,
            "db_size_bytes": None,
            "db_size_readable": None,
        }

        # total trips
        try:
            stats["total_trips"] = self.con.execute(
                "SELECT COUNT(*) FROM yellow_taxi_trips;"
            ).fetchone()[0]
        except Exception:
            pass

        # files imported
        try:
            stats["files_imported"] = self.con.execute(
                "SELECT COUNT(*) FROM import_log;"
            ).fetchone()[0]
        except Exception:
            pass

        # date range
        try:
            row = self.con.execute(
                """
                SELECT
                    MIN(tpep_pickup_datetime),
                    MAX(tpep_dropoff_datetime)
                FROM yellow_taxi_trips;
                """
            ).fetchone()
            stats["pickup_min"] = row[0].isoformat(sep=" ") if row and row[0] else None
            stats["dropoff_max"] = row[1].isoformat(sep=" ") if row and row[1] else None
        except Exception:
            pass

        # db size
        if str(self.db_path) != ":memory:" and self.db_path.exists():
            size = self.db_path.stat().st_size
            stats["db_size_bytes"] = size
            stats["db_size_readable"] = self._human_size(size)

        # Affichage "humain"
        print("=== STATISTIQUES ===")
        print(f"Total trips           : {stats['total_trips']}")
        print(f"Fichiers importés     : {stats['files_imported']}")
        print(f"Pickup min            : {stats['pickup_min']}")
        print(f"Dropoff max           : {stats['dropoff_max']}")
        print(f"DB size               : {stats['db_size_readable']} ({stats['db_size_bytes']} bytes)")
        print("====================")
        return stats

    # -------------------------------------------------------------------------
    # Fermeture
    # -------------------------------------------------------------------------
    def close(self) -> None:
        self.con.close()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _human_size(nbytes: int) -> str:
        # format lisible pour la taille
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if nbytes < 1024:
                return f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} PB"
    
    @staticmethod
    def _ident(name: str) -> str:
        # Quote un identifiant SQL (nom de colonne) proprement
        return '"' + str(name).replace('"', '""') + '"'


    def _get_table_columns(self, table: str = "yellow_taxi_trips") -> list[str]:
        # ordre des colonnes tel que stocké dans la table
        rows = self.con.execute(
            "SELECT name FROM pragma_table_info(?) ORDER BY cid;", [table]
        ).fetchall()
        return [r[0] for r in rows]

    def _get_parquet_columns(self, path: Path) -> list[str]:
        # colonnes détectées dans le parquet (sans lire les données)
        cur = self.con.execute("SELECT * FROM read_parquet(?) LIMIT 0;", [str(path)])
        return [d[0] for d in cur.description]
