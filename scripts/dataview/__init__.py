"""
Module Dataview - Transforme les blocs dataview en contenu Markdown statique

Usage:
    from dataview import DataviewProcessor

    processor = DataviewProcessor()
    new_content = processor.process_file_content(content, vault_base_path)
"""
import re

from .parser import DataviewParser
from .executor import ExecutionEngine
from .renderer import DataviewRenderer

__version__ = "2.0.0"
__all__ = ["DataviewProcessor"]


class DataviewProcessor:
    """
    Façade principale: transforme les blocs dataview d'un fichier
    en contenu Markdown statique prêt à être publié.
    """

    def __init__(self):
        self.parser = DataviewParser()
        self.engine = ExecutionEngine()
        self.renderer = DataviewRenderer()

    def process_block(self, block_content: str, vault_base_path: str) -> str:
        """
        Transforme un bloc dataview en Markdown statique.

        Args:
            block_content:    Contenu brut du bloc (sans les ```)
            vault_base_path:  Chemin de base du vault pour résoudre le FROM

        Returns:
            Markdown statique (tableau, liste de tâches, etc.)
        """
        try:
            query = self.parser.parse(block_content)
            results = self.engine.execute(query, vault_base_path)
            return self.renderer.render(query, results)
        except Exception as e:
            print(f"  ⚠️ Erreur dataview: {e}")
            return f"*Erreur lors du traitement dataview: {e}*\n"

    def process_file_content(self, content: str, vault_base_path: str) -> str:
        """
        Remplace tous les blocs ```dataview ... ``` dans un contenu Markdown.

        Args:
            content:          Contenu complet du fichier .md
            vault_base_path:  Chemin de base du vault

        Returns:
            Contenu avec tous les blocs dataview remplacés
        """
        pattern = re.compile(r'```dataview\n(.*?)\n```', re.DOTALL | re.IGNORECASE)

        def replace_block(match):
            block_content = match.group(1).strip()
            if not block_content:
                return match.group(0)
            return self.process_block(block_content, vault_base_path)

        return pattern.sub(replace_block, content)
