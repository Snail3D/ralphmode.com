from typing import List, Dict

class QuestionGenerator:
    def __init__(self, model_name: str = "default-model"):
        self.model_name = model_name

    def generate(self, code_context: List[Dict]) -> List[Dict]:
        if not code_context:
            return []

        questions = []
        
        for item in code_context:
            q_type = "Implementation" if item['type'] == 'function' else "Architecture"
            
            # Generate primary question
            questions.append({
                "question": f"What is the specific responsibility of the {item['type']} '{item['name']}' defined in {os.path.basename(item['file'])}?",
                "context": item['docstring'],
                "category": q_type,
                "metadata": {
                    "file": item['file'],
                    "line": item['line']
                }
            })
            
            # Generate complexity question if code is long
            if len(item['source']) > 300:
                questions.append({
                    "question": f"Can the logic within '{item['name']}' be simplified or refactored for better readability?",
                    "context": item['source'],
                    "category": "Refactoring",
                    "metadata": {
                        "file": item['file'],
                        "line": item['line']
                    }
                })

        return questions