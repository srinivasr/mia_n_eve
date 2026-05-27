#!/usr/bin/env python3
"""
LLM Validation Script for mia_n_eve runtime.
Checks Ollama availability and OpenAI API.
"""
import sys
import urllib.request
import json
import os

def check_ollama():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = [m['name'] for m in data.get('models', [])]
                print(f"✅ Ollama running. Found {len(models)} models.")
                if models:
                    print(f"   Available: {', '.join(models[:3])}{'...' if len(models)>3 else ''}")
                return True
    except Exception:
        print("❌ Ollama not running or not reachable at localhost:11434")
        return False

def check_openai():
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print("✅ OPENAI_API_KEY environment variable is set.")
    else:
        print("⚠️ OPENAI_API_KEY not set (required for OpenAI LLM).")
        
def main():
    print("--- LLM Environment Validation ---")
    ollama_ok = check_ollama()
    check_openai()
    # Don't fail if just Ollama is missing, as cloud could be used
    return 0 

if __name__ == "__main__":
    sys.exit(main())
