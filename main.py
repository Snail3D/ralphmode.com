from character import Character
from traits.job_anxiety import JobAnxiety

def main():
    ralph = Character("Ralph")
    ralph.add_trait(JobAnxiety())

    # Test Case 1: Trigger keyword
    print(ralph.react("Did you see the news about the economy?"))
    
    # Test Case 2: Work context
    print(ralph.react("The boss wants to see you in his office."))
    
    # Test Case 3: No trigger
    print(ralph.react("I like pizza."))

if __name__ == "__main__":
    main()