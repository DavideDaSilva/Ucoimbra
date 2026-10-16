"""
Executa um comando externo (terraform, opa, tflint, checkov) de forma segura.

O que este arquivo faz, em linguagem simples:
  * Roda um programa de linha de comando dentro de uma pasta.
  * Espera no maximo "timeout" segundos. Se passar disso, o programa e encerrado
    e o resultado e marcado como "estourou o tempo".
  * Guarda tudo o que o programa escreveu na tela (stdout e stderr), o codigo de
    saida e quanto tempo levou.
  * Nunca repassa credenciais AWS reais da sua maquina para os programas
    (por seguranca, elas sao removidas do ambiente antes da execucao).
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# Variaveis de ambiente que NUNCA devem chegar aos verificadores.
# Assim garantimos que nenhum teste use (ou cobre) a sua conta AWS real.
VARIAVEIS_AWS_REMOVIDAS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "AWS_CONFIG_FILE",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
]


@dataclass
class ResultadoComando:
    """Tudo o que sabemos sobre uma execucao de comando."""

    comando: List[str]
    pasta: str
    codigo_saida: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    tempo_segundos: float = 0.0
    estourou_tempo: bool = False
    erro_execucao: Optional[str] = None  # ex.: programa nao instalado
    extras: Dict[str, str] = field(default_factory=dict)

    @property
    def sucesso(self) -> bool:
        """Verdadeiro somente se o programa terminou sozinho com codigo 0."""
        return (
            self.erro_execucao is None
            and not self.estourou_tempo
            and self.codigo_saida == 0
        )

    def como_texto(self) -> str:
        """Texto legivel para ser salvo em arquivo .txt."""
        linhas = [
            "COMANDO        : " + " ".join(self.comando),
            "PASTA          : " + self.pasta,
            "CODIGO DE SAIDA: " + str(self.codigo_saida),
            "TEMPO (s)      : {:.2f}".format(self.tempo_segundos),
            "ESTOUROU TEMPO : " + ("sim" if self.estourou_tempo else "nao"),
        ]
        if self.erro_execucao:
            linhas.append("ERRO EXECUCAO  : " + self.erro_execucao)
        linhas += [
            "",
            "========== STDOUT (saida normal) ==========",
            self.stdout or "(vazio)",
            "",
            "========== STDERR (mensagens de erro) ==========",
            self.stderr or "(vazio)",
            "",
        ]
        return "\n".join(linhas)


def montar_ambiente(variaveis_extras: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Copia o ambiente atual, remove credenciais AWS reais e acrescenta extras."""
    ambiente = dict(os.environ)
    for nome in VARIAVEIS_AWS_REMOVIDAS:
        ambiente.pop(nome, None)
    if variaveis_extras:
        ambiente.update({k: str(v) for k, v in variaveis_extras.items()})
    return ambiente


def executar(
    comando: List[str],
    pasta: Path,
    timeout: int,
    variaveis_extras: Optional[Dict[str, str]] = None,
) -> ResultadoComando:
    """Roda `comando` dentro de `pasta` e devolve um ResultadoComando."""
    resultado = ResultadoComando(comando=[str(c) for c in comando], pasta=str(pasta))
    inicio = time.time()
    ambiente = montar_ambiente(variaveis_extras)

    # Em Linux/macOS criamos um "grupo de processos" para conseguir encerrar
    # tambem os subprocessos (o terraform abre o provider AWS como subprocesso).
    opcoes_extras = {}
    if os.name != "nt":
        opcoes_extras["start_new_session"] = True

    try:
        processo = subprocess.Popen(
            resultado.comando,
            cwd=str(pasta),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            env=ambiente,
            text=True,
            encoding="utf-8",
            errors="replace",
            **opcoes_extras,
        )
    except FileNotFoundError:
        resultado.erro_execucao = (
            "Programa nao encontrado: '{}'. Verifique se ele esta instalado e no PATH "
            "(ou ajuste o caminho no arquivo configuracao.yaml).".format(comando[0])
        )
        resultado.tempo_segundos = time.time() - inicio
        return resultado
    except OSError as erro:
        resultado.erro_execucao = "Falha ao iniciar o programa: {}".format(erro)
        resultado.tempo_segundos = time.time() - inicio
        return resultado

    try:
        stdout, stderr = processo.communicate(timeout=timeout)
        resultado.codigo_saida = processo.returncode
    except subprocess.TimeoutExpired:
        resultado.estourou_tempo = True
        _encerrar(processo)
        stdout, stderr = processo.communicate()
        resultado.codigo_saida = processo.returncode
    resultado.stdout = stdout or ""
    resultado.stderr = stderr or ""
    resultado.tempo_segundos = time.time() - inicio
    return resultado


def _encerrar(processo: subprocess.Popen) -> None:
    """Encerra o processo (e os filhos dele, quando possivel)."""
    try:
        if os.name != "nt":
            os.killpg(os.getpgid(processo.pid), signal.SIGKILL)
        else:
            processo.kill()
    except Exception:  # noqa: BLE001  (se ja terminou, nao ha o que fazer)
        try:
            processo.kill()
        except Exception:  # noqa: BLE001
            pass
