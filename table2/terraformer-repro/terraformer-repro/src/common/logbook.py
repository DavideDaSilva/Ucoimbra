"""
REGISTRO DE RESULTADOS (pass.txt / fail.txt / error.txt)
=========================================================

Este modulo implementa o requisito de guardar, em arquivos .txt separados,
cada resultado devolvido pelos oraculos:

  pass.txt   -> todo comando que PASSOU na verificacao
  fail.txt   -> todo comando que FALHOU na verificacao
  error.txt  -> o texto de erro (error certificate) produzido pela falha

Cada registro escrito nos arquivos identifica claramente:
  - a instancia avaliada (por exemplo tfgen_001);
  - o oraculo (FV-i, FV-ii, FV-iii) ou a metrica (TFLint, Checkov);
  - o COMANDO EXATO que foi executado;
  - o codigo de saida e o momento da execucao.

Os arquivos sao escritos em dois niveis, para facilitar tanto a leitura
rapida quanto a investigacao detalhada:

  1. Nivel agregado, por oraculo:
     results/evaluations/<modelo>/<dataset>/oracles/<oraculo>/pass.txt
                                                             fail.txt
                                                             error.txt

  2. Nivel da instancia:
     results/evaluations/<modelo>/<dataset>/instances/<id>/<oraculo>/pass.txt
                                                                    fail.txt
                                                                    error.txt
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

SEPARATOR = "=" * 78
THIN = "-" * 78

PASS_FILE = "pass.txt"
FAIL_FILE = "fail.txt"
ERROR_FILE = "error.txt"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _render(
    instance_id: str,
    oracle: str,
    step: str,
    command: str,
    exit_code: int,
    status: str,
    body: str,
) -> str:
    lines = [
        SEPARATOR,
        f"DATA/HORA .......: {_timestamp()}",
        f"INSTANCIA .......: {instance_id}",
        f"ORACULO/METRICA .: {oracle}",
        f"ETAPA ...........: {step}",
        f"COMANDO .........: {command}",
        f"CODIGO DE SAIDA .: {exit_code}",
        f"RESULTADO .......: {status}",
        THIN,
        body.strip() if body.strip() else "(sem saida)",
        SEPARATOR,
        "",
        "",
    ]
    return "\n".join(lines)


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


class Logbook:
    """Escreve os registros nos dois niveis (agregado e por instancia)."""

    def __init__(self, aggregate_dir: Path, instance_dir: Optional[Path] = None):
        self.aggregate_dir = Path(aggregate_dir)
        self.instance_dir = Path(instance_dir) if instance_dir else None

    def record(
        self,
        instance_id: str,
        oracle: str,
        step: str,
        command: str,
        exit_code: int,
        passed: bool,
        output: str,
    ) -> None:
        status = "PASS" if passed else "FAIL"
        entry = _render(
            instance_id, oracle, step, command, exit_code, status, output
        )
        target = PASS_FILE if passed else FAIL_FILE

        _append(self.aggregate_dir / target, entry)
        if self.instance_dir:
            _append(self.instance_dir / target, entry)

        if not passed:
            error_entry = _render(
                instance_id,
                oracle,
                step,
                command,
                exit_code,
                "ERROR CERTIFICATE",
                output,
            )
            _append(self.aggregate_dir / ERROR_FILE, error_entry)
            if self.instance_dir:
                _append(self.instance_dir / ERROR_FILE, error_entry)

    def record_note(self, instance_id: str, oracle: str, step: str, note: str) -> None:
        """Registra uma observacao que nao e pass nem fail (apenas contexto)."""
        entry = _render(instance_id, oracle, step, "(nenhum)", 0, "INFO", note)
        _append(self.aggregate_dir / "notes.txt", entry)
        if self.instance_dir:
            _append(self.instance_dir / "notes.txt", entry)
