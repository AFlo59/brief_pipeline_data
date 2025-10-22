#!/usr/bin/env python3
"""
Script pour attendre que la base de données PostgreSQL soit prête.
"""
import sys
import time
from src.database import check_db_connection

def main():
    """Attendre que la base de données soit prête et initialiser les tables."""
    print("🔍 Vérification de PostgreSQL...")
    
    max_attempts = 30  # Maximum 30 tentatives (60 secondes)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            if check_db_connection():
                print("✅ PostgreSQL prêt !")
                
                # Initialiser les tables si nécessaire
                from src.database import init_db
                print("📝 Initialisation des tables PostgreSQL...")
                init_db()
                print("✅ Tables PostgreSQL initialisées")
                
                return 0
            else:
                print(f"⏳ Tentative {attempt + 1}/{max_attempts}: En attente de PostgreSQL...")
                time.sleep(2)
                attempt += 1
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            time.sleep(2)
            attempt += 1
    
    print("❌ Timeout: Impossible de se connecter à PostgreSQL")
    return 1

if __name__ == "__main__":
    sys.exit(main())
