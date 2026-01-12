import os
import ast
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class CodeContext:
    file_path: str
    class_name: Optional[str]
    function_name: str
    docstring: Optional[str]
    source_lines: List[str]

class CodebaseAnalyzer:
    def analyze_directory(self, root_path: str) -> List[CodeContext]:
        contexts = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    contexts.extend(self._analyze_file(file_path))
        return contexts

    def _analyze_file(self, file_path: str) -> List[CodeContext]:
        contexts = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source)
                
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node)
                    source_lines = source.splitlines()
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
                    
                    contexts.append(CodeContext(
                        file_path=file_path,
                        class_name=None,
                        function_name=node.name,
                        docstring=docstring,
                        source_lines=source_lines[start_line:end_line]
                    ))
        except Exception:
            pass
        return contexts

class DynamicQuestionService:
    def __init__(self, analyzer: CodebaseAnalyzer, llm_client):
        self.analyzer = analyzer
        self.llm_client = llm_client

    def generate_questions(self, repo_path: str, focus_area: Optional[str] = None) -> List[str]:
        contexts = self.analyzer.analyze_directory(repo_path)
        if not contexts:
            return []
        
        context_summary = self._summarize_contexts(contexts)
        prompt = self._build_prompt(context_summary, focus_area)
        
        response = self.llm_client.generate(prompt)
        return self._parse_response(response)

    def _summarize_contexts(self, contexts: List[CodeContext]) -> str:
        summary_parts = []
        for ctx in contexts[:20]: # Limit context window
            sig = f"{ctx.file_path}::{ctx.function_name}"
            summary_parts.append(f"Function: {sig}\nDoc: {ctx.docstring or 'No docs'}")
        return "\n---\n".join(summary_parts)

    def _build_prompt(self, summary: str, focus_area: Optional[str]) -> str:
        base = f"Analyze the following codebase summary:\n{summary}\n\n"
        if focus_area:
            base += f"Focus specifically on: {focus_area}\n"
        base += "Generate 3 distinct, contextual technical questions to verify understanding of this code."
        return base

    def _parse_response(self, response: str) -> List[str]:
        # Simple parsing logic assuming LLM returns numbered list
        questions = []
        for line in response.split('\n'):
            if line.strip().startswith(('1.', '2.', '3.', '-', '*')):
                questions.append(line.split('.', 1)[-1].strip())
        return questions