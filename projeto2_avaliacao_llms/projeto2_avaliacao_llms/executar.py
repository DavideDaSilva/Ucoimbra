#!/usr/bin/env python3
"""
PROJETO 2: geracao de Terraform com LLMs locais (Ollama) e avaliacao com as
5 metricas da Table 2 do TerraFormer, no dataset IaC-Eval (3-shot, pass@1).

Use SEMPRE a partir desta pasta. Comandos, na ordem:

  python executar.py verificar-ambiente   confere programas, Ollama e modelos
  python executar.py preparar             escolhe os 30 cenarios e mostra um prompt de exemplo
  python executar.py gerar                Etapas 2 e 3: monta prompts e gera as respostas
  python executar.py avaliar              Etapa 4: roda os 5 verificadores
  python executar.py tabela               Etapa 5: calcula a tabela final
  python executar.py tudo                 preparar + gerar + avaliar + tabela

Comando auxiliar:
  python executar.py ver-prompt --linha 12 --setting A
        mostra na tela o prompt exato de um cenario, sem chamar nenhum modelo

Opcoes uteis (valem para gerar, avaliar e tudo):
  --modelos "qwen2.5-coder:7b" "llama3.2:latest"   so estes modelos
  --settings A                                      so o Setting A
  --refazer                                         refaz mesmo o que ja existe
  --config outro.yaml                               outro arquivo de configuracao
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA_PROJETO))

try:
    import yaml  # noqa: F401
    import requests  # noqa: F401
except ImportError:
    sys.exit("Faltam pacotes Python. Instale com:  pip install -r requirements.txt")

from pipeline.configuracao import carregar_projeto  # noqa: E402
from pipeline.etapa1_dataset.carregar_dataset import carregar_dataset  # noqa: E402
from pipeline.etapa1_dataset.selecionar_cenarios import (  # noqa: E402
    carregar_exemplos_fixos,
    salvar_lista_de_cenarios,
    selecionar_cenarios,
)
from pipeline.etapa2_prompt_builder.montar_prompt import montar_prompt  # noqa: E402
from pipeline.etapa3_geracao.gerar_respostas import criar_cliente, gerar_respostas  # noqa: E402
from pipeline.etapa4_avaliacao.avaliar_respostas import avaliar_respostas  # noqa: E402
from pipeline.etapa5_resultados.calcular_tabela import calcular_tabela  # noqa: E402
from verificadores.comum.verificar_ambiente import verificar_ambiente  # noqa: E402


class Execucao:
    """Guarda o projeto carregado e escreve o log em tela e em arquivo."""

    def __init__(self, arquivo_config: str):
        self.projeto = carregar_projeto(PASTA_PROJETO, arquivo_config)
        self.projeto.pasta_resultados.mkdir(parents=True, exist_ok=True)
        self._log = open(self.projeto.pasta_resultados / "log_execucao.txt", "a", encoding="utf-8")

    def log(self, mensagem: str) -> None:
        linha = "[{}] {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mensagem)
        print(linha, flush=True)
        self._log.write(linha + "\n")
        self._log.flush()

    # --------------------------------------------------------------
    def carregar_dados(self):
        cfg = self.projeto.bruto
        origem = cfg.get("dataset", {}).get("origem", "dados/iac_eval.csv")
        aba = cfg.get("dataset", {}).get("aba_planilha", "dataset")
        cenarios_todos = carregar_dataset(origem, PASTA_PROJETO, aba)
        exemplos = carregar_exemplos_fixos(self.projeto.arquivo_exemplos_fixos)
        sel = cfg.get("cenarios", {}) or {}
        escolhidos = selecionar_cenarios(
            cenarios_todos,
            exemplos,
            estrategia=str(sel.get("estrategia", "aleatoria")),
            quantidade_por_dificuldade=int(sel.get("quantidade_por_dificuldade", 5)),
            dificuldades=[int(d) for d in sel.get("dificuldades", [1, 2, 3, 4, 5, 6])],
            semente=int(sel.get("semente", 42)),
        )
        informacoes = {
            "origem_do_dataset": str(origem),
            "total_no_dataset": len(cenarios_todos),
            "linhas_dos_exemplos_fixos (removidas)": [e["linha"] for e in exemplos],
            "estrategia": sel.get("estrategia", "aleatoria"),
            "quantidade_por_dificuldade": sel.get("quantidade_por_dificuldade", 5),
            "semente": sel.get("semente", 42),
            "total_selecionado": len(escolhidos),
        }
        salvar_lista_de_cenarios(escolhidos, self.projeto.pasta_resultados, informacoes)
        return escolhidos, exemplos, informacoes

    def modelos_escolhidos(self, args):
        todos = [m.nome for m in self.projeto.modelos]
        if not getattr(args, "modelos", None):
            return todos
        desconhecidos = [m for m in args.modelos if m not in todos]
        if desconhecidos:
            sys.exit("Modelos fora do configuracao.yaml: {}. Disponiveis: {}".format(desconhecidos, todos))
        return list(args.modelos)

    def settings_escolhidos(self, args):
        if not getattr(args, "settings", None):
            return self.projeto.settings
        return [s.upper() for s in args.settings]


# ------------------------------------------------------------------
# Comandos
# ------------------------------------------------------------------
def cmd_verificar_ambiente(ex: Execucao, args) -> int:
    ok = verificar_ambiente(ex.projeto.verificadores, PASTA_PROJETO / "ferramentas" / "tflint_init")
    print("=== Ollama ===\n")
    try:
        instalados = criar_cliente(ex.projeto).modelos_instalados()
        print("  [OK] Ollama respondendo. Modelos instalados: {}".format(len(instalados)))
        for modelo in ex.projeto.modelos:
            presente = modelo.nome in instalados
            ok &= presente
            print("  [{}] {}".format("OK" if presente else "FALTANDO", modelo.nome) +
                  ("" if presente else "   -> baixe com: ollama pull " + modelo.nome))
    except Exception as erro:  # noqa: BLE001
        ok = False
        print("  [FALTANDO] " + str(erro))
    print("\n=== Exemplos fixos (Projeto 1) ===\n")
    try:
        exemplos = carregar_exemplos_fixos(ex.projeto.arquivo_exemplos_fixos)
        print("  [OK] {} exemplos: linhas {}".format(len(exemplos), [e["linha"] for e in exemplos]))
    except Exception as erro:  # noqa: BLE001
        ok = False
        print("  [FALTANDO] " + str(erro))
    print("\nResultado geral: " + ("TUDO PRONTO." if ok else "corrija os itens acima.") + "\n")
    return 0 if ok else 1


def cmd_preparar(ex: Execucao, args) -> int:
    cenarios, exemplos, info = ex.carregar_dados()
    ex.log("Exemplos fixos (linhas do dataset): {}".format([e["linha"] for e in exemplos]))
    ex.log("Cenarios selecionados: {} ({})".format(len(cenarios), json.dumps(info, ensure_ascii=False)))
    por_dificuldade = {}
    for c in cenarios:
        por_dificuldade.setdefault(c["Difficulty"], []).append(c["linha"])
    for dificuldade in sorted(por_dificuldade):
        ex.log("   dificuldade {}: linhas {}".format(dificuldade, por_dificuldade[dificuldade]))
    for setting in ex.projeto.settings:
        prompt, _ = montar_prompt(cenarios[0], exemplos, setting)
        destino = ex.projeto.pasta_resultados / "exemplo_de_prompt_setting_{}.txt".format(setting)
        destino.write_text(prompt, encoding="utf-8")
        ex.log("Exemplo de prompt (setting {}) salvo em {}".format(setting, destino))
    total = len(cenarios) * len(ex.projeto.modelos) * len(ex.projeto.settings)
    ex.log("Total de geracoes previstas: {} cenarios x {} modelos x {} setting(s) = {}".format(
        len(cenarios), len(ex.projeto.modelos), len(ex.projeto.settings), total))
    return 0


def cmd_gerar(ex: Execucao, args) -> int:
    cenarios, exemplos, _ = ex.carregar_dados()
    gerar_respostas(ex.projeto, cenarios, exemplos, ex.modelos_escolhidos(args),
                    ex.settings_escolhidos(args), args.refazer, ex.log)
    ex.log("Etapa 'gerar' concluida.")
    return 0


def cmd_avaliar(ex: Execucao, args) -> int:
    cenarios, _, _ = ex.carregar_dados()
    avaliar_respostas(ex.projeto, cenarios, ex.modelos_escolhidos(args),
                      ex.settings_escolhidos(args), args.refazer, ex.log)
    ex.log("Etapa 'avaliar' concluida.")
    return 0


def cmd_tabela(ex: Execucao, args) -> int:
    cenarios, _, _ = ex.carregar_dados()
    calcular_tabela(ex.projeto, cenarios, ex.log)
    for setting in ex.projeto.settings:
        arquivo = ex.projeto.pasta_tabela / "tabela_setting_{}.md".format(setting)
        print("\n" + arquivo.read_text(encoding="utf-8"))
    return 0


def cmd_tudo(ex: Execucao, args) -> int:
    for funcao in (cmd_preparar, cmd_gerar, cmd_avaliar, cmd_tabela):
        codigo = funcao(ex, args)
        if codigo:
            return codigo
    return 0


def cmd_ver_prompt(ex: Execucao, args) -> int:
    cenarios_todos = carregar_dataset(
        ex.projeto.bruto.get("dataset", {}).get("origem", "dados/iac_eval.csv"), PASTA_PROJETO,
        ex.projeto.bruto.get("dataset", {}).get("aba_planilha", "dataset"))
    exemplos = carregar_exemplos_fixos(ex.projeto.arquivo_exemplos_fixos)
    cenario = next((c for c in cenarios_todos if c["linha"] == args.linha), None)
    if cenario is None:
        sys.exit("Linha {} nao existe no dataset.".format(args.linha))
    prompt, resumo = montar_prompt(cenario, exemplos, args.setting.upper())
    print(prompt)
    print("----- resumo: " + json.dumps(resumo, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="configuracao.yaml")
    sub = parser.add_subparsers(dest="comando", required=True)

    def com_filtros(p):
        p.add_argument("--modelos", nargs="+", help="nomes como em `ollama list`")
        p.add_argument("--settings", nargs="+", choices=["A", "B", "a", "b"])
        p.add_argument("--refazer", action="store_true")
        return p

    sub.add_parser("verificar-ambiente")
    sub.add_parser("preparar")
    com_filtros(sub.add_parser("gerar"))
    com_filtros(sub.add_parser("avaliar"))
    sub.add_parser("tabela")
    com_filtros(sub.add_parser("tudo"))
    p = sub.add_parser("ver-prompt")
    p.add_argument("--linha", type=int, required=True)
    p.add_argument("--setting", default="A", choices=["A", "B", "a", "b"])

    args = parser.parse_args()
    ex = Execucao(args.config)
    acoes = {
        "verificar-ambiente": cmd_verificar_ambiente,
        "preparar": cmd_preparar,
        "gerar": cmd_gerar,
        "avaliar": cmd_avaliar,
        "tabela": cmd_tabela,
        "tudo": cmd_tudo,
        "ver-prompt": cmd_ver_prompt,
    }
    return acoes[args.comando](ex, args)


if __name__ == "__main__":
    sys.exit(main())
