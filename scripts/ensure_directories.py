#!/usr/bin/env python3
"""
Script de vérification et création des répertoires de données.

Ce script vérifie que les répertoires nécessaires existent et les crée si nécessaire.
"""

import os
import sys
from pathlib import Path

def ensure_data_directories():
    """
    Vérifie et crée les répertoires de données nécessaires.
    
    Returns:
        bool: True si tous les répertoires sont prêts, False sinon
    """
    print("📁 Vérification des répertoires de données...")
    
    # Répertoires à vérifier/créer
    directories = [
        "data",
        "data/raw",
        "data/database"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            print(f"📝 Création du répertoire: {directory}")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Répertoire '{directory}' créé avec succès")
            except Exception as e:
                print(f"❌ Erreur lors de la création de '{directory}': {e}")
                return False
        else:
            print(f"✅ Répertoire '{directory}' existe déjà")
    
    # Vérifier les permissions d'écriture
    data_dir = Path("data")
    if not os.access(data_dir, os.W_OK):
        print(f"❌ Pas de permissions d'écriture sur le répertoire 'data'")
        return False
    
    print("✅ Tous les répertoires de données sont prêts")
    return True

def main():
    """Fonction principale."""
    if ensure_data_directories():
        print("🎉 Vérification des répertoires terminée avec succès")
        return 0
    else:
        print("❌ Échec de la vérification des répertoires")
        return 1

if __name__ == "__main__":
    sys.exit(main())
