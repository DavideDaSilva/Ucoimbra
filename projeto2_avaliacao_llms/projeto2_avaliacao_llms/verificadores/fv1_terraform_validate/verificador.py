"""
FV-i  terraform validate  ->  COMPILABILITY

O que e verificado:
  O codigo Terraform tem sintaxe correta e todas as referencias existem?
  (ex.: nao usa variavel que nao foi declarada, nao tem chave faltando)

Comandos executados (dentro da pasta de trabalho do Terraform):
  1. terraform init -backend=false -input=false -no-color
       baixa os providers (aws, random...). Sem isso o validate nao roda.
       -backend=false: nao tenta configurar armazenamento remoto de estado.
  2. terraform validate -no-color

Resultado:
  PASS (valor 1) se os DOIS comandos terminarem com codigo de saida 0.
  FAIL (valor 0) caso contrario. O motivo diz qual dos dois falhou.

Arquivos salvos na pasta de registro desta etapa:
  saida_terraform_init.txt      (tudo o que o init escreveu)
  saida_terraform_validate.txt  (tudo o que o validate escreveu)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.comum.resultado_verificacao import FAIL, PASS, ResultadoVerificacao

NOME_COMANDO = "terraform validate"


def verificar(
    pasta_terraform: Path,
    pasta_registro: Path,
    cfg: ConfiguracaoVerificadores,
    variaveis: Dict[str, str],
) -> ResultadoVerificacao:
    pasta_registro.mkdir(parents=True, exist_ok=True)
    ambiente = dict(cfg.variaveis_terraform())
    ambiente.update(variaveis)

    # Passo 1: terraform init
    init = executar(
        [cfg.terraform, "init", "-backend=false", "-input=false", "-no-color"],
        pasta_terraform,
        cfg.tempos.terraform_init,
        ambiente,
    )
    (pasta_registro / "saida_terraform_init.txt").write_text(init.como_texto(), encoding="utf-8")
    if not init.sucesso:
        return ResultadoVerificacao(
            comando=NOME_COMANDO,
            status=FAIL,
            valor=0,
            motivo=_motivo("terraform init", init),
            detalhes={"etapa_que_falhou": "terraform init", "codigo_saida": init.codigo_saida},
        )

    # Passo 2: terraform validate
    validate = executar(
        [cfg.terraform, "validate", "-no-color"],
        pasta_terraform,
        cfg.tempos.terraform_validate,
        ambiente,
    )
    (pasta_registro / "saida_terraform_validate.txt").write_text(
        validate.como_texto(), encoding="utf-8"
    )
    if validate.sucesso:
        return ResultadoVerificacao(
            comando=NOME_COMANDO,
            status=PASS,
            valor=1,
            motivo="terraform init e terraform validate terminaram sem erro",
            detalhes={"codigo_saida": validate.codigo_saida},
        )
    return ResultadoVerificacao(
        comando=NOME_COMANDO,
        status=FAIL,
        valor=0,
        motivo=_motivo("terraform validate", validate),
        detalhes={"etapa_que_falhou": "terraform validate", "codigo_saida": validate.codigo_saida},
    )


def _motivo(nome: str, resultado) -> str:
    if resultado.erro_execucao:
        return "{}: {}".format(nome, resultado.erro_execucao)
    if resultado.estourou_tempo:
        return "{}: excedeu o tempo limite".format(nome)
    primeira_linha_erro = _primeira_linha_de_erro(resultado.stderr or resultado.stdout)
    return "{} falhou (codigo {}): {}".format(nome, resultado.codigo_saida, primeira_linha_erro)


def _primeira_linha_de_erro(texto: str) -> str:
    for linha in texto.splitlines():
        if "Error" in linha or "Erro" in linha:
            return linha.strip()[:300]
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    return linhas[0][:300] if linhas else "(sem mensagem)"
