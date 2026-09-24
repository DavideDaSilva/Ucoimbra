#!/usr/bin/env bash
# Roda as tres etapas em sequencia, para todos os datasets e todos os modelos.
#
# Uso:
#   ./scripts/99_pipeline_completo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m src.common.check_environment || true

for DATASET in iac_eval tf_gen_test; do
  echo ""
  echo "############ DATASET: $DATASET ############"
  python3 -m src.generation.generate --dataset "$DATASET" --all-models
  python3 -m src.evaluation.evaluate --dataset "$DATASET" --all-models
done

python3 -m src.reporting.build_table2
