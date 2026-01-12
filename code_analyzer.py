import ast
import os
from typing import List, Dict

class CodeAnalyzer:
    def analyze_directory(self, root_path: str) -> List[Dict]:
        context = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    context.extend(self._analyze_file(file_path))
        return context

    def _analyze_file(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            return []

        nodes = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                nodes.append({
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": node.name,
                    "file": file_path,
                    "line": node.lineno,
                    "docstring": docstring or "",
                    "source": self._get_snippet(file_path, node.lineno)
                })
        return nodes

    def _get_snippet(self, file_path: str, lineno: int) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                start = max(0, lineno - 1)
                end = min(len(lines), lineno + 4)
                return "".join(lines[start:end])
        except Exception:
            return ""