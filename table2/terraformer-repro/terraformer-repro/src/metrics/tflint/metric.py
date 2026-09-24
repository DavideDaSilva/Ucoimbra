"""
METRICA: LINTER PASS RATE
=========================

Ferramenta: TFLint.

O que mede: se a configuracao respeita as boas praticas verificadas pelo
linter. E uma metrica booleana por instancia: passou (nenhum problema) ou nao
passou. O valor da tabela e a porcentagem de instancias que passaram.

Comando executado:
  tflint --format json --no-color --force

A flag --force faz o TFLint sempre sair com codigo 0, para que possamos contar
os problemas pela saida JSON em vez de depender do codigo de saida.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.common import shell


def run_tflint(cfg, workdir: Path, instance_id: str, logbook) -> Dict[str, Any]:
    tools = cfg.tools
    cmd = [tools["tflint_binary"], "--format", "json", "--no-color", "--force"]
    result = shell.run(
        cmd, cwd=workdir,
        timeout=int(tools.get("tflint_timeout_seconds", 120)),
        env=cfg.aws_env(),
    )

    issues = []
    errors = []
    available = result.exit_code != 127
    try:
        payload = json.loads(result.stdout or "{}")
        issues = payload.get("issues", []) or []
        errors = payload.get("errors", []) or []
    except json.JSONDecodeError:
        pass

    passed = available and not issues and not errors

    lines = [
        f"Problemas encontrados (issues): {len(issues)}",
        f"Erros do proprio linter ......: {len(errors)}",
    ]
    for issue in issues[:30]:
        rule = issue.get("rule", {}).get("name", "regra desconhecida")
        message = issue.get("message", "")
        lines.append(f"  - [{rule}] {message}")
    if not available:
        lines.append(result.combined_output)

    logbook.record(
        instance_id=instance_id,
        oracle="TFLint (Linter Pass Rate)",
        step="verificacao de boas praticas",
        command=result.command_line,
        exit_code=result.exit_code,
        passed=passed,
        output="\n".join(lines),
    )

    (workdir / "tflint_saida.json").write_text(
        result.stdout or result.stderr, encoding="utf-8"
    )

    return {
        "available": available,
        "passed": passed,
        "issues": len(issues),
        "command": result.command_line,
    }
