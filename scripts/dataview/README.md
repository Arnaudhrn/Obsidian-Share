# Module Dataview (v2)

Transforme les blocs `dataview` d'une note Obsidian en Markdown statique pour publication web.

## Usage

```python
from dataview import DataviewProcessor

processor = DataviewProcessor()

# Remplacer tous les blocs dataview dans un fichier
new_content = processor.process_file_content(content, vault_base_path)

# Traiter un seul bloc
markdown = processor.process_block(block_content, vault_base_path)
```

`vault_base_path` = chemin du dossier (web) copié par `prepare_folder.py`. Il sert à résoudre les chemins `FROM` et à calculer les liens relatifs.

---

## Pipeline d'exécution

```
bloc dataview (string)
    ↓
[DataviewParser]       → AST structuré
    ↓
[ExecutionEngine]
    ├─ MarkdownDataExtractor  → lit chaque fichier .md
    ├─ apply_where()          → filtre
    ├─ apply_group()          → groupe
    ├─ apply_sort()           → trie
    └─ apply_limit()          → coupe
    ↓
[DataviewRenderer]     → Markdown statique
    ↓
Markdown prêt à être publié
```

**Ordre des opérations garanti :** `WHERE → GROUP BY → SORT → LIMIT`

---

## Fichiers

| Fichier | Classe | Rôle |
|---------|--------|------|
| `data_extractor.py` | `MarkdownDataExtractor` | Extrait frontmatter YAML, headers, tâches `[ ]`/`[x]`, tags `#emoji` |
| `parser.py` | `DataviewParser` | Parse la requête en AST (AND/OR imbriqués, parenthèses, fonctions) |
| `functions.py` | `FunctionRegistry` | Fonctions Dataview : `contains`, `replace`, `dateformat`, `choice`… |
| `executor.py` | `ExecutionEngine` | Applique WHERE → GROUP → SORT → LIMIT sur les données extraites |
| `renderer.py` | `DataviewRenderer` | Génère le Markdown final (TABLE, TASK, LIST) |
| `__init__.py` | `DataviewProcessor` | Façade : `process_block()` et `process_file_content()` |

---

## Fonctions supportées

| Fonction | Exemple | Résultat |
|----------|---------|----------|
| `contains(list, val)` | `contains(tags, "#🛒-Achat")` | `True/False` |
| `string(val)` | `string(header)` | `"Mon Header"` |
| `replace(text, old, new)` | `replace(string(header), "Méca > ", "")` | `"Freins"` |
| `dateformat(date, fmt)` | `dateformat(date, "dd MMMM yyyy")` | `"28 septembre 2024"` |
| `choice(val, oui, non)` | `choice(derushe-vidéo, "✅", "❌")` | `"✅"` |
| `min(rows.field)` | `min(rows.line)` | `42` (pour SORT sur groupes) |

---

## Requêtes supportées

### TABLE

```dataview
TABLE WITHOUT ID
  intervention AS "N°",
  file.link AS "Intervention",
  statut AS "Statut",
  dateformat(date, "dd MMMM yyyy") AS "Date",
  choice(derushe-vidéo, "✅", "❌") AS "Vidéo ✂️"
FROM "1 Mécanique/Interventions"
WHERE intervention != null AND intervention <= 9
SORT intervention ASC
```

### TASK avec GROUP BY

```dataview
TASK FROM "2 Projets/Mon-Projet/1 Mécanique"
WHERE contains(tags, "#🛒-Achat") OR contains(tags, "#⚙️-Travaux")
GROUP BY header
SORT min(rows.line) ASC
```

### TASK avec GROUP BY et replace()

```dataview
TASK FROM "Analyse"
WHERE contains(tags, "#🛒-Achat") OR contains(tags, "#⚙️-Travaux")
GROUP BY replace(string(header), "Analyse > ", "")
SORT min(rows.line) ASC
```

---

## Notes importantes

- Les **tags avec emojis** (`#🛒-Achat`, `#⚙️-Travaux`) sont correctement extraits
- Le **header parent** d'une tâche = le dernier `#` vu avant la ligne de la tâche
- Les **listes YAML** (`statut: [🟢 Terminé]`) sont dépaquetées automatiquement
- Les **espaces insécables** (`\xa0`) d'Obsidian sont nettoyés
- Les **cellules vides** affichent `-` pour garder l'alignement du tableau
- `file.link` génère un lien relatif `[[chemin/relatif/Nom|Nom]]`
- **Noms de champs avec tirets/espaces** : le moteur normalise automatiquement les noms de variables. `derushe-vidéo` dans la query trouvera `derushe vidéo` dans le frontmatter YAML (et inversement pour les tirets/underscores). Permet d'utiliser la syntaxe Obsidian sans modifier les propriétés des notes.
- **Champs booléens avec `choice()`** : `choice(mon-champ, "✅", "❌")` reçoit bien `true`/`false` brut — la conversion en `☑️`/`☐` n'a lieu que pour les champs booléens affichés directement en cellule.
- **FROM pointant un fichier** : si le chemin FROM désigne un fichier `.md` (et non un dossier), le programme le traite comme source unique et logge un warning. Utile quand un dossier contient plusieurs fichiers et qu'on veut en cibler un seul (ex: `Analyse & Études/Analyse & Études - SDB`).
- **TASK avec GROUP BY** : les titres de groupe sont rendus en lien interne cliquable `[[filepath|clé]]` si le fichier source est identifiable (premier row du groupe). Si aucun filepath disponible, repli sur `### clé`.
- **Tags affichés sur les tâches** : les tags extraits (`#🛒-Achat`, etc.) sont réaffichés en fin de ligne de chaque tâche dans le rendu TASK.
- **Groupes apparemment dupliqués** : si deux groupes affichent la même clé, c'est que des tâches de fichiers différents partagent le même texte de header. Affiner le `FROM` pour cibler un seul fichier ou dossier résout le problème.
