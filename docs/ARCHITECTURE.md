# 🏗️ Architecture du Projet

## Vue Générale

Le projet divise les responsabilités en 3 phases :

```
Phase 1: LOCAL (Mac)                Phase 2: CONVERSION                Phase 3: SERVEUR (VPS)
┌─────────────────────────────────┐         ┌──────────────┐        ┌────────────────────┐
│ Obsidian Vault                  │         │ prepare_     │        │ Hostinger          │
│ /Users/.../Mon-Projet           │  ──→    │ folder.py    │   ──→  │ /public_html/      │
│ - 1 Mécanique/                  │         │              │        │ obsidian/          │
│ - 2 Electricité/                │         │ • Parse MD   │        │ ├── index.php      │
│ - Attachments/                  │         │ • Extract    │        │ ├── view.php       │
│ - notes.md                      │         │ • Dataview   │        │ ├── config.json    │
│                                 │         │ • Copy imgs  │        │ ├── logo.png       │
│                                 │         │              │        │ └── [projets web]/ │
└─────────────────────────────────┘         └──────────────┘        └────────────────────┘
```

## Composants Clés

### 1. **Server** (`server/`)
Fichiers PHP du site web, **uploadés sur le serveur**.

```
server/
├── index.php          # Page d'accueil + authentification
│                      # Lit config.json
│                      # Liste les dossiers partagés
│                      # Gère POST du mot de passe
│                      # Endpoint JSON: ?action=search (recherche fulltext)
│                      # TOC panel: H1/H2/H3 avec visual indicator SVG
│                      # Barre de recherche sidebar: filterTree() JS
│                      #   filtre uniquement les fichiers par nom (jamais les dossiers)
│                      #   affiche toute l'arborescence des dossiers parents des matchs
│                      #   → dropdown AJAX (?action=search) pour recherche plein texte
│                      # Système d'onglets (TabManager JS)
│                      # closeTab(): fermeture → onglet à gauche prioritaire,
│                      #             sinon à droite (jamais retour au premier)
│                      # Détecte ?file=*.stl → iframe viewer 3D (class stl-view)
│
├── view.php           # Affichage du contenu Markdown
│                      # Rend HTML depuis fichiers .md
│                      # Gère les images (.images/)
│                      # findProjectRoot(): remonte depuis le dossier courant
│                      #   jusqu'au dossier contenant .images/ → racine du projet
│                      # Carrousel Litegal: détecte blocs ```litegal → carousel
│                      # Images: chemins résolus depuis la racine du projet
│                      #   (fonctionne depuis n'importe quelle profondeur d'imbrication,
│                      #    racine du projet incluse)
│                      # Résolution liens internes [[note]]:
│                      #   recherche depuis findProjectRoot() → trouve les fichiers
│                      #   à tous les niveaux (parent, frère, enfant)
│                      # Résolution liens avec chemin [[Dossier/note]]:
│                      #   résout depuis la racine du projet (comportement Obsidian)
│                      # Liens STL: [text](.stl/file.stl) → <a class="stl-link external-link">
│                      #            → ouvre dans un nouvel onglet du site
│
├── viewer.php         # Visualisateur 3D STL (WebGL via Three.js)
│                      # Vérifie l'authentification session
│                      # Sécurité anti path-traversal sur ?file= et ?folder=
│                      # Rendu Three.js: éclairage 3 points, OrbitControls
│                      # Mode embed (?embed=1): toolbar masquée (usage iframe)
│                      # Canvas transparent → fond géré par CSS (#1e1e1e)
│
├── style.css          # Styles (dark mode, Obsidian-like)
│                      # .stl-link: style lien vers fichier 3D
│                      # .stl-view: layout fullscreen pour iframe viewer
│
├── config.json        # Configuration des dossiers
│                      # Généré par prepare_folder.py
│                      # Structure:
│                      # {
│                      #   "folders": {
│                      #     "Mon-Projet": {
│                      #       "path": "...",
│                      #       "password": "$2y$10$hash..."
│                      #     }
│                      #   }
│                      # }
│
└── .htaccess          # Réécriture URLs + sécurité
                       # Bloque l'accès à config.json
                       # Crée des URLs propres
```

### 2. **Scripts** (`scripts/`)
Outils Python pour transformer et uploader, **NON uploadés sur le serveur**.

```
scripts/
├── prepare_folder.py      # Script principal
│                          # 1. Demande le dossier source
│                          # 2. Parse YAML frontmatter
│                          # 3. Traite les blocs Dataview
│                          # 4. Normalise les délimiteurs ``` (strip espaces parasites)
│                          # 5. Copie images depuis Attachments (inclut blocs litegal)
│                          # 6. Crée le dossier (share) → projects/
│                          # 7. Met à jour config.json
│                          # 8. Upload FTP (auto)
│
├── config.py              # Configuration centralisée (FTP, SITE_URL, chemins images)
│                          # ⚙️ Seul fichier à modifier pour une nouvelle installation
│
├── ftp_utils.py           # Fonctions FTP réutilisables
│                          # connect_ftp() / reconnect_ftp() → revient à FTP_DIR
│                          # upload_directory(ftp, local, remote_dir)
│                          #   remote_dir inclut le nom du projet → chemins absolus
│                          #   depuis FTP_DIR, reconnexion automatique sans perte de cible
│                          # remove_ftp_folder()
│
├── upload_core_files.py   # Upload juste les fichiers PHP
│
├── upload_folder.py       # Upload un dossier spécifique
│
├── upload_to_ftp.py       # Orchestration des uploads
│
├── dataview/              # MODULE DATAVIEW (v2)
│   ├── __init__.py        # Façade: DataviewProcessor
│   ├── data_extractor.py  # Extraction frontmatter, headers, tasks, tags
│   ├── parser.py          # Parse requête → AST structuré
│   ├── functions.py       # Registry: contains, replace, dateformat, choice…
│   ├── executor.py        # Pipeline: WHERE → GROUP → SORT → LIMIT
│   ├── renderer.py        # Génère Markdown statique (TABLE, TASK, LIST)
│   ├── evaluator.py       # (Legacy, non utilisé)
│   └── README.md          # Doc du module
│
├── stl/                   # MODULE STL 3D (v1)
│   ├── __init__.py        # Façade: STL3DProcessor
│   ├── extractor.py       # Détecte liens file:// .stl dans les .md
│   ├── processor.py       # Copie fichiers + transforme liens en .stl/
│   └── README.md          # Doc du module
│
└── logo.png               # Logo optimisé
```

### 3. **Documentation** (`docs/`)
Documentation du projet, **NON uploadée sur le serveur**.

```
docs/
├── README.md                    # 📖 Vue d'ensemble du projet
│                                # - Guide principal pour démarrer
│                                # - Features et fonctionnalités
│                                # - Workflow complet
│
├── ARCHITECTURE.md              # 🏗️ Explication technique
│                                # - Vue générale du projet
│                                # - Composants clés (server/, scripts/, etc.)
│                                # - Flux de données détaillé
│                                # - Module Dataview isolé
│
├── SETUP.md                     # 🚀 Installation et configuration
│                                # - Prérequis
│                                # - Configuration locale (Mac)
│                                # - Configuration serveur (Hostinger)
│                                # - Scripts disponibles
│
├── CHANGELOG.md                 # 📋 Historique des sessions
│                                # Format: Date + Heure, Titre court
│                                # - Résumé (1-2 lignes contexte global)
│                                # - À retenir (1-2 points clés)
│                                # - Permet continuité entre sessions
│
└── archive/                     # 📦 Docs obsolètes/temporaires
    └── (Docs anciennes archivées)
```

### 4. **Projects** (`projects/`)
Dossiers générés par `prepare_folder.py`, **contenus à uploader**.

```
projects/
├── Mon-Projet (share)/        # Exemple: généré par prepare_folder.py
│   ├── .images/                       # 📌 Images extraites (caché, non visible sidebar)
│   ├── .stl/                          # 📌 Fichiers STL extraits (caché, non visible sidebar)
│   └── ............                   # 📝 Dossiers et fichiers spécifiques au vault
│
└── Mon-Projet-2 (share)/                      # Exemple: projet Mon-Projet-2
    ├── .images/                       # 📌 Images extraites
    ├── .stl/                          # 📌 Fichiers STL (présent si le vault contient des liens STL)
    └── ............                   # 📝 Dossiers et fichiers spécifiques au vault
```

**⚠️ Important:**
- **`.images/`** → Présent dans TOUS les projets (dossier fixe)
- **`.stl/`** → Présent uniquement si le vault contient des liens `file://` vers des `.stl`
- Les deux dossiers commencent par un point → cachés dans la sidebar (règle `$item[0] === '.'` dans `index.php`)
- Chaque projet a sa propre structure basée sur le vault Obsidian original

## Flux de Données

### Flux Local (prepare_folder.py)

```python
1. Utilisateur lance le script
   └─> select_folder()
       └─> Demande le chemin (drag-drop)

2. Parser le dossier source
   └─> scan_folder()
       ├─ Lit tous les fichiers .md
       └─ Extrait frontmatter YAML

3. Traiter chaque fichier
   └─> process_markdown_file()
       ├─ Cherche blocs ```dataview ... ```
       └─ DataviewProcessor.process_file_content()
          ├─ DataviewParser.parse()       → AST structuré
          ├─ ExecutionEngine.execute()
          │  ├─ MarkdownDataExtractor     → frontmatter, tasks, tags, headers
          │  ├─ apply_where()             → filtre les données
          │  ├─ apply_group()             → groupe par clé
          │  ├─ apply_sort()              → trie (support min/max agrégés)
          │  └─ apply_limit()
          └─ DataviewRenderer.render()    → Markdown statique

4. Copier les images
   └─> find_and_copy_attachments()
       ├─ Cherche Attachments/ dans le vault
       ├─ Crée .images/ local
       └─ Copie les images référencées

4b. Traiter les liens STL
   └─> STL3DProcessor.process_folder()
       ├─ Parcourt tous les .md du projet
       ├─ Détecte liens file:// pointant vers .stl
       ├─ Copie les fichiers .stl vers .stl/
       └─ Transforme les liens:
          AVANT: [Pièce](file:///Users/.../piece.stl)
          APRÈS: [Pièce](.stl/piece.stl)

5. Créer le dossier (share)
   └─> create_web_folder()
       ├─ Copie tous les fichiers .md traités
       ├─ Crée la structure de dossiers
       └─ Place .images/

6. Générer mot de passe
   └─> generate_password()
       ├─ 15 caractères aléatoires
       ├─ Hash Bcrypt
       └─ Ajoute à config.json

7. Upload FTP
   └─> upload_directory()
       ├─ Connecte FTP
       ├─ Upload dossier (share)
       ├─ Upload config.json
       └─ Upload core files si besoin
```

### Flux Serveur (index.php)

```
1. Utilisateur accède: https://obsidian.votre-domaine.com/
   └─> index.php charge
       ├─ Lit config.json
       └─ Liste les dossiers

2. Utilisateur sélectionne un dossier
   └─> Affiche formulaire mot de passe

3. POST du mot de passe
   └─> Vérifie avec password_verify()
       ├─ Si correct: crée session
       └─ Si faux: affiche erreur

4. Utilisateur authentifié
   └─> Affiche l'arborescence du dossier
       └─> Clique sur un fichier

5. Clique sur un fichier .md
   └─> ?file=path/to/file.md
       └─> view.php rend le contenu
           ├─ Lit le fichier .md
           ├─ Parse Markdown → HTML
           ├─ Détecte blocs ```litegal → generateCarousel()
           │     image principale + vignettes cliquables
           ├─ Replace images: ![[image]] → src=".images/image"
           ├─ Replace tags: #tag → <span class="tag">
           ├─ Détecte liens .stl → <a class="stl-link external-link" data-stl-file="...">
           └─ Affiche avec CSS

6. Clique sur un lien STL dans une note
   └─> JS: openFileInNewTab('.stl/piece.stl')
       ├─ TabManager.createNewTab()
       ├─ TabManager.setTabFile(tabId, '.stl/piece.stl')
       └─> ?file=.stl/piece.stl (nouvel onglet dans le site)
           └─> index.php détecte extension .stl
               └─> <iframe src="viewer.php?folder=X&file=piece.stl&embed=1">
                   └─> viewer.php
                       ├─ Vérifie session auth
                       ├─ Valide chemin (anti path-traversal)
                       ├─ Charge Three.js (CDN) + STLLoader + OrbitControls
                       ├─ Rendu WebGL: éclairage 3 points, matériau blanc mat
                       └─ Canvas transparent (fond CSS #1e1e1e)
```

## Carrousel Litegal

Le plugin Obsidian **Litegal** génère des blocs ` ```litegal ` pour afficher des galeries d'images. Le serveur les détecte et les transforme en carrousel interactif.

### Syntaxe dans Obsidian

```
 ```litegal
![[Ajout Rangement Plan 1.jpeg]]
![[Ajout Rangement Plan 2.jpeg]]
![[Ajout Rangement Plan 3.jpeg]]
 ```
```

### Pipeline de traitement

```
Bloc ```litegal dans .md
    ↓ [prepare_folder.py - Local]
    • Délimiteurs ``` normalisés (espaces parasites supprimés)
    • Images ![[...]] extraites et copiées dans .images/
    • Bloc litegal conservé tel quel dans le .md
    ↓ [Upload FTP]
    ↓ [view.php - Serveur]
    • parseMarkdownToHtml() détecte ``` litegal → $in_litegal = true
    • Chaque ligne ![[image]] → extrait le nom (alias |300 ignoré)
    • Fermeture ``` → generateCarousel($images, $base_path)
    ↓
HTML: <div class="carousel"> + image principale + vignettes
      + <script> pour showCarouselImage() (JS client)
```

### Fonctions PHP concernées (`view.php`)

| Fonction | Rôle |
|----------|------|
| `parseMarkdownToHtml()` | Détecte ` ```litegal ` et accumule les noms d'images |
| `generateCarousel($images, $base)` | Génère le HTML du carrousel + balise `<script>` d'état |
| `findImage($name, $base)` | Remonte l'arborescence pour trouver `.images/` |
| `showCarouselImage()` (JS) | Gère le clic sur une vignette (défini dans `index.php`) |

### Notes techniques

- **Alias Obsidian ignorés** : `![[image.jpg|300]]` → nom extrait = `image.jpg` uniquement
- **Fermeture tolérante** : un espace devant ` ``` ` est accepté (généré par certaines versions du plugin)
- **Fallback** : si une image est introuvable, les images restantes s'affichent quand même
- **Images extraites automatiquement** : `extract_images_from_md()` scanne tout le fichier (blocs litegal inclus)

---

## Module STL 3D (v1)

Pipeline complet : détection des liens locaux → copie → transformation → affichage WebGL.

### Syntaxe dans Obsidian

Les liens STL dans Obsidian pointent vers des fichiers locaux via le protocole `file://` :

```markdown
[Ma Pièce](file:///Users/votre-nom/Documents/Impression3D/ma-piece.stl)
```

### Pipeline de traitement

```
Lien file:// dans .md (Obsidian)
    ↓ [prepare_folder.py - Local]
    • STL3DProcessor.process_folder() parcourt tous les .md
    • extractor.py détecte les liens file://*.stl par regex
    • processor.py copie le fichier vers .stl/
    • processor.py transforme le lien:
        AVANT: [Pièce](file:///Users/.../Fixation%20Phare%201.stl)
        APRÈS: [Pièce](.stl/Fixation%20Phare%201.stl)
    ↓ [Upload FTP]
    • .stl/ uploadé avec le reste du projet (non exclu)
    ↓ [view.php - Serveur]
    • Lien .stl détecté dans processInlineMarkdown()
    • Généré: <a class="stl-link external-link" data-stl-file=".stl/piece.stl">◉ Pièce</a>
    ↓ [Clic utilisateur - JS]
    • Intercepté par listener sur .stl-link[data-stl-file]
    • TabManager crée un nouvel onglet dans la barre du site
    • Navigation: ?folder=X&file=.stl/piece.stl
    ↓ [index.php]
    • Détecte extension .stl → rendu iframe (classe stl-view)
    • <iframe src="viewer.php?folder=X&file=piece.stl&embed=1">
    ↓ [viewer.php]
    • Auth session vérifiée
    • Three.js charge le .stl via STLLoader
    • Rendu WebGL avec OrbitControls
```

### Fonctions PHP concernées

| Fichier | Fonction | Rôle |
|---------|----------|------|
| `view.php` | `processInlineMarkdown()` | Détecte `.stl` dans liens, génère `stl-link` |
| `index.php` | PHP + `$is_stl_view` | Détecte `.stl` dans `?file=`, injecte l'iframe |
| `index.php` | `openFileInNewTab()` (JS) | Crée un nouvel onglet dans TabManager |
| `viewer.php` | Tout | Auth, sécurité, rendu Three.js |

### Module Python (`scripts/stl/`)

```python
from stl import STL3DProcessor

processor = STL3DProcessor()

# Traiter tout un dossier projet
count = processor.process_folder(project_path, stl_folder)

# Ou fichier par fichier
new_content, count = processor.process_file_content(content, stl_folder)
```

### Notes techniques

- **Dossier `.stl/` caché** : commence par un point → exclu de la sidebar (`$item[0] === '.'`)
- **Sécurité viewer** : `basename()` + `realpath()` + comparaison préfixe pour empêcher path-traversal
- **Canvas transparent** : `alpha: true` + `scene.background = null` → fond géré par CSS, pas affecté par le tone mapping Three.js
- **Mode embed** : `?embed=1` masque la toolbar de `viewer.php` (usage dans iframe du site)

---

## Module Dataview (v2)

Pipeline complet : parsing → extraction → exécution → rendu Markdown statique.

```python
from dataview import DataviewProcessor

processor = DataviewProcessor()

# Remplace tous les blocs dataview d'un fichier
new_content = processor.process_file_content(content, vault_base_path)

# Traiter un seul bloc
markdown = processor.process_block(block_content, vault_base_path)
```

### Architecture du Module

```
dataview/
├── data_extractor.py  # MarkdownDataExtractor
│                      #   - extract(file_path) → {file, frontmatter, headers, tasks, tags}
│                      #   Gère: YAML frontmatter, en-têtes, tâches [ ] [x], tags #emoji-tag
│
├── parser.py          # DataviewParser
│                      #   - parse(query_str) → AST structuré
│                      #   Gère: TABLE/TASK/LIST, FROM, WHERE (AND/OR imbriqués),
│                      #         GROUP BY, SORT, LIMIT, fonctions imbriquées
│
├── functions.py       # FunctionRegistry
│                      #   contains, string, replace, dateformat, choice,
│                      #   lower, upper, length, min, max
│
├── executor.py        # ExecutionEngine
│                      #   - execute(query, vault_base_path)
│                      #   Ordre garanti: WHERE → GROUP BY → SORT → LIMIT
│
├── renderer.py        # DataviewRenderer
│                      #   - render(query, results) → Markdown
│                      #   TABLE: tableau GFM | TASK: liste checkboxes | LIST: liste liens
│
└── __init__.py        # DataviewProcessor (façade)
                       #   - process_block(block, vault_base_path) → str
                       #   - process_file_content(content, vault_base_path) → str
```

## Problèmes Connus & Restrictions

### ✅ Fonctionne

- **TABLE** avec fonctions (`dateformat`, `choice`, `file.link`)
- **TASK** avec filtrage par tags (emojis inclus: `#🛒-Achat`)
- **GROUP BY** avec expressions (`replace(string(header), ...)`)
- **SORT** avec agrégations (`min(rows.line) ASC`)
- **AND/OR** imbriqués avec parenthèses
- Cellules vides affichées avec `-`
- **FROM pointant un fichier** : si le chemin cible un `.md` et non un dossier, le fichier est traité seul + warning affiché

## Configuration & Secrets

### Local (`scripts/config.py`)

Seul fichier à modifier pour une nouvelle installation. Contient :

```python
# FTP
FTP_HOST = "votre.serveur.com"
FTP_USER = "votre_user_ftp"
FTP_PASS = "mot_de_passe_secret"
FTP_DIR  = "obsidian"          # Dossier sur le serveur FTP (pas le sous-domaine)

# Site web
SITE_URL = "https://obsidian.tondomaine.com"

# Chemins images supplémentaires (hors vault Obsidian)
EXTRA_IMAGE_PATHS = [
    Path.home() / "chemin/vers/tes/images",
]
```

**⚠️ Jamais versionner ce fichier avec les vrais identifiants!** Utiliser `.env` ou variables d'environnement en production.

### Serveur (`server/config.json`)

```json
{
  "folders": {
    "Mon-Projet": {
      "path": "/chemin/ou/non-utilisé",
      "password": "$2y$10$..."  // ✅ Hash Bcrypt
    }
  }
}
```

## Performance & Limites

- **Taille max vault**: ~500 MB (test sur Hostinger)
- **Temps de conversion**: ~5-30 secondes pour 1000 fichiers
- **Upload FTP**: ~2 MB/s (dépend de la connexion)
- **Requêtes Dataview**: ~50-100 ms par requête


