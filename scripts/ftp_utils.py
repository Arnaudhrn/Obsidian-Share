#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitaires FTP réutilisables
Fonctions communes pour upload, gestion de connexion
"""

import sys
import time
from pathlib import Path
from ftplib import FTP, all_errors
from config import FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR

MAX_RETRIES = 3
RETRY_DELAY = 2  # secondes entre chaque tentative


def connect_ftp():
    """Connecter à FTP et retourner l'objet FTP"""
    try:
        print(f"🔗 Connexion FTP à {FTP_HOST}...\n")
        ftp = FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=120)
        print(f"✓ Connecté en tant que {FTP_USER}\n")
        return ftp
    except all_errors as e:
        print(f"❌ Erreur FTP: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def is_ftp_alive(ftp):
    """Vérifier si la connexion FTP est encore saine via un NOOP"""
    try:
        ftp.voidcmd('NOOP')
        return True
    except:
        return False


def reconnect_ftp():
    """Créer une nouvelle connexion FTP et se positionner dans FTP_DIR"""
    ftp = connect_ftp()
    if not ftp:
        return None
    if not ensure_ftp_dir(ftp):
        return None
    return ftp


def ensure_ftp_dir(ftp):
    """Vérifier/créer le répertoire FTP principal"""
    try:
        ftp.cwd(FTP_DIR)
        print(f"✓ Accès au dossier: {FTP_DIR}\n")
        return True
    except:
        print(f"⚠️  Création du dossier {FTP_DIR}...")
        try:
            ftp.mkd(FTP_DIR)
            ftp.cwd(FTP_DIR)
            print(f"✓ Dossier créé\n")
            return True
        except Exception as e:
            print(f"❌ Erreur création dossier: {e}")
            return False


def upload_file(ftp, local_path, remote_path):
    """Uploader un fichier unique"""
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  ✓ {remote_path}")
        return True
    except Exception as e:
        print(f"  ✗ Erreur: {remote_path} — {e}")
        return False


def _ensure_remote_dirs(ftp, remote_file):
    """Créer les sous-dossiers distants nécessaires pour un fichier"""
    remote_parts = remote_file.split('/')[:-1]
    for i in range(1, len(remote_parts) + 1):
        remote_folder = '/'.join(remote_parts[:i])
        try:
            ftp.mkd(remote_folder)
        except:
            pass


def _upload_single_file(ftp, local_path, remote_file):
    """
    Tente d'uploader un fichier avec retry et reconnexion automatique.
    Retourne (ftp, success) — ftp peut être un nouvel objet si reconnexion.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        # Vérifier la connexion avant chaque tentative (sauf la première)
        if attempt > 1:
            if not is_ftp_alive(ftp):
                print(f"    🔄 Reconnexion FTP (tentative {attempt}/{MAX_RETRIES})...")
                ftp = reconnect_ftp()
                if not ftp:
                    print(f"    ❌ Reconnexion échouée, abandon de {local_path.name}")
                    return None, False
            time.sleep(RETRY_DELAY)

        try:
            _ensure_remote_dirs(ftp, remote_file)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            if attempt > 1:
                print(f"  ✓ {remote_file} (réussi à la tentative {attempt})")
            else:
                print(f"  ✓ {remote_file}")
            return ftp, True

        except Exception as e:
            err_msg = str(e)[:60]
            if attempt < MAX_RETRIES:
                print(f"  ⚠️  {remote_file} - {err_msg} → retry {attempt}/{MAX_RETRIES}")
                # Connexion potentiellement corrompue : forcer reconnexion au prochain tour
                try:
                    ftp.abort()
                except:
                    pass
            else:
                print(f"  ✗ {remote_file} - {err_msg} (échec après {MAX_RETRIES} tentatives)")

    return ftp, False


def upload_directory(ftp, local_dir, remote_dir):
    """Uploader un dossier récursivement avec retry et reconnexion automatique"""
    try:
        if remote_dir and remote_dir.strip():
            try:
                ftp.mkd(remote_dir)
            except:
                pass

        ignore_items = {'.DS_Store', '.obsidian', '__pycache__', '.git', '.images'}
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.tif'}

        all_files = [
            item for item in Path(local_dir).rglob('*')
            if item.is_file()
            and item.name not in ignore_items
            and not item.name.startswith('.')
        ]
        # Images en dernier pour éviter que les gros fichiers corrompent la session
        all_files.sort(key=lambda f: f.suffix.lower() in image_exts)

        failed = []

        for item in all_files:
            try:
                rel_path = item.relative_to(local_dir)
                if remote_dir and remote_dir.strip():
                    remote_file = f"{remote_dir}/{rel_path}".replace('\\', '/')
                else:
                    remote_file = str(rel_path).replace('\\', '/')

                ftp, success = _upload_single_file(ftp, item, remote_file)

                if ftp is None:
                    # Reconnexion impossible : on annule tout
                    print(f"\n  ❌ Connexion FTP irrécupérable, arrêt de l'upload.")
                    break

                if not success:
                    failed.append((item, remote_file))

            except Exception as e:
                print(f"  ⚠️  Erreur traitement {item.name}: {str(e)[:50]}")
                failed.append((item, remote_file if 'remote_file' in dir() else item.name))

        # Second passage sur les fichiers échoués avec une connexion fraîche
        if failed:
            print(f"\n  🔁 Second passage sur {len(failed)} fichier(s) échoué(s)...")
            ftp_fresh = reconnect_ftp()
            if ftp_fresh:
                still_failed = []
                for item, remote_file in failed:
                    ftp_fresh, success = _upload_single_file(ftp_fresh, item, remote_file)
                    if ftp_fresh is None:
                        still_failed.extend([(i, r) for i, r in failed])
                        break
                    if not success:
                        still_failed.append((item, remote_file))

                if still_failed:
                    print(f"\n  ❌ {len(still_failed)} fichier(s) impossible(s) à uploader :")
                    for item, remote_file in still_failed:
                        print(f"     • {remote_file}")
                else:
                    print(f"  ✓ Tous les fichiers récupérés au second passage!")

                ftp_fresh.quit()
            else:
                print(f"  ❌ Impossible de reconnecter pour le second passage.")
                print(f"  Fichiers non uploadés :")
                for item, remote_file in failed:
                    print(f"     • {remote_file}")

    except Exception as e:
        print(f"  ✗ Erreur lors de l'upload du dossier {local_dir}: {e}")


def ftp_folder_exists(ftp, folder_name: str) -> bool:
    """Vérifier si un dossier existe sur FTP"""
    try:
        ftp.cwd(folder_name)
        ftp.cwd('..')
        return True
    except:
        return False


def remove_ftp_folder(ftp, folder_name: str) -> bool:
    """Supprimer récursivement un dossier FTP"""
    try:
        def remove_tree_simple(ftp, path):
            """Supprimer un dossier et son contenu"""
            try:
                ftp.cwd(path)
                lines = []
                ftp.dir(lines.append)

                for line in lines:
                    parts = line.split()
                    if len(parts) < 9:
                        continue

                    is_dir = line.startswith('d')
                    name = ' '.join(parts[8:])

                    if name in ['.', '..']:
                        continue

                    try:
                        if is_dir:
                            remove_tree_simple(ftp, name)
                        else:
                            ftp.delete(name)
                    except:
                        pass

                ftp.cwd('..')
                try:
                    ftp.rmd(path)
                except:
                    pass
            except Exception as e:
                pass

        remove_tree_simple(ftp, folder_name)
        return True
    except Exception as e:
        print(f"  ⚠️  Erreur suppression: {e}")
        return False
