"""
ORACULO FV-ii: DEPLOYABILITY
============================

Ferramenta: `terraform plan` (HashiCorp).

O que ele responde: "este codigo seria realmente implantavel?" O comando monta
o grafo de execucao (DAG) simulando o deploy, checando compatibilidade de
provider, dependencias entre recursos e restricoes de tempo de execucao.
Nada e criado na nuvem: a verificacao e pre-deploy, como no paper.

Passos executados:
  1. terraform plan -input=false -lock=false -no-color -out=plan.bin
     (com tempo limite de 30 segundos, igual ao paper)
  2. terraform show -json plan.bin > plan.json
     (o plan.json e a entrada do oraculo FV-iii)

Observacao sobre o tempo limite: o paper trata o estouro de 30 segundos como
falha, pois em geral indica que o Terraform ficou esperando a digitacao de uma
variavel sem valor padrao.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.common import shell
from src.oracles.base import Oracle, OracleResult

PLAN_BINARY = "plan.bin"
PLAN_JSON = "plan.json"


class PlanOracle(Oracle):
    oracle_id = "FV-ii"
    oracle_name = "terraform plan"

    def run(
        self,
        workdir: Path,
        instance: Dict[str, Any],
        logbook,
        context: Optional[Dict[str, Any]] = None,
    ) -> OracleResult:
        instance_id = instance["id"]
        env = self.cfg.aws_env()
        tf = self.tools["terraform_binary"]
        steps = []

        plan_cmd = [
            tf, "plan", "-input=false", "-lock=false", "-no-color",
            f"-out={PLAN_BINARY}",
        ]
        plan = shell.run(
            plan_cmd, cwd=workdir,
            timeout=int(self.tools.get("plan_timeout_seconds", 30)), env=env,
        )
        self._log(logbook, instance_id, "terraform plan", plan, plan.ok)
        steps.append({"step": "terraform plan", "passed": plan.ok, **plan.to_dict()})

        if not plan.ok:
            certificate = plan.combined_output
            if plan.timed_out:
                certificate += (
                    "\n[NOTA] O comando excedeu o tempo limite. Isso costuma "
                    "acontecer quando o Terraform espera a digitacao de uma "
                    "variavel sem valor padrao."
                )
            return OracleResult(
                self.oracle_id, self.oracle_name, False, steps=steps,
                error_certificate=certificate,
            )

        # ---- converte o plano binario em JSON para o oraculo FV-iii ----
        show_cmd = [tf, "show", "-json", PLAN_BINARY]
        show = shell.run(
            show_cmd, cwd=workdir,
            timeout=int(self.tools.get("plan_timeout_seconds", 30)) * 2, env=env,
        )
        self._log(logbook, instance_id, "terraform show -json", show, show.ok)
        steps.append({"step": "terraform show -json", "passed": show.ok, **show.to_dict()})

        if not show.ok:
            return OracleResult(
                self.oracle_id, self.oracle_name, False, steps=steps,
                error_certificate=show.combined_output,
            )

        (workdir / PLAN_JSON).write_text(show.stdout, encoding="utf-8")

        return OracleResult(
            self.oracle_id, self.oracle_name, True, steps=steps,
            details={"plan_json": str(workdir / PLAN_JSON)},
        )
