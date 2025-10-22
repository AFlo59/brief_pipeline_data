#!/usr/bin/env python3
"""
Script pour créer une release sur une branche protégée.
Ce script génère la version, construit les packages, et prépare tout pour une Pull Request.
"""

import subprocess
import sys
import os
from pathlib import Path
import re


def run_command(cmd, description, check=True):
    """Exécute une commande et affiche le résultat."""
    print(f"\n[INFO] {description}")
    print(f"Commande: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        print("[SUCCESS] Succès!")
        if result.stdout:
            print("Sortie:", result.stdout)
        return True, result
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Erreur: {e}")
        if e.stdout:
            print("Sortie:", e.stdout)
        if e.stderr:
            print("Erreur:", e.stderr)
        return False, e


def check_dependencies():
    """Vérifie que les dépendances nécessaires sont installées."""
    print("VÉRIFICATION DES DÉPENDANCES")
    print("=" * 50)
    
    # Vérifier semantic-release
    success, result = run_command("which semantic-release", "Vérification de semantic-release", check=False)
    if not success or "not found" in result.stderr:
        print("\n❌ semantic-release n'est pas installé!")
        print("\n📦 Solutions:")
        print("1. Avec pip:")
        print("   pip install python-semantic-release")
        print("\n2. Avec uv:")
        print("   uv add python-semantic-release")
        print("\n3. Avec conda:")
        print("   conda install -c conda-forge python-semantic-release")
        return False
    
    # Vérifier uv
    success, result = run_command("which uv", "Vérification de uv", check=False)
    if not success or "not found" in result.stderr:
        print("\n⚠️  uv n'est pas installé, utilisation de pip à la place")
        return True
    
    print("✅ Toutes les dépendances sont disponibles")
    return True


def get_current_version():
    """Récupère la version actuelle depuis pyproject.toml."""
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Chercher la ligne version = "X.X.X"
        pattern = r'version = "([^"]*)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        else:
            print("[ERROR] Version non trouvée dans pyproject.toml")
            return None
    except Exception as e:
        print(f"[ERROR] Impossible de lire la version: {e}")
        return None


def main():
    """Fonction principale pour créer une release sur branche protégée."""
    print("RELEASE POUR BRANCHE PROTÉGÉE")
    print("=" * 50)
    
    # Vérifier qu'on est dans un repo Git
    if not Path(".git").exists():
        print("[ERROR] Pas dans un repository Git!")
        sys.exit(1)
    
    # Vérifier les dépendances
    if not check_dependencies():
        print("\n❌ Dépendances manquantes. Veuillez les installer avant de continuer.")
        sys.exit(1)
    
    # Vérifier la branche actuelle
    success, result = run_command("git branch --show-current", "Vérification de la branche actuelle")
    if not success:
        sys.exit(1)
    
    current_branch = result.stdout.strip()
    print(f"[INFO] Branche actuelle: {current_branch}")
    
    # Générer la version avec semantic-release
    print("\n" + "="*50)
    print("GÉNÉRATION DE LA VERSION")
    print("="*50)
    
    success, _ = run_command("semantic-release --verbose version --changelog", "Génération de la version")
    if not success:
        print("[ERROR] Échec de la génération de version")
        sys.exit(1)
    
    # Récupérer la nouvelle version
    new_version = get_current_version()
    if not new_version:
        print("[ERROR] Impossible de récupérer la nouvelle version")
        sys.exit(1)
    
    print(f"[INFO] Nouvelle version générée: {new_version}")
    
    # Construire les packages
    print("\n" + "="*50)
    print("CONSTRUCTION DES PACKAGES")
    print("="*50)
    
    # Essayer d'abord uv, puis fallback sur pip + build
    success, _ = run_command("uv build", "Construction avec uv", check=False)
    if not success:
        print("[INFO] uv non disponible, utilisation de pip + build...")
        success, _ = run_command("pip install build", "Installation de build", check=False)
        if not success:
            print("[ERROR] Impossible d'installer build")
            sys.exit(1)
        success, _ = run_command("python -m build", "Construction avec python -m build")
        if not success:
            print("[ERROR] Échec de la construction des packages")
            sys.exit(1)
    
    # Créer le commit
    print("\n" + "="*50)
    print("CRÉATION DU COMMIT")
    print("="*50)
    
    subprocess.run("git add .", shell=True)
    
    commit_message = f"chore: release version {new_version}"
    success, _ = run_command(f'git commit -m "{commit_message}"', "Création du commit", check=False)
    if not success:
        print("[INFO] Pas de changements à commiter ou commit déjà existant")
    
    # Créer le tag
    print("\n" + "="*50)
    print("CRÉATION DU TAG")
    print("="*50)
    
    tag_name = f"v{new_version}"
    success, _ = run_command(f'git tag "{tag_name}"', "Création du tag", check=False)
    if not success:
        print("[INFO] Tag déjà existe ou erreur")
    
    # Instructions finales
    print("\n" + "="*50)
    print("INSTRUCTIONS POUR BRANCHE PROTÉGÉE")
    print("="*50)
    print("✅ Release préparée avec succès!")
    print()
    print("📋 Prochaines étapes:")
    print("1. Créer une nouvelle branche pour la release:")
    print(f"   git checkout -b release/{new_version}")
    print()
    print("2. Pousser la branche:")
    print(f"   git push origin release/{new_version}")
    print()
    print("3. Pousser les tags:")
    print("   git push origin --tags")
    print()
    print("4. Créer une Pull Request:")
    print(f"   - Titre: 'chore: release version {new_version}'")
    print(f"   - De: release/{new_version}")
    print(f"   - Vers: {current_branch}")
    print()
    print("5. Une fois la PR mergée:")
    print("   - Les releases GitHub seront créées automatiquement")
    print("   - Le workflow GitHub Actions s'occupera du reste")
    print("="*50)
    
    print(f"\n[SUCCESS] Release {new_version} préparée avec succès!")


if __name__ == "__main__":
    main()
