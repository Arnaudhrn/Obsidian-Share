# 🚀 Installation sur une nouvelle machine

Guide pour installer **Obsidian Share** sur un nouveau Mac.

---

## Ce dont tu as besoin

- Mac avec **Python 3** installé (vérifier : ouvre Terminal et tape `python3 --version`)
- Le dossier **obsidian-share** (reçu par transfert, clé USB, etc.)
- Un accès **FTP** au serveur (identifiants à configurer)

---

## Étape 1 — Placer le dossier

Place le dossier `obsidian-share` où tu veux sur ton Mac.  
Exemple courant : `Documents`, `Bureau`, ou un dossier dédié.

> ⚠️ Note bien le chemin complet, tu en auras besoin aux étapes suivantes.  
> Exemple : `/Users/tonnom/Documents/obsidian-share`

---

## Étape 2 — Installer les dépendances Python

Ouvre le Terminal et tape :

```bash
pip3 install bcrypt pyyaml
```

---

## Étape 3 — Configurer le fichier `config.py`

Tout ce qui est à personnaliser se trouve dans **un seul fichier** :  
`obsidian-share/scripts/config.py`

Ouvre-le avec un éditeur de texte et modifie les sections suivantes :

### Identifiants FTP
```python
FTP_HOST = "adresse.de.ton.serveur"
FTP_USER = "ton_utilisateur_ftp"
FTP_PASS = "ton_mot_de_passe_ftp"
FTP_DIR  = "obsidian"   # nom du dossier sur le serveur FTP (pas le sous-domaine)
```

### URL de ton site
```python
SITE_URL = "https://ton-sous-domaine.ton-domaine.com"
```

### Chemins images supplémentaires
Le script cherche d'abord les images dans les emplacements standards (dossier `Attachments` à côté du vault). Si tes images sont ailleurs, ajoute ton chemin ici :

```python
EXTRA_IMAGE_PATHS = [
    Path.home() / "chemin/vers/ton/dossier/images",
]
```

Exemple si tes images sont sur iCloud :
```python
EXTRA_IMAGE_PATHS = [
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Attachments",
]
```

> ⚠️ Ne jamais partager `config.py` avec tes identifiants dedans.

> **Note :** Les fichiers STL n'ont pas besoin de configuration — le script les détecte automatiquement depuis les liens `file://` dans tes notes Obsidian et les copie lui-même.

---

## Étape 5 — Créer l'application lanceur (Automator)

1. Ouvre **Automator** (Cmd+Espace → "Automator")
2. Nouveau document → choisir **Application**
3. Dans la barre de recherche à gauche, tape **"script shell"**
4. Double-clique sur **"Exécuter un script Shell"** pour l'ajouter
5. Colle ce texte dans la zone du script en **adaptant les deux chemins** :

```bash
open "/chemin/vers/ton/coffre/obsidian"
osascript -e 'tell application "Terminal" to do script "cd \"/chemin/vers/obsidian-share/scripts\" && python3 prepare_folder.py"'
```

**Les deux chemins à remplacer :**

| Placeholder | Remplacer par |
|---|---|
| `/chemin/vers/ton/coffre/obsidian` | Le chemin de ton vault Obsidian |
| `/chemin/vers/obsidian-share/scripts` | Exemple : `/Users/tonnom/Documents/obsidian-share/scripts` |

6. **Fichier → Enregistrer** → nomme-la `Obsidian Share` → sauvegarde dans `/Applications`

---

## Étape 6 — Ajouter le logo (optionnel)

1. Ouvre l'image du logo Obsidian dans Aperçu → **Cmd+A** puis **Cmd+C** (copier)
2. Clic droit sur `Obsidian Share.app` dans `/Applications` → **Lire les informations**
3. Clique sur l'icône en haut à gauche de la fenêtre info → **Cmd+V** (coller)

---

## Utilisation au quotidien

1. **Cmd+Espace** → tape "Obsidian Share" → **Entrée**
2. Le Finder s'ouvre sur ton coffre Obsidian
3. Le Terminal s'ouvre et attend que tu glisses un dossier dedans
4. Glisse le dossier à partager → le script fait tout automatiquement

---

## En cas de problème

| Problème | Solution |
|---|---|
| `python3: command not found` | Installer Python 3 depuis [python.org](https://python.org) |
| `ModuleNotFoundError: bcrypt` | Relancer `pip3 install bcrypt pyyaml` |
| `EOFError` dans Automator | Le chemin du script est incorrect — vérifier l'étape 5 |
| Connexion FTP échouée | Vérifier les identifiants dans `ftp_config.py` |
| Images manquantes après upload | Vérifier le chemin des images à l'étape 4 |
| Le Finder ne s'ouvre pas au bon endroit | Corriger le premier chemin dans Automator |
