"""
ETAPA 2: AVALIACAO (os tres oraculos + as duas metricas auxiliares)
===================================================================

O que este script faz, em linguagem simples:
  para cada codigo Terraform gerado na etapa 1, ele executa nesta ordem:

    FV-i   terraform validate  -> Compilability
    FV-ii  terraform plan      -> Deployability
    FV-iii opa eval            -> Correctness
    TFLint                     -> Linter Pass Rate
    Checkov                    -> Security Compliance

  A hierarquia do paper e respeitada: correctness exige deployability, que
  exige compilability. Se FV-i falha, FV-ii nem e executado, e a instancia
  conta como nao implantavel e incorreta.

Tudo o que cada comando devolve e gravado em pass.txt, fail.txt e error.txt.

Uso:
    python -m src.evaluation.evaluate --dataset tf_gen_test --model qwen2.5-coder:7b
    python -m src.evaluation.evaluate --dataset tf_gen_test --all-models
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from src.common.config import Config, load_config
from src.common.logbook import Logbook
from src.common.naming import slug
from src.generation.generate import read_instances
from src.metrics.checkov.metric import run_checkov
from src.metrics.tflint.metric import run_tflint
from src.oracles.fv1_validate.oracle import ValidateOracle
from src.oracles.fv2_plan.oracle import PlanOracle
from src.oracles.fv3_opa.oracle import OpaOracle

_AWS_PROVIDER_RE = re.compile(r'provider\s+"aws"', re.IGNORECASE)


def prepare_workdir(
    cfg: Config, generation_dir: Path, eval_dir: Path
) -> Path:
    """Copia o main.tf gerado para a pasta de avaliacao e prepara o ambiente."""
    eval_dir.mkdir(parents=True, exist_ok=True)
    src_main = generation_dir / "main.tf"
    dst_main = eval_dir / "main.tf"
    code = src_main.read_text(encoding="utf-8") if src_main.exists() else ""
    dst_main.write_text(code, encoding="utf-8")

    aws_cfg = cfg.aws
    if aws_cfg.get("inject_provider_override", True) and _AWS_PROVIDER_RE.search(code):
        override_src = cfg.resolve(aws_cfg["provider_override_file"])
        if override_src.exists():
            shutil.copyfile(override_src, eval_dir / "provider_override.tf")
    return eval_dir


def evaluate_instance(
    cfg: Config,
    instance: Dict[str, Any],
    policy_path: Path | None,
    generation_dir: Path,
    eval_root: Path,
) -> Dict[str, Any]:
    instance_id = instance["id"]
    inst_dir = eval_root / "instances" / instance_id
    workdir = prepare_workdir(cfg, generation_dir, inst_dir / "workdir")

    def book(oracle_folder: str) -> Logbook:
        return Logbook(
            aggregate_dir=eval_root / "oracles" / oracle_folder,
            instance_dir=inst_dir / oracle_folder,
        )

    record: Dict[str, Any] = {"id": instance_id}

    # ---------------- FV-i ----------------
    fv1 = ValidateOracle(cfg).run(workdir, instance, book("fv1_validate"))
    record["compilable"] = fv1.passed
    record["fv1"] = fv1.to_dict()

    # ---------------- FV-ii ----------------
    if fv1.passed:
        fv2 = PlanOracle(cfg).run(workdir, instance, book("fv2_plan"))
        record["deployable"] = fv2.passed
        record["fv2"] = fv2.to_dict()
    else:
        book("fv2_plan").record(
            instance_id=instance_id,
            oracle="FV-ii (terraform plan)",
            step="execucao ignorada",
            command="(nao executado)",
            exit_code=1,
            passed=False,
            output=(
                "FV-ii nao foi executado porque o codigo falhou em FV-i "
                "(terraform validate). Pela hierarquia do paper, deployability "
                "exige compilability, entao a instancia conta como reprovada."
            ),
        )
        record["deployable"] = False
        record["fv2"] = None

    # ---------------- FV-iii ----------------
    if record["deployable"]:
        fv3 = OpaOracle(cfg).run(
            workdir, instance, book("fv3_opa"), {"policy_path": policy_path}
        )
        record["correct"] = fv3.passed
        record["policy_ratio"] = fv3.details.get("ratio", 0.0)
        record["fv3"] = fv3.to_dict()
    else:
        book("fv3_opa").record(
            instance_id=instance_id,
            oracle="FV-iii (opa eval)",
            step="execucao ignorada",
            command="(nao executado)",
            exit_code=1,
            passed=False,
            output=(
                "FV-iii nao foi executado porque o codigo nao passou em FV-ii "
                "(terraform plan) e portanto nao ha plan.json para avaliar. "
                "Pela hierarquia do paper, correctness exige deployability."
            ),
        )
        record["correct"] = False
        record["policy_ratio"] = 0.0
        record["fv3"] = None

    # -------- recompensa da Equacao 2 do paper (util na fase de RL) --------
    if record["deployable"]:
        record["reward"] = round(1.0 + record["policy_ratio"], 4)
    elif record["compilable"]:
        record["reward"] = 0.5
    else:
        record["reward"] = 0.0

    # ---------------- metricas auxiliares ----------------
    record["tflint"] = run_tflint(cfg, workdir, instance_id, book("tflint"))
    record["checkov"] = run_checkov(cfg, workdir, instance_id, book("checkov"))

    (inst_dir / "resultado.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return record


def summarize(cfg: Config, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    if total == 0:
        return {}

    denominators = cfg.table2.get("denominators", {})
    linter_mode = denominators.get("linter", "parsable")
    security_mode = denominators.get("security", "applicable")

    correct = sum(1 for r in records if r["correct"])
    deployable = sum(1 for r in records if r["deployable"])
    compilable = sum(1 for r in records if r["compilable"])

    if linter_mode == "all":
        linter_base = [r for r in records]
    else:
        linter_base = [r for r in records if r["compilable"]]
    linter_pass = sum(1 for r in linter_base if r["tflint"]["passed"])

    if security_mode == "all":
        scores = [
            (r["checkov"]["score"] if r["checkov"]["score"] is not None else 0.0)
            for r in records
        ]
    else:
        scores = [
            r["checkov"]["score"] for r in records if r["checkov"]["score"] is not None
        ]

    def pct(part: int, whole: int) -> float:
        return round(part / whole * 100.0, 2) if whole else 0.0

    return {
        "instances": total,
        "correctness": pct(correct, total),
        "deployability": pct(deployable, total),
        "compilability": pct(compilable, total),
        "linter_pass_rate": pct(linter_pass, len(linter_base)),
        "security_compliance": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "mean_reward": round(sum(r["reward"] for r in records) / total, 4),
        "counts": {
            "correct": correct,
            "deployable": deployable,
            "compilable": compilable,
            "linter_pass": linter_pass,
            "linter_base": len(linter_base),
            "security_base": len(scores),
        },
        "denominators": {"linter": linter_mode, "security": security_mode},
    }


def evaluate_model(
    cfg: Config,
    dataset_key: str,
    model_name: str,
    limit: int | None = None,
) -> Dict[str, Any]:
    ds = cfg.dataset(dataset_key)
    instances = read_instances(cfg, dataset_key)
    if limit:
        instances = instances[:limit]

    policies_dir = cfg.resolve(ds["policies_dir"]).parent
    gen_root = cfg.path("generations") / slug(model_name) / dataset_key
    eval_root = cfg.path("evaluations") / slug(model_name) / dataset_key

    if not gen_root.exists():
        raise FileNotFoundError(
            f"Nao existem geracoes para o modelo '{model_name}' no dataset "
            f"'{dataset_key}'.\nEsperado em: {gen_root}\n"
            "Rode antes a etapa de geracao (scripts/01_gerar.sh)."
        )

    # Comeca do zero para nao misturar execucoes antigas com novas.
    if eval_root.exists():
        shutil.rmtree(eval_root)
    eval_root.mkdir(parents=True, exist_ok=True)

    print(f"\n[AVALIACAO] modelo={model_name} dataset={dataset_key} "
          f"instancias={len(instances)}")

    records = []
    for idx, inst in enumerate(instances, start=1):
        policy_rel = inst.get("policy")
        policy_path = (policies_dir / policy_rel) if policy_rel else None
        rec = evaluate_instance(
            cfg, inst, policy_path, gen_root / inst["id"], eval_root
        )
        records.append(rec)
        marks = (
            f"compilavel={'sim' if rec['compilable'] else 'nao'} "
            f"implantavel={'sim' if rec['deployable'] else 'nao'} "
            f"correto={'sim' if rec['correct'] else 'nao'}"
        )
        print(f"  ({idx}/{len(instances)}) {inst['id']}: {marks}")

    summary = summarize(cfg, records)
    summary.update({"model": model_name, "dataset": dataset_key})

    (eval_root / "resumo.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (eval_root / "instancias.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )

    print(
        f"[AVALIACAO] {model_name} / {dataset_key}: "
        f"Correctness={summary['correctness']}% "
        f"Deployability={summary['deployability']}% "
        f"Compilability={summary['compilability']}%"
    )
    print(f"[AVALIACAO] resultados em: {eval_root}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Roda os oraculos sobre o codigo gerado")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model")
    parser.add_argument("--all-models", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--config")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.all_models:
        targets = [m["name"] for m in cfg.models]
    elif args.model:
        targets = [args.model]
    else:
        parser.error("informe --model NOME ou --all-models")

    for model_name in targets:
        try:
            evaluate_model(cfg, args.dataset, model_name, args.limit)
        except FileNotFoundError as exc:
            print(f"[AVISO] {exc}")


if __name__ == "__main__":
    main()
