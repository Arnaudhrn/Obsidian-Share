"""
FunctionRegistry - Fonctions Dataview (contains, string, replace, dateformat, choice, ...)

Extensible: ajouter une fonction = ajouter une méthode _fn_* et l'enregistrer dans __init__.
"""
from datetime import datetime
from typing import Any, Dict


class FunctionRegistry:

    def __init__(self):
        self._functions: Dict = {
            'contains':   self._fn_contains,
            'string':     self._fn_string,
            'replace':    self._fn_replace,
            'dateformat': self._fn_dateformat,
            'choice':     self._fn_choice,
            'lower':      self._fn_lower,
            'upper':      self._fn_upper,
            'length':     self._fn_length,
            'min':        self._fn_min,
            'max':        self._fn_max,
        }

    def call(self, name: str, *args) -> Any:
        func = self._functions.get(name.lower())
        if func is None:
            raise ValueError(f"Fonction Dataview inconnue: '{name}'")
        return func(*args)

    def has(self, name: str) -> bool:
        return name.lower() in self._functions

    # ------------------------------------------------------------------
    # Implémentations
    # ------------------------------------------------------------------

    @staticmethod
    def _fn_contains(haystack: Any, needle: Any) -> bool:
        """
        contains(list, "#tag")  → True si "#tag" est dans la liste
        contains("texte", "mot") → True si "mot" est dans "texte"
        """
        if haystack is None:
            return False
        needle_str = str(needle)
        if isinstance(haystack, list):
            return any(needle_str.lower() in str(item).lower() for item in haystack)
        return needle_str.lower() in str(haystack).lower()

    @staticmethod
    def _fn_string(value: Any) -> str:
        """string(value) → str"""
        return '' if value is None else str(value)

    @staticmethod
    def _fn_replace(text: Any, old: Any, new: Any) -> str:
        """replace(text, "old", "new") → str"""
        return '' if text is None else str(text).replace(str(old), str(new))

    @staticmethod
    def _fn_dateformat(date: Any, fmt: str) -> str:
        """
        dateformat(date, "dd MMMM yyyy") → "28 septembre 2024"
        Convertit le format Obsidian en strftime Python.
        """
        if date is None:
            return ''

        if isinstance(date, str):
            for pattern in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
                try:
                    date = datetime.strptime(date.strip(), pattern)
                    break
                except ValueError:
                    continue
            else:
                return str(date)

        # Obsidian token → strftime (ordre important: MMMM avant MM)
        py_fmt = fmt
        py_fmt = py_fmt.replace('yyyy', '%Y')
        py_fmt = py_fmt.replace('yy',   '%y')
        py_fmt = py_fmt.replace('MMMM', '%B')
        py_fmt = py_fmt.replace('MMM',  '%b')
        py_fmt = py_fmt.replace('MM',   '%m')
        py_fmt = py_fmt.replace('dd',   '%d')
        py_fmt = py_fmt.replace('HH',   '%H')
        py_fmt = py_fmt.replace('mm',   '%M')
        py_fmt = py_fmt.replace('ss',   '%S')

        try:
            return date.strftime(py_fmt)
        except Exception:
            return str(date)

    @staticmethod
    def _fn_choice(value: Any, true_val: Any, false_val: Any) -> Any:
        """choice(value, "✅", "❌") → true_val si truthy, false_val sinon"""
        return true_val if bool(value) else false_val

    @staticmethod
    def _fn_lower(value: Any) -> str:
        return str(value).lower() if value is not None else ''

    @staticmethod
    def _fn_upper(value: Any) -> str:
        return str(value).upper() if value is not None else ''

    @staticmethod
    def _fn_length(value: Any) -> int:
        if value is None:
            return 0
        return len(value) if hasattr(value, '__len__') else 0

    @staticmethod
    def _fn_min(*args) -> Any:
        flat = []
        for a in args:
            if isinstance(a, list):
                flat.extend(a)
            else:
                flat.append(a)
        nums = [x for x in flat if x is not None]
        return min(nums) if nums else None

    @staticmethod
    def _fn_max(*args) -> Any:
        flat = []
        for a in args:
            if isinstance(a, list):
                flat.extend(a)
            else:
                flat.append(a)
        nums = [x for x in flat if x is not None]
        return max(nums) if nums else None
