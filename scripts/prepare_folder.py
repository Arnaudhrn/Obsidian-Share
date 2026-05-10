#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
import string
import secrets
import re
from pathlib import Path
from typing import Set, Dict, List, Tuple
from ftplib import FTP, all_errors
from ftp_utils import connect_ftp, ensure_ftp_dir, upload_directory, remove_ftp_folder, ftp_folder_exists
from config import FTP_DIR, FTP_USER, FTP_PASS, FTP_HOST, SITE_URL, EXTRA_IMAGE_PATHS
from stl import STL3DProcessor
try:
    import yaml
except ImportError:
    yaml = None

def parse_yaml_simple(yaml_text: str) -> Dict:
    """Simple YAML parser for basic key-value pairs and lists when yaml module is not available"""
    result = {}
    lines = yaml_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith('#'):
            i += 1
            continue

        if ':' not in stripped:
            i += 1
            continue

        key, value = stripped.split(':', 1)
        key = key.strip()
        value = value.strip()

        # Check if this is a list (value is empty and next line is indented with -)
        if not value and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.startswith('  -'):
                # Parse list items
                list_items = []
                j = i + 1
                while j < len(lines) and lines[j].startswith('  -'):
                    item = lines[j].replace('  -', '').strip()
                    if item:
                        list_items.append(item)
                    j += 1

                if list_items:
                    result[key] = list_items[0] if len(list_items) == 1 else list_items
                    i = j
                    continue

        # Parse simple value types
        if value.lower() in ('true', 'yes', 'on'):
            result[key] = True
        elif value.lower() in ('false', 'no', 'off'):
            result[key] = False
        elif value.lower() in ('null', 'nil', '~'):
            result[key] = None
        elif value and value.isdigit():
            result[key] = int(value)
        elif value and value.replace('.', '', 1).isdigit():
            result[key] = float(value)
        else:
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            result[key] = value if value else None

        i += 1

    return result

OUTPUT_DIR = Path(__file__).parent
CONFIG_FILE = OUTPUT_DIR.parent / "server" / "config.json"


def select_folder() -> Path:
    """Demander le dossier à préparer (drag-drop ou chemin)"""
    while True:
        print("\n📁 Glisse-dépose le dossier à préparer (ou tape le chemin):")
        user_input = input("> ").strip()

        # Retirer les guillemets (drag-drop ajoute parfois)
        user_input = user_input.strip('"\'')

        # Gérer les escapes du terminal (\ suivi d'un caractère spécial)
        user_input = user_input.replace('\\ ', ' ')  # Espaces échappés
        user_input = user_input.replace('\\~', '~')  # Tilde échappé
        user_input = user_input.replace('\\(', '(')  # Parenthèses échappées
        user_input = user_input.replace('\\)', ')')
        user_input = user_input.replace('\\[', '[')  # Crochets échappés
        user_input = user_input.replace('\\]', ']')

        if not user_input:
            print("❌ Veuillez entrer un chemin valide")
            continue

        folder_path = Path(user_input).expanduser()

        if folder_path.exists() and folder_path.is_dir():
            return folder_path
        else:
            print(f"❌ Le dossier n'existe pas: {folder_path}")
            continue


def format_date_fr(date_str: str) -> str:
    """Format a date string (YYYY-MM-DD) to French format (30 septembre 2024)"""
    if not date_str:
        return ""

    months_fr = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril',
        5: 'mai', 6: 'juin', 7: 'juillet', 8: 'août',
        9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }

    try:
        parts = str(date_str).strip().split('-')
        if len(parts) == 3:
            year, month, day = parts
            month_num = int(month)
            day_num = int(day)
            if month_num in months_fr:
                return f"{day_num} {months_fr[month_num]} {year}"
    except:
        pass

    return str(date_str)


def format_properties(frontmatter: Dict) -> str:
    """Convert YAML frontmatter to formatted markdown"""
    if not frontmatter:
        return ""

    # Filter properties (skip internal ones, keep all others)
    props = []
    for key, value in frontmatter.items():
        if key.startswith('_'):
            continue

        # Special handling for date field - skip if empty (don't show "rien")
        if key == 'date' or key == 'Date':
            if value:
                display = format_date_fr(str(value))
                display_key = "Date"
                props.append(f"{display_key}  `{display}`")
            continue

        # Format the value
        if isinstance(value, bool):
            display = "☑️" if value else "☐"
        elif value is None or value == '':
            continue  # Skip empty values completely
        elif isinstance(value, list):
            # For lists, skip if empty, otherwise join with commas
            if not value:
                continue
            display = ", ".join(str(v) for v in value)
        else:
            display = str(value)

        # Format key
        display_key = key.replace('_', ' ').replace('-', ' ').capitalize()
        props.append(f"{display_key}  `{display}`")

    if not props:
        return ""

    lines = []
    for prop in props:
        lines.append(prop + "\n")
    lines.append("\n")
    return "".join(lines)


def transform_markdown_content(content: str) -> Tuple[str, Dict]:
    """Transform markdown content for web display"""
    lines = content.split('\n')
    result = []
    in_code_block = False
    in_frontmatter = False
    frontmatter_lines = []
    frontmatter_data = {}
    frontmatter_start_idx = -1

    i = 0
    while i < len(lines):
        line = lines[i]

        # Handle code blocks - normaliser les délimiteurs (retirer les espaces parasites)
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result.append(line.strip())  # strip: évite les espaces avant ``` (ex: Obsidian litegal)
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # Handle frontmatter (YAML at start)
        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            frontmatter_start_idx = len(result)
            result.append(line)  # Keep the opening ---
            i += 1
            continue

        if in_frontmatter:
            result.append(line)  # Keep all frontmatter lines in result
            if line.strip() == '---':
                in_frontmatter = False
                # Parse frontmatter
                frontmatter_yaml = '\n'.join(frontmatter_lines)
                if yaml:
                    try:
                        frontmatter_data = yaml.safe_load(frontmatter_yaml) or {}
                    except:
                        frontmatter_data = parse_yaml_simple(frontmatter_yaml)
                else:
                    frontmatter_data = parse_yaml_simple(frontmatter_yaml)
                i += 1
                continue
            else:
                frontmatter_lines.append(line)
                i += 1
                continue

        # Transform separators (--- or ***)
        if re.match(r'^[\*\-]{3,}\s*$', line.strip()):
            result.append('---')  # Markdown HR
            i += 1
            continue

        # Transform checkbox symbols
        if '✓' in line or '☐' in line:
            line = line.replace('✓', '☑️')

        result.append(line)
        i += 1

    return '\n'.join(result), frontmatter_data


def process_markdown_file(file_path: Path, target_path: Path, verbose: bool = False) -> bool:
    """Process a single markdown file - SAFETY CHECK: only edit files in target_path"""
    try:
        # SÉCURITÉ CRITIQUE: Vérifier que le fichier est dans le dossier cible, jamais dans Obsidian
        file_path_resolved = file_path.resolve()
        target_path_resolved = target_path.resolve()

        if not str(file_path_resolved).startswith(str(target_path_resolved)):
            print(f"  ❌ SÉCURITÉ: Tentative d'éditer en dehors du dossier cible! {file_path}")
            return False

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Transform content
        transformed_content, frontmatter = transform_markdown_content(content)

        if verbose and frontmatter:
            print(f"    📋 Properties trouvées: {len(frontmatter)} propriété(s)")

        # Remplacer les blocs dataview avec le nouveau moteur
        if re.search(r'```dataview', transformed_content, re.IGNORECASE):
            import sys as _sys
            import os as _os
            _scripts_dir = _os.path.dirname(_os.path.abspath(__file__))
            if _scripts_dir not in _sys.path:
                _sys.path.insert(0, _scripts_dir)
            from dataview import DataviewProcessor
            _processor = DataviewProcessor()
            transformed_content = _processor.process_file_content(
                transformed_content, str(target_path)
            )

        # Insert properties after title if frontmatter exists
        if frontmatter and any(v for k, v in frontmatter.items() if not k.startswith('_')):
            properties_md = format_properties(frontmatter)
            lines = transformed_content.split('\n')
            result_lines = []
            title_inserted = False

            for line in lines:
                # Insert properties BEFORE first H1 heading, avec séparateur ---
                if not title_inserted and line.startswith('# '):
                    result_lines.extend(properties_md.rstrip('\n').split('\n'))
                    result_lines.append('')
                    result_lines.append('---')
                    result_lines.append('')
                    title_inserted = True
                result_lines.append(line)

            transformed_content = '\n'.join(result_lines)

        # Write back - SÉCURITÉ: Seul dans le dossier cible
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(transformed_content)

        return True
    except Exception as e:
        print(f"  ⚠️  Erreur: {e}")
        return False


def extract_images_from_md(md_path: Path) -> Set[str]:
    """Extraire les références d'images d'un fichier markdown"""
    images = set()

    try:
        with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Wiki style: ![[image.png]] ou ![[image.png|300]]
        wiki_images = re.findall(r'!\[\[([^\]|]+)', content)
        images.update(wiki_images)

        # Markdown style: ![alt](path)
        md_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        for alt, path in md_images:
            # Extraire juste le nom du fichier (avant les paramètres de taille)
            filename = Path(path).name.split('|')[0].strip()
            images.add(filename)

    except Exception as e:
        print(f"⚠️  Erreur lors de la lecture de {md_path}: {e}")

    return images


def scan_images(folder_path: Path) -> Set[str]:
    """Scanner tous les fichiers markdown et extraire les images référencées"""
    print(f"\n🔍 Scan des références d'images dans {folder_path.name}...\n")

    all_images = set()

    for md_file in folder_path.rglob('*.md'):
        images = extract_images_from_md(md_file)
        if images:
            print(f"  📄 {md_file.relative_to(folder_path)}: {', '.join(sorted(images))}")
            all_images.update(images)

    return all_images


def find_image(image_name: str, attachments_path: Path) -> Path or None:
    """Chercher une image dans le dossier Attachments"""
    if not attachments_path.exists():
        return None

    # Cherche exact
    exact_path = attachments_path / image_name
    if exact_path.exists():
        return exact_path

    # Cherche insensible à la casse
    for item in attachments_path.iterdir():
        if item.name.lower() == image_name.lower():
            return item

    return None


def copy_images(folder_name: str, images: Set[str], attachments_path: Path, target_images_folder: Path = None) -> int:
    """Copier les images du vault vers le dossier local

    Args:
        folder_name: Nom du dossier (pour affichage)
        images: Set des noms d'images à copier
        attachments_path: Chemin du dossier Attachments du vault
        target_images_folder: Chemin cible (par défaut: ./folder_name/images)
    """
    if target_images_folder is None:
        local_folder = OUTPUT_DIR / folder_name
        target_images_folder = local_folder / "images"

    target_images_folder.mkdir(parents=True, exist_ok=True)

    copied = 0
    not_found = []

    print(f"\n📷 Copie des images vers .images/...\n")

    for image_name in sorted(images):
        image_path = find_image(image_name, attachments_path)

        if image_path:
            dest_path = target_images_folder / image_path.name
            try:
                shutil.copy2(image_path, dest_path)
                print(f"  ✓ {image_path.name}")
                copied += 1
            except Exception as e:
                print(f"  ✗ Erreur copie {image_name}: {e}")
        else:
            not_found.append(image_name)

    if not_found:
        print(f"\n⚠️  Images non trouvées ({len(not_found)}):")
        for img in not_found:
            print(f"    - {img}")

    return copied


def generate_password(length: int = 15) -> str:
    """Générer un mot de passe aléatoire sécurisé (15 caractères: majuscules + chiffres)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def hash_password(password: str) -> str:
    """Hasher le mot de passe avec Bcrypt"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        print("⚠️  'bcrypt' non disponible. Installation en cours...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "bcrypt"], check=True)
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def update_config(folder_name: str, folder_path: str, password_hash: str):
    """Mettre à jour config.json avec le nouveau dossier"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {'folders': {}}

    # IMPORTANT: Sauvegarder le chemin RELATIF au répertoire obsidian sur le serveur
    # Pas le chemin absolu local!
    relative_path = f"./{folder_name}"

    config['folders'][folder_name] = {
        'path': relative_path,
        'password': password_hash
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def upload_to_ftp(folder_name: str, local_path: Path) -> bool:
    """Connecter à FTP et uploader le dossier avec tous les fichiers"""
    print()
    ftp = connect_ftp()
    if not ftp:
        return False

    if not ensure_ftp_dir(ftp):
        return False

    # Vérifier si le dossier existe
    if ftp_folder_exists(ftp, folder_name):
        print(f"🔄 Le dossier '{folder_name}' existe déjà - écrasement en cours...")
        print(f"🗑️  Suppression récursive de '{folder_name}'...")
        if not remove_ftp_folder(ftp, folder_name):
            print(f"  ⚠️  Erreur lors de la suppression")
        else:
            print(f"  ✓ Suppression terminée")

    # Uploader config.json en premier (mot de passe actif dès le début)
    print(f"\n📝 Upload config.json...")
    try:
        from ftp_utils import upload_file
        upload_file(ftp, CONFIG_FILE, 'config.json')
    except Exception as e:
        print(f"  ✗ config.json — {e}")

    print(f"\n📤 Upload de '{folder_name}'...\n")

    # Les chemins incluent folder_name comme préfixe → une reconnexion FTP qui
    # revient à obsidian/ repart toujours du bon endroit sans cwd manuel.
    upload_directory(ftp, local_path, folder_name)

    try:
        ftp.quit()
    except Exception:
        pass  # Connexion déjà fermée suite à une reconnexion automatique
    return True


def main():
    print("=" * 60)
    print("📁 PRÉPARATION DOSSIER - Obsidian Web")
    print("=" * 60)

    # Sélectionner le dossier source
    source_path = select_folder()
    source_name = source_path.name
    target_name = f"{source_name} (share)"

    # IMPORTANT: Créer le dossier (share) dans projects/, pas dans scripts/
    project_dir = OUTPUT_DIR.parent / "projects"
    project_dir.mkdir(parents=True, exist_ok=True)  # Créer le dossier s'il n'existe pas
    target_path = project_dir / target_name

    print()
    print(f"📂 Source (Obsidian): {source_path}")
    print(f"📂 Cible (Projet):    {target_path}")
    print()

    # Copier le dossier
    print("📋 Copie du dossier...")
    if target_path.exists():
        print(f"  ⚠️  Existe déjà, suppression...")
        shutil.rmtree(target_path)

    try:
        shutil.copytree(source_path, target_path)
        print("  ✓ Copie terminée")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        sys.exit(1)

    # Créer le dossier .images à la racine du dossier (share)
    images_path = target_path / ".images"
    images_path.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Dossier .images créé: {images_path}")

    print()
    print("⚙️  Traitement des fichiers...")

    # Traiter tous les fichiers markdown
    processed = 0
    dataview_count = 0
    for md_file in target_path.rglob('*.md'):
        rel_path = md_file.relative_to(target_path)

        # Vérifier si le fichier a des blocs dataview
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_dataview = '```dataview' in content

        if process_markdown_file(md_file, target_path):
            # Vérifier si dataview a été traité
            with open(md_file, 'r', encoding='utf-8') as f:
                result_content = f.read()
                had_dataview = has_dataview
                has_dataview_now = '```dataview' in result_content

            if had_dataview and not has_dataview_now:
                print(f"  ✓ {rel_path} [dataview traité]")
                dataview_count += 1
            else:
                print(f"  ✓ {rel_path}")
            processed += 1

    print(f"\n  ✓ {processed} fichier(s) traité(s)")
    if dataview_count > 0:
        print(f"  ✓ {dataview_count} fichier(s) avec dataview traité(s)")
    else:
        print(f"  ⚠️  Aucun dataview traité! (attendu si aucun bloc dataview)")

    # Scanner et copier les images du vault Obsidian
    print()
    all_images = scan_images(target_path)
    if all_images:
        # Chercher le dossier contenant les images
        # Essayer plusieurs chemins possibles :
        possible_paths = [
            source_path.parent / "Attachments",
            source_path / "Attachments",
            source_path.parent.parent / "5 🛠️ Outils" / "📥 Fichiers & Documents",
        ] + EXTRA_IMAGE_PATHS

        attachments_path = None
        for path in possible_paths:
            if path.exists():
                attachments_path = path
                print(f"\n  ℹ️  Dossier d'images trouvé: {path.name}/")
                break

        if attachments_path:
            # Copier les images dans le dossier .images du dossier (share)
            target_images_folder = target_path / ".images"
            images_copied = copy_images(source_name, all_images, attachments_path, target_images_folder)
            print(f"\n  ✓ {images_copied} image(s) copiée(s) vers .images/")
        else:
            print(f"\n  ⚠️  Dossier d'images non trouvé")
            print(f"     Chemins essayés:")
            for path in possible_paths:
                print(f"       - {path}")
            print(f"\n     Les images devront être copiées manuellement dans .images/")
    else:
        print("\n  ℹ️  Aucune image trouvée dans les markdown")

    # Scanner et transformer les liens STL
    print()
    print("🔩 Scan des liens STL...")
    stl_folder = target_path / ".stl"
    stl_processor = STL3DProcessor()
    stl_count = stl_processor.process_folder(target_path, stl_folder)
    if stl_count > 0:
        print(f"\n  ✓ {stl_count} fichier(s) STL copié(s) vers .stl/")
    else:
        print("  ℹ️  Aucun lien STL trouvé dans les markdown")

    # Vérifier si le dossier existe déjà dans config.json
    password_was_existing = False
    password_use_existing = False

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if target_name in config.get('folders', {}):
                # Dossier existe déjà
                password_was_existing = True
                print()
                print("⚠️  Ce dossier existe déjà dans config.json")
                while True:
                    choice = input("Voulez-vous garder l'ancien mot de passe? (o/n): ").strip().lower()
                    if choice in ('o', 'yes', 'oui', 'y'):
                        password_hash = config['folders'][target_name]['password']
                        password_use_existing = True
                        password = "[Mot de passe conservé]"
                        break
                    elif choice in ('n', 'no', 'non'):
                        password = generate_password()
                        password_hash = hash_password(password)
                        password_was_existing = False
                        break
                    else:
                        print("Répondez par 'o' (oui) ou 'n' (non)")
            else:
                # Nouveau dossier - générer nouveau mot de passe
                password = generate_password()
                password_hash = hash_password(password)
    else:
        # Nouveau fichier config - générer nouveau mot de passe
        password = generate_password()
        password_hash = hash_password(password)
        config = {'folders': {}}

    # Mettre à jour config.json avec le NOM du dossier cible
    update_config(target_name, str(target_path), password_hash)

    print()
    print("=" * 60)
    print("✅ PRÉPARATION TERMINÉE!")
    print("=" * 60)
    print()
    print(f"📂 Dossier préparé: {target_path}")
    print()
    if password_use_existing:
        print(f"🔐 Mot de passe (CONSERVÉ - utilisateurs existants gardent accès):")
        print(f"   [Inchangé - Ancien mot de passe maintenu]")
    else:
        print(f"🔐 Mot de passe pour ce dossier:")
        print(f"   {password}")
        if password_was_existing:
            print(f"   ⚠️  Ancien mot de passe: REMPLACÉ par le nouveau ci-dessus")
    print()

    # Upload sur FTP
    print("=" * 60)
    print("📤 UPLOAD SUR HOSTINGER")
    print("=" * 60)

    if upload_to_ftp(target_name, target_path):
        print()
        print("=" * 60)
        print("🎉 SUCCÈS COMPLET!")
        print("=" * 60)
        print()
        print(f"🔗 URL: {SITE_URL}/")
        if password_use_existing:
            print(f"🔐 Mot de passe: [CONSERVÉ - Ancien mot de passe maintenu]")
        else:
            print(f"🔐 Mot de passe: {password}")
        print()
        print("Accès au dossier: " + SITE_URL + "/?folder=" + target_name.lower().replace(' ', '%20'))
        print()
    else:
        print()
        print("⚠️  Upload échoué")
        print(f"Vous pouvez l'uploader manuellement: {target_path}")


if __name__ == '__main__':
    main()
