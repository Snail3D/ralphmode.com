import os
from integration import RequirementExtractionService
from storage import InMemoryStorage


def main():
    storage = InMemoryStorage()
    storage.add_question("q1", "What features do you need in your application?")
    storage.add_question("q2", "What are your performance requirements?")
    storage.set_user_context("user123", {"project": "E-commerce Platform", "role": "Product Manager"})
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    service = RequirementExtractionService(api_key, storage)
    
    response1 = service.process_user_response(
        user_id="user123",
        question_id="q1",
        answer="We need user authentication, product catalog, shopping cart, and payment processing. The system should support at least 10,000 concurrent users."
    )
    
    response2 = service.process_user_response(
        user_id="user123",
        question_id="q2",
        answer="Page load times should be under 2 seconds. API responses should be under 100ms. We need 99.9% uptime."
    )
    
    all_requirements = service.get_user_requirements("user123")
    
    print("Extracted Requirements:")
    for req in all_requirements:
        print(f"- [{req['type']}] {req['description']} (Priority: {req['priority']})")


if __name__ == "__main__":
    main()