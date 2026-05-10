"""
Evaluator - Évalue les conditions WHERE et les fonctions Dataview
"""

import re
from typing import Any, Dict, List


class ConditionEvaluator:
    """Évalue les conditions WHERE et les expressions Dataview"""

    def evaluate(self, obj: Dict, condition: str) -> bool:
        """
        Évalue une condition pour un objet

        Exemples:
        - evaluate({intervention: 5}, "intervention <= 9") → True
        - evaluate({tags: ["#tag1", "#tag2"]}, "contains(tags, "#tag1")") → True

        Args:
            obj: Dictionnaire avec les propriétés de l'objet
            condition: Chaîne de condition (ex: "intervention != null AND intervention <= 9")

        Returns:
            bool: Résultat de l'évaluation
        """
        # Gérer les opérateurs AND/OR
        # Diviser par OR d'abord (priorité basse)
        or_parts = self._split_operator(condition, "OR")

        if len(or_parts) > 1:
            return any(self.evaluate(obj, part.strip()) for part in or_parts)

        # Puis diviser par AND (priorité haute)
        and_parts = self._split_operator(condition, "AND")

        if len(and_parts) > 1:
            return all(self.evaluate(obj, part.strip()) for part in and_parts)

        # Évaluer une condition simple
        return self._evaluate_single(obj, condition.strip())

    def _evaluate_single(self, obj: Dict, condition: str) -> bool:
        """Évalue une condition simple (sans AND/OR)"""
        condition = condition.strip()

        # Fonctions
        if "contains(" in condition:
            return self._eval_contains(obj, condition)
        if "string(" in condition:
            return self._eval_string(obj, condition)
        if "replace(" in condition:
            return self._eval_replace(obj, condition)

        # Comparaisons
        for op in ["!=", "==", "<=", ">=", "<", ">"]:
            if op in condition:
                return self._eval_comparison(obj, condition, op)

        return False

    def _eval_contains(self, obj: Dict, condition: str) -> bool:
        """
        Évalue: contains(tags, "#value")

        Exemples:
        - contains(tags, "#tag1") → True si #tag1 in obj['tags']
        - contains(string(header), "Frein") → True si "Frein" in str(obj['header'])
        """
        # Pattern: contains(field, "value")
        match = re.search(r'contains\s*\(\s*(\w+)\s*,\s*["\']([^"\']+)["\']\s*\)', condition)

        if match:
            field = match.group(1)
            value = match.group(2)
            field_value = obj.get(field, "")

            if isinstance(field_value, list):
                return value in field_value
            else:
                return value in str(field_value)

        # Pattern: contains(string(field), "value")
        match = re.search(r'contains\s*\(\s*string\s*\(\s*(\w+)\s*\)\s*,\s*["\']([^"\']+)["\']\s*\)', condition)

        if match:
            field = match.group(1)
            value = match.group(2)
            field_value = str(obj.get(field, ""))
            return value in field_value

        return False

    def _eval_string(self, obj: Dict, condition: str) -> bool:
        """
        Évalue: string(header) = "value"

        Convertit un champ en string et le compare
        """
        match = re.search(r'string\s*\(\s*(\w+)\s*\)\s*(==|!=|<=|>=|<|>)\s*["\']([^"\']+)["\']', condition)

        if match:
            field = match.group(1)
            op = match.group(2)
            value = match.group(3)

            field_value = str(obj.get(field, ""))
            return self._compare(field_value, value, op)

        return False

    def _eval_replace(self, obj: Dict, condition: str) -> bool:
        """
        Évalue: replace(string(header), "old", "new") = "result"

        Remplace un pattern dans un champ et compare
        """
        # Pattern: replace(string(field), "old", "new") = "result"
        match = re.search(
            r'replace\s*\(\s*string\s*\(\s*(\w+)\s*\)\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)\s*(==|!=)\s*["\']([^"\']+)["\']',
            condition
        )

        if match:
            field = match.group(1)
            old_val = match.group(2)
            new_val = match.group(3)
            op = match.group(4)
            result = match.group(5)

            field_value = str(obj.get(field, ""))
            replaced = field_value.replace(old_val, new_val)

            return self._compare(replaced, result, op)

        return False

    def _eval_comparison(self, obj: Dict, condition: str, op: str) -> bool:
        """
        Évalue une comparaison: field op value

        Exemples:
        - intervention != null
        - intervention <= 9
        - status == "done"
        """
        # Diviser par l'opérateur
        parts = condition.split(op)

        if len(parts) != 2:
            return False

        field_str = parts[0].strip()
        value_str = parts[1].strip()

        # Extraire la valeur du champ
        field_value = obj.get(field_str, None)

        # Parser la valeur à comparer
        compare_value = self._parse_value(value_str)

        return self._compare(field_value, compare_value, op)

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Parse une valeur (string, number, null, boolean)"""
        value_str = value_str.strip()

        if value_str.lower() == "null":
            return None
        elif value_str.lower() == "true":
            return True
        elif value_str.lower() == "false":
            return False
        elif value_str.isdigit():
            return int(value_str)
        elif value_str.replace(".", "", 1).isdigit():
            return float(value_str)
        else:
            # String (retirer guillemets si présents)
            return value_str.strip('\'"')

    @staticmethod
    def _compare(left: Any, right: Any, op: str) -> bool:
        """Compare deux valeurs avec un opérateur"""
        try:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == "<=":
                return left <= right
            elif op == ">=":
                return left >= right
            elif op == "<":
                return left < right
            elif op == ">":
                return left > right
        except TypeError:
            # Conversions au besoin
            try:
                left = float(left) if left is not None else 0
                right = float(right) if right is not None else 0
                if op == "<=":
                    return left <= right
                elif op == ">=":
                    return left >= right
                elif op == "<":
                    return left < right
                elif op == ">":
                    return left > right
            except (ValueError, TypeError):
                return False

        return False

    @staticmethod
    def _split_operator(text: str, operator: str) -> List[str]:
        """
        Divise le texte par un opérateur, en respectant les parenthèses

        Exemple:
        "(a OR b) AND c" divisé par "AND" → ["(a OR b)", "c"]
        """
        parts = []
        current = ""
        paren_depth = 0

        # Chercher l'opérateur en ignorant les parenthèses
        i = 0
        while i < len(text):
            if text[i] == "(":
                paren_depth += 1
                current += text[i]
            elif text[i] == ")":
                paren_depth -= 1
                current += text[i]
            elif paren_depth == 0 and text[i:i + len(operator)].upper() == operator:
                if current.strip():
                    parts.append(current.strip())
                current = ""
                i += len(operator) - 1
            else:
                current += text[i]

            i += 1

        if current.strip():
            parts.append(current.strip())

        return parts if len(parts) > 1 else [text]
