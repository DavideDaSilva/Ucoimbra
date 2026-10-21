"""
FV-iii  opa eval (Rego intent)  ->  CORRECTNESS

O que e verificado:
  A infraestrutura planejada faz EXATAMENTE o que o usuario pediu?
  Quem decide isso e a "Rego intent" do IaC-Eval: um pequeno programa (policy)
  escrito na linguagem Rego que examina o plano (plan.json) e responde
  verdadeiro/falso. O LLM NUNCA ve essa policy (seta verde tracejada da Figure 1).

Pre-requisito:
  So roda se o terraform plan (FV-ii) passou e gerou o plan.json.

Comando executado:
  opa eval [--v0-compatible] -i plan.json -d intent.rego data --format json

  * "data" pede ao OPA o valor de TODAS as regras da policy de uma vez.
  * --v0-compatible: as policies do IaC-Eval foram escritas na sintaxe antiga
    do Rego (v0). O OPA 1.x usa a sintaxe nova (v1) por padrao e recusaria essas
    policies. Por isso, quando a policy NAO tem "import rego.v1" e o OPA
    instalado e da versao 1.x ou maior, acrescentamos --v0-compatible.
    (Mesma regra usada no codigo original do IaC-Eval, adaptada ao OPA 1.x.)

Regra de decisao (igual ao IaC-Eval, arquivo evaluation/eval.py):
  Percorremos todos os valores devolvidos pelo OPA.
  * Se QUALQUER regra der false  -> FAIL (valor 0).
  * Se nenhuma der false         -> PASS (valor 1).
  Protecao extra (pode ser desligada no configuracao.yaml,
  opa.exigir_pelo_menos_um_true): exigimos que pelo menos UMA regra seja true.
  Isso evita "passar" quando a policy nao produziu resultado nenhum.

Arquivos salvos na pasta de registro desta etapa:
  intent.rego          (a policy usada)
  saida_opa_eval.txt   (tudo o que o OPA escreveu)
  regras_avaliadas.json (cada regra e o seu valor true/false)
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.comum.resultado_verificacao import FAIL, PASS, ResultadoVerificacao

NOME_COMANDO = "opa eval"


@functools.lru_cache(maxsize=4)
def versao_principal_opa(executavel_opa: str) -> int:
    """Descobre a versao principal do OPA instalado (ex.: 1 para 1.4.2)."""
    resultado = executar([executavel_opa, "version"], Path("."), 30)
    achado = re.search(r"Version:\s*v?(\d+)\.", resultado.stdout)
    return int(achado.group(1)) if achado else 1


def montar_comando(cfg: ConfiguracaoVerificadores, policy: str, plan_json: Path, rego: Path) -> List[str]:
    comando = [cfg.opa, "eval"]
    policy_v1 = "import rego.v1" in policy
    if not policy_v1 and versao_principal_opa(cfg.opa) >= 1:
        comando.append("--v0-compatible")
    comando += ["-i", str(plan_json), "-d", str(rego), "data", "--format", "json"]
    return comando


def verificar(
    plan_json: Path,
    policy_rego: str,
    pasta_registro: Path,
    cfg: ConfiguracaoVerificadores,
) -> ResultadoVerificacao:
    pasta_registro.mkdir(parents=True, exist_ok=True)
    caminho_rego = pasta_registro / "intent.rego"
    caminho_rego.write_text(policy_rego, encoding="utf-8")

    comando = montar_comando(cfg, policy_rego, plan_json.resolve(), caminho_rego.resolve())
    resultado = executar(comando, pasta_registro, cfg.tempos.opa_eval)
    (pasta_registro / "saida_opa_eval.txt").write_text(resultado.como_texto(), encoding="utf-8")

    if not resultado.sucesso:
        motivo = resultado.erro_execucao or (
            "opa eval excedeu o tempo limite" if resultado.estourou_tempo
            else "opa eval terminou com erro (codigo {}). Provavel erro na policy Rego; veja saida_opa_eval.txt".format(
                resultado.codigo_saida
            )
        )
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0, motivo=motivo,
            detalhes={"erro_do_verificador": True, "codigo_saida": resultado.codigo_saida},
        )

    valor_data, erro = _extrair_valor(resultado.stdout)
    if erro:
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0, motivo=erro,
            detalhes={"erro_do_verificador": True},
        )

    regras = list(_folhas(valor_data))
    (pasta_registro / "regras_avaliadas.json").write_text(
        json.dumps([{"regra": c, "valor": v} for c, v in regras], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    booleanos = [(c, v) for c, v in regras if isinstance(v, bool)]
    falsas = [c for c, v in booleanos if v is False]
    verdadeiras = [c for c, v in booleanos if v is True]

    if falsas:
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0,
            motivo="regras da Rego intent que deram false: " + ", ".join(falsas),
            detalhes={"regras_true": verdadeiras, "regras_false": falsas},
        )
    if cfg.opa_exigir_pelo_menos_um_true and not verdadeiras:
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0,
            motivo="a Rego intent nao produziu nenhuma regra true (resultado vazio)",
            detalhes={"regras_true": [], "regras_false": []},
        )
    return ResultadoVerificacao(
        comando=NOME_COMANDO, status=PASS, valor=1,
        motivo="todas as regras da Rego intent deram true: " + ", ".join(verdadeiras),
        detalhes={"regras_true": verdadeiras, "regras_false": []},
    )


def _extrair_valor(stdout: str) -> Tuple[Any, Optional[str]]:
    try:
        dados = json.loads(stdout)
        return dados["result"][0]["expressions"][0]["value"], None
    except (ValueError, KeyError, IndexError, TypeError):
        return None, "nao foi possivel ler a resposta do OPA (resultado vazio ou indefinido)"


def _folhas(valor: Any, caminho: str = "data"):
    """Percorre o JSON devolvido pelo OPA e gera (caminho_da_regra, valor)."""
    if isinstance(valor, dict):
        for chave, filho in valor.items():
            yield from _folhas(filho, "{}.{}".format(caminho, chave))
    elif isinstance(valor, list):
        for posicao, filho in enumerate(valor):
            yield from _folhas(filho, "{}[{}]".format(caminho, posicao))
    else:
        yield caminho, valor
