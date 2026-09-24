#!/usr/bin/env bash
# ETAPA 0: confere se tudo que o projeto precisa esta instalado.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m src.common.check_environment
