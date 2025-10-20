# Guide de Release avec Branches Protégées

## Problème Résolu

Votre semantic-release ne fonctionnait plus à cause des **branches protégées GitHub** qui empêchent les pushes directs vers `develop`. 

## Solution Implémentée

### 1. Configuration Mise à Jour (`pyproject.toml`)

```toml
[tool.semantic_release]
# Configuration pour éviter les erreurs avec les branches protégées
push = false      # Ne pousse pas automatiquement vers le remote
tag = true        # Crée les tags localement
commit = true     # Crée les commits localement
```

### 2. Scripts d'Aide

- `release_helper.py` : Version interactive
- `release_helper_auto.py` : Version automatique (recommandée)

## Comment Utiliser

### Option 1 : Script Automatique (Recommandé)

```bash
# 1. Activer l'environnement virtuel
.\venv\Scripts\activate

# 2. Exécuter le script
python release_helper_auto.py
```

### Option 2 : Commandes Manuelles

```bash
# 1. Activer l'environnement virtuel
.\venv\Scripts\activate

# 2. Générer la version et changelog
python -m semantic_release version --changelog

# 3. Construire les packages
python -m semantic_release publish
```

## Processus Complet

### Étape 1 : Génération
- ✅ Version calculée automatiquement
- ✅ Changelog mis à jour
- ✅ Fichiers de configuration modifiés

### Étape 2 : Build
- ✅ Packages construits (`dist/`)
- ✅ Fichiers `uv.lock` mis à jour

### Étape 3 : Création de Pull Request
```bash
# Ajouter les changements
git add .

# Créer le commit de release
git commit -m "chore: release version X.X.X"

# Pousser vers votre branche
git push origin feature/duckdb-import
```

### Étape 4 : Pull Request GitHub
1. Aller sur GitHub
2. Créer une PR de `feature/duckdb-import` vers `develop`
3. Titre : `chore: release version X.X.X`
4. Description : `Release automatique générée par semantic-release`

### Étape 5 : Merge et Release
- Une fois la PR mergée, le workflow GitHub Actions créera automatiquement :
  - Les tags Git
  - Les releases GitHub
  - Les artifacts de build

## Avantages de Cette Solution

1. **✅ Compatible avec les branches protégées**
2. **✅ Respecte le workflow de PR de votre équipe**
3. **✅ Automatise la génération de version**
4. **✅ Intègre avec GitHub Actions**
5. **✅ Pas de push direct vers les branches protégées**

## Dépannage

### Erreur "semantic-release not found"
```bash
# Installer dans l'environnement virtuel
.\venv\Scripts\pip install python-semantic-release
```

### Erreur "401 Unauthorized"
- Normal si pas de token GitHub configuré
- Le processus fonctionne quand même localement
- Les releases GitHub seront créées par le workflow Actions

### Erreur de syntaxe TOML
- Vérifier qu'il n'y a pas de caractères invalides dans `pyproject.toml`
- Utiliser un éditeur qui supporte la syntaxe TOML

## Configuration GitHub Actions

Votre workflow `.github/workflows/release.yml` est déjà configuré pour :
- Détecter les pushes sur `main`, `develop`, et `feature/*`
- Exécuter semantic-release automatiquement
- Créer les releases GitHub avec les artifacts

## Types de Versions

- **`main`** : Versions stables (1.0.0, 1.1.0, 2.0.0)
- **`develop`** : Versions RC (1.1.0-rc.1, 1.1.0-rc.2)
- **`feature/*`** : Versions alpha (1.1.0-alpha.1, 1.1.0-alpha.2)

## Exemple de Workflow Complet

```bash
# 1. Développement sur feature branch
git checkout -b feature/nouvelle-fonctionnalite

# 2. Commits avec conventional commits
git commit -m "feat: add nouvelle fonctionnalite"
git commit -m "fix: correct bug in nouvelle fonctionnalite"

# 3. Release local
python release_helper_auto.py

# 4. Créer PR
git add .
git commit -m "chore: release version 1.2.0-alpha.1"
git push origin feature/nouvelle-fonctionnalite

# 5. Merge PR sur develop → Version RC automatique
# 6. Merge PR sur main → Version stable automatique
```
