#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️  Configuration — À MODIFIER pour chaque nouvelle installation
Tous les paramètres personnalisables sont ici.
"""

import os
from pathlib import Path

# ── FTP ────────────────────────────────────────────────────────────────────────
FTP_HOST = os.getenv("FTP_HOST", "votre.serveur.com")
FTP_USER = os.getenv("FTP_USER", "votre_utilisateur_ftp")
FTP_PASS = os.getenv("FTP_PASS", "votre_mot_de_passe_ftp")
FTP_DIR  = os.getenv("FTP_DIR",  "obsidian")

# ── Site web ───────────────────────────────────────────────────────────────────
SITE_URL = "https://obsidian.votre-domaine.com"

# ── Chemins images supplémentaires ────────────────────────────────────────────
# Dossiers où chercher les images/pièces jointes hors du vault Obsidian.
# Le script essaie d'abord les emplacements standards (./Attachments, etc.),
# puis ceux-ci dans l'ordre. Ajouter/remplacer avec son propre chemin.
EXTRA_IMAGE_PATHS = [
    # Exemple:
    # Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Attachments",
    # Path.home() / "chemin/vers/ton/dossier/images",
]

# ── Interne (ne pas modifier) ──────────────────────────────────────────────────
OUTPUT_DIR  = Path(__file__).parent
CONFIG_FILE = OUTPUT_DIR.parent / "server" / "config.json"

CORE_FILES = [
    "index.php",
    "view.php",
    "viewer.php",
    "style.css",
    "config.json",
    ".htaccess",
    "README.md",
    "Obsidian_logo.png",
]
