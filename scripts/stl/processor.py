"""
Traitement des liens STL: copie des fichiers et transformation des liens Markdown.
"""
import shutil
from pathlib import Path
from urllib.parse import quote
from typing import Tuple

from .extractor import extract_stl_links


def process_file_content(content: str, stl_folder: Path) -> Tuple[str, int]:
    """
    Copie les fichiers STL vers stl_folder et transforme les liens dans le Markdown.

    Transformation:
        AVANT : [Fixation Phare 1](file:///Users/.../Fixation%20Phare%201.stl)
        APRÈS : [Fixation Phare 1](.stl/Fixation%20Phare%201.stl)

    Args:
        content:     Contenu brut du fichier .md
        stl_folder:  Chemin du dossier .stl/ de destination

    Returns:
        (contenu_transformé, nombre_fichiers_copiés)
    """
    links = extract_stl_links(content)
    if not links:
        return content, 0

    stl_folder.mkdir(parents=True, exist_ok=True)
    copied = 0

    for display, src_path, full_match in links:
        src = Path(src_path)

        if not src.exists():
            print(f"  ⚠️  STL introuvable: {src_path}")
            continue

        dest = stl_folder / src.name
        try:
            shutil.copy2(src, dest)
            copied += 1
        except Exception as e:
            print(f"  ✗ Erreur copie {src.name}: {e}")
            continue

        # Transformer le lien: file:// absolu → chemin relatif .stl/
        filename_encoded = quote(src.name)
        new_link = f"[{display}](.stl/{filename_encoded})"
        content = content.replace(full_match, new_link, 1)

    return content, copied
