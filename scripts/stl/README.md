# Module STL - scripts/stl/

Gère les fichiers STL référencés dans les notes Obsidian : détection, copie, et transformation des liens.

## Fonctionnement

Les notes Obsidian contiennent des liens externes vers des fichiers STL locaux :
```markdown
[Ma Pièce](file:///Users/votre-nom/Documents/Impression3D/ma-piece.stl)
```

Le module :
1. **Détecte** ces liens `file://` pointant vers un `.stl`
2. **Copie** les fichiers STL vers le dossier `.stl/` du projet (web)
3. **Transforme** les liens en chemins relatifs exploitables par le serveur

Résultat dans le markdown transformé :
```markdown
[Fixation Phare 1](.stl/Fixation%20Phare%201.stl)
```

## Structure

| Fichier | Rôle |
|---|---|
| `__init__.py` | Façade publique : `STL3DProcessor` |
| `extractor.py` | Détecte les liens `file://` STL via regex |
| `processor.py` | Copie les fichiers + transforme les liens |

## Usage

```python
from stl import STL3DProcessor

processor = STL3DProcessor()

# Traiter tout un dossier projet
count = processor.process_folder(project_path, stl_folder)
print(f"{count} fichier(s) STL copiés")

# Ou traiter le contenu d'un seul fichier
new_content, count = processor.process_file_content(content, stl_folder)
```

## Intégration dans prepare_folder.py

Appelé automatiquement après `copy_images()` dans le flow principal.
Le dossier `.stl/` créé est uploadé sur FTP avec le reste du projet.

## Côté serveur

- `view.php` détecte les liens `.stl/...` → génère un lien `viewer.php?folder=X&file=Y`
- `viewer.php` affiche le fichier avec Three.js (WebGL) dans un nouvel onglet
- Le dossier `.stl/` est caché dans la sidebar (règle du point, comme `.images/`)
