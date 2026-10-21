"""
Grava cada resultado "PASS" ou "FAIL" em arquivos .txt separados.

Regra pedida:
  * resultado PASS            -> arquivo pass.txt
  * resultado FAIL            -> arquivo fail.txt
  * resultado NAO_EXECUTADO   -> arquivo fail.txt (conta como 0; o motivo diz
                                 que a etapa anterior falhou)
  * cada linha diz QUAL COMANDO gerou o resultado.

Para facilitar ainda mais, os mesmos registros tambem sao gravados por comando:
  por_comando/1_terraform_validate/pass.txt  e  fail.txt
  por_comando/2_terraform_plan/pass.txt      e  fail.txt
  por_comando/3_opa_eval/pass.txt            e  fail.txt
  por_comando/4_tflint/pass.txt              e  fail.txt
  por_comando/5_checkov/pass.txt             e  fail.txt

Formato de cada linha (campos separados por " | "):
  data e hora | PASS/FAIL/NAO_EXECUTADO | comando=... | (contexto: modelo, setting,
  linha do dataset, dificuldade...) | valor=... | motivo=...
"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Dict

from verificadores.comum.resultado_verificacao import PASS, ResultadoVerificacao

PASTAS_POR_COMANDO = {
    "terraform validate": "1_terraform_validate",
    "terraform plan": "2_terraform_plan",
    "opa eval": "3_opa_eval",
    "tflint": "4_tflint",
    "checkov": "5_checkov",
}

CABECALHO = (
    "# Arquivo {nome}: cada linha e um resultado {tipo}.\n"
    "# Formato: data e hora | status | comando | contexto | valor | motivo\n"
    "# (NAO_EXECUTADO = a etapa anterior da escada falhou; conta como 0)\n"
)

_trava = threading.Lock()


class RegistroPassFail:
    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)
        # Cria pass.txt e fail.txt logo no inicio (mesmo que fiquem sem registros),
        # para ficar claro que "arquivo so com cabecalho" = nenhum resultado daquele tipo.
        for nome, tipo in (("pass.txt", "PASS"), ("fail.txt", "FAIL ou NAO_EXECUTADO")):
            arquivo = self.pasta / nome
            if not arquivo.exists():
                arquivo.write_text(CABECALHO.format(nome=nome, tipo=tipo), encoding="utf-8")

    def registrar(self, contexto: Dict[str, object], resultado: ResultadoVerificacao) -> None:
        nome_arquivo = "pass.txt" if resultado.status == PASS else "fail.txt"
        partes = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            resultado.status,
            "comando=" + resultado.comando,
        ]
        partes += ["{}={}".format(chave, valor) for chave, valor in contexto.items()]
        # Checkov tem nota continua (0 a 1); os demais valem 0 ou 1.
        if resultado.comando == "checkov":
            partes.append("valor={:.4f}".format(float(resultado.valor)))
        else:
            partes.append("valor={}".format(int(resultado.valor)))
        partes.append("motivo=" + " ".join(str(resultado.motivo).split()))
        linha = " | ".join(partes) + "\n"

        destinos = [self.pasta / nome_arquivo]
        subpasta = PASTAS_POR_COMANDO.get(resultado.comando)
        if subpasta:
            destinos.append(self.pasta / "por_comando" / subpasta / nome_arquivo)

        with _trava:
            for destino in destinos:
                destino.parent.mkdir(parents=True, exist_ok=True)
                novo = not destino.exists()
                with open(destino, "a", encoding="utf-8") as arquivo:
                    if novo:
                        arquivo.write(
                            CABECALHO.format(
                                nome=destino.name,
                                tipo="PASS" if nome_arquivo == "pass.txt" else "FAIL ou NAO_EXECUTADO",
                            )
                        )
                    arquivo.write(linha)
