"""Cria geracoes falsas para o autoteste, sem precisar do Ollama."""
from pathlib import Path

CODIGO = (
    'terraform {\n  required_version = "~> 1.12.0"\n}\n\n'
    'provider "aws" {\n  region = "us-east-1"\n}\n\n'
    'resource "aws_s3_bucket" "b" {\n  bucket = "app-artifacts-2026"\n}\n'
)

def main() -> None:
    for modelo, quantas_ok in (("qwen2.5-coder_7b", 2), ("llama3.2", 1)):
        raiz = Path("results_autoteste/generations") / modelo / "tf_gen_test"
        for i in (1, 2, 3):
            pasta = raiz / f"tfgen_{i:03d}"
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / "main.tf").write_text(CODIGO if i <= quantas_ok else "")
    print("Geracoes falsas criadas em results_autoteste/generations")

if __name__ == "__main__":
    main()
