"""
ETAPA 1 (parte 2): escolhe QUAIS cenarios do IaC-Eval serao avaliados.

Regra do documento "Instrucoes-Geracao-de-IaC":
  "Ha 6 niveis de dificuldade. 5 exemplos de cada nivel ja e o suficiente."
  -> 6 niveis x 5 cenarios = 30 cenarios por modelo.
  -> 8 modelos x 30 cenarios = 240 codigos gerados (por setting).

Regras aplicadas, nesta ordem:
  1. Os 3 exemplos fixos (escolhidos no Projeto 1) sao REMOVIDOS da lista.
     Assim nenhum modelo ve, no prompt, a resposta do cenario que esta sendo
     avaliado (mesma ideia do "N = 455" dos slides).
  2. Para cada dificuldade (1 a 6) sao escolhidos "quantidade_por_dificuldade"
     cenarios (padrao 5), conforme a estrategia:
       "aleatoria" (padrao): sorteio com semente fixa (padrao 42).
                   Semente fixa = o sorteio da SEMPRE o mesmo resultado,
                   em qualquer computador. Evita pegar 5 cenarios quase iguais
                   (no dataset, cenarios parecidos ficam em linhas vizinhas).
       "primeiros": os primeiros cenarios de cada dificuldade, na ordem do dataset.
       "todos":     todos os cenarios (455), como no paper. Demora muito mais.
  3. A lista final e salva em resultados/cenarios_selecionados.csv e .json.
     O Projeto 3 vai usar exatamente esta lista.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Dict, List


def carregar_exemplos_fixos(caminho: Path) -> List[Dict[str, Any]]:
    """Le o arquivo exemplos_fixos.json produzido pelo Projeto 1."""
    if not caminho.exists():
        raise FileNotFoundError(
            "Nao encontrei o arquivo de exemplos fixos: {}\n"
            "Rode o Projeto 1 e copie o arquivo resultados/exemplos_fixos.json "
            "para a pasta entrada/ deste projeto.".format(caminho)
        )
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    exemplos = dados.get("exemplos", dados) if isinstance(dados, dict) else dados
    obrigatorios = ["linha", "Prompt", "Intent", "Reference output", "Difficulty"]
    for exemplo in exemplos:
        faltando = [c for c in obrigatorios if c not in exemplo]
        if faltando:
            raise ValueError("Exemplo fixo sem os campos {}: {}".format(faltando, exemplo.get("linha")))
    if len(exemplos) != 3:
        print("AVISO: o arquivo tem {} exemplos fixos (o protocolo usa 3).".format(len(exemplos)))
    return sorted(exemplos, key=lambda e: e.get("numero_do_exemplo", 0))


def selecionar_cenarios(
    cenarios: List[Dict[str, Any]],
    exemplos_fixos: List[Dict[str, Any]],
    estrategia: str,
    quantidade_por_dificuldade: int,
    dificuldades: List[int],
    semente: int,
) -> List[Dict[str, Any]]:
    linhas_exemplos = {int(e["linha"]) for e in exemplos_fixos}
    candidatos = [c for c in cenarios if c["linha"] not in linhas_exemplos]

    if estrategia == "todos":
        return candidatos
    if estrategia not in ("aleatoria", "primeiros"):
        raise ValueError("cenarios.estrategia deve ser 'aleatoria', 'primeiros' ou 'todos'")

    sorteador = random.Random(semente)
    escolhidos: List[Dict[str, Any]] = []
    for dificuldade in dificuldades:
        do_nivel = [c for c in candidatos if c["Difficulty"] == dificuldade]
        if len(do_nivel) < quantidade_por_dificuldade:
            print("AVISO: dificuldade {} tem apenas {} cenarios.".format(dificuldade, len(do_nivel)))
        if estrategia == "aleatoria":
            do_nivel = sorteador.sample(do_nivel, min(quantidade_por_dificuldade, len(do_nivel)))
            do_nivel.sort(key=lambda c: c["linha"])
        else:
            do_nivel = do_nivel[:quantidade_por_dificuldade]
        escolhidos.extend(do_nivel)
    return escolhidos


def salvar_lista_de_cenarios(cenarios: List[Dict[str, Any]], pasta: Path, informacoes: Dict[str, Any]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "cenarios_selecionados.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["linha", "linha_na_planilha", "Difficulty", "Resource", "Prompt", "Intent"])
        for c in cenarios:
            escritor.writerow([c["linha"], c["linha_na_planilha"], c["Difficulty"], c["Resource"], c["Prompt"], c["Intent"]])
    (pasta / "cenarios_selecionados.json").write_text(
        json.dumps({"informacoes": informacoes, "cenarios": cenarios}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
