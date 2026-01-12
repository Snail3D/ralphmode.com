import sys
from src.service import DynamicQuestionService

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <file1.py> <file2.py> ...")
        sys.exit(1)
        
    service = DynamicQuestionService()
    files = sys.argv[1:]
    questions = service.process_codebase(files)
    
    print("--- Generated Contextual Questions ---")
    for q in questions:
        print(f"- {q}")