#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from ftplib import all_errors
from ftp_utils import connect_ftp, ensure_ftp_dir, upload_file
from config import CORE_FILES, FTP_DIR, SITE_URL

def main():
    print("=" * 60)
    print("📤 UPLOAD FICHIERS CORE - Obsidian Web")
    print("=" * 60)

    ftp = connect_ftp()
    if not ftp:
        sys.exit(1)

    if not ensure_ftp_dir(ftp):
        sys.exit(1)

    print("📄 Upload des fichiers core...\n")
    scripts_dir = Path(__file__).parent
    server_dir  = scripts_dir.parent / "server"

    for file in CORE_FILES:
        local_path = server_dir / file
        if local_path.exists():
            upload_file(ftp, local_path, file)
        else:
            print(f"  ⚠️  {file} non trouvé")

    ftp.quit()

    print(f"\n" + "=" * 60)
    print("✅ UPLOAD FICHIERS CORE TERMINÉ!")
    print("=" * 60)
    print(f"\n🔗 Testez: {SITE_URL}/")

if __name__ == '__main__':
    main()
