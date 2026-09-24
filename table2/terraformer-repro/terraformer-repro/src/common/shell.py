"""
Executa comandos externos (terraform, opa, tflint, checkov) de forma segura.

Sempre devolve um objeto `CommandResult` com:
  - a linha de comando exata que foi executada (para rastreabilidade);
  - o codigo de saida;
  - a saida padrao e a saida de erro;
  - se houve estouro de tempo (timeout).
"""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CommandResult:
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float
    cwd: str = ""

    @property
    def command_line(self) -> str:
        return " ".join(shlex.quote(part) for part in self.command)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        if self.timed_out:
            parts.append("[TIMEOUT] O comando excedeu o tempo limite configurado.")
        return "\n".join(parts)

    def to_dict(self) -> Dict:
        return {
            "command": self.command_line,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_seconds": round(self.duration_seconds, 3),
            "cwd": self.cwd,
        }


def run(
    command: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 120,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return CommandResult(
            command=command,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            timed_out=False,
            duration_seconds=time.time() - start,
            cwd=str(cwd or ""),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=command,
            exit_code=124,
            stdout=exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            timed_out=True,
            duration_seconds=time.time() - start,
            cwd=str(cwd or ""),
        )
    except FileNotFoundError:
        return CommandResult(
            command=command,
            exit_code=127,
            stdout="",
            stderr=(
                f"Binario nao encontrado: '{command[0]}'. "
                "Instale a ferramenta ou ajuste o caminho em config/config.yaml "
                "na secao 'tools'."
            ),
            timed_out=False,
            duration_seconds=time.time() - start,
            cwd=str(cwd or ""),
        )
