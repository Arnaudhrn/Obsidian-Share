#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from ftplib import all_errors
from ftp_utils import connect_ftp, ensure_ftp_dir, upload_directory
from config import FTP_DIR, SITE_URL

def main():
    print("=" * 60)
    print("📁 UPLOAD DOSSIER - Obsidian Web Viewer")
    print("=" * 60)

    ftp = connect_ftp()
    if not ftp:
        sys.exit(1)

    if not ensure_ftp_dir(ftp):
        sys.exit(1)

    folder_name = "Mon-Projet (share)"  # ⚙️ Remplacer par le nom de votre projet
    print(f"📁 Upload du dossier {folder_name}...\n")
    local_path = Path(__file__).parent / folder_name
    if local_path.exists():
        upload_directory(ftp, local_path, folder_name)
    else:
        print(f"⚠️  Le dossier {folder_name} n'existe pas!")
        ftp.quit()
        sys.exit(1)

    ftp.quit()

    print(f"\n" + "=" * 60)
    print("✅ UPLOAD DOSSIER TERMINÉ!")
    print("=" * 60)
    print(f"\n🔗 URL: {SITE_URL}/")

if __name__ == '__main__':
    main()
