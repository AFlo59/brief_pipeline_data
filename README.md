# Pipeline Data Engineering - NYC Taxi Data

Une pipeline complète d'ingestion, traitement et analyse des données de taxis de New York (NYC Taxi Trip Records) avec une infrastructure moderne de data engineering.

## 🏗️ Architecture

```
NYC Open Data (2025)
        │
        │ ① Téléchargement
        ▼
┌──────────────┐
│  Parquet     │
│   Files      │
└──────┬───────┘
        │
        │ ② Ingestion
        ▼
┌──────────────┐    
│    Azure     │
│   PostgreSQL │
│   (Brut)     │
└──────┬───────┘
        │
        │ ③ Clean
        │ 
        ▼
┌──────────────┐
│ DLT Pipeline │ ④  DLT Migration
└──────┬───────┘
        │
        │ ⑤ Déploiement
        ▼
┌──────────────┐
│    Azure     │
│  MongoDB     │
│  (Nettoyé)   │
└──────────────┘
        │
        │ ⑥ Automatisation
        ▼
┌──────────────┐
│  GitHub      │
│  Actions     │
│  (Mensuel)   │
└──────────────┘
```

## 🚀 Technologies Utilisées

- **Python 3.12+** - Langage principal
- **DuckDB** - Base de données analytique locale
- **PostgreSQL** - Base de données relationnelle
- **MongoDB** - Base de données NoSQL
- **Docker & Docker Compose** - Conteneurisation
- **FastAPI** - API REST moderne
- **SQLAlchemy** - ORM Python
- **DLT (Data Load Tool)** - Pipeline de données moderne
- **Azure** - Cloud computing
- **GitHub Actions** - CI/CD et automatisation
- **Semantic Release** - Gestion automatique des versions

## 📊 Source des Données

- **URL**: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- **Format**: Fichiers Parquet (Yellow Taxi Trip Records)
- **Période**: Année 2025 uniquement
- **Exemple**: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-01.parquet

### Structure des Données

Colonnes principales :
- `VendorID`: Identifiant du fournisseur
- `tpep_pickup_datetime`: Date/heure de prise en charge
- `tpep_dropoff_datetime`: Date/heure de dépose
- `passenger_count`: Nombre de passagers
- `trip_distance`: Distance du trajet (miles)
- `fare_amount`: Montant du tarif
- `tip_amount`: Montant du pourboire
- `total_amount`: Montant total
- `payment_type`: Type de paiement

## 🛠️ Installation et Utilisation

### Prérequis

- Python 3.12+
- Docker et Docker Compose
- Git

### Installation

1. **Cloner le repository**
```bash
git clone https://github.com/AFlo59/brief_pipeline_data.git
cd brief_pipeline_data
```

2. **Installer les dépendances**
```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

3. **Télécharger les données**
```bash
python src/download_data.py
```

4. **Importer dans DuckDB**
```bash
python src/import_to_duckdb.py
```

5. **Démarrer avec Docker**
```bash
cp .env.example .env
docker-compose up -d
```

## 📁 Structure du Projet

```
brief_pipeline_data/
├── src/
│   ├── download_data.py      # Téléchargement des données NYC
│   ├── import_to_duckdb.py   # Import vers DuckDB
│   ├── import_to_postgres.py # Import vers PostgreSQL
│   ├── database.py          # Configuration SQLAlchemy
│   └── main.py              # Application FastAPI
├── data/
│   ├── raw/                 # Fichiers Parquet bruts
│   └── database/            # Base DuckDB locale
├── .github/workflows/       # GitHub Actions
├── docker-compose.yml       # Services Docker
├── Dockerfile              # Image Docker
├── requirements.txt        # Dépendances Python
└── pyproject.toml         # Configuration du projet
```

## 🔄 Workflow de Développement

1. **Branches protégées**: `main` (production) et `develop` (développement)
2. **Feature branches**: `feature/nom-de-la-fonctionnalite`
3. **Semantic Release**: Versioning automatique basé sur les commits
4. **Conventional Commits**: `feat:`, `fix:`, `docs:`, `chore:`

## 📈 Roadmap

- [x] **Jour 1**: Configuration Git/GitHub et ingestion des données
- [x] **Jour 2**: Import dans DuckDB et transition vers Docker
- [ ] **Jour 3**: API REST avec FastAPI
- [ ] **Jour 4**: Pipeline DLT moderne
- [ ] **Jour 5**: Déploiement Azure et automatisation

## 🤝 Contribution

1. Fork le projet
2. Créer une feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'feat: add some AmazingFeature'`)
4. Push vers la branch (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.
