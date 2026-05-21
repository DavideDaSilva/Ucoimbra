#!/usr/bin/env python3
import requests

CONTEXT_FILE = "context.txt"
PROMPT_FILE = "prompt.txt"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# --- Generation parameters ---
TEMPERATURE = 0.2      # 0.0 = deterministic, 1.0+ = creative
TOP_P       = 0.9      # nucleus sampling cutoff
TOP_K       = 40       # top-k sampling (0 = disabled)
SEED        = 42       # fixed seed for reproducibility (-1 = random)
NUM_PREDICT = 2048     # max tokens to generate (-1 = unlimited)

MODELS = [
    "qwen2.5:latest",
    "qwen2.5-coder:32b",
    "qwen2.5:0.5b",
    "qwen2.5-coder:7b",
    "deepseek-coder",
    "deepseek-coder-v2:16b",
    "llama3.2",
    "mistral",
]

def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def query_local_llm(system_context, user_prompt, model):
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
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "top_p":       TOP_P,
            "top_k":       TOP_K,
            "seed":        SEED,
            "num_predict": NUM_PREDICT,
        }
    }

    response = requests.post(OLLAMA_URL, json=payload)

    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error: {response.text}")

    return response.json().get("response", "")

def main():
    print("Loading context and prompt...")
    context = load_file(CONTEXT_FILE)
    prompt  = load_file(PROMPT_FILE)

    for model in MODELS:
        print(f"Querying model: {model} ...")
        generated_code = query_local_llm(context, prompt, model)

        output_file = f"terraform_{model.replace(':', '_')}.tf"
        print(f"  -> Saving to {output_file}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(generated_code)

    print("Done.")

if __name__ == "__main__":
    main()