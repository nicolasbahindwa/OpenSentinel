"""
Quick environment test - run this first to verify .env is loading
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env
project_root = Path(__file__).parent
env_path = project_root / ".env"

print(f"Project root: {project_root}")
print(f"Looking for .env at: {env_path}")
print(f".env file exists: {env_path.exists()}")

if env_path.exists():
    print(f"\nFirst 20 lines of .env file:")
    with open(env_path, 'r') as f:
        for i, line in enumerate(f):
            if i < 20:
                print(f"  {line.rstrip()}")

print("\n" + "="*60)
print("Loading .env file...")
print("="*60)

loaded = load_dotenv(dotenv_path=env_path, override=True)
print(f"load_dotenv returned: {loaded}")

print("\n" + "="*60)
print("Environment variables after load:")
print("="*60)

# Check specific variables
test_vars = [
    "OPENSENTINEL_MODEL_NAME",
    "OPENSENTINEL_MODEL_TEMPERATURE",
    "OPENSENTINEL_MODEL_MAX_TOKENS",
    "OLLAMA_BASE_URL",
    "OLLAMA_DEFAULT_MODEL",
]

for var in test_vars:
    value = os.getenv(var)
    status = "✓" if value else "✗"
    print(f"{status} {var} = {value}")

print("\n" + "="*60)
print("All environment variables containing 'OPENSENTINEL' or 'OLLAMA':")
print("="*60)

for key, value in sorted(os.environ.items()):
    if "OPENSENTINEL" in key or "OLLAMA" in key:
        print(f"  {key} = {value}")

# Now test the LLM factory
print("\n" + "="*60)
print("Testing LLM factory...")
print("="*60)

try:
    from src.Agent.llm_factory import create_llm, DEFAULT_MODEL_NAME

    print(f"DEFAULT_MODEL_NAME from factory: {DEFAULT_MODEL_NAME}")

    if DEFAULT_MODEL_NAME:
        print(f"\nAttempting to create LLM with model: {DEFAULT_MODEL_NAME}")
        llm = create_llm()
        print(f"✓ Successfully created LLM: {type(llm).__name__}")
    else:
        print("✗ DEFAULT_MODEL_NAME is empty!")

except Exception as e:
    print(f"✗ Error creating LLM: {e}")
    import traceback
    traceback.print_exc()
