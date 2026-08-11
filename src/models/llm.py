import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def get_llm():
    """Return the initialized LLM client."""
    # Priority for keys
    if os.getenv("DEEPSEEK_API_KEY"):
        return ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            max_tokens=2048,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=2048,
        )
    else:
        raise ValueError("No supported API key found in .env (expected DEEPSEEK_API_KEY or OPENAI_API_KEY)")
