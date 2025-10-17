from pathlib import Path
from import_to_duckdb import DuckDBImporter  # adapt the path if needed

db = DuckDBImporter("data/database/DUCKDB.duckdb")

# Importer tout un répertoire
db.import_all_parquet_files(Path("data/raw"))

# Statistiques
db.get_statistics()

db.close()