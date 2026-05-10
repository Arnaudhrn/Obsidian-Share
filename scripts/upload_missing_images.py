#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synchronise les images locales vers le dossier .images/ du serveur FTP.
- Compare les fichiers locaux vs serveur
- Uploade uniquement les images absentes du serveur
- Utilise cd/cwd pour naviguer (évite les problèmes de chemins avec espaces)
"""

import sys
from pathlib import Path
from ftplib import FTP, all_errors

sys.path.insert(0, str(Path(__file__).parent))
from config import FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR

# Dossier source local
PROJECT_NAME = "Mon-Projet (share)"  # ⚙️ Remplacer par le nom de votre projet
LOCAL_IMAGES = Path(__file__).parent.parent / "projects" / PROJECT_NAME / ".images"


def connect():
    print(f"🔗 Connexion à {FTP_HOST}...")
    ftp = FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=120)
    ftp.set_pasv(True)
    print(f"✓ Connecté")
    return ftp


def navigate_to_images(ftp):
    """Navigue dans le dossier .images/ en faisant des cd successifs (plus fiable que les chemins longs)"""
    # Retour à la racine FTP
    ftp.cwd('/')

    # Naviguer étape par étape
    for part in FTP_DIR.strip('/').split('/'):
        if part:
            try:
                ftp.cwd(part)
            except:
                ftp.mkd(part)
                ftp.cwd(part)

    # Naviguer dans le dossier projet
    try:
        ftp.cwd(PROJECT_NAME)
    except:
        ftp.mkd(PROJECT_NAME)
        ftp.cwd(PROJECT_NAME)

    # Naviguer dans .images/
    try:
        ftp.cwd('.images')
    except:
        ftp.mkd('.images')
        ftp.cwd('.images')

    print(f"✓ Dossier distant : {ftp.pwd()}\n")


def get_remote_files(ftp):
    """Liste les fichiers présents sur le serveur (on est déjà dans .images/)"""
    try:
        return set(ftp.nlst())
    except:
        return set()


def main():
    print("=" * 60)
    print("🖼️  SYNCHRONISATION IMAGES → SERVEUR")
    print("=" * 60)

    if not LOCAL_IMAGES.exists():
        print(f"❌ Dossier local introuvable : {LOCAL_IMAGES}")
        sys.exit(1)

    local_files = [f for f in sorted(LOCAL_IMAGES.iterdir()) if f.is_file()]
    print(f"📁 {len(local_files)} images locales\n")

    ftp = connect()
    navigate_to_images(ftp)

    # Lister les fichiers déjà présents
    remote_files = get_remote_files(ftp)
    print(f"   → {len(remote_files)} déjà sur le serveur\n")

    uploaded = 0
    skipped = 0
    failed = 0

    for local_file in local_files:
        name = local_file.name

        if name in remote_files:
            print(f"  ⏭  {name}")
            skipped += 1
        else:
            size_kb = local_file.stat().st_size // 1024
            print(f"  ⬆️  {name} ({size_kb} Ko)...")
            try:
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f'STOR {name}', f)
                print(f"     ✓ OK")
                uploaded += 1
            except Exception as e:
                print(f"     ✗ Erreur: {e}")
                failed += 1
                # Reconnexion si la connexion est corrompue
                try:
                    ftp.voidcmd('NOOP')
                except:
                    print(f"     🔄 Reconnexion...")
                    try:
                        ftp = connect()
                        navigate_to_images(ftp)
                    except Exception as e2:
                        print(f"     ❌ Reconnexion impossible: {e2}")
                        break

    try:
        ftp.quit()
    except:
        pass

    print(f"\n{'=' * 60}")
    print(f"✅ Résultat : {uploaded} uploadé(s)  |  {skipped} déjà présent(s)  |  {failed} échoué(s)")
    print("=" * 60)

    if failed > 0:
        print("\n⚠️  Relance le script pour réessayer les fichiers échoués.")


if __name__ == '__main__':
    main()
