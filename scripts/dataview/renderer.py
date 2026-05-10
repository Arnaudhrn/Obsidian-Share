"""
DataviewRenderer - Génère du Markdown statique à partir des résultats d'exécution

Supporte: TASK (liste de tâches), TABLE (tableau), LIST (liste simple)
"""
from typing import Any, Dict, List, Optional

from .functions import FunctionRegistry


class DataviewRenderer:

    def __init__(self):
        self.functions = FunctionRegistry()

    def render(self, query: Dict, results: List[Dict]) -> str:
        query_type = query['type']
        if query_type == 'TASK':
            return self._render_task(results)
        if query_type == 'TABLE':
            return self._render_table(query, results)
        if query_type == 'LIST':
            return self._render_list(results)
        return f"*Type '{query_type}' non supporté*\n"

    # ------------------------------------------------------------------
    # TASK
    # ------------------------------------------------------------------

    def _render_task(self, results: List[Dict]) -> str:
        if not results:
            return "*Aucune tâche trouvée*\n"

        lines = []

        # Résultats groupés (après GROUP BY)
        if self._is_grouped(results):
            for group in results:
                group_key = group.get('key') or 'Sans titre'
                rows = group['rows']
                first = rows[0] if rows else {}
                filepath = first.get('__filepath__', '')
                if filepath:
                    lines.append(f"[[{filepath}|{group_key}]]")
                else:
                    lines.append(f"### {group_key}")
                lines.append("")
                for task in rows:
                    lines.append(self._task_line(task))
                lines.append("")
        else:
            for task in results:
                lines.append(self._task_line(task))

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _task_line(task: Dict) -> str:
        done = task.get('completed', False)
        checkbox = "[x]" if done else "[ ]"
        text = task.get('text') or task.get('raw_text', '')
        tags = task.get('tags', [])
        suffix = (" " + " ".join(f'<span class="tag">{t}</span>' for t in tags)) if tags else ""
        return f"- {checkbox} {text}{suffix}"

    # ------------------------------------------------------------------
    # TABLE
    # ------------------------------------------------------------------

    def _render_table(self, query: Dict, results: List[Dict]) -> str:
        if not results:
            return "*Aucun résultat*\n"

        fields = query.get('fields') or []
        # Champ par défaut si TABLE sans colonnes déclarées
        if not fields:
            fields = [{
                'expression': 'file.link',
                'parsed_expr': {'type': 'field_access', 'object': 'file', 'field': 'link'},
                'alias': 'Fichier',
            }]

        lines = []

        # Résultats groupés
        if self._is_grouped(results):
            for group in results:
                group_key = group.get('key') or 'Sans titre'
                lines.append(f"### {group_key}")
                lines.append("")
                lines.extend(self._build_table(fields, group['rows']))
                lines.append("")
        else:
            lines.extend(self._build_table(fields, results))

        return "\n".join(lines).rstrip() + "\n"

    def _build_table(self, fields: List[Dict], rows: List[Dict]) -> List[str]:
        """Construit les lignes d'un tableau Markdown."""
        headers = [f['alias'] for f in fields]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            cells = []
            for field in fields:
                val = self._resolve_field(row, field)
                if isinstance(val, bool):
                    cells.append("☑️" if val else "☐")
                else:
                    cells.append(str(val) if val is not None and val != '' else "-")
            lines.append("| " + " | ".join(cells) + " |")
        return lines

    def _resolve_field(self, row: Dict, field: Dict) -> Any:
        parsed = field.get('parsed_expr')
        return self._eval_display(row, parsed) if parsed else "—"

    def _eval_display(self, row: Dict, node: Optional[Dict]) -> Any:
        """Évalue un nœud AST pour l'affichage (retourne une valeur affichable)."""
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
            if isinstance(val, list):
                val = val[0] if val else None
            if isinstance(val, str):
                val = val.replace('\xa0', ' ').strip()
            return val

        if node_type == 'field_access':
            obj = node['object']
            field = node['field']
            # Cas spécial: file.link → [[chemin|nom]]
            if obj == 'file' and field == 'link':
                filepath = row.get('__filepath__', '')
                filename = row.get('__filename__', '')
                if filepath and filename:
                    return f"[[{filepath}|{filename}]]"
                return f"[[{filename}]]" if filename else "—"
            obj_val = row.get(obj)
            if isinstance(obj_val, dict):
                return obj_val.get(field)
            return None

        if node_type == 'function':
            func_name = node['name']
            args = [self._eval_display(row, arg) for arg in node.get('args', [])]
            try:
                return self.functions.call(func_name, *args)
            except Exception:
                return "—"

        return None

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def _render_list(self, results: List[Dict]) -> str:
        if not results:
            return "*Aucun résultat*\n"

        lines = []

        if self._is_grouped(results):
            for group in results:
                lines.append(f"### {group.get('key') or 'Sans titre'}")
                lines.append("")
                for item in group['rows']:
                    lines.append(f"- {self._list_item_text(item)}")
                lines.append("")
        else:
            for item in results:
                lines.append(f"- {self._list_item_text(item)}")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _list_item_text(item: Dict) -> str:
        name = item.get('__filename__') or item.get('text', '')
        return f"[[{name}]]" if name else "—"

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _is_grouped(results: List[Dict]) -> bool:
        """Vérifie si les résultats sont des groupes (après GROUP BY)."""
        return bool(results) and isinstance(results[0], dict) and 'rows' in results[0]
