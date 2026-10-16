"""
Salva os exemplos fixos escolhidos em 3 formatos:

  resultados/exemplos_fixos.json
      ARQUIVO PRINCIPAL. E este arquivo que o Projeto 2 le.
      Contem, para cada exemplo: linha no dataset, Prompt, Intent,
      Rego intent, Reference output, dificuldade e o resultado das 5 verificacoes.

  resultados/exemplos_fixos.md
      Versao para leitura humana (abre em qualquer editor ou no GitHub).

  resultados/exemplos/exemplo_N_linha_XXXX/
      Uma pasta por exemplo, com cada campo em um arquivo separado:
        prompt.txt, intent.txt, rego_intent.rego, reference_output.tf,
        metadados.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

NOMES_METRICAS = {
    "compilability": "Compilability (terraform validate)",
    "deployability": "Deployability (terraform plan)",
    "correctness": "Correctness (opa eval)",
    "linter_pass": "Linter (TFLint)",
    "security_compliance": "Security Compliance (Checkov)",
}


def salvar_exemplos(exemplos: List[Dict[str, Any]], pasta: Path, informacoes: Dict[str, Any]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)

    conteudo = {"informacoes_da_execucao": informacoes, "exemplos": exemplos}
    (pasta / "exemplos_fixos.json").write_text(
        json.dumps(conteudo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    for exemplo in exemplos:
        subpasta = pasta / "exemplos" / "exemplo_{}_linha_{:04d}".format(
            exemplo["numero_do_exemplo"], exemplo["linha"]
        )
        subpasta.mkdir(parents=True, exist_ok=True)
        (subpasta / "prompt.txt").write_text(exemplo["Prompt"] + "\n", encoding="utf-8")
        (subpasta / "intent.txt").write_text(exemplo["Intent"] + "\n", encoding="utf-8")
        (subpasta / "rego_intent.rego").write_text(exemplo["Rego intent"] + "\n", encoding="utf-8")
        (subpasta / "reference_output.tf").write_text(exemplo["Reference output"] + "\n", encoding="utf-8")
        metadados = {k: exemplo[k] for k in ("numero_do_exemplo", "linha", "linha_na_planilha", "Resource", "Difficulty")}
        metadados["metricas"] = exemplo["verificacao"]["metricas"]
        (subpasta / "metadados.json").write_text(
            json.dumps(metadados, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    (pasta / "exemplos_fixos.md").write_text(_markdown(exemplos, informacoes), encoding="utf-8")


def _markdown(exemplos: List[Dict[str, Any]], informacoes: Dict[str, Any]) -> str:
    linhas = ["# Exemplos fixos escolhidos (Projeto 1)", ""]
    linhas.append("Gerado em: {}".format(informacoes.get("data_hora", "")))
    linhas.append("")
    linhas.append("| Exemplo | Linha no dataset | Linha na planilha | Dificuldade | Resource |")
    linhas.append("|---|---|---|---|---|")
    for e in exemplos:
        linhas.append("| {} | {} | {} | {} | {} |".format(
            e["numero_do_exemplo"], e["linha"], e["linha_na_planilha"], e["Difficulty"], e["Resource"]))
    linhas.append("")
    linhas.append("Linha no dataset: contagem a partir de 0 (mesma numeracao dos slides).")
    linhas.append("Linha na planilha: linha onde o cenario aparece ao abrir o arquivo no Excel/LibreOffice.")
    linhas.append("")

    for e in exemplos:
        linhas.append("## Exemplo {} (linha {}, dificuldade {})".format(
            e["numero_do_exemplo"], e["linha"], e["Difficulty"]))
        linhas.append("")
        linhas.append("**Resultado das 5 verificacoes do Reference output:**")
        linhas.append("")
        for chave, nome in NOMES_METRICAS.items():
            valor = e["verificacao"]["metricas"][chave]
            texto = "{:.2%}".format(valor) if chave == "security_compliance" else ("passou" if valor >= 1 else "falhou")
            linhas.append("- {}: {}".format(nome, texto))
        linhas.append("")
        for titulo, campo, linguagem in (
            ("Prompt", "Prompt", "text"),
            ("Intent", "Intent", "text"),
            ("Rego intent", "Rego intent", "rego"),
            ("Reference output", "Reference output", "hcl"),
        ):
            linhas.append("### " + titulo)
            linhas.append("")
            linhas.append("```" + linguagem)
            linhas.append(e[campo])
            linhas.append("```")
            linhas.append("")
    return "\n".join(linhas)
