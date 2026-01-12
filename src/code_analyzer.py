import ast
from typing import List, Dict

class CodeAnalyzer:
    def analyze(self, file_path: str) -> Dict:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'args': [arg.arg for arg in node.args.args]
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
                
        return {'functions': functions, 'classes': classes}