from pathlib import Path
from import_to_duckdb import DuckDBImporter  # adapte le chemin si besoin

db = DuckDBImporter("data/database/DUCKDB.duckdb")

# Importer tout un répertoire
db.import_all_parquet_files(Path("data/raw"))

# Statistiques
db.get_statistics()

db.close()