"""
ETAPA 1: GERACAO DE CODIGO TERRAFORM (IaC Generation)
=====================================================

O que este script faz, em linguagem simples:
  1. le a lista de tarefas (prompts em linguagem natural) de um dataset;
  2. para cada tarefa, monta o prompt do paper com 3 exemplos few-shot;
  3. envia o prompt para um modelo local do Ollama;
  4. guarda o codigo Terraform devolvido em results/generations/...

O modelo tem UMA unica chance por tarefa (protocolo pass@1 do paper).

Uso:
    python -m src.generation.generate --dataset tf_gen_test --model qwen2.5-coder:7b
    python -m src.generation.generate --dataset tf_gen_test --all-models
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

from src.common.config import Config, load_config
from src.common.naming import slug
from src.generation.ollama_client import OllamaClient
from src.generation.prompt_builder import (
    build_prompt,
    extract_terraform,
    load_few_shot_block,
)


def read_instances(cfg: Config, dataset_key: str) -> List[Dict]:
    ds = cfg.dataset(dataset_key)
    path = cfg.resolve(ds["instances"])
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de instancias nao encontrado: {path}\n"
            "Confira o caminho em config/config.yaml na secao 'datasets'."
        )
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def generate_for_model(
    cfg: Config,
    dataset_key: str,
    model_name: str,
    limit: int | None = None,
    overwrite: bool = False,
) -> Path:
    instances = read_instances(cfg, dataset_key)
    if limit:
        instances = instances[:limit]

    client = OllamaClient(cfg.ollama)
    few_shot = load_few_shot_block(
        cfg.resolve(cfg.prompting["few_shot_file"]),
        int(cfg.prompting.get("num_few_shot_examples", 3)),
    )
    template_file = cfg.resolve(cfg.prompting["template_file"])

    out_root = cfg.path("generations") / slug(model_name) / dataset_key
    out_root.mkdir(parents=True, exist_ok=True)

    manifest_path = out_root / "manifest.jsonl"
    done_ids = set()
    if manifest_path.exists() and not overwrite:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    done_ids.add(json.loads(line)["id"])
    elif overwrite and manifest_path.exists():
        manifest_path.unlink()

    print(f"\n[GERACAO] modelo={model_name} dataset={dataset_key} "
          f"instancias={len(instances)}")

    for idx, inst in enumerate(instances, start=1):
        inst_id = inst["id"]
        if inst_id in done_ids:
            print(f"  ({idx}/{len(instances)}) {inst_id}: ja gerado, pulando.")
            continue

        inst_dir = out_root / inst_id
        inst_dir.mkdir(parents=True, exist_ok=True)

        prompt = build_prompt(template_file, few_shot, inst["prompt"])
        (inst_dir / "prompt_enviado.txt").write_text(prompt, encoding="utf-8")

        started = time.time()
        result = client.generate(model_name, prompt)
        elapsed = time.time() - started

        (inst_dir / "resposta_bruta.txt").write_text(
            result.text if result.ok else result.error, encoding="utf-8"
        )

        code = extract_terraform(result.text) if result.ok else ""
        (inst_dir / "main.tf").write_text(code, encoding="utf-8")

        record = {
            "id": inst_id,
            "model": model_name,
            "dataset": dataset_key,
            "ok": result.ok,
            "error": result.error,
            "empty_code": len(code.strip()) == 0,
            "chars": len(code),
            "seconds": round(elapsed, 2),
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        flag = "OK " if result.ok and code.strip() else "VAZIO"
        print(f"  ({idx}/{len(instances)}) {inst_id}: {flag} "
              f"{len(code)} chars em {elapsed:.1f}s")

    print(f"[GERACAO] concluida. Saida em: {out_root}")
    return out_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera codigo Terraform com LLMs locais")
    parser.add_argument("--dataset", required=True, help="chave do dataset (ex: tf_gen_test)")
    parser.add_argument("--model", help="nome do modelo no Ollama")
    parser.add_argument("--all-models", action="store_true", help="roda todos os modelos do config")
    parser.add_argument("--limit", type=int, help="usa apenas as N primeiras instancias")
    parser.add_argument("--overwrite", action="store_true", help="refaz geracoes ja existentes")
    parser.add_argument("--config", help="caminho alternativo do config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)

    client = OllamaClient(cfg.ollama)
    if not client.is_alive():
        print("AVISO: o Ollama nao respondeu. Rode 'ollama serve' em outro terminal.")

    if args.all_models:
        targets = [m["name"] for m in cfg.models]
    elif args.model:
        targets = [args.model]
    else:
        parser.error("informe --model NOME ou --all-models")

    for model_name in targets:
        generate_for_model(cfg, args.dataset, model_name, args.limit, args.overwrite)


if __name__ == "__main__":
    main()
