from typing import List, Dict

class QuestionGenerator:
    def generate(self, analysis_data: Dict) -> List[str]:
        questions = []
        
        for func in analysis_data.get('functions', []):
            questions.append(f"What is the responsibility of the function '{func['name']}'?")
            if len(func['args']) > 3:
                questions.append(f"Could the function '{func['name']}' be refactored to reduce the number of parameters?")
                
        for cls in analysis_data.get('classes', []):
            questions.append(f"What problem does the class '{cls['name']}' solve?")
            if len(cls['methods']) > 7:
                questions.append(f"Does the class '{cls['name']}' violate the Single Responsibility Principle?")
                
        return questions