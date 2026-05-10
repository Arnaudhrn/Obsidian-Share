# 🔐 Obsidian Web Viewer

Un visualiseur web statique pour partager vos coffres Obsidian en ligne avec authentification par mot de passe.

## 🎯 Fonctionnalités

- 📂 **Sélection de dossiers** à partager (contrôle complet des contenus)
- 🔐 **Authentification** par mot de passe (15 caractères aléatoires, hashés en Bcrypt)
- 🎨 **Style personnalisé** (dark mode, violet/lavande, identique à Obsidian)
- 📊 **Support Dataview** (tables, listes de tâches)
- 🖼️ **Carrousel d'images** via blocs ` ```litegal ` (image principale + vignettes)
- 🔩 **Viewer 3D STL** (fichiers CAO affichés dans un onglet du site, rotation/zoom/pan)
- 🔗 **Liens Obsidian** (affichage en badges, non-fonctionnels par design)
- 🔍 **Barre de recherche** (filtre les fichiers dans la sidebar, affiche l'arborescence complète des dossiers parents)
- 🗂️ **Système d'onglets** (navigation multi-fichiers, fermeture intelligente vers l'onglet précédent)
- ⚡ **URLs propres** via `.htaccess`

## 📁 Structure du Projet

```
obsidian-share/
├── server/                        # 📦 Fichiers serveur (à uploader)
│   ├── index.php                  # Page d'accueil + authentification + onglets
│   ├── view.php                   # Affichage du contenu Markdown
│   ├── viewer.php                 # Visualisateur 3D STL (Three.js WebGL)
│   ├── style.css                  # Styles (dark mode)
│   ├── config.json                # Mots de passe (généré par prepare_folder.py)
│   └── .htaccess                  # Réécriture URLs + sécurité
│
├── scripts/                       # 🔧 Outils de transformation (local)
│   ├── prepare_folder.py          # Convertit Obsidian → Web
│   ├── config.py                  # Configuration (FTP, URL, chemins) ⚙️ à modifier
│   ├── ftp_utils.py               # Fonctions FTP réutilisables
│   ├── upload_core_files.py       # Upload fichiers PHP/CSS/config
│   ├── upload_folder.py           # Upload un dossier spécifique
│   ├── upload_to_ftp.py           # Orchestration uploads
│   ├── upload_missing_images.py   # Synchronise les images manquantes (FTP diff)
│   ├── dataview/                  # Module Dataview (isolé, réutilisable)
│   │   ├── __init__.py
│   │   ├── parser.py              # Parse les blocs Dataview
│   │   ├── executor.py            # Exécute les requêtes
│   │   ├── evaluator.py           # Évalue les conditions WHERE
│   │   └── README.md              # Doc du module
│   └── stl/                       # Module STL 3D (isolé, réutilisable)
│       ├── __init__.py            # Façade STL3DProcessor
│       ├── extractor.py           # Détecte les liens file:// .stl
│       ├── processor.py           # Copie + transforme les liens
│       └── README.md              # Doc du module
│
├── projects/                      # 📂 Dossiers générés (après prepare_folder.py)
│   ├── Mon-Projet (share)/        # Exemple: généré automatiquement
│   └── ...
│
├── docs/                          # 📚 Documentation
│   ├── ARCHITECTURE.md            # Explique comment ça marche
│   ├── SETUP.md                   # Installation et configuration
│   └── CHANGELOG.md               # Historique des sessions
│
└── .gitignore
```

## 🚀 Installation Rapide

### 1. Sur votre Mac (préparation locale)

```bash
python3 scripts/prepare_folder.py
```

Le script vous demandera :
1. Le chemin du dossier Obsidian à partager (drag-drop)
2. Génère un mot de passe aléatoire
3. Crée le dossier `projects/Nom du projet (share)/`
4. Met à jour `server/config.json`

### 2. Sur Hostinger (serveur)

Via FTP vers `/public_html/obsidian/` (ou votre dossier FTP_DIR) :
```
server/index.php
server/view.php
server/style.css
server/config.json
server/.htaccess
Mon-Projet (share)/
... (autres dossiers)
```

**⚠️ Ne PAS uploader :**
- `scripts/` (outils locaux)
- `docs/` (documentation)
- `prepare_folder.py` (script Python local)

## 📋 Workflow Complet

```bash
# 1. Préparer localement
python3 scripts/prepare_folder.py
# → Glissez votre dossier Obsidian dans le Terminal
# → Mot de passe généré: xxxxxxxx
# → Dossier créé: projects/Mon-Projet (share)/

# 2. Upload manuel ou via script
python3 scripts/upload_to_ftp.py  # Upload tout
# ou
python3 scripts/upload_folder.py   # Upload un dossier spécifique

# 3. Accéder au site
# https://obsidian.votre-domaine.com/
# Sélectionner le projet → Entrer le mot de passe
```

## 🔧 Configuration

### `server/config.json`

Généré automatiquement par `prepare_folder.py`:

```json
{
    "folders": {
        "Mon-Projet": {
            "path": "./Mon-Projet (share)",
            "password": "$2y$10$hash..."
        }
    }
}
```

### `scripts/config.py`

À configurer avec vos identifiants — c'est le seul fichier à modifier :

```python
FTP_HOST = "votre.serveur.com"
FTP_USER = "votre_utilisateur_ftp"
FTP_PASS = "votre_mot_de_passe"
FTP_DIR  = "obsidian"
SITE_URL = "https://obsidian.votre-domaine.com"
```

## 🎨 Personnalisation

Modifiez `server/style.css` pour :
- Couleurs (variables CSS `:root`)
- Polices (`font-family`)
- Espacements (`padding`, `margin`)

Principales variables CSS :
```css
--bg-primary: #1a1a1a;
--accent-primary: #7f6df2;      /* Violet */
--accent-secondary: #a594f9;    /* Lavande */
--text-primary: #e3e3e3;        /* Gris clair */
```

## 📊 Support Markdown / Dataview

| Élément | Support |
|---------|---------|
| Titres (H1-H6) | ✅ |
| Gras, Italique | ✅ |
| Code inline/bloc | ✅ |
| Listes | ✅ |
| Tables Markdown | ✅ |
| Blocs Dataview | ✅ (partiellement) |
| Carrousel ` ```litegal ` | ✅ |
| Images Wiki `![[]]` | ✅ |
| Images redimensionnées `![[image\|300]]` | ✅ (width en px) |
| Liens Obsidian `[[]]` | ✅ (badges) |
| Tags `#hashtag` | ✅ (badges) |
| Fichiers STL `[](file://*.stl)` | ✅ (viewer 3D interactif) |

## 🔒 Sécurité

- ✅ `config.json` non accessible (`.htaccess`)
- ✅ Mots de passe 15 caractères générés avec `secrets.choice()` (cryptographiquement sûr), hashés Bcrypt
- ✅ HTTPS forcé via `.htaccess` (redirection 301)
- ✅ En-têtes sécurité HTTP : `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`
- ✅ Cookies de session PHP sécurisés (`httponly`, `samesite=Lax`, `secure`)
- ✅ Protection brute force : blocage par IP après 500 tentatives / 24h (fichier `/tmp`)
- ✅ Anti path-traversal sur `index.php` (`realpath` + vérification préfixe)
- ✅ Anti path-traversal sur `viewer.php` (`basename` + `realpath`)
- ✅ Dossiers `.images/` et `.stl/` cachés (sidebar + convention point Unix)
- ⚠️ **À faire** : Configurer vos identifiants dans `scripts/config.py`

## ❓ FAQ

**Q: Comment changer un mot de passe?**
A: Relancez `prepare_folder.py` sur le même dossier pour générer un nouveau.

**Q: Puis-je partager plusieurs dossiers?**
A: Oui! Lancez le script pour chaque dossier source.

**Q: Les images ne s'affichent pas?**
A: Vérifiez que le dossier `.images/` a été créé et contient les images.

## 📖 Documentation Détaillée

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** → Explique l'architecture et le flux de données
- **[SETUP.md](docs/SETUP.md)** → Installation complète
- **[CHANGELOG.md](docs/CHANGELOG.md)** → Historique des sessions de travail

## 🐛 Dépannage Rapide

| Problème | Solution |
|----------|----------|
| "Erreur 500" | Vérifier permissions FTP, chemins relatifs |
| "Images manquantes" | Vérifier dossier `.images/`, noms sensibles à la casse |
| Images en FTP mais invisibles sur le site | `.images/` doit être dans `[projet]/.images/`, pas à la racine `obsidian/` — lancer `upload_missing_images.py` |
| "Config not found" | Vérifier que `config.json` est uploadé |

## 📝 Licence

Usage personnel.
