"""
METRICA: SECURITY COMPLIANCE
============================

Ferramenta: Checkov.

O que mede: a porcentagem de checagens de seguranca aprovadas em cada
instancia. O paper define a metrica como a porcentagem de checagens aprovadas
por instancia, depois tirando a media sobre o dataset.

Formula por instancia:
    aprovadas / (aprovadas + reprovadas) * 100

Comando executado:
  checkov --directory . --framework terraform --output json --compact --quiet
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.common import shell


def _collect(payload: Any) -> List[Dict[str, Any]]:
    """O Checkov devolve ora um objeto, ora uma lista de objetos."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def run_checkov(cfg, workdir: Path, instance_id: str, logbook) -> Dict[str, Any]:
    tools = cfg.tools
    cmd = [
        tools["checkov_binary"],
        "--directory", ".",
        "--framework", "terraform",
        "--output", "json",
        "--compact",
        "--quiet",
    ]
    result = shell.run(
        cmd, cwd=workdir,
        timeout=int(tools.get("checkov_timeout_seconds", 300)),
        env=cfg.aws_env(),
    )

    available = result.exit_code != 127
    passed_checks = 0
    failed_checks = 0

    try:
        payload = json.loads(result.stdout or "{}")
        for block in _collect(payload):
            summary = block.get("summary", {})
            passed_checks += int(summary.get("passed", 0))
            failed_checks += int(summary.get("failed", 0))
    except json.JSONDecodeError:
        pass

    total = passed_checks + failed_checks
    # Sem nenhuma checagem aplicavel, a instancia nao entra na media.
    score = (passed_checks / total * 100.0) if total else None
    ok = available and (score is None or failed_checks == 0)

    lines = [
        f"Checagens aprovadas .: {passed_checks}",
        f"Checagens reprovadas : {failed_checks}",
        f"Conformidade ........: "
        + (f"{score:.2f}%" if score is not None else "nao aplicavel"),
    ]
    if not available:
        lines.append(result.combined_output)

    logbook.record(
        instance_id=instance_id,
        oracle="Checkov (Security Compliance)",
        step="varredura de seguranca",
        command=result.command_line,
        exit_code=result.exit_code,
        passed=ok,
        output="\n".join(lines),
    )

    (workdir / "checkov_saida.json").write_text(
        result.stdout or result.stderr, encoding="utf-8"
    )

    return {
        "available": available,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "score": score,
        "command": result.command_line,
    }
