"""
Formato padrao do resultado de CADA verificador.

Todo verificador (terraform validate, terraform plan, opa eval, TFLint, Checkov)
devolve um objeto ResultadoVerificacao com:

  comando : nome do comando que foi verificado (ex.: "terraform validate")
  status  : "PASS"          -> passou
            "FAIL"          -> falhou
            "NAO_EXECUTADO" -> nem chegou a rodar porque uma etapa anterior
                               da escada falhou (conta como 0, igual a FAIL)
  valor   : numero usado na tabela.
            1 ou 0 para Compilability, Deployability, Correctness e Linter.
            de 0.0 a 1.0 para Security Compliance (fracao de checks aprovados).
  motivo  : frase curta explicando o resultado (em portugues).
  detalhes: informacoes extras (codigo de saida, contagens, arquivos gerados...).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict

PASS = "PASS"
FAIL = "FAIL"
NAO_EXECUTADO = "NAO_EXECUTADO"


@dataclass
class ResultadoVerificacao:
    comando: str
    status: str
    valor: float
    motivo: str
    detalhes: Dict[str, Any] = field(default_factory=dict)

    def como_dicionario(self) -> Dict[str, Any]:
        return asdict(self)


def nao_executado(comando: str, motivo: str) -> ResultadoVerificacao:
    """Atalho para quando a etapa anterior falhou (seta vermelha da Figure 3)."""
    return ResultadoVerificacao(comando=comando, status=NAO_EXECUTADO, valor=0.0, motivo=motivo)
