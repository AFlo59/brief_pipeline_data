#!/usr/bin/env python3
"""
Script pour attendre que la base de données PostgreSQL soit prête.
"""
import sys
import time
from src.database import check_db_connection

def main():
    """Attendre que la base de données soit prête."""
    print("Attente de la base de données...")
    
    max_attempts = 30  # Maximum 30 tentatives (60 secondes)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            if check_db_connection():
                print("Base de données prête !")
                return 0
            else:
                print("En attente de PostgreSQL...")
                time.sleep(2)
                attempt += 1
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            time.sleep(2)
            attempt += 1
    
    print("Timeout: Impossible de se connecter à la base de données")
    return 1

if __name__ == "__main__":
    sys.exit(main())
