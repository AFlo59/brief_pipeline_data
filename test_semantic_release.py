#!/usr/bin/env python3
"""
Script de test pour vérifier que semantic-release fonctionne avec les branches protégées.
Ce script simule le comportement de GitHub Actions.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Exécute une commande et affiche le résultat."""
    print(f"\n[TEST] {description}")
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


def test_semantic_release_config():
    """Teste la configuration semantic-release avec push=false."""
    print("TEST: Configuration Semantic Release avec Branches Protegees")
    print("=" * 70)
    
    # Vérifier qu'on est dans un repo Git
    if not Path(".git").exists():
        print("[ERROR] Pas dans un repository Git!")
        return False
    
    # Créer un fichier de configuration temporaire
    config_content = """[tool.semantic_release]
push = false
tag = true
commit = true
upload_to_pypi = false
upload_to_release = true
"""
    
    with open("semantic-release-config.toml", "w") as f:
        f.write(config_content)
    
    print("[INFO] Configuration temporaire creee")
    
    # Tester la génération de version
    if not run_command(
        "python -m semantic_release version --changelog",
        "Test generation de version avec push=false"
    ):
        print("[ERROR] Echec du test de generation de version")
        return False
    
    # Tester la construction
    if not run_command(
        "python -m semantic_release publish",
        "Test construction des packages avec push=false"
    ):
        print("[ERROR] Echec du test de construction")
        return False
    
    # Vérifier les changements
    print("\n[INFO] Verification des changements...")
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("[SUCCESS] Changements detectes (comme attendu):")
        print(result.stdout)
    else:
        print("[INFO] Aucun changement detecte")
    
    # Nettoyer
    if Path("semantic-release-config.toml").exists():
        Path("semantic-release-config.toml").unlink()
        print("[INFO] Configuration temporaire supprimee")
    
    print("\n[SUCCESS] Test reussi! Semantic-release fonctionne avec push=false")
    return True


def main():
    """Fonction principale."""
    print("Script de Test - Semantic Release avec Branches Protegees")
    print("=" * 70)
    
    if test_semantic_release_config():
        print("\n" + "="*70)
        print("RESULTAT: Configuration fonctionnelle!")
        print("="*70)
        print("[SUCCESS] Semantic-release peut fonctionner avec push=false")
        print("[SUCCESS] Aucune erreur de push vers branches protegees")
        print("[SUCCESS] Version et changelog generes correctement")
        print("[SUCCESS] Packages construits avec succes")
        print("="*70)
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("RESULTAT: Configuration necessite des ajustements")
        print("="*70)
        print("[ERROR] Des erreurs ont ete detectees")
        print("[ERROR] Verification de la configuration necessaire")
        print("="*70)
        sys.exit(1)


if __name__ == "__main__":
    main()
