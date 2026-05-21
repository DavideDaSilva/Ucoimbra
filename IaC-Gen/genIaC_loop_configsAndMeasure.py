# import time

# def query_local_llm(system_context, user_prompt, model):
#     full_prompt = f"""
# <system>
# {system_context}
# </system>

# <user>
# {user_prompt}
# </user>
# """

#     payload = {
#         "model": model,
#         "prompt": full_prompt,
#         "stream": False,
#         "options": {
#             "temperature": TEMPERATURE,
#             "top_p": TOP_P,
#             "top_k": TOP_K,
#             "seed": SEED,
#             "num_predict": NUM_PREDICT,
#         }
#     }

#     start = time.time()
#     response = requests.post(OLLAMA_URL, json=payload)
#     end = time.time()

#     if response.status_code != 200:
#         raise RuntimeError(f"Ollama API error: {response.text}")

#     data = response.json()

#     # Extract metrics
#     response_time = end - start
#     eval_count = data.get("eval_count", 0)
#     eval_duration = data.get("eval_duration", 1) / 1e9  # ns → seconds
#     tokens_per_second = eval_count / eval_duration

#     return {
#         "text": data.get("response", ""),
#         "response_time": response_time,
#         "tokens_per_second": tokens_per_second,
#         "eval_count": eval_count,
#         "prompt_eval_count": data.get("prompt_eval_count", 0),
#         "eval_duration_seconds": eval_duration
#     }
# # ======================================================
# # ======================================================

#!/usr/bin/env python3
import requests
import time

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
            "top_p": TOP_P,
            "top_k": TOP_K,
            "seed": SEED,
            "num_predict": NUM_PREDICT,
        }
    }

    start = time.time()
    response = requests.post(OLLAMA_URL, json=payload)
    end = time.time()

    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error: {response.text}")

    data = response.json()

    # Extract metrics
    response_time = end - start
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 1) / 1e9  # ns → seconds
    tokens_per_second = eval_count / eval_duration

    return {
        "text": data.get("response", ""),
        "response_time": response_time,
        "tokens_per_second": tokens_per_second,
        "eval_count": eval_count,
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "eval_duration_seconds": eval_duration
    }
# ======================================================
# ======================================================

def main():
    print("Loading context and prompt...")
    context = load_file(CONTEXT_FILE)
    prompt  = load_file(PROMPT_FILE)

    for model in MODELS:
        print(f"Querying model: {model} ...")
        result = query_local_llm(context, prompt, model)  # result is a dict

        output_file = f"terraform_{model.replace(':', '_')}.tf"
        print(f"  -> Saving to {output_file}")
        print(f"     Response time:     {result['response_time']:.2f}s")
        print(f"     Tokens generated:  {result['eval_count']}")
        print(f"     Tokens/sec:        {result['tokens_per_second']:.1f}")
        print(f"     Prompt tokens:     {result['prompt_eval_count']}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["text"])  # <-- extract the string

    print("Done.")

if __name__ == "__main__":
    main()