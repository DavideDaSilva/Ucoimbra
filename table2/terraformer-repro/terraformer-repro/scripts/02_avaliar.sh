#!/usr/bin/env bash
# ETAPA 2: roda os tres oraculos e as duas metricas sobre o codigo gerado.
#
# Uso:
#   ./scripts/02_avaliar.sh tf_gen_test
#   ./scripts/02_avaliar.sh tf_gen_test qwen2.5-coder:7b
set -euo pipefail
cd "$(dirname "$0")/.."

DATASET="${1:-tf_gen_test}"
MODELO="${2:-}"

if [ -z "$MODELO" ]; then
  python3 -m src.evaluation.evaluate --dataset "$DATASET" --all-models
else
  python3 -m src.evaluation.evaluate --dataset "$DATASET" --model "$MODELO"
fi
