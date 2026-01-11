
"""
Environment Verification Script
Run this script to check if your environment is correctly set up for TradingAgents.
"""
import os
import sys
import importlib.util
from pathlib import Path

def check_python_version():
    print(f"Checking Python version... {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        return False
    print("✅ Python version OK")
    return True

def check_dependencies():
    print("\nChecking core dependencies...")
    required = [
        "langchain_openai", "langchain_anthropic", "langgraph", 
        "pandas", "yfinance", "streamlit", "sqlite3"
    ]
    missing = []
    for pkg in required:
        if importlib.util.find_spec(pkg) is None and importlib.util.find_spec(pkg.replace("-", "_")) is None:
            # Handle special cases like sqlite3 (built-in usually)
            if pkg == "sqlite3": continue
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    print("✅ Core dependencies OK")
    return True

def check_env_vars():
    print("\nChecking environment variables...")
    # These are optional depending on config but checking for common ones
    keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]
    found = []
    for key in keys:
        if os.getenv(key):
            found.append(key)
    
    if not found:
        print("⚠️  No LLM API keys found in environment variables.")
        print("   If using Ollama (local), this is fine.")
        print("   If using OpenAI/Anthropic/OpenRouter, set them in .env")
    else:
        print(f"✅ Found keys: {', '.join(found)}")
    return True

def check_directories():
    print("\nChecking directories...")
    current = Path.cwd()
    required = ["dashboard", "tradingagents", "results", "data"]
    
    for d in required:
        p = current / d
        if not p.exists():
            print(f"⚠️  Directory '{d}' missing. Creating...")
            p.mkdir(exist_ok=True)
            
    # Check data/llm_cache.db path
    db_path = current / "dashboard" / "data"
    db_path.mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories OK")
    return True

def main():
    print("🔍 TradingAgents Environment Check")
    print("="*40)
    
    steps = [
        check_python_version,
        check_dependencies,
        check_directories,
        check_env_vars
    ]
    
    all_passed = True
    for step in steps:
        if not step():
            all_passed = False
            
    print("="*40)
    if all_passed:
        print("🚀 System looks ready! You can run:")
        print("   streamlit run dashboard/app.py")
    else:
        print("❌ Some checks failed. Please fix issues above.")

if __name__ == "__main__":
    main()
