#!/usr/bin/env python3
"""
PROJETO 1: selecao dos 3 exemplos fixos do IaC-Eval.

Como usar (sempre a partir desta pasta):

  1) Conferir se tudo esta instalado (faca uma vez):
        python executar.py --verificar-ambiente

  2) Rodar a selecao:
        python executar.py

  3) Ver o resultado:
        resultados/exemplos_fixos.md     (para ler)
        resultados/exemplos_fixos.json   (para copiar para o Projeto 2)

Opcoes:
  --config ARQUIVO        usa outro arquivo de configuracao (padrao: configuracao.yaml)
  --verificar-ambiente    apenas confere os programas e prepara o TFLint
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA_PROJETO))

try:
    import yaml
except ImportError:
    sys.exit("Falta o pacote PyYAML. Instale as dependencias com:  pip install -r requirements.txt")

from selecao.carregar_dataset import carregar_dataset  # noqa: E402
from selecao.salvar_exemplos import salvar_exemplos  # noqa: E402
from selecao.selecionar_exemplos import carregar_configuracao_selecao, selecionar_exemplos  # noqa: E402
from verificadores.comum.configuracao_verificadores import carregar_configuracao_verificadores  # noqa: E402
from verificadores.comum.verificar_ambiente import verificar_ambiente, versao_terraform  # noqa: E402
from verificadores.fv2_terraform_plan.simulador_moto import simulador_aws  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Projeto 1: selecao dos 3 exemplos fixos do IaC-Eval")
    parser.add_argument("--config", default="configuracao.yaml")
    parser.add_argument("--verificar-ambiente", action="store_true")
    args = parser.parse_args()

    caminho_config = (PASTA_PROJETO / args.config).resolve()
    config = yaml.safe_load(caminho_config.read_text(encoding="utf-8")) or {}
    cfg_verif = carregar_configuracao_verificadores(config.get("verificadores", {}), PASTA_PROJETO)
    cfg_selecao = carregar_configuracao_selecao(config.get("selecao", {}))
    pasta_resultados = PASTA_PROJETO / config.get("pasta_resultados", "resultados")

    if args.verificar_ambiente:
        ok = verificar_ambiente(cfg_verif, PASTA_PROJETO / "ferramentas" / "tflint_init")
        return 0 if ok else 1

    # Cada execucao comeca do zero: os resultados anteriores vao para uma copia de seguranca.
    if pasta_resultados.exists() and any(pasta_resultados.iterdir()):
        copia = pasta_resultados.with_name(
            pasta_resultados.name + "_anterior_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.move(str(pasta_resultados), str(copia))
        print("Resultados anteriores movidos para: " + str(copia))
    pasta_resultados.mkdir(parents=True, exist_ok=True)

    arquivo_log = open(pasta_resultados / "log_execucao.txt", "w", encoding="utf-8")

    def log(mensagem: str) -> None:
        linha = "[{}] {}".format(datetime.now().strftime("%H:%M:%S"), mensagem)
        print(linha)
        arquivo_log.write(linha + "\n")
        arquivo_log.flush()

    origem = config.get("dataset", {}).get("origem", "huggingface")
    aba = config.get("dataset", {}).get("aba_planilha", "dataset")
    log("Carregando dataset de: " + str(origem))
    cenarios = carregar_dataset(origem, PASTA_PROJETO, aba)
    log("{} cenarios carregados.".format(len(cenarios)))
    log("Estrategia: {} | dificuldades: {} | quantidade: {}".format(
        cfg_selecao.estrategia, cfg_selecao.dificuldades_desejadas, cfg_selecao.quantidade_de_exemplos))

    with simulador_aws(cfg_verif, pasta_resultados) as situacao:
        log(situacao)
        exemplos = selecionar_exemplos(cenarios, cfg_selecao, cfg_verif, pasta_resultados, log)

    informacoes = {
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "origem_do_dataset": str(origem),
        "total_de_cenarios_no_dataset": len(cenarios),
        "estrategia": cfg_selecao.estrategia,
        "dificuldades_desejadas": cfg_selecao.dificuldades_desejadas,
        "criterios": vars(cfg_selecao.criterios),
        "versao_terraform": versao_terraform(cfg_verif),
        "modo_deployability": cfg_verif.modo_deployability,
        "tflint_gravidades_que_reprovam": cfg_verif.tflint_gravidades_que_reprovam,
    }
    salvar_exemplos(exemplos, pasta_resultados, informacoes)

    if len(exemplos) < cfg_selecao.quantidade_de_exemplos:
        log("ATENCAO: so foram encontrados {} de {} exemplos. Veja relatorio_da_busca.csv "
            "e considere afrouxar os criterios no configuracao.yaml.".format(
                len(exemplos), cfg_selecao.quantidade_de_exemplos))
    else:
        log("Pronto! Exemplos escolhidos (linha no dataset): " +
            ", ".join(str(e["linha"]) for e in exemplos))
    log("Arquivo para o Projeto 2: " + str(pasta_resultados / "exemplos_fixos.json"))
    arquivo_log.close()
    return 0 if len(exemplos) == cfg_selecao.quantidade_de_exemplos else 2


if __name__ == "__main__":
    sys.exit(main())
