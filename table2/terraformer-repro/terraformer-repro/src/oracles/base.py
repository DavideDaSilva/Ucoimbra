"""
Contrato comum dos oraculos de verificacao formal.

O paper define tres oraculos (Secao 3):
  FV-i   terraform validate  -> compilabilidade (correcao sintatica)
  FV-ii  terraform plan      -> deployability   (correcao semantica)
  FV-iii opa eval            -> correctness     (conformidade com a politica)

Todo oraculo recebe uma pasta de trabalho com o main.tf gerado pelo modelo e
devolve um `OracleResult` padronizado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class OracleResult:
    oracle_id: str            # "FV-i", "FV-ii", "FV-iii"
    oracle_name: str          # "terraform validate", ...
    passed: bool
    steps: List[Dict[str, Any]] = field(default_factory=list)
    error_certificate: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "oracle_id": self.oracle_id,
            "oracle_name": self.oracle_name,
            "passed": self.passed,
            "steps": self.steps,
            "error_certificate": self.error_certificate,
            "details": self.details,
        }


class Oracle:
    oracle_id = "FV-?"
    oracle_name = "oraculo"

    def __init__(self, cfg):
        self.cfg = cfg
        self.tools = cfg.tools

    def run(
        self,
        workdir: Path,
        instance: Dict[str, Any],
        logbook,
        context: Optional[Dict[str, Any]] = None,
    ) -> OracleResult:
        raise NotImplementedError

    # utilitario compartilhado
    def _log(self, logbook, instance_id: str, step: str, result, passed: bool) -> None:
        logbook.record(
            instance_id=instance_id,
            oracle=f"{self.oracle_id} ({self.oracle_name})",
            step=step,
            command=result.command_line,
            exit_code=result.exit_code,
            passed=passed,
            output=result.combined_output,
        )
