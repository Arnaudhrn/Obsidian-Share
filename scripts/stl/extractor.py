"""
Extraction des liens STL depuis un contenu Markdown.

Détecte les liens de type: [Texte](file:///chemin/absolu/fichier.stl)
"""
import re
from urllib.parse import unquote
from typing import List, Tuple

# Correspond à: [Texte](file:///chemin/absolu/fichier.stl)
# Capture: (texte_affiché, chemin_absolu_encodé, match_complet)
_STL_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(file://(/[^)]+\.stl)\)',
    re.IGNORECASE
)


def extract_stl_links(content: str) -> List[Tuple[str, str, str]]:
    """
    Trouve tous les liens STL (file://) dans un contenu Markdown.

    Args:
        content: Contenu brut d'un fichier .md

    Returns:
        Liste de tuples (texte_affiché, chemin_absolu_décodé, match_complet)
        Exemple: ("Fixation Phare 1", "/Users/.../Fixation Phare 1.stl", "[Fixation Phare 1](file:///...)")
    """
    results = []
    for match in _STL_LINK_RE.finditer(content):
        display = match.group(1)
        raw_path = match.group(2)        # /Users/... (sans le file://)
        decoded_path = unquote(raw_path) # Décode %20 → espace, etc.
        full_match = match.group(0)
        results.append((display, decoded_path, full_match))
    return results
