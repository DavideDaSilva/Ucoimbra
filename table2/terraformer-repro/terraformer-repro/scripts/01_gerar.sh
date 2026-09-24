#!/usr/bin/env bash
# ETAPA 1: gera o codigo Terraform com os modelos do Ollama.
#
# Uso:
#   ./scripts/01_gerar.sh tf_gen_test                  (todos os modelos)
#   ./scripts/01_gerar.sh tf_gen_test qwen2.5-coder:7b (um modelo so)
set -euo pipefail
cd "$(dirname "$0")/.."

DATASET="${1:-tf_gen_test}"
MODELO="${2:-}"

if [ -z "$MODELO" ]; then
  python3 -m src.generation.generate --dataset "$DATASET" --all-models
else
  python3 -m src.generation.generate --dataset "$DATASET" --model "$MODELO"
fi
