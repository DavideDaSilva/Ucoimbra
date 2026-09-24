#!/usr/bin/env bash
# ETAPA 3: junta todos os resultados e escreve a Tabela 2.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m src.reporting.build_table2 "$@"
