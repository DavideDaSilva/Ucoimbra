"""
ETAPA 3: CONSTRUCAO DA TABELA 2
===============================

O que este script faz, em linguagem simples:
  ele procura todos os arquivos resumo.json produzidos pela etapa de avaliacao
  e junta tudo em uma unica tabela, no mesmo formato da Tabela 2 do paper:

    linhas   = modelos avaliados
    colunas  = Correctness, Deployability, Compilability, Linter Pass Rate e
               Security Compliance, repetidas para cada dataset

  O melhor valor de cada coluna fica em negrito e o segundo melhor sublinhado,
  exatamente como no paper.

Saidas geradas em results/tables/:
  tabela2.md    -> para ler e colar no seu relatorio
  tabela2.csv   -> para abrir no Excel ou no LibreOffice
  tabela2.tex   -> para colar direto em um artigo LaTeX
  tabela2.json  -> os numeros crus, caso queira reprocessar

Uso:
    python -m src.reporting.build_table2
    python -m src.reporting.build_table2 --datasets tf_gen_test
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from src.common.config import Config, load_config
from src.common.naming import slug

METRIC_LABELS = {
    "correctness": "Correctness (%)",
    "deployability": "Deployability (%)",
    "compilability": "Compilability (%)",
    "linter_pass_rate": "Linter Pass Rate (%)",
    "security_compliance": "Security Compliance (%)",
}


def collect(cfg: Config, dataset_keys: List[str]) -> Dict[str, Dict[str, Any]]:
    """Le todos os resumo.json disponiveis: {modelo: {dataset: metricas}}."""
    data: Dict[str, Dict[str, Any]] = {}
    eval_root = cfg.path("evaluations")
    for model in cfg.models:
        name = model["name"]
        per_dataset = {}
        for ds_key in dataset_keys:
            summary_file = eval_root / slug(name) / ds_key / "resumo.json"
            if summary_file.exists():
                per_dataset[ds_key] = json.loads(
                    summary_file.read_text(encoding="utf-8")
                )
        if per_dataset:
            data[name] = per_dataset
    return data


def rank_marks(values: List[float | None]) -> Dict[int, str]:
    """Descobre qual posicao recebe negrito (1o) e sublinhado (2o)."""
    pairs = [(v, i) for i, v in enumerate(values) if v is not None]
    if not pairs:
        return {}
    ordered = sorted({v for v, _ in pairs}, reverse=True)
    marks: Dict[int, str] = {}
    best = ordered[0]
    second = ordered[1] if len(ordered) > 1 else None
    for value, idx in pairs:
        if value == best:
            marks[idx] = "best"
        elif second is not None and value == second:
            marks[idx] = "second"
    return marks


def fmt(value: float | None, mark: str | None, style: str) -> str:
    if value is None:
        return "n/d"
    text = f"{value:.2f}"
    if mark == "best":
        return f"**{text}**" if style == "md" else f"\\textbf{{{text}}}"
    if mark == "second":
        return f"<u>{text}</u>" if style == "md" else f"\\underline{{{text}}}"
    return text


def build(cfg: Config, dataset_keys: List[str]) -> Dict[str, Any]:
    metrics = cfg.table2.get("metrics", list(METRIC_LABELS))
    data = collect(cfg, dataset_keys)

    if not data:
        raise SystemExit(
            "Nenhum resultado encontrado em results/evaluations.\n"
            "Rode antes a geracao e a avaliacao."
        )

    # Mantem a ordem dos modelos definida no config.yaml.
    model_names = [m["name"] for m in cfg.models if m["name"] in data]

    rows = []
    for name in model_names:
        meta = cfg.model_by_name(name)
        row = {"model": name, "label": meta["label"], "params": meta["params"], "cells": {}}
        for ds_key in dataset_keys:
            summary = data[name].get(ds_key)
            for metric in metrics:
                row["cells"][(ds_key, metric)] = (
                    summary.get(metric) if summary else None
                )
        rows.append(row)

    # Calcula negrito e sublinhado coluna por coluna.
    marks: Dict[Any, Dict[int, str]] = {}
    for ds_key in dataset_keys:
        for metric in metrics:
            column = [r["cells"][(ds_key, metric)] for r in rows]
            marks[(ds_key, metric)] = rank_marks(column)

    return {"rows": rows, "metrics": metrics, "datasets": dataset_keys, "marks": marks}


def write_markdown(cfg: Config, table: Dict[str, Any], out: Path) -> None:
    metrics, datasets, rows, marks = (
        table["metrics"], table["datasets"], table["rows"], table["marks"]
    )
    ds_labels = [cfg.dataset(d)["label"] for d in datasets]

    header1 = ["Model", "#Params."]
    for label in ds_labels:
        header1 += [f"{label}: {METRIC_LABELS[m]}" for m in metrics]

    lines = [
        "# Tabela 2: Avaliacao de IaC Generation",
        "",
        "Comparacao de modelos open source em "
        + " e ".join(ds_labels)
        + ". Negrito indica o melhor valor da coluna e sublinhado o segundo melhor.",
        "",
        "| " + " | ".join(header1) + " |",
        "|" + "|".join(["---"] * len(header1)) + "|",
    ]

    for idx, row in enumerate(rows):
        cells = [row["label"], row["params"]]
        for ds_key in datasets:
            for metric in metrics:
                value = row["cells"][(ds_key, metric)]
                cells.append(fmt(value, marks[(ds_key, metric)].get(idx), "md"))
        lines.append("| " + " | ".join(cells) + " |")

    lines += [
        "",
        "Notas de leitura:",
        "",
        "- Correctness: o codigo passa no terraform validate, no terraform plan "
        "e satisfaz todas as regras da politica Rego.",
        "- Deployability: o codigo passa no terraform validate e no terraform plan.",
        "- Compilability: o codigo passa no terraform validate.",
        "- Linter Pass Rate: porcentagem de configuracoes sem nenhum alerta do TFLint.",
        "- Security Compliance: media da porcentagem de checagens do Checkov aprovadas.",
        "- Protocolo pass@1: cada modelo teve uma unica tentativa por instancia.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def write_csv(cfg: Config, table: Dict[str, Any], out: Path) -> None:
    metrics, datasets, rows = table["metrics"], table["datasets"], table["rows"]
    header = ["model", "params"]
    for ds_key in datasets:
        header += [f"{ds_key}__{m}" for m in metrics]

    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            line = [row["label"], row["params"]]
            for ds_key in datasets:
                for metric in metrics:
                    value = row["cells"][(ds_key, metric)]
                    line.append("" if value is None else f"{value:.2f}")
            writer.writerow(line)


def write_latex(cfg: Config, table: Dict[str, Any], out: Path) -> None:
    metrics, datasets, rows, marks = (
        table["metrics"], table["datasets"], table["rows"], table["marks"]
    )
    ncols = 2 + len(datasets) * len(metrics)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Evaluation of IaC Generation with open source LLMs.}",
        "\\begin{tabular}{" + "l" * 2 + "c" * (ncols - 2) + "}",
        "\\toprule",
    ]
    header = ["Model", "\\#Params."]
    for ds_key in datasets:
        label = cfg.dataset(ds_key)["label"]
        header += [f"{label} {METRIC_LABELS[m].replace('(%)', '')}" for m in metrics]
    lines.append(" & ".join(header) + " \\\\")
    lines.append("\\midrule")

    for idx, row in enumerate(rows):
        cells = [row["label"], row["params"]]
        for ds_key in datasets:
            for metric in metrics:
                value = row["cells"][(ds_key, metric)]
                cells.append(fmt(value, marks[(ds_key, metric)].get(idx), "tex"))
        lines.append(" & ".join(cells) + " \\\\")

    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}"]
    out.write_text("\n".join(lines), encoding="utf-8")


def write_json(table: Dict[str, Any], out: Path) -> None:
    payload = {
        "datasets": table["datasets"],
        "metrics": table["metrics"],
        "rows": [
            {
                "model": r["label"],
                "params": r["params"],
                "values": {
                    f"{ds}__{m}": r["cells"][(ds, m)]
                    for ds in table["datasets"]
                    for m in table["metrics"]
                },
            }
            for r in table["rows"]
        ],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta a Tabela 2")
    parser.add_argument(
        "--datasets", nargs="*",
        help="quais datasets entram na tabela (padrao: os do config.yaml)",
    )
    parser.add_argument("--config")
    args = parser.parse_args()

    cfg = load_config(args.config)
    dataset_keys = args.datasets or cfg.table2.get(
        "dataset_order", list(cfg.datasets)
    )
    dataset_keys = [d for d in dataset_keys if d in cfg.datasets]

    table = build(cfg, dataset_keys)

    out_dir = cfg.path("tables")
    out_dir.mkdir(parents=True, exist_ok=True)

    write_markdown(cfg, table, out_dir / "tabela2.md")
    write_csv(cfg, table, out_dir / "tabela2.csv")
    write_latex(cfg, table, out_dir / "tabela2.tex")
    write_json(table, out_dir / "tabela2.json")

    print("\nTabela 2 gerada com sucesso:")
    for name in ("tabela2.md", "tabela2.csv", "tabela2.tex", "tabela2.json"):
        print(f"  - {out_dir / name}")
    print("\nPreview:\n")
    print((out_dir / "tabela2.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
