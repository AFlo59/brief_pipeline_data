#!/usr/bin/env python3
"""
Script d'attente pour MongoDB.

Ce script attend que MongoDB soit prêt avant de continuer l'exécution.
Il vérifie la connexion et l'authentification.
"""

import os
import time
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

def wait_for_mongodb(max_retries=30, delay=2):
    """
    Attend que MongoDB soit prêt et crée la base de données si nécessaire.
    
    Args:
        max_retries: Nombre maximum de tentatives (défaut: 30)
        delay: Délai entre les tentatives en secondes (défaut: 2)
    """
    # Configuration MongoDB depuis les variables d'environnement
    mongo_user = os.getenv("MONGO_USER", "admin")
    mongo_password = os.getenv("MONGO_PASSWORD", "admin")
    mongo_host = os.getenv("MONGO_HOST", "mongodb")
    mongo_port = os.getenv("MONGO_PORT", "27017")
    mongo_db = os.getenv("MONGO_DB", "nyc_taxi_clean")
    
    # Construction de l'URL de connexion
    mongo_url = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/"
    
    print(f"🔍 Vérification de MongoDB sur {mongo_host}:{mongo_port}...")
    
    for attempt in range(max_retries):
        try:
            # Tentative de connexion
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
            
            # Test de connexion avec ping
            client.admin.command('ping')
            
            # Vérifier si la base de données existe, sinon la créer
            db = client[mongo_db]
            db.command('ping')
            
            # Vérifier si la collection cleaned_trips existe
            collections = db.list_collection_names()
            if 'cleaned_trips' not in collections:
                print(f"📝 Création de la collection 'cleaned_trips' dans la base '{mongo_db}'...")
                db.create_collection('cleaned_trips')
                print(f"✅ Collection 'cleaned_trips' créée avec succès")
            else:
                print(f"✅ Collection 'cleaned_trips' existe déjà")
            
            print(f"✅ MongoDB prêt ! Base '{mongo_db}' accessible (tentative {attempt + 1}/{max_retries})")
            client.close()
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            if attempt < max_retries - 1:
                print(f"⏳ Tentative {attempt + 1}/{max_retries} échouée: {e}")
                print(f"⏳ Attente de {delay}s avant la prochaine tentative...")
                time.sleep(delay)
            else:
                print(f"❌ Impossible de se connecter à MongoDB après {max_retries} tentatives")
                print(f"❌ Dernière erreur: {e}")
                return False
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return False
    
    return False

if __name__ == "__main__":
    if wait_for_mongodb():
        print("✅ MongoDB est prêt !")
        sys.exit(0)
    else:
        print("❌ MongoDB n'est pas accessible")
        sys.exit(1)
