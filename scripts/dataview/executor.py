"""
ExecutionEngine - Applique les opérations Dataview sur les données extraites

Ordre OBLIGATOIRE: WHERE → GROUP BY → SORT → LIMIT
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data_extractor import MarkdownDataExtractor
from .functions import FunctionRegistry


class ExecutionEngine:

    def __init__(self):
        self.extractor = MarkdownDataExtractor()
        self.functions = FunctionRegistry()

    def execute(self, query: Dict, vault_base_path: str) -> List[Dict]:
        """
        Pipeline complet:
        1. Résoudre les fichiers depuis FROM
        2. Extraire les données (tasks ou fichiers)
        3. Appliquer WHERE → GROUP → SORT → LIMIT
        """
        query_type = query['type']
        source_path = query['source']['path']

        # 1. Résoudre les fichiers source
        files = self._resolve_files(source_path, vault_base_path)
        if not files:
            print(f"  ⚠️ Aucun fichier trouvé pour: {source_path}")
            return []

        # 2. Extraire les données selon le type de requête
        if query_type == 'TASK':
            data = self._collect_tasks(files, vault_base_path)
        else:
            data = self._collect_file_data(files, vault_base_path)

        print(f"  📊 {len(data)} élément(s) extrait(s) depuis {len(files)} fichier(s)")

        # 3. Appliquer les opérations dans l'ordre strict
        for op in query['operations']:
            op_type = op['type']
            before = len(data)

            if op_type == 'where':
                data = self._apply_where(data, op)
                print(f"  → WHERE: {before} → {len(data)}")
            elif op_type == 'group':
                data = self._apply_group(data, op)
                print(f"  → GROUP BY: {len(data)} groupe(s)")
            elif op_type == 'sort':
                data = self._apply_sort(data, op)
                print(f"  → SORT ({op.get('direction', 'ASC')})")
            elif op_type == 'limit':
                data = data[:op['amount']]
                print(f"  → LIMIT: {op['amount']}")

        return data

    # ------------------------------------------------------------------
    # Résolution des fichiers
    # ------------------------------------------------------------------

    def _resolve_files(self, from_path: str, base_path: str) -> List[str]:
        """
        Cherche le dossier FROM dans base_path.
        Si non trouvé en direct, essaie de matcher par segments de fin de chemin.
        Si le chemin pointe un fichier (et non un dossier), le traite comme source unique.
        """
        base = Path(base_path).resolve()

        # Essai direct
        candidate = base / from_path
        if candidate.is_dir():
            if str(candidate.resolve()).startswith(str(base)):
                return sorted(str(p) for p in candidate.rglob('*.md'))

        # Option C: FROM pointe un fichier au lieu d'un dossier → fichier seul + warning
        result = self._resolve_as_file(candidate, base)
        if result is not None:
            return result

        # Matching par suffixe (ex: "Projets/Mon-Projet" → cherche "*/Projets/Mon-Projet")
        segments = [s for s in from_path.replace('\\', '/').split('/') if s]
        for n in range(len(segments), 0, -1):
            suffix = '/'.join(segments[-n:])
            candidate = base / suffix
            if candidate.is_dir():
                resolved = candidate.resolve()
                if str(resolved).startswith(str(base)):
                    return sorted(str(p) for p in resolved.rglob('*.md'))

            # Option C: même vérification dans le suffix matching
            result = self._resolve_as_file(candidate, base)
            if result is not None:
                return result

        return []

    def _resolve_as_file(self, candidate: Path, base: Path) -> Optional[List[str]]:
        """
        Si candidate (ou candidate.md) est un fichier dans base, retourne [fichier].
        Logge un warning pour informer l'utilisateur.
        """
        for path in [candidate, Path(str(candidate) + '.md')]:
            resolved = path.resolve()
            if path.is_file() and str(resolved).startswith(str(base)):
                print(f"  ⚠️ FROM pointe un fichier ({path.name}) et non un dossier — traitement du fichier seul.")
                return [str(resolved)]
        return None

    # ------------------------------------------------------------------
    # Collecte des données
    # ------------------------------------------------------------------

    def _collect_file_data(self, files: List[str], vault_base_path: str) -> List[Dict]:
        """Pour TABLE/LIST: un dict par fichier (frontmatter + metadata)."""
        base = Path(vault_base_path).resolve()
        results = []
        for f in files:
            extracted = self.extractor.extract(f)
            row = dict(extracted['frontmatter'])
            row['file'] = extracted['file']
            row['headers'] = extracted['headers']
            row['tags'] = extracted['tags']
            row['__filename__'] = extracted['file']['name']
            row['__filepath__'] = self._relative_path(f, base)
            results.append(row)
        return results

    def _collect_tasks(self, files: List[str], vault_base_path: str) -> List[Dict]:
        """Pour TASK: un dict par tâche, enrichi des métadonnées du fichier."""
        base = Path(vault_base_path).resolve()
        results = []
        for f in files:
            extracted = self.extractor.extract(f)
            rel = self._relative_path(f, base)
            for task in extracted['tasks']:
                row = dict(task)
                row['file'] = extracted['file']
                row['__filename__'] = extracted['file']['name']
                row['__filepath__'] = rel
                results.append(row)
        return results

    @staticmethod
    def _relative_path(file_path: str, base: Path) -> str:
        """Chemin relatif depuis base, sans extension .md, slashes normalisés."""
        try:
            rel = Path(file_path).resolve().relative_to(base)
            return str(rel.with_suffix('')).replace('\\', '/')
        except ValueError:
            return Path(file_path).stem

    # ------------------------------------------------------------------
    # WHERE
    # ------------------------------------------------------------------

    def _apply_where(self, data: List[Dict], op: Dict) -> List[Dict]:
        condition = op['condition']
        results = []
        errors = 0
        for row in data:
            try:
                if self._eval_condition(row, condition):
                    results.append(row)
            except Exception:
                errors += 1
        if errors:
            print(f"    ⚠️ {errors} erreur(s) WHERE ignorée(s)")
        return results

    def _eval_condition(self, row: Dict, node: Dict) -> bool:
        node_type = node.get('type')

        if node_type == 'binaryop':
            op = node['operator']
            if op == 'AND':
                return (self._eval_condition(row, node['left'])
                        and self._eval_condition(row, node['right']))
            if op == 'OR':
                return (self._eval_condition(row, node['left'])
                        or self._eval_condition(row, node['right']))
            # Comparaison
            left_val = self._eval_expr(row, node['left'])
            right_val = self._eval_expr(row, node['right'])
            return self._compare(left_val, right_val, op)

        if node_type == 'function':
            return bool(self._call_function(row, node))

        if node_type == 'variable':
            name = node['name']
            val = row.get(name)
            if val is None: val = row.get(name.replace('-', '_'))
            if val is None: val = row.get(name.replace('-', ' '))
            if val is None: val = row.get(name.replace('_', ' '))
            return bool(val)

        if node_type == 'literal':
            return bool(node['value'])

        return False

    # ------------------------------------------------------------------
    # GROUP BY
    # ------------------------------------------------------------------

    def _apply_group(self, data: List[Dict], op: Dict) -> List[Dict]:
        """Groupe par expression et retourne [{key, rows}, ...]."""
        groups: Dict[str, List] = {}
        order: List[str] = []  # Conserver l'ordre d'apparition

        for row in data:
            key = self._eval_expr(row, op['parsed_expr'])
            key_str = str(key) if key is not None else ''
            if key_str not in groups:
                groups[key_str] = []
                order.append(key_str)
            groups[key_str].append(row)

        return [{'key': k, 'rows': groups[k]} for k in order]

    # ------------------------------------------------------------------
    # SORT
    # ------------------------------------------------------------------

    def _apply_sort(self, data: List[Dict], op: Dict) -> List[Dict]:
        if not data:
            return data

        reverse = op.get('reverse', False)
        parsed = op.get('parsed_expr')

        # Tri de groupes (après GROUP BY)
        if isinstance(data[0], dict) and 'rows' in data[0] and 'key' in data[0]:
            return self._sort_groups(data, parsed, reverse)

        # Tri de données brutes
        return self._sort_flat(data, parsed, reverse)

    def _sort_flat(self, data: List[Dict], parsed_expr: Dict, reverse: bool) -> List[Dict]:
        def sort_key(row):
            val = self._eval_expr(row, parsed_expr)
            return (val is None, val if val is not None else '')

        try:
            return sorted(data, key=sort_key, reverse=reverse)
        except TypeError:
            def safe_key(row):
                val = self._eval_expr(row, parsed_expr)
                try:
                    return (val is None, float(val) if val is not None else 0)
                except (ValueError, TypeError):
                    return (val is None, str(val) if val is not None else '')
            try:
                return sorted(data, key=safe_key, reverse=reverse)
            except Exception:
                return data

    def _sort_groups(self, groups: List[Dict], parsed_expr: Dict,
                     reverse: bool) -> List[Dict]:
        """
        Trie des groupes.
        Supporte min(rows.field) et max(rows.field) pour trier par agrégation.
        """
        if parsed_expr is None:
            return groups

        expr_type = parsed_expr.get('type')

        # Cas: min(rows.line) ou max(rows.line)
        if expr_type == 'function' and parsed_expr['name'] in ('min', 'max'):
            fn_name = parsed_expr['name']
            args = parsed_expr.get('args', [])
            if args and args[0].get('type') == 'field_access':
                field = args[0]['field']  # ex: 'line'

                def agg_key(group):
                    values = [r.get(field) for r in group['rows']
                              if r.get(field) is not None]
                    if not values:
                        return 0
                    return min(values) if fn_name == 'min' else max(values)

                return sorted(groups, key=agg_key, reverse=reverse)

        # Tri par key du groupe
        def key_sort(group):
            val = group.get('key', '')
            return (val is None, str(val) if val is not None else '')

        try:
            return sorted(groups, key=key_sort, reverse=reverse)
        except Exception:
            return groups

    # ------------------------------------------------------------------
    # Évaluation des expressions
    # ------------------------------------------------------------------

    def _eval_expr(self, row: Dict, node: Optional[Dict]) -> Any:
        if node is None:
            return None

        node_type = node.get('type')

        if node_type == 'literal':
            return node['value']

        if node_type == 'variable':
            name = node['name']
            val = row.get(name)
            if val is None: val = row.get(name.replace('-', '_'))
            if val is None: val = row.get(name.replace('-', ' '))
            if val is None: val = row.get(name.replace('_', ' '))
            return val

        if node_type == 'field_access':
            # ex: file.link, rows.line
            obj_val = row.get(node['object'])
            if isinstance(obj_val, dict):
                return obj_val.get(node['field'])
            return None

        if node_type == 'function':
            return self._call_function(row, node)

        if node_type == 'binaryop':
            op = node['operator']
            if op in ('AND', 'OR'):
                return self._eval_condition(row, node)
            left_val = self._eval_expr(row, node['left'])
            right_val = self._eval_expr(row, node['right'])
            return self._compare(left_val, right_val, op)

        return None

    def _call_function(self, row: Dict, node: Dict) -> Any:
        func_name = node['name']
        args = [self._eval_expr(row, arg) for arg in node.get('args', [])]
        try:
            return self.functions.call(func_name, *args)
        except ValueError as e:
            print(f"    ⚠️ {e}")
            return None

    # ------------------------------------------------------------------
    # Comparaison
    # ------------------------------------------------------------------

    @staticmethod
    def _compare(left: Any, right: Any, op: str) -> bool:
        # Gestion null
        if left is None or right is None:
            if op == '!=':
                return left != right
            if op == '==':
                return left == right
            return False

        try:
            if op == '==':
                return left == right
            if op == '!=':
                return left != right
            if op == '<':
                return left < right
            if op == '>':
                return left > right
            if op == '<=':
                return left <= right
            if op == '>=':
                return left >= right
        except TypeError:
            # Tentative de conversion numérique
            try:
                lf, rf = float(left), float(right)
                if op == '<':
                    return lf < rf
                if op == '>':
                    return lf > rf
                if op == '<=':
                    return lf <= rf
                if op == '>=':
                    return lf >= rf
            except (ValueError, TypeError):
                pass
        return False
