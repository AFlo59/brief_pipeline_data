#!/usr/bin/env python3
"""
Script automatique pour les releases.
Version complètement automatique sans interaction utilisateur.
"""

import subprocess
import sys
import os
from pathlib import Path
import re


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
            return "1.0.0"
    except Exception as e:
        print(f"[ERROR] Impossible de lire la version: {e}")
        return "1.0.0"


def increment_version(version):
    """Incrémente la version automatiquement."""
    try:
        # Gestion des versions RC (Release Candidate)
        if "-rc." in version:
            # Incrémenter le numéro RC
            parts = version.split("-rc.")
            if len(parts) == 2:
                rc_num = int(parts[1]) + 1
                return f"{parts[0]}-rc.{rc_num}"
        
        # Gestion des versions alpha
        if "-alpha." in version:
            # Incrémenter le numéro alpha
            parts = version.split("-alpha.")
            if len(parts) == 2:
                alpha_num = int(parts[1]) + 1
                return f"{parts[0]}-alpha.{alpha_num}"
        
        # Version normale : incrémenter le patch
        parts = version.split(".")
        if len(parts) >= 3:
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        
        return version
    except:
        return version


def update_version_in_file(new_version):
    """Met à jour la version dans pyproject.toml."""
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remplacer la version
        pattern = r'version = "[^"]*"'
        new_content = re.sub(pattern, f'version = "{new_version}"', content)
        
        with open("pyproject.toml", "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"[SUCCESS] Version mise a jour: {new_version}")
        return True
    except Exception as e:
        print(f"[ERROR] Impossible de mettre a jour la version: {e}")
        return False


def main():
    """Fonction principale."""
    print("RELEASE AUTOMATIQUE - SCRIPT SIMPLE")
    print("=" * 50)
    
    # Vérifier qu'on est dans un repo Git
    if not Path(".git").exists():
        print("[ERROR] Pas dans un repository Git!")
        sys.exit(1)
    
    # Récupérer la version actuelle
    current_version = get_current_version()
    print(f"[INFO] Version actuelle: {current_version}")
    
    # Incrémenter automatiquement la version
    new_version = increment_version(current_version)
    print(f"[INFO] Nouvelle version: {new_version}")
    
    # Mettre à jour la version
    if not update_version_in_file(new_version):
        sys.exit(1)
    
    # Construire les packages
    print("\n" + "="*50)
    print("CONSTRUCTION DES PACKAGES")
    print("="*50)
    
    # Essayer d'abord uv, puis fallback sur pip + build
    if not run_command("uv build", "Construction avec uv"):
        print("[INFO] uv non disponible, utilisation de pip + build...")
        if not run_command("pip install build", "Installation de build"):
            print("[ERROR] Impossible d'installer build")
            sys.exit(1)
        if not run_command("python -m build", "Construction avec python -m build"):
            print("[ERROR] Echec de la construction")
            sys.exit(1)
    
    # Créer le commit
    print("\n" + "="*50)
    print("CREATION DU COMMIT")
    print("="*50)
    
    subprocess.run("git add .", shell=True)
    
    commit_message = f"chore: release version {new_version}"
    if not run_command(f'git commit -m "{commit_message}"', "Creation du commit"):
        print("[INFO] Pas de changements a commiter")
    
    # Créer le tag
    print("\n" + "="*50)
    print("CREATION DU TAG")
    print("="*50)
    
    tag_name = f"v{new_version}"
    if not run_command(f'git tag "{tag_name}"', "Creation du tag"):
        print("[INFO] Tag deja existe ou erreur")
    
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
    print(f"   - Titre: 'chore: release version {new_version}'")
    print()
    print("4. Une fois la PR mergee:")
    print("   - Les releases GitHub seront creees automatiquement")
    print("   - Le workflow GitHub Actions s'occupera du reste")
    print("="*50)
    
    print(f"\n[SUCCESS] Release {new_version} terminee avec succes!")


if __name__ == "__main__":
    main()
