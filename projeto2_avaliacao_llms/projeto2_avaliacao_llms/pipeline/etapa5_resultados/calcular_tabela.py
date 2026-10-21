"""
ETAPA 5: monta a tabela "Evaluation on IaC-Eval" (formato da Table 2 do TerraFormer).

COMO CADA PORCENTAGEM E CALCULADA (N = numero de cenarios avaliados por modelo,
30 no protocolo deste projeto: 5 cenarios x 6 dificuldades):

  Compilability(%)      = 100 x (cenarios com terraform validate PASS) / N
  Deployability(%)      = 100 x (cenarios com terraform plan PASS) / N
  Correctness(%)        = 100 x (cenarios com opa eval PASS) / N
  Linter Pass Rate(%)   = 100 x (cenarios com TFLint PASS) / N
  SecurityCompliance(%) = 100 x (soma das notas do Checkov) / N
                          (nota de cada cenario = passed / (passed + failed))

  Cenario sem HCL extraido conta como 0 em TODAS as metricas.
  Cenario ainda nao avaliado tambem conta como 0, e a tabela avisa "INCOMPLETO".

Arquivos gerados em resultados/tabela/ (um conjunto por setting):
  tabela_setting_A.md / .csv           A TABELA FINAL (formato pedido)
  calculos_detalhados_setting_A.md     a conta de cada numero, passo a passo
  resultados_por_cenario_setting_A.csv as notas 0/1 de cada cenario (base das contas)
  por_dificuldade_setting_A.md / .csv  as mesmas metricas separadas por dificuldade
  tabela_resultados.xlsx               tudo acima em uma planilha (uma aba por item)
"""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pipeline.configuracao import Projeto

# (chave interna, titulo da coluna exatamente como na tabela pedida, comando)
COLUNAS = [
    ("correctness", "Correctness(%)", "opa eval"),
    ("deployability", "Deployability(%)", "terraform plan"),
    ("compilability", "Compilability(%)", "terraform validate"),
    ("linter_pass", "Linter Pass Rate(%)", "tflint"),
    ("security_compliance", "SecurityCompliance(%)", "checkov"),
]

NOME_SETTING = {
    "A": "Setting A (Prompt-only, igual ao paper)",
    "B": "Setting B (Prompt + Intent)",
}


def _ler_resultado(projeto: Projeto, setting: str, modelo: str, linha: int) -> Optional[Dict[str, Any]]:
    arquivo = projeto.pasta_cenario(setting, modelo, linha) / "resultado.json"
    if not arquivo.exists():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _fmt(valor: float) -> str:
    return "{:.2f}".format(valor)


def calcular_tabela(projeto: Projeto, cenarios: List[Dict[str, Any]], log: Callable[[str], None]) -> None:
    pasta = projeto.pasta_tabela
    pasta.mkdir(parents=True, exist_ok=True)
    N = len(cenarios)
    abas_excel: "OrderedDict[str, List[List[Any]]]" = OrderedDict()

    for setting in projeto.settings:
        linhas_tabela = []        # uma por modelo
        linhas_por_cenario = []   # uma por (modelo, cenario)
        calculos = []             # texto do passo a passo
        por_dificuldade = []      # uma por (modelo, dificuldade)

        for modelo in projeto.modelos:
            resultados = []
            for cenario in cenarios:
                r = _ler_resultado(projeto, setting, modelo.nome, cenario["linha"])
                resultados.append((cenario, r))
                m = (r or {}).get("metricas", {})
                linhas_por_cenario.append([
                    modelo.nome, cenario["linha"], cenario["Difficulty"], cenario["Resource"],
                    "sim" if r is not None else "nao",
                    "sim" if (r or {}).get("hcl_extraido") else "nao",
                    int(m.get("compilability", 0)), int(m.get("deployability", 0)),
                    int(m.get("correctness", 0)), int(m.get("linter_pass", 0)),
                    round(float(m.get("security_compliance", 0.0)), 4),
                ])

            avaliados = sum(1 for _, r in resultados if r is not None)
            somas = {chave: sum(float((r or {}).get("metricas", {}).get(chave, 0)) for _, r in resultados)
                     for chave, _, _ in COLUNAS}
            porcentagens = {chave: (100.0 * somas[chave] / N if N else 0.0) for chave in somas}
            sem_hcl = sum(1 for _, r in resultados if r is not None and not r.get("hcl_extraido"))
            violacoes = [
                c["linha"] for c, r in resultados if r is not None and not (
                    r["metricas"]["correctness"] <= r["metricas"]["deployability"] <= r["metricas"]["compilability"])
            ]
            situacao = "completo" if avaliados == N else "INCOMPLETO ({}/{} avaliados)".format(avaliados, N)

            linhas_tabela.append({
                "modelo": modelo.nome,
                "parametros": modelo.parametros,
                "porcentagens": porcentagens,
                "situacao": situacao,
            })
            calculos.append(_texto_calculo(modelo.nome, modelo.parametros, resultados, somas,
                                           porcentagens, N, avaliados, sem_hcl, violacoes))

            for dificuldade in sorted({c["Difficulty"] for c in cenarios}):
                do_nivel = [(c, r) for c, r in resultados if c["Difficulty"] == dificuldade]
                n = len(do_nivel)
                valores = [
                    _fmt(100.0 * sum(float((r or {}).get("metricas", {}).get(chave, 0)) for _, r in do_nivel) / n)
                    if n else "-" for chave, _, _ in COLUNAS
                ]
                por_dificuldade.append([modelo.nome, dificuldade, n] + valores)

        # ---------------- gravar arquivos deste setting ----------------
        cabecalho = ["Model", "#Params"] + [titulo for _, titulo, _ in COLUNAS]
        linhas_csv = [[l["modelo"], l["parametros"]] + [_fmt(l["porcentagens"][c]) for c, _, _ in COLUNAS]
                      for l in linhas_tabela]

        with open(pasta / "tabela_setting_{}.csv".format(setting), "w", newline="", encoding="utf-8") as arq:
            escritor = csv.writer(arq)
            escritor.writerow(cabecalho)
            escritor.writerows(linhas_csv)

        (pasta / "tabela_setting_{}.md".format(setting)).write_text(
            _markdown_tabela(setting, cabecalho, linhas_csv, linhas_tabela, N), encoding="utf-8")

        cab_cenario = ["modelo", "linha", "dificuldade", "resource", "avaliado", "hcl_extraido",
                       "compilability", "deployability", "correctness", "linter_pass", "security_compliance"]
        with open(pasta / "resultados_por_cenario_setting_{}.csv".format(setting), "w", newline="", encoding="utf-8") as arq:
            escritor = csv.writer(arq)
            escritor.writerow(cab_cenario)
            escritor.writerows(linhas_por_cenario)

        cab_dif = ["Model", "Difficulty", "N"] + [titulo for _, titulo, _ in COLUNAS]
        with open(pasta / "por_dificuldade_setting_{}.csv".format(setting), "w", newline="", encoding="utf-8") as arq:
            escritor = csv.writer(arq)
            escritor.writerow(cab_dif)
            escritor.writerows(por_dificuldade)
        (pasta / "por_dificuldade_setting_{}.md".format(setting)).write_text(
            "# Resultados por dificuldade, {}\n\n".format(NOME_SETTING[setting])
            + _tabela_md(cab_dif, por_dificuldade) + "\n", encoding="utf-8")

        (pasta / "calculos_detalhados_setting_{}.md".format(setting)).write_text(
            "# Calculos detalhados, {}\n\n".format(NOME_SETTING[setting])
            + "Gerado em {}. N = {} cenarios por modelo.\n\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M"), N)
            + "\n".join(calculos), encoding="utf-8")

        abas_excel["Tabela_" + setting] = [cabecalho] + [
            [l["modelo"], l["parametros"]] + [round(l["porcentagens"][c], 2) for c, _, _ in COLUNAS]
            for l in linhas_tabela]
        abas_excel["Cenarios_" + setting] = [cab_cenario] + linhas_por_cenario
        abas_excel["Dificuldade_" + setting] = [cab_dif] + por_dificuldade

        log("Tabela do setting {} gravada em {}".format(setting, pasta / "tabela_setting_{}.md".format(setting)))
        for l in linhas_tabela:
            if l["situacao"] != "completo":
                log("   AVISO: {} esta {}".format(l["modelo"], l["situacao"]))

    _gravar_excel(pasta / "tabela_resultados.xlsx", abas_excel, log)


# ----------------------------------------------------------------------
# Textos
# ----------------------------------------------------------------------
def _tabela_md(cabecalho: List[Any], linhas: List[List[Any]]) -> str:
    saida = ["| " + " | ".join(str(c) for c in cabecalho) + " |",
             "|" + "|".join("---" for _ in cabecalho) + "|"]
    saida += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def _markdown_tabela(setting, cabecalho, linhas_csv, linhas_tabela, N) -> str:
    texto = [
        "# Evaluation on IaC-Eval",
        "",
        "**{}**. Few-shot com 3 exemplos fixos, pass@1. N = {} cenarios por modelo.".format(NOME_SETTING[setting], N),
        "",
        _tabela_md(cabecalho, linhas_csv),
        "",
        "Como ler: cada numero e uma porcentagem dos {} cenarios. Exemplo: Correctness 50.00 = metade dos {} "
        "cenarios passou no opa eval. SecurityCompliance e a media das notas do Checkov, em %.".format(N, N),
        "",
        "Conferencia obrigatoria: em toda linha, Correctness <= Deployability <= Compilability.",
        "",
        "Situacao de cada modelo:",
        "",
    ]
    texto += ["- {}: {}".format(l["modelo"], l["situacao"]) for l in linhas_tabela]
    texto += ["", "A conta de cada numero esta em calculos_detalhados_setting_{}.md".format(setting), ""]
    return "\n".join(texto)


def _texto_calculo(modelo, parametros, resultados, somas, porcentagens, N, avaliados, sem_hcl, violacoes) -> str:
    t = ["## {} ({})".format(modelo, parametros or "#Params nao informado"), ""]
    t.append("- Cenarios avaliados: {} de {}".format(avaliados, N))
    t.append("- Respostas sem HCL extraido (valem 0 em tudo): {}".format(sem_hcl))
    t.append("- Conferencia Correctness <= Deployability <= Compilability: " +
             ("OK em todos os cenarios" if not violacoes else "VIOLADA nas linhas {} (erro no pipeline!)".format(violacoes)))
    t.append("")
    t.append("| Metrica | Conta | Resultado |")
    t.append("|---|---|---|")
    for chave, titulo, comando in COLUNAS:
        if chave == "security_compliance":
            conta = "100 x {:.4f} / {}".format(somas[chave], N)
        else:
            conta = "100 x {:.0f} / {}".format(somas[chave], N)
        t.append("| {} ({}) | {} | **{}** |".format(titulo, comando, conta, _fmt(porcentagens[chave])))
    t.append("")
    t.append("Notas de cada cenario (1 = passou, 0 = falhou; Security = nota do Checkov):")
    t.append("")
    t.append("| linha | dificuldade | HCL? | Compil. | Deploy. | Correct. | Linter | Security |")
    t.append("|---|---|---|---|---|---|---|---|")
    for cenario, r in resultados:
        if r is None:
            t.append("| {} | {} | (nao avaliado) | 0 | 0 | 0 | 0 | 0.0000 |".format(cenario["linha"], cenario["Difficulty"]))
            continue
        m = r["metricas"]
        t.append("| {} | {} | {} | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.4f} |".format(
            cenario["linha"], cenario["Difficulty"], "sim" if r.get("hcl_extraido") else "nao",
            m["compilability"], m["deployability"], m["correctness"], m["linter_pass"], m["security_compliance"]))
    t.append("| **soma** | | | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.4f} |".format(
        somas["compilability"], somas["deployability"], somas["correctness"],
        somas["linter_pass"], somas["security_compliance"]))
    t.append("")
    return "\n".join(t)


def _gravar_excel(caminho: Path, abas, log) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        log("openpyxl nao instalado: planilha .xlsx nao gerada (os .csv e .md foram gerados).")
        return
    livro = Workbook()
    livro.remove(livro.active)
    for nome, linhas in abas.items():
        aba = livro.create_sheet(nome[:31])
        for linha in linhas:
            aba.append(linha)
        for celula in aba[1]:
            celula.font = Font(bold=True)
        for coluna in aba.columns:
            largura = max(len(str(c.value)) if c.value is not None else 0 for c in coluna)
            aba.column_dimensions[coluna[0].column_letter].width = min(max(10, largura + 2), 60)
    livro.save(caminho)
    log("Planilha gravada em " + str(caminho))
