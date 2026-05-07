#!/usr/bin/env python3
import requests

CONTEXT_FILE = "context.txt"
PROMPT_FILE = "prompt.txt"
OUTPUT_FILE = "terraform.tf"

# Local Ollama server URL
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


#! Model to test
#? MODEL_NAME = "qwen2.5:latest"   # deepseek-coder-v2:16b, qwen2.5-coder:32b, deepseek-coder, llama3, mistral

#! Model to test
#? MODEL_NAME = "qwen2.5:latest"   # deepseek-coder-v2:16b, qwen2.5-coder:32b, deepseek-coder, llama3, mistral, etc.
# To check which model is available, one can use the following command: ollama list
MODEL_NAME = "qwen2.5-coder:32b"


def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def query_local_llm(system_context: str, user_prompt: str, model: str) -> str:
    """
    Sends a structured system + user message to a local LLM using the Ollama HTTP API.
    """
    full_prompt = f"""
<system>
{system_context}
</system>

<user>
{user_prompt}
</user>
"""

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error: {response.text}")

    data = response.json()
    return data.get("response", "")


def main():
    print("Loading context and prompt...")
    context = load_file(CONTEXT_FILE)
    prompt = load_file(PROMPT_FILE)

    print(f"Querying model: {MODEL_NAME} via HTTP API...")
    generated_code = query_local_llm(context, prompt, MODEL_NAME)

    print(f"Saving Terraform code to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generated_code)

    print("Done. Terraform code generated successfully.")


if __name__ == "__main__":
    main()
