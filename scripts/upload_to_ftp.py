#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from ftplib import all_errors
from ftp_utils import connect_ftp, ensure_ftp_dir, upload_file, upload_directory
from config import CORE_FILES, FTP_DIR, SITE_URL

# Dossiers à uploader
FOLDERS_TO_UPLOAD = [
    "Mon-Projet (share)",  # ⚙️ Remplacer par le(s) nom(s) de vos projets
]

def main():
    print("=" * 60)
    print("📤 UPLOAD FTP COMPLET - Obsidian Web Viewer")
    print("=" * 60)

    ftp = connect_ftp()
    if not ftp:
        sys.exit(1)

    if not ensure_ftp_dir(ftp):
        sys.exit(1)

    # Uploader les fichiers core
    print("📄 Upload des fichiers core...\n")
    for file in CORE_FILES:
        local_path = Path(__file__).parent / file
        if local_path.exists():
            upload_file(ftp, local_path, file)
        else:
            print(f"  ⚠️  {file} non trouvé")

    # Uploader les dossiers
    for folder in FOLDERS_TO_UPLOAD:
        print(f"\n📁 Upload du dossier {folder}...\n")
        local_path = Path(__file__).parent / folder
        if local_path.exists():
            upload_directory(ftp, local_path, folder)
        else:
            print(f"  ⚠️  {folder} non trouvé")

    ftp.quit()

    print(f"\n" + "=" * 60)
    print("✅ UPLOAD COMPLET TERMINÉ!")
    print("=" * 60)
    print(f"\n🔗 URL: {SITE_URL}/")
    print(f"\n⚠️  N'oubliez pas de changer le mot de passe FTP sur Hostinger!")
    print("=" * 60)

if __name__ == '__main__':
    main()
