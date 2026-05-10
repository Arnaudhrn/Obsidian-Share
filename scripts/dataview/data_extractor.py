"""
MarkdownDataExtractor - Extrait toutes les données d'un fichier Markdown
(frontmatter, headers, tâches, tags)
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError:
    yaml = None


class MarkdownDataExtractor:
    """Extrait frontmatter, headers, tâches et tags d'un fichier Markdown"""

    def extract(self, file_path: str) -> Dict:
        """
        Retourne un dict complet avec toutes les données du fichier:
        {
            'file':        {'name', 'path', 'link'},
            'frontmatter': {...},
            'headers':     [{'level', 'text', 'line'}, ...],
            'tasks':       [{'text', 'completed', 'tags', 'header', 'line'}, ...],
            'tags':        [...]
        }
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠️ Erreur lecture {file_path}: {e}")
            return self._empty_result(file_path)

        frontmatter, body = self._extract_frontmatter(content)
        headers = self._extract_headers(body)
        tasks = self._extract_tasks(body)

        # Collecter tous les tags (tâches + frontmatter)
        all_tags: set = set()
        for task in tasks:
            all_tags.update(task['tags'])

        fm_tags = frontmatter.get('tags')
        if fm_tags:
            if isinstance(fm_tags, list):
                all_tags.update(str(t) for t in fm_tags)
            else:
                all_tags.add(str(fm_tags))

        file_name = Path(file_path).stem
        file_info = {
            'name': file_name,
            'path': str(file_path),
            'link': file_name,
        }
        frontmatter['file'] = file_info

        return {
            'file': file_info,
            'frontmatter': frontmatter,
            'headers': headers,
            'tasks': tasks,
            'tags': sorted(all_tags),
        }

    @staticmethod
    def _empty_result(file_path: str) -> Dict:
        file_name = Path(file_path).stem
        file_info = {'name': file_name, 'path': str(file_path), 'link': file_name}
        return {
            'file': file_info,
            'frontmatter': {'file': file_info},
            'headers': [],
            'tasks': [],
            'tags': [],
        }

    def _extract_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Retourne (frontmatter_dict, corps_sans_frontmatter)"""
        if not content.startswith('---'):
            return {}, content

        match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', content, re.DOTALL)
        if not match:
            return {}, content

        yaml_text = match.group(1)
        body = content[match.end():]

        if yaml:
            try:
                data = yaml.safe_load(yaml_text) or {}
            except Exception:
                data = self._parse_yaml_simple(yaml_text)
        else:
            data = self._parse_yaml_simple(yaml_text)

        return data, body

    @staticmethod
    def _parse_yaml_simple(yaml_text: str) -> Dict:
        """Parser YAML minimal: key: value, listes indentées et listes inline"""
        result: Dict = {}
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

            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()

            # Liste indentée sur lignes suivantes
            if not value and i + 1 < len(lines) and lines[i + 1].strip().startswith('-'):
                items = []
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith('-'):
                    item = lines[j].strip().lstrip('-').strip().strip('\'"')
                    if item:
                        items.append(item)
                    j += 1
                result[key] = items
                i = j
                continue

            # Liste inline [a, b]
            if value.startswith('[') and value.endswith(']'):
                inner = value[1:-1]
                items = [x.strip().strip('\'"') for x in inner.split(',') if x.strip()]
                result[key] = items
                i += 1
                continue

            # Valeurs simples
            if value.lower() in ('true', 'yes'):
                result[key] = True
            elif value.lower() in ('false', 'no'):
                result[key] = False
            elif value.lower() in ('null', 'nil', '~', ''):
                result[key] = None
            elif re.match(r'^-?\d+$', value):
                result[key] = int(value)
            elif re.match(r'^-?\d+\.\d+$', value):
                result[key] = float(value)
            else:
                result[key] = value.strip('\'"')

            i += 1

        return result

    @staticmethod
    def _extract_headers(body: str) -> List[Dict]:
        """Extrait tous les en-têtes Markdown avec leur niveau et ligne"""
        headers = []
        for line_num, line in enumerate(body.split('\n'), 1):
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if m:
                headers.append({
                    'level': len(m.group(1)),
                    'text': m.group(2).strip(),
                    'line': line_num,
                })
        return headers

    @staticmethod
    def _extract_tasks(body: str) -> List[Dict]:
        """
        Extrait les tâches (- [ ] et - [x]) avec:
        - text: texte nettoyé (sans les tags)
        - completed: bool
        - tags: liste des #tags du texte
        - header: dernier en-tête vu avant la tâche (CRUCIAL)
        - line: numéro de ligne
        """
        tasks = []
        lines = body.split('\n')
        current_header = ''

        for line_num, line in enumerate(lines, 1):
            # Tracker le header courant (dernier vu)
            header_m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_m:
                current_header = header_m.group(2).strip()
                continue

            # Matcher les tâches avec indentation possible
            task_m = re.match(r'^\s*[-*]\s+\[([xX ])\]\s+(.+)$', line)
            if not task_m:
                continue

            completed = task_m.group(1).lower() == 'x'
            raw_text = task_m.group(2).strip()

            # Extraire les tags (supporte les emojis dans les tags: #🛒-Achat)
            tags = re.findall(r'#[^\s\[\]\(\),\.\!\?\"\']+', raw_text)

            # Nettoyer le texte (retirer les tags)
            clean_text = re.sub(r'\s*#[^\s\[\]\(\),\.\!\?\"\']+', '', raw_text).strip()

            tasks.append({
                'text': clean_text,
                'raw_text': raw_text,
                'completed': completed,
                'tags': tags,
                'header': current_header,
                'line': line_num,
            })

        return tasks
