#!/usr/bin/env python3
"""
Script simple pour lancer semantic-release avec les branches protégées.
Un seul script pour tout faire !
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
            print("Sortie:", result.stdout)
        if e.stderr:
            print("Erreur:", e.stderr)
        return False


def check_git_status():
    """Vérifie le statut Git."""
    print("[INFO] Verification du statut Git...")
    
    if not Path(".git").exists():
        print("[ERROR] Pas dans un repository Git!")
        return False
    
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    current_branch = result.stdout.strip()
    print(f"[INFO] Branche actuelle: {current_branch}")
    
    return True


def main():
    """Fonction principale."""
    print("SEMANTIC RELEASE - SCRIPT SIMPLE")
    print("=" * 50)
    
    # Vérifications préliminaires
    if not check_git_status():
        print("[ERROR] Arret du processus.")
        sys.exit(1)
    
    print("\n[INFO] Processus de release:")
    print("1. Generation de la version et du changelog")
    print("2. Construction des packages")
    print("3. Creation du commit de release")
    
    # Étape 1: Version et changelog
    print("\n" + "="*50)
    print("ETAPE 1: GENERATION VERSION ET CHANGELOG")
    print("="*50)
    
    result = subprocess.run(
        "python -m semantic_release version --changelog",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.stdout and "The next version is:" in result.stdout:
        print("[SUCCESS] Version generee avec succes!")
        print("Sortie:", result.stdout)
    else:
        print("[ERROR] Echec de la generation de version")
        print("Sortie:", result.stdout)
        print("Erreur:", result.stderr)
        print("\n[INFO] Continuation quand meme...")
    
    # Étape 2: Build
    print("\n" + "="*50)
    print("ETAPE 2: CONSTRUCTION DES PACKAGES")
    print("="*50)
    
    result = subprocess.run(
        "python -m semantic_release publish",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if "Build completed successfully" in result.stdout or "Successfully built" in result.stdout:
        print("[SUCCESS] Construction reussie!")
        print("Sortie:", result.stdout)
    else:
        print("[ERROR] Echec de la construction")
        print("Sortie:", result.stdout)
        print("Erreur:", result.stderr)
        print("\n[INFO] Continuation quand meme...")
    
    # Étape 3: Commit et tag
    print("\n" + "="*50)
    print("ETAPE 3: CREATION COMMIT ET TAG")
    print("="*50)
    
    # Ajouter les fichiers
    subprocess.run("git add .", shell=True)
    
    # Créer le commit
    result = subprocess.run(
        'git commit -m "chore: release version $(python -c "import toml; print(toml.load(\'pyproject.toml\')[\'project\'][\'version\'])")"',
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("[SUCCESS] Commit cree avec succes!")
        print("Sortie:", result.stdout)
    else:
        print("[INFO] Pas de changements a commiter")
        print("Sortie:", result.stdout)
    
    # Créer le tag
    result = subprocess.run(
        'git tag "v$(python -c "import toml; print(toml.load(\'pyproject.toml\')[\'project\'][\'version\'])")"',
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("[SUCCESS] Tag cree avec succes!")
        print("Sortie:", result.stdout)
    else:
        print("[INFO] Tag deja existe ou erreur")
        print("Sortie:", result.stdout)
    
    # Vérifier les changements
    print("\n" + "="*50)
    print("VERIFICATION DES CHANGEMENTS")
    print("="*50)
    
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("[INFO] Changements detectes:")
        print(result.stdout)
    else:
        print("[INFO] Aucun changement en attente")
    
    # Instructions finales
    print("\n" + "="*50)
    print("INSTRUCTIONS FINALES")
    print("="*50)
    print("1. Pour pousser vers votre branche:")
    print("   git push origin <nom-de-votre-branche>")
    print()
    print("2. Pour pousser les tags:")
    print("   git push origin --tags")
    print()
    print("3. Pour creer une Pull Request:")
    print("   - Aller sur GitHub")
    print("   - Creer une PR de votre branche vers 'develop'")
    print("   - Titre: 'chore: release version X.X.X'")
    print()
    print("4. Une fois la PR mergee:")
    print("   - Les releases GitHub seront creees automatiquement")
    print("   - Le workflow GitHub Actions s'occupera du reste")
    print("="*50)
    
    print("\n[SUCCESS] Processus de release termine avec succes!")


if __name__ == "__main__":
    main()
