"""
Module STL - Gère les fichiers STL référencés dans les notes Obsidian

Usage:
    from stl import STL3DProcessor

    processor = STL3DProcessor()
    count = processor.process_folder(project_path, stl_dest_folder)
"""
from pathlib import Path

from .extractor import extract_stl_links
from .processor import process_file_content

__version__ = "1.0.0"
__all__ = ["STL3DProcessor"]


class STL3DProcessor:
    """
    Façade principale: détecte les liens file:// .stl dans les fichiers markdown,
    copie les fichiers STL vers .stl/, et transforme les liens en chemins relatifs.
    """

    def process_file_content(self, content: str, stl_folder: Path) -> tuple:
        """
        Transforme les liens STL d'un fichier et copie les fichiers.

        Args:
            content:     Contenu brut du fichier .md
            stl_folder:  Chemin du dossier .stl/ de destination

        Returns:
            (new_content, count_copied)
        """
        return process_file_content(content, stl_folder)

    def process_folder(self, project_path: Path, stl_folder: Path) -> int:
        """
        Traite tous les .md du projet: copie les STL et transforme les liens.

        Args:
            project_path:  Racine du dossier projet (share)
            stl_folder:    Chemin du dossier .stl/ de destination

        Returns:
            Nombre total de fichiers STL copiés
        """
        total_copied = 0
        stl_folder.mkdir(parents=True, exist_ok=True)

        for md_file in project_path.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                links = extract_stl_links(content)
                if not links:
                    continue

                new_content, copied = process_file_content(content, stl_folder)
                total_copied += copied

                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

                rel = md_file.relative_to(project_path)
                print(f"  ✓ {rel} [{copied} STL transformé(s)]")

            except Exception as e:
                print(f"  ⚠️  Erreur {md_file.name}: {e}")

        return total_copied
