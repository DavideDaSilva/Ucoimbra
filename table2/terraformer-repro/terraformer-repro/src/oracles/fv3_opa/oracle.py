"""
ORACULO FV-iii: CORRECTNESS (conformidade com a politica)
=========================================================

Ferramenta: `opa eval` (Open Policy Agent).

O que ele responde: "o que o modelo gerou atende de fato a intencao do prompt?"
A intencao e escrita como uma politica formal em Rego, que funciona como um
teste unitario da infraestrutura. A entrada da politica e o plan.json produzido
pelo oraculo FV-ii.

Comando executado:
  opa eval --format json --data <politica>.rego --input plan.json
           "data.terraform.policy"

CONVENCAO DAS POLITICAS (usada tambem pelo paper na Figura 4b):
  toda regra de verificacao se chama `is_valid_<alguma_coisa>`.
  - Regras que aparecem como verdadeiras na saida contam como aprovadas.
  - Regras declaradas no arquivo mas ausentes da saida contam como reprovadas
    (em Rego, uma regra falsa simplesmente fica indefinida).

Resultado:
  - passed = True somente se TODAS as regras `is_valid_*` passarem.
  - a razao (regras aprovadas / total de regras) tambem e gravada, porque e
    exatamente esse valor que alimenta a recompensa da Equacao 2 do paper,
    util na fase futura de treinamento por reforco.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common import shell
from src.oracles.base import Oracle, OracleResult

POLICY_PACKAGE = "data.terraform.policy"
RULE_PREFIX = "is_valid_"

# Captura nomes de regras no inicio da linha, por exemplo:
#   is_valid_vpc if {          -> is_valid_vpc
#   is_valid_vpc := true       -> is_valid_vpc
#   is_valid_vpc {             -> is_valid_vpc  (sintaxe antiga do Rego)
_RULE_RE = re.compile(r"^(is_valid_[A-Za-z0-9_]*)\s*(?:if\b|:=|=|\{|\()", re.MULTILINE)


def declared_rules(policy_text: str) -> List[str]:
    return sorted(set(_RULE_RE.findall(policy_text)))


class OpaOracle(Oracle):
    oracle_id = "FV-iii"
    oracle_name = "opa eval"

    def run(
        self,
        workdir: Path,
        instance: Dict[str, Any],
        logbook,
        context: Optional[Dict[str, Any]] = None,
    ) -> OracleResult:
        instance_id = instance["id"]
        context = context or {}
        policy_path: Optional[Path] = context.get("policy_path")
        opa = self.tools["opa_binary"]
        steps = []

        if not policy_path or not Path(policy_path).exists():
            message = (
                f"A instancia {instance_id} nao possui politica Rego associada. "
                "Sem politica nao e possivel medir Correctness."
            )
            logbook.record(
                instance_id=instance_id,
                oracle=f"{self.oracle_id} ({self.oracle_name})",
                step="localizacao da politica",
                command="(nenhum comando executado)",
                exit_code=1,
                passed=False,
                output=message,
            )
            return OracleResult(
                self.oracle_id, self.oracle_name, False,
                error_certificate=message,
                details={"rules_total": 0, "rules_passed": 0, "ratio": 0.0},
            )

        plan_json = workdir / "plan.json"
        if not plan_json.exists():
            message = (
                "plan.json nao existe: o oraculo FV-ii (terraform plan) nao "
                "chegou a produzir o grafo de execucao. Sem ele a politica nao "
                "pode ser avaliada, e a instancia conta como incorreta."
            )
            logbook.record(
                instance_id=instance_id,
                oracle=f"{self.oracle_id} ({self.oracle_name})",
                step="pre-verificacao do plan.json",
                command="(nenhum comando executado)",
                exit_code=1,
                passed=False,
                output=message,
            )
            return OracleResult(
                self.oracle_id, self.oracle_name, False,
                error_certificate=message,
                details={"rules_total": 0, "rules_passed": 0, "ratio": 0.0},
            )

        policy_text = Path(policy_path).read_text(encoding="utf-8")
        rules = declared_rules(policy_text)

        cmd = [
            opa, "eval", "--format", "json",
            "--data", str(policy_path),
            "--input", str(plan_json),
            POLICY_PACKAGE,
        ]
        result = shell.run(
            cmd, cwd=workdir,
            timeout=int(self.tools.get("opa_timeout_seconds", 60)),
            env=self.cfg.aws_env(),
        )

        evaluated: Dict[str, Any] = {}
        parse_error = ""
        if result.ok:
            try:
                payload = json.loads(result.stdout or "{}")
                expressions = payload.get("result", [{}])[0].get("expressions", [{}])
                value = expressions[0].get("value", {})
                if isinstance(value, dict):
                    evaluated = value
            except (json.JSONDecodeError, IndexError, KeyError, TypeError) as exc:
                parse_error = f"Nao foi possivel interpretar a saida do OPA: {exc}"

        passed_rules = [
            name for name in rules if bool(evaluated.get(name, False))
        ]
        # Regras que existem na saida mas nao foram detectadas no texto.
        for name, val in evaluated.items():
            if name.startswith(RULE_PREFIX) and name not in rules:
                rules.append(name)
                if bool(val):
                    passed_rules.append(name)

        total = len(rules)
        passed_count = len(set(passed_rules))
        ratio = (passed_count / total) if total else 0.0
        all_passed = bool(result.ok and total > 0 and passed_count == total)

        failed_rules = sorted(set(rules) - set(passed_rules))
        report_lines = [
            f"Regras da politica: {total}",
            f"Regras aprovadas ..: {passed_count}",
            f"Regras reprovadas .: {len(failed_rules)}",
            f"Proporcao .........: {ratio:.4f}",
        ]
        if failed_rules:
            report_lines.append("Lista de regras reprovadas:")
            report_lines.extend(f"  - {name}" for name in failed_rules)
        if parse_error:
            report_lines.append(parse_error)
        if not result.ok:
            report_lines.append("Saida bruta do OPA:")
            report_lines.append(result.combined_output)

        report = "\n".join(report_lines)

        logbook.record(
            instance_id=instance_id,
            oracle=f"{self.oracle_id} ({self.oracle_name})",
            step="opa eval da politica formal",
            command=result.command_line,
            exit_code=result.exit_code,
            passed=all_passed,
            output=report,
        )
        steps.append({"step": "opa eval", "passed": all_passed, **result.to_dict()})

        (workdir / "fv3_opa_saida.json").write_text(
            json.dumps(evaluated, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return OracleResult(
            self.oracle_id,
            self.oracle_name,
            all_passed,
            steps=steps,
            error_certificate="" if all_passed else report,
            details={
                "rules_total": total,
                "rules_passed": passed_count,
                "rules_failed": failed_rules,
                "ratio": round(ratio, 4),
            },
        )
