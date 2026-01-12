from .code_analyzer import CodeAnalyzer
from .question_generator import QuestionGenerator

class DynamicQuestionService:
    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.generator = QuestionGenerator()

    def process_codebase(self, file_paths: list) -> list:
        all_questions = []
        for path in file_paths:
            try:
                data = self.analyzer.analyze(path)
                questions = self.generator.generate(data)
                all_questions.extend(questions)
            except Exception as e:
                print(f"Error processing {path}: {e}")
        return all_questions