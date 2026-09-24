"""
IMPORTADOR DO DATASET IaC-Eval
==============================

Para que serve:
  O paper avalia os modelos no IaC-Eval, que e o unico benchmark publico de
  NL-to-Terraform (458 instancias). Este script converte o IaC-Eval para o
  formato usado pelo projeto:

      data/benchmark/iac_eval/instances.jsonl
      data/benchmark/iac_eval/policies/<id>.rego

Como usar:
  1. instale a biblioteca de datasets:
       pip install datasets
  2. rode em modo inspecao para ver os nomes das colunas:
       python -m src.data_tools.import_iac_eval --inspecionar
  3. rode a conversao (ajustando os nomes das colunas se necessario):
       python -m src.data_tools.import_iac_eval \
           --coluna-prompt Prompt --coluna-policy Policy

Observacao honesta: os nomes das colunas do IaC-Eval podem mudar entre versoes
do dataset. Por isso o modo inspecao existe: ele mostra as colunas reais antes
de voce converter qualquer coisa.

As politicas do IaC-Eval seguem a convencao de negacao (`deny`). O conversor
mantem o texto original e apenas envolve a regra em um nome `is_valid_policy`
quando nao encontra nenhuma regra `is_valid_*`, para respeitar a convencao do
projeto. Revise os arquivos gerados antes de confiar nos numeros.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.common.config import load_config

CANDIDATAS_PROMPT = ["Prompt", "prompt", "nl_prompt", "instruction", "Intent"]
CANDIDATAS_POLICY = ["Policy", "policy", "rego", "rego_policy", "policy_code"]

_RULE_RE = re.compile(r"^is_valid_[A-Za-z0-9_]*", re.MULTILINE)


def escolher(colunas, candidatas, informada):
    if informada:
        if informada not in colunas:
            raise SystemExit(
                f"A coluna '{informada}' nao existe. Colunas disponiveis: {colunas}"
            )
        return informada
    for c in candidatas:
        if c in colunas:
            return c
    raise SystemExit(
        f"Nao consegui adivinhar a coluna. Informe manualmente. Colunas: {colunas}"
    )


def adaptar_policy(texto: str) -> str:
    """Garante o pacote e ao menos uma regra `is_valid_*`."""
    corpo = texto.strip()
    if "package " not in corpo:
        corpo = "package terraform.policy\n\nimport rego.v1\n\n" + corpo
    if not _RULE_RE.search(corpo):
        corpo += (
            "\n\n# Regra de compatibilidade criada pelo importador:\n"
            "# a instancia so e considerada correta quando nenhuma regra de\n"
            "# negacao (deny) dispara.\n"
            "is_valid_policy if {\n"
            "\tcount(deny) == 0\n"
            "}\n"
        )
    return corpo


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte o IaC-Eval para este projeto")
    parser.add_argument("--hf-id", default="autoiac-project/iac-eval")
    parser.add_argument("--split", default="test")
    parser.add_argument("--coluna-prompt")
    parser.add_argument("--coluna-policy")
    parser.add_argument("--inspecionar", action="store_true")
    parser.add_argument("--limite", type=int)
    args = parser.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        raise SystemExit("Instale a biblioteca primeiro: pip install datasets")

    ds = load_dataset(args.hf_id, split=args.split)
    colunas = list(ds.column_names)

    if args.inspecionar:
        print("Colunas encontradas:", colunas)
        print("\nPrimeira linha (resumida):")
        print(json.dumps({k: str(ds[0][k])[:300] for k in colunas}, indent=2))
        return

    col_prompt = escolher(colunas, CANDIDATAS_PROMPT, args.coluna_prompt)
    col_policy = escolher(colunas, CANDIDATAS_POLICY, args.coluna_policy)

    cfg = load_config()
    destino = cfg.resolve(cfg.dataset("iac_eval")["instances"]).parent
    politicas = destino / "policies"
    politicas.mkdir(parents=True, exist_ok=True)

    linhas = []
    total = len(ds) if not args.limite else min(len(ds), args.limite)
    for i in range(total):
        row = ds[i]
        inst_id = f"iaceval_{i + 1:04d}"
        (politicas / f"{inst_id}.rego").write_text(
            adaptar_policy(str(row[col_policy] or "")), encoding="utf-8"
        )
        linhas.append(
            json.dumps(
                {
                    "id": inst_id,
                    "prompt": str(row[col_prompt]).strip(),
                    "policy": f"policies/{inst_id}.rego",
                },
                ensure_ascii=False,
            )
        )

    (destino / "instances.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Importadas {total} instancias para {destino / 'instances.jsonl'}")
    print("Revise alguns arquivos .rego antes de rodar a avaliacao.")


if __name__ == "__main__":
    main()
