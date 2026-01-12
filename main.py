import argparse
import json
import os
from code_analyzer import CodeAnalyzer
from question_generator import QuestionGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate contextual questions from codebase.")
    parser.add_argument("path", help="Path to the codebase directory")
    parser.add_argument("--output", "-o", help="Output JSON file path", default=None)
    args = parser.parse_args()

    print(f"Analyzing codebase at: {args.path}")
    
    # 1. Analyze Code
    analyzer = CodeAnalyzer()
    context = analyzer.analyze_directory(args.path)
    
    if not context:
        print("No analyzable Python code found.")
        return

    print(f"Found {len(context)} code structures.")

    # 2. Generate Questions
    generator = QuestionGenerator()
    questions = generator.generate(context)

    # 3. Output Results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(questions, f, indent=2)
        print(f"Generated {len(questions)} questions saved to {args.output}")
    else:
        print("\n=== Generated Questions ===")
        for i, q in enumerate(questions, 1):
            print(f"\nQ{i} [{q['category']}]: {q['question']}")
            print(f"   Ref: {q['metadata']['file']}:{q['metadata']['line']}")

if __name__ == "__main__":
    main()