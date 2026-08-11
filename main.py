from src.models.llm import get_llm

def main():
    print("🤖 Agent project initialized successfully!")
    client = get_llm()
    print("Model status:", client)

if __name__ == "__main__":
    main()
