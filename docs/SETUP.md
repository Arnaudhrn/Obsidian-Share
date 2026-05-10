# 🚀 Installation & Configuration

## Prérequis

- **Mac** avec Python 3.6+
- **Hostinger** (ou serveur VPS similaire)
- **Accès FTP** au serveur
- **Obsidian** avec un vault

## 1️⃣ Configuration Locale (Mac)

### Étape 1: Cloner ou organiser le projet

```bash
cd ~/Desktop/obsidian-share
# Vérifier la structure
ls -la
# Vous devez avoir: server/, scripts/, projects/, docs/, logo.png
```

### Étape 2: Configurer `scripts/config.py`

C'est le **seul fichier à modifier** pour une nouvelle installation. Éditez-le avec un éditeur de texte :

```python
# FTP
FTP_HOST = "votre.serveur.com"           # Adresse du serveur FTP
FTP_USER = "votre_user_ftp"              # Votre user FTP
FTP_PASS = "votre_mot_de_passe"      # Votre mot de passe FTP
FTP_DIR  = "obsidian"                # Dossier sur le serveur FTP

# Site web
SITE_URL = "https://obsidian.tondomaine.com"

# Chemins images supplémentaires (si vos images sont hors vault)
EXTRA_IMAGE_PATHS = [
    Path.home() / "chemin/vers/ton/dossier/images",
]
```

**⚠️ Jamais committer ce fichier avec les vrais identifiants!**

### Étape 3: Tester la connexion FTP

```bash
python3 -c "from scripts.ftp_utils import connect_ftp; connect_ftp()" 
# Ou vérifier avec un terminal:
ftp votre.serveur.com
# user: votre_user_ftp
# pass: xxxxxxxx
```

## 2️⃣ Première Conversion

### Lancer le script

```bash
python3 scripts/prepare_folder.py
```

### Étapes interactives

1. **Glisser-déposer le dossier source**
   ```
   📁 Glisse-dépose le dossier à préparer (ou tape le chemin):
   > /Users/votre-nom/Documents/Mon-Projet/
   ```

2. **Vérifier le dossier reconnu**
   ```
   ✅ Dossier trouvé: Mon-Projet
   Fichiers trouvés: 45 .md files
   ```

3. **Confirmer la conversion**
   ```
   Continuer? (y/n)
   ```

4. **Attendre la conversion**
   ```
   ⏳ Traitement en cours...
   ✅ Mot de passe généré: Abc1234567
   ✅ Dossier créé: projects/Mon-Projet (share)/
   ✅ Uploading to FTP...
   ```

5. **Succès!**
   ```
   ✅ Conversion terminée!
   Mot de passe: Abc1234567
   URL: https://obsidian.votre-domaine.com/?folder=Mon-Projet
   ```

## 3️⃣ Configuration Serveur (Hostinger)

### Accès FTP

```bash
ftp votre.serveur.com
# user: votre_user_ftp
# pass: xxxxxxxx
```

### Structure attendue

Une fois l'upload fait, vous devez avoir:

```
/public_html/obsidian/
├── index.php                    # ✅ Depuis server/
├── view.php                     # ✅ Depuis server/
├── style.css                    # ✅ Depuis server/
├── config.json                  # ✅ Depuis server/ (avec pwd)
├── .htaccess                    # ✅ Depuis server/
├── logo.png                     # ✅ Depuis racine
│
├── Mon-Projet (share)/  # ✅ Depuis projects/
│   ├── .images/                 # ✅ Images ICI (pas à la racine !)
│   ├── 0 Intro/
│   ├── 1 Mécanique/
│   └── ...
│
└── Mon-Projet-2 (share)/          # ✅ Depuis projects/ (exemple)
    └── ...
```

> ⚠️ **Piège fréquent :** Ne jamais placer `.images/` directement sous `obsidian/`.
> PHP remonte depuis le fichier note pour trouver `.images/` — il cherche dans
> `Mon-Projet (share)/.images/`, pas dans le dossier FTP_DIR racine.

### Vérifier les permissions

```bash
# Via FTP:
# Permissions doivent être 644 pour fichiers, 755 pour dossiers
# Ou via FileZilla: Tools → File Attributes

# Fichiers critiques:
# - config.json: 644 (lisible par PHP)
# - .htaccess: 644 (reconnu par Apache)
# - logo.png: 644
```

### Tester l'accès

```
https://obsidian.votre-domaine.com/
```

Si erreur:
1. Vérifier que `index.php` est bien là
2. Vérifier que `config.json` existe
3. Vérifier les erreurs PHP dans Hostinger → Erreurs

## 4️⃣ Ajouter un Nouveau Dossier

### Répéter pour chaque vault/dossier

```bash
python3 scripts/prepare_folder.py
# Glisse le nouveau dossier
# Génère nouveau mot de passe
# Upload automatiquement
```

Le nouveau dossier apparaît automatiquement sur la page d'accueil.

## 5️⃣ Mettre à Jour un Dossier Existant

### Option 1: Relancer le script (recommandé)

```bash
python3 scripts/prepare_folder.py
# Glisse le MÊME dossier source
# Génère un nouveau mot de passe (ou réutilise l'ancien)
# Remplace l'ancien dossier (share) sur le serveur
```

### Option 2: Manuel

```bash
# 1. Supprimer l'ancien sur le serveur (FTP)
# 2. Upload manuellement la nouvelle version
```

## 6️⃣ Changer un Mot de Passe

### Option 1: Via le script

```bash
python3 scripts/prepare_folder.py
# Relancer sur le même dossier
# Il demande si vous voulez garder l'ancien mot de passe
```

### Option 2: Manuellement

1. Ouvrir `server/config.json`
2. Trouver l'entrée du dossier
3. Générer un nouveau hash Bcrypt
4. Uploader sur le serveur

**Script rapide pour générer un hash :**

```python
import bcrypt
password = "nouveau_mot_de_passe"
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
print(f'"password": "{hash}"')
```

## 7️⃣ Personnaliser les Styles

Éditez `server/style.css`:

```css
:root {
  --bg-primary: #1a1a1a;        /* Fond */
  --accent-primary: #7f6df2;    /* Violet principal */
  --accent-secondary: #a594f9;  /* Lavande */
  --text-primary: #e3e3e3;      /* Texte */
}
```

Puis re-upload `style.css` sur le serveur.

## ⚡ Scripts Disponibles

### `prepare_folder.py`
- Conversion complète: Obsidian → Web
- Gère les images, Dataview, mot de passe
- Upload automatique FTP

### `upload_core_files.py`
- Upload juste `index.php`, `view.php`, `style.css`, `.htaccess`
- Utile pour des mises à jour PHP sans toucher aux projets

### `upload_folder.py`
- Upload un dossier spécifique
- Pour tester ou re-uploader un projet

### `upload_to_ftp.py`
- Script maître d'orchestration
- Peut être appelé seul ou par d'autres

### `upload_missing_images.py`
- Compare les images locales (`projects/[nom]/.images/`) vs serveur
- Uploade uniquement les fichiers absents (diff FTP)
- À lancer après chaque `prepare_folder.py` ou si des images manquent sur le site
- Utilise navigation par `cwd` successifs (fiable avec espaces/parenthèses)

## 🐛 Dépannage

| Problème | Cause | Solution |
|----------|-------|----------|
| "Erreur de connexion FTP" | Identifiants incorrects | Vérifier `config.py` |
| "Module 'yaml' not found" | Python dépendence manquante | `pip3 install pyyaml` |
| "Erreur 500" sur le serveur | Permissions, config.json manquant | Vérifier les uploads, permissions |
| "Images manquantes" | Dossier Attachments non trouvé | Vérifier chemin Attachments |
| Images visibles en FTP mais pas sur le site | `.images/` au mauvais niveau | Lancer `upload_missing_images.py` (place images dans `[projet]/.images/`) |
| "Mot de passe refusé" | Hash incorrect | Relancer `prepare_folder.py` |

## 📚 Ressources

- **ARCHITECTURE.md** → Comprendre l'architecture
- **CHANGELOG.md** → Historique des sessions
- **Module Dataview** → Voir `scripts/dataview/README.md`
