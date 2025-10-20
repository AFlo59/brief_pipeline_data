#!/usr/bin/env python3
"""
Script d'aide pour exécuter semantic-release avec des branches protégées.
Version automatique (non-interactive) pour les tests.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Exécute une commande et affiche le résultat."""
    print(f"\n[INFO] {description}")
    print(f"Commande: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("[SUCCESS] Succes!")
        if result.stdout:
            print("Sortie:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Erreur: {e}")
        if e.stdout:
            print("Sortie:", e.stdout)
        if e.stderr:
            print("Erreur:", e.stderr)
        return False


def check_git_status():
    """Vérifie le statut Git avant de commencer."""
    print("[INFO] Verification du statut Git...")
    
    # Vérifier si on est dans un repo Git
    if not Path(".git").exists():
        print("[ERROR] Pas dans un repository Git!")
        return False
    
    # Vérifier s'il y a des changements non commitées
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("[WARNING] Changements non commitees detectes:")
        print(result.stdout)
        print("[INFO] Continuation automatique...")
    
    # Vérifier la branche actuelle
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    current_branch = result.stdout.strip()
    print(f"[INFO] Branche actuelle: {current_branch}")
    
    return True


def main():
    """Fonction principale."""
    print("Assistant Semantic Release pour Branches Protegees")
    print("=" * 60)
    
    # Vérifications préliminaires
    if not check_git_status():
        print("[ERROR] Arret du processus.")
        sys.exit(1)
    
    print("\n[INFO] Processus de release:")
    print("1. Generation de la version et du changelog")
    print("2. Construction des packages")
    print("3. Creation du commit de release")
    print("4. Instructions pour creer une PR")
    
    # Étape 1: Version et changelog
    if not run_command(
        "python -m semantic_release version --changelog",
        "Generation de la version et du changelog"
    ):
        print("[ERROR] Echec de la generation de version.")
        sys.exit(1)
    
    # Étape 2: Build
    if not run_command(
        "python -m semantic_release publish",
        "Construction des packages"
    ):
        print("[ERROR] Echec de la construction.")
        sys.exit(1)
    
    # Vérifier les changements créés
    print("\n[INFO] Verification des changements...")
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("[INFO] Changements detectes:")
        print(result.stdout)
        
        # Afficher les instructions pour la PR
        print("\n" + "="*60)
        print("ETAPES SUIVANTES POUR CREER UNE PULL REQUEST:")
        print("="*60)
        print("1. Ajouter les fichiers modifies:")
        print("   git add .")
        print()
        print("2. Creer un commit de release:")
        print("   git commit -m 'chore: release version X.X.X'")
        print()
        print("3. Pousser vers votre branche:")
        print("   git push origin <nom-de-votre-branche>")
        print()
        print("4. Creer une Pull Request sur GitHub vers 'develop'")
        print("   - Titre: 'chore: release version X.X.X'")
        print("   - Description: 'Release automatique generee par semantic-release'")
        print()
        print("5. Une fois la PR mergee, les tags et releases GitHub")
        print("   seront crees automatiquement par le workflow GitHub Actions.")
        print("="*60)
    else:
        print("[INFO] Aucun changement detecte. Aucune nouvelle version necessaire.")


if __name__ == "__main__":
    main()
