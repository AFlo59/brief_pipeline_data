-- Script d'initialisation de la base de données PostgreSQL
-- Ce script est exécuté automatiquement lors du premier démarrage du conteneur PostgreSQL

-- Créer la base de données si elle n'existe pas déjà
-- (Cette commande est généralement gérée par les variables d'environnement Docker)

-- Créer des extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Créer un utilisateur pour l'application (optionnel)
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- GRANT ALL PRIVILEGES ON DATABASE nyc_taxi TO app_user;

-- Configurer les paramètres de performance (optionnel)
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET track_activity_query_size = 2048;
-- ALTER SYSTEM SET pg_stat_statements.track = 'all';

-- Afficher un message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Base de données NYC Taxi initialisée avec succès!';
END $$;
