"""
ORACULO FV-i: COMPILABILIDADE
=============================

Ferramenta: `terraform validate` (HashiCorp).

O que ele responde: "o codigo esta sintaticamente correto e internamente
consistente?" Ele checa a sintaxe HCL, campos obrigatorios e referencias entre
blocos, sem falar com a nuvem.

Passos executados:
  1. terraform init -backend=false -input=false -no-color
     (necessario para que o Terraform conheca os providers usados)
  2. terraform validate -no-color -json

Resultado: PASS se os dois comandos terminarem com sucesso e o validate
reportar valid=true. Caso contrario FAIL, e a mensagem de erro vira o
"error certificate" descrito no paper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.common import shell
from src.oracles.base import Oracle, OracleResult


class ValidateOracle(Oracle):
    oracle_id = "FV-i"
    oracle_name = "terraform validate"

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

        main_tf = workdir / "main.tf"
        if not main_tf.exists() or not main_tf.read_text(encoding="utf-8").strip():
            message = (
                "O modelo nao produziu nenhum codigo Terraform para esta "
                "instancia (arquivo main.tf vazio ou ausente)."
            )
            logbook.record(
                instance_id=instance_id,
                oracle=f"{self.oracle_id} ({self.oracle_name})",
                step="pre-verificacao do arquivo main.tf",
                command="(nenhum comando executado)",
                exit_code=1,
                passed=False,
                output=message,
            )
            return OracleResult(
                self.oracle_id, self.oracle_name, False,
                steps=[{"step": "arquivo vazio", "passed": False}],
                error_certificate=message,
            )

        # ---- passo 1: terraform init ----
        init_cmd = [tf, "init", "-backend=false", "-input=false", "-no-color"]
        init = shell.run(
            init_cmd, cwd=workdir,
            timeout=int(self.tools.get("init_timeout_seconds", 600)), env=env,
        )
        self._log(logbook, instance_id, "terraform init", init, init.ok)
        steps.append({"step": "terraform init", "passed": init.ok, **init.to_dict()})

        if not init.ok:
            return OracleResult(
                self.oracle_id, self.oracle_name, False, steps=steps,
                error_certificate=init.combined_output,
            )

        # ---- passo 2: terraform validate ----
        val_cmd = [tf, "validate", "-no-color", "-json"]
        val = shell.run(
            val_cmd, cwd=workdir,
            timeout=int(self.tools.get("validate_timeout_seconds", 120)), env=env,
        )

        valid_flag = val.ok
        parsed: Dict[str, Any] = {}
        try:
            parsed = json.loads(val.stdout) if val.stdout.strip() else {}
            if "valid" in parsed:
                valid_flag = bool(parsed["valid"])
        except json.JSONDecodeError:
            pass

        self._log(logbook, instance_id, "terraform validate", val, valid_flag)
        steps.append({"step": "terraform validate", "passed": valid_flag, **val.to_dict()})

        (workdir / "fv1_validate_saida.json").write_text(
            val.stdout or val.stderr, encoding="utf-8"
        )

        return OracleResult(
            self.oracle_id,
            self.oracle_name,
            valid_flag,
            steps=steps,
            error_certificate="" if valid_flag else val.combined_output,
            details={"diagnostics": parsed.get("diagnostics", [])},
        )
