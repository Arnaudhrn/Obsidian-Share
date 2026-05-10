"""
DataviewParser - Parse les requêtes Dataview en AST structuré

Supporte:
- Types: TABLE, TASK, LIST
- FROM "chemin"
- WHERE expr AND/OR expr (avec parenthèses imbriquées)
- GROUP BY expr
- SORT expr ASC|DESC
- LIMIT n
- Fonctions: contains(), replace(), string(), dateformat(), choice()...
"""
import re
from typing import Any, Dict, List


class DataviewParser:

    def parse(self, query_str: str) -> Dict:
        """Parse un bloc Dataview complet et retourne un AST."""
        # Normaliser: rejoindre les lignes AND/OR continuées à la ligne précédente
        raw_lines = query_str.strip().split('\n')
        merged: List[str] = []
        for line in raw_lines:
            s = line.strip()
            if not s:
                continue
            upper = s.upper()
            if merged and (upper.startswith('AND ') or upper.startswith('OR ')):
                merged[-1] = merged[-1] + ' ' + s
            else:
                merged.append(s)

        full = ' '.join(merged)

        # Type de requête
        type_m = re.match(r'^(TABLE|TASK|LIST|CALENDAR)\b', full, re.I)
        query_type = type_m.group(1).upper() if type_m else 'TABLE'

        # TABLE WITHOUT ID
        without_id = bool(re.search(r'\bWITHOUT\s+ID\b', full, re.I))

        # FROM "chemin"
        from_m = re.search(r'\bFROM\s+["\']([^"\']+)["\']', full, re.I)
        source_path = from_m.group(1) if from_m else ''

        # Champs TABLE (entre TABLE ... et FROM)
        fields: List[Dict] = []
        if query_type == 'TABLE':
            fields = self._parse_fields(full)

        # WHERE
        where_m = re.search(
            r'\bWHERE\s+(.+?)(?=\s+\bGROUP\s+BY\b|\s+\bSORT\b|\s+\bLIMIT\b|$)',
            full, re.I
        )
        where_expr = where_m.group(1).strip() if where_m else None

        # GROUP BY
        group_m = re.search(
            r'\bGROUP\s+BY\s+(.+?)(?=\s+\bSORT\b|\s+\bLIMIT\b|$)',
            full, re.I
        )
        group_expr = group_m.group(1).strip() if group_m else None

        # SORT
        sort_m = re.search(r'\bSORT\s+(.+?)(?=\s+\bLIMIT\b|$)', full, re.I)
        sort_expr = sort_m.group(1).strip() if sort_m else None

        # LIMIT
        limit_m = re.search(r'\bLIMIT\s+(\d+)', full, re.I)
        limit = int(limit_m.group(1)) if limit_m else None

        # Construire les opérations dans l'ordre obligatoire: WHERE → GROUP → SORT → LIMIT
        operations: List[Dict] = []

        if where_expr:
            operations.append({
                'type': 'where',
                'condition': self._parse_expression(where_expr),
            })

        if group_expr:
            operations.append({
                'type': 'group',
                'raw': group_expr,
                'parsed_expr': self._parse_simple_expression(group_expr),
            })

        if sort_expr:
            operations.append({'type': 'sort', **self._parse_sort(sort_expr)})

        if limit is not None:
            operations.append({'type': 'limit', 'amount': limit})

        return {
            'type': query_type,
            'without_id': without_id,
            'source': {'type': 'folder', 'path': source_path},
            'fields': fields,
            'operations': operations,
        }

    # ------------------------------------------------------------------
    # Champs TABLE
    # ------------------------------------------------------------------

    def _parse_fields(self, full: str) -> List[Dict]:
        """Extrait les champs entre TABLE ... et FROM."""
        m = re.search(
            r'\bTABLE\b(?:\s+WITHOUT\s+ID)?\s*(.*?)\s*\bFROM\b',
            full, re.I | re.DOTALL
        )
        if not m or not m.group(1).strip():
            return []
        return self._split_fields(m.group(1).strip())

    def _split_fields(self, fields_str: str) -> List[Dict]:
        """Divise les champs par virgule en respectant parenthèses et guillemets."""
        fields: List[Dict] = []
        current = ''
        depth = 0
        in_quotes = False
        quote_char = ''

        for ch in fields_str:
            if ch in ('"', "'") and not in_quotes:
                in_quotes, quote_char = True, ch
                current += ch
            elif in_quotes and ch == quote_char:
                in_quotes = False
                current += ch
            elif not in_quotes and ch == '(':
                depth += 1
                current += ch
            elif not in_quotes and ch == ')':
                depth -= 1
                current += ch
            elif not in_quotes and depth == 0 and ch == ',':
                if current.strip():
                    fields.append(self._parse_field_def(current.strip()))
                current = ''
            else:
                current += ch

        if current.strip():
            fields.append(self._parse_field_def(current.strip()))
        return fields

    def _parse_field_def(self, field_str: str) -> Dict:
        """Parse 'expr AS "alias"' ou 'expr'."""
        m = re.match(r'(.+?)\s+AS\s+["\']([^"\']+)["\']', field_str, re.I)
        if m:
            expr_str = m.group(1).strip()
            alias = m.group(2).strip()
        else:
            expr_str = field_str.strip()
            alias = expr_str

        return {
            'expression': expr_str,
            'parsed_expr': self._parse_simple_expression(expr_str),
            'alias': alias,
        }

    # ------------------------------------------------------------------
    # Expressions (WHERE / GROUP BY)
    # ------------------------------------------------------------------

    def _parse_expression(self, expr: str) -> Dict:
        """Parse récursivement une expression booléenne (AND/OR imbriqués)."""
        expr = self._strip_outer_parens(expr.strip())

        # OR (priorité la plus basse)
        or_parts = self._split_logical(expr, 'OR')
        if len(or_parts) > 1:
            return {
                'type': 'binaryop',
                'operator': 'OR',
                'left': self._parse_expression(or_parts[0]),
                'right': self._parse_expression(' OR '.join(or_parts[1:])),
            }

        # AND
        and_parts = self._split_logical(expr, 'AND')
        if len(and_parts) > 1:
            return {
                'type': 'binaryop',
                'operator': 'AND',
                'left': self._parse_expression(and_parts[0]),
                'right': self._parse_expression(' AND '.join(and_parts[1:])),
            }

        return self._parse_simple_expression(expr)

    def _parse_simple_expression(self, expr: str) -> Dict:
        """Parse une expression simple (sans AND/OR racine)."""
        expr = self._strip_outer_parens(expr.strip())

        # Fonction: name(args...)
        func_m = re.match(r'^(\w+)\s*\((.+)\)$', expr, re.DOTALL)
        if func_m:
            return {
                'type': 'function',
                'name': func_m.group(1).lower(),
                'args': self._parse_args(func_m.group(2)),
            }

        # Comparaisons (ordre important: != avant =)
        for op in ('!=', '==', '<=', '>=', '<', '>'):
            idx = self._find_operator_pos(expr, op)
            if idx >= 0:
                left_str = expr[:idx].strip()
                right_str = expr[idx + len(op):].strip()
                return {
                    'type': 'binaryop',
                    'operator': op,
                    'left': self._parse_simple_expression(left_str),
                    'right': {'type': 'literal', 'value': self._parse_value(right_str)},
                }

        # Literal string
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return {'type': 'literal', 'value': expr[1:-1]}

        # Literal numérique
        if re.match(r'^-?\d+$', expr):
            return {'type': 'literal', 'value': int(expr)}
        if re.match(r'^-?\d+\.\d+$', expr):
            return {'type': 'literal', 'value': float(expr)}

        # Literals spéciaux
        lower = expr.lower()
        if lower == 'null':
            return {'type': 'literal', 'value': None}
        if lower == 'true':
            return {'type': 'literal', 'value': True}
        if lower == 'false':
            return {'type': 'literal', 'value': False}

        # Accès imbriqué: rows.line, file.link
        if '.' in expr and not expr.startswith('.'):
            obj, _, field = expr.partition('.')
            return {'type': 'field_access', 'object': obj.strip(), 'field': field.strip()}

        # Variable simple
        return {'type': 'variable', 'name': expr}

    def _parse_args(self, args_str: str) -> List[Dict]:
        """Parse les arguments d'une fonction (séparés par virgule)."""
        args: List[Dict] = []
        current = ''
        depth = 0
        in_quotes = False
        quote_char = ''

        for ch in args_str:
            if ch in ('"', "'") and not in_quotes:
                in_quotes, quote_char = True, ch
                current += ch
            elif in_quotes and ch == quote_char:
                in_quotes = False
                current += ch
            elif not in_quotes and ch == '(':
                depth += 1
                current += ch
            elif not in_quotes and ch == ')':
                depth -= 1
                current += ch
            elif not in_quotes and depth == 0 and ch == ',':
                if current.strip():
                    args.append(self._parse_simple_expression(current.strip()))
                current = ''
            else:
                current += ch

        if current.strip():
            args.append(self._parse_simple_expression(current.strip()))
        return args

    def _parse_sort(self, sort_str: str) -> Dict:
        """Parse 'expr ASC|DESC'."""
        sort_str = sort_str.strip()
        m = re.match(r'^(.+?)\s+(ASC|DESC)$', sort_str, re.I)
        if m:
            expr_str = m.group(1).strip()
            direction = m.group(2).upper()
        else:
            expr_str = sort_str
            direction = 'ASC'

        return {
            'expression': expr_str,
            'parsed_expr': self._parse_simple_expression(expr_str),
            'direction': direction,
            'reverse': direction == 'DESC',
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _split_logical(self, text: str, operator: str) -> List[str]:
        """Divise par AND ou OR en respectant parenthèses et guillemets."""
        parts: List[str] = []
        current = ''
        depth = 0
        in_quotes = False
        quote_char = ''
        op_len = len(operator)
        i = 0

        while i < len(text):
            ch = text[i]

            if ch in ('"', "'") and not in_quotes:
                in_quotes, quote_char = True, ch
                current += ch
                i += 1
                continue
            if in_quotes:
                if ch == quote_char:
                    in_quotes = False
                current += ch
                i += 1
                continue

            if ch == '(':
                depth += 1
                current += ch
                i += 1
                continue
            if ch == ')':
                depth -= 1
                current += ch
                i += 1
                continue

            if depth == 0:
                candidate = text[i:i + op_len]
                before = text[i - 1] if i > 0 else ' '
                after = text[i + op_len] if i + op_len < len(text) else ' '
                if candidate.upper() == operator and before == ' ' and after == ' ':
                    if current.strip():
                        parts.append(current.strip())
                    current = ''
                    i += op_len
                    continue

            current += ch
            i += 1

        if current.strip():
            parts.append(current.strip())

        return parts if len(parts) > 1 else [text]

    @staticmethod
    def _strip_outer_parens(expr: str) -> str:
        """Retire les parenthèses qui couvrent toute l'expression."""
        if not (expr.startswith('(') and expr.endswith(')')):
            return expr
        depth = 0
        for i, ch in enumerate(expr):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            # Si depth tombe à 0 avant la fin → les parens ne couvrent pas tout
            if depth == 0 and i < len(expr) - 1:
                return expr
        return expr[1:-1].strip()

    @staticmethod
    def _find_operator_pos(expr: str, op: str) -> int:
        """Position d'un opérateur hors parenthèses et guillemets. -1 si absent."""
        depth = 0
        in_quotes = False
        quote_char = ''
        i = 0
        while i < len(expr):
            ch = expr[i]
            if ch in ('"', "'") and not in_quotes:
                in_quotes, quote_char = True, ch
            elif in_quotes and ch == quote_char:
                in_quotes = False
            elif not in_quotes:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif depth == 0 and expr[i:i + len(op)] == op:
                    return i
            i += 1
        return -1

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Convertit une string en valeur Python."""
        v = value_str.strip()
        lower = v.lower()
        if lower == 'null':
            return None
        if lower == 'true':
            return True
        if lower == 'false':
            return False
        if re.match(r'^-?\d+$', v):
            return int(v)
        if re.match(r'^-?\d+\.\d+$', v):
            return float(v)
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        return v
