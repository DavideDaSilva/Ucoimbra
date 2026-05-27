#!/usr/bin/env python3
import os
import requests
import time

# -----------------------------
# Configuration
# -----------------------------
BASE_DIR = "scenarioprincipal"
PROMPT_FILENAME = "prompt.txt"
OUTPUT_FOLDER = "codigo_gerado"
METRICS_FILENAME = "metrics.txt"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# --- Generation parameters ---
TEMPERATURE = 0.2
TOP_P       = 0.9
TOP_K       = 40
SEED        = 42
NUM_PREDICT = 2048

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

# -----------------------------
# Helper functions
# -----------------------------
def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def query_local_llm(user_prompt, model):
    payload = {
        "model": model,
        "prompt": user_prompt,
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

    response_time = end - start
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 1) / 1e9
    tokens_per_second = eval_count / eval_duration

    return {
        "text": data.get("response", ""),
        "response_time": response_time,
        "tokens_per_second": tokens_per_second,
        "eval_count": eval_count,
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "eval_duration_seconds": eval_duration
    }

# -----------------------------
# Main processing loop
# -----------------------------
def main():
    print("Scanning scenarios inside:", BASE_DIR)

    # Collecting only the scenario folders and sort them numerically: scenario1, scenario2, ..., scenario30
    scenarios = []
    for name in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, name)
        if os.path.isdir(path) and name.startswith("scenario"):
            try:
                num = int(name.replace("scenario", ""))
                scenarios.append((num, name))
            except ValueError:
                continue

    scenarios.sort(key=lambda x: x[0])

    for num, scenario in scenarios:
        scenario_path = os.path.join(BASE_DIR, scenario)
        print(f"\n=== Processing {scenario} ===")

        metrics_path = os.path.join(scenario_path, METRICS_FILENAME)

        try:
            prompt_path  = os.path.join(scenario_path, PROMPT_FILENAME)
            output_dir   = os.path.join(scenario_path, OUTPUT_FOLDER)

            os.makedirs(output_dir, exist_ok=True)

            # Create/clear metrics file at start of scenario
            with open(metrics_path, "w", encoding="utf-8") as m:
                m.write(f"Metrics for {scenario}\n")
                m.write("=" * 40 + "\n\n")

            # If prompt.txt is missing, log it but continue
            if not os.path.exists(prompt_path):
                msg = "Missing prompt.txt"
                print(f"  -> {msg}")
                with open(metrics_path, "a", encoding="utf-8") as m:
                    m.write(f"SCENARIO WARNING: {msg}\n")
                    m.write("=" * 40 + "\n")
                continue

            prompt = load_file(prompt_path)

            # Model loop
            for model in MODELS:
                print(f"  -> Querying model: {model}")

                try:
                    result = query_local_llm(prompt, model)

                    output_file = os.path.join(
                        output_dir,
                        f"terraform_{model.replace(':', '_')}.tf"
                    )

                    print(f"     Saving to: {output_file}")
                    print(f"     Response time: {result['response_time']:.2f}s")
                    print(f"     Tokens generated: {result['eval_count']}")
                    print(f"     Tokens/sec: {result['tokens_per_second']:.1f}")

                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(result["text"])

                    with open(metrics_path, "a", encoding="utf-8") as m:
                        m.write(f"Model: {model}\n")
                        m.write(f"Response time: {result['response_time']:.2f}s\n")
                        m.write(f"Tokens generated: {result['eval_count']}\n")
                        m.write(f"Tokens/sec: {result['tokens_per_second']:.1f}\n")
                        m.write("-" * 40 + "\n")

                except Exception as e:
                    print(f"     ERROR with model {model}: {e}")
                    with open(metrics_path, "a", encoding="utf-8") as m:
                        m.write(f"Model: {model}\n")
                        m.write(f"ERROR: {e}\n")
                        m.write("-" * 40 + "\n")
                    continue

        except Exception as scenario_error:
            print(f"UNEXPECTED ERROR in {scenario}: {scenario_error}")
            try:
                with open(metrics_path, "a", encoding="utf-8") as m:
                    m.write(f"\nSCENARIO ERROR: {scenario_error}\n")
                    m.write("=" * 40 + "\n")
            except Exception:
                pass

    print("\nAll scenarios processed in numeric order (scenario1 → scenario30).")

if __name__ == "__main__":
    main()
