#!/usr/bin/env bash
# AUTOTESTE: confere se o pipeline funciona de ponta a ponta usando ferramentas
# FALSAS. Serve para validar o codigo do projeto antes de instalar Terraform,
# OPA, TFLint e Checkov de verdade. Os numeros deste teste NAO tem valor
# cientifico: servem apenas para verificar o encanamento.
set -euo pipefail
cd "$(dirname "$0")/.."

# Copia as ferramentas falsas para uma pasta temporaria e as torna executaveis.
FAKEBIN="$(mktemp -d)"
for f in terraform opa tflint checkov; do
  cp "tests/fake_tools/$f.sh" "$FAKEBIN/$f"
  chmod +x "$FAKEBIN/$f"
done
export PATH="$FAKEBIN:$PATH"
trap 'rm -rf "$FAKEBIN"' EXIT

rm -rf results_autoteste
python3 tests/preparar_geracoes_falsas.py
python3 -m src.evaluation.evaluate --config config/config.autoteste.yaml --dataset tf_gen_test --model qwen2.5-coder:7b --limit 3
python3 -m src.evaluation.evaluate --config config/config.autoteste.yaml --dataset tf_gen_test --model llama3.2 --limit 3
python3 -m src.reporting.build_table2 --config config/config.autoteste.yaml --datasets tf_gen_test

echo ""
echo "Autoteste concluido. Veja tambem os arquivos pass.txt, fail.txt e error.txt em:"
echo "  results_autoteste/evaluations/qwen2.5-coder_7b/tf_gen_test/oracles/"
