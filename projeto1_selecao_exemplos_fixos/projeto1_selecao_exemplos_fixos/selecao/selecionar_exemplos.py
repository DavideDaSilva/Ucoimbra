"""
Procura, no dataset IaC-Eval, os 3 exemplos fixos que serao usados no
bloco [C] do template do TerraFormer (Projeto 2).

Regra pedida:
  "Checar, primeiro, a validade dos codigos Terraform (Reference output)
   usando os 5 criterios. Quando os tres exemplos forem encontrados,
   parar a checagem."

Como a busca funciona (passo a passo):
  1. Percorre as linhas do dataset em ordem (0, 1, 2, ...), a partir de
     "linha_inicial".
  2. Pula a linha (sem avaliar) se:
       * a estrategia for "uma_por_dificuldade" e a dificuldade da linha
         nao for uma das desejadas, ou ja tiver um exemplo escolhido;
       * faltar Prompt, Rego intent ou Reference output;
       * faltar Intent e "exigir_intent_preenchido" for true
         (o Intent e necessario no Setting B do Projeto 2);
       * "evitar_recursos_repetidos" for true e a linha usar algum tipo de
         recurso (coluna Resource) que ja aparece em um exemplo escolhido.
         Motivo: exemplos variados ensinam mais ao modelo. Sem essa regra,
         os 3 exemplos acabavam sendo todos de Elastic Beanstalk (servico com
         poucas regras do Checkov, que passa facilmente com nota 100%).
  3. Avalia o Reference output com os 5 verificadores (mesma escada do
     Projeto 2: validate -> plan -> opa, e TFLint + Checkov).
  4. A linha e APROVADA se cumprir TODOS os criterios do configuracao.yaml
     (secao selecao.criterios). Se aprovada, vira um exemplo fixo.
  5. Para assim que encontrar a quantidade pedida (padrao: 3).

Estrategias:
  "uma_por_dificuldade" (padrao): um exemplo para cada dificuldade listada em
      "dificuldades_desejadas" (padrao [1, 2, 3], igual aos slides:
      linhas 2, 56 e 142 tinham dificuldade 1, 2 e 3).
  "sequencial": os primeiros N exemplos aprovados, de qualquer dificuldade.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.registro_pass_fail import RegistroPassFail
from verificadores.escada_de_avaliacao import ORDEM_DOS_COMANDOS, avaliar_configuracao


@dataclass
class CriteriosAprovacao:
    compilability: bool = True
    deployability: bool = True
    correctness: bool = True
    linter: bool = True
    security_minima: float = 1.0  # nota minima do Checkov, de 0.0 a 1.0

    def avaliar(self, metricas: Dict[str, float]) -> List[str]:
        """Devolve a lista de criterios NAO atendidos (vazia = aprovado)."""
        faltas = []
        if self.compilability and metricas["compilability"] < 1:
            faltas.append("Compilability (terraform validate)")
        if self.deployability and metricas["deployability"] < 1:
            faltas.append("Deployability (terraform plan)")
        if self.correctness and metricas["correctness"] < 1:
            faltas.append("Correctness (opa eval)")
        if self.linter and metricas["linter_pass"] < 1:
            faltas.append("Linter (tflint)")
        if metricas["security_compliance"] + 1e-9 < self.security_minima:
            faltas.append(
                "Security (checkov) nota {:.4f} < minimo {:.4f}".format(
                    metricas["security_compliance"], self.security_minima
                )
            )
        return faltas


@dataclass
class ConfiguracaoSelecao:
    estrategia: str = "uma_por_dificuldade"
    dificuldades_desejadas: List[int] = field(default_factory=lambda: [1, 2, 3])
    quantidade_de_exemplos: int = 3
    linha_inicial: int = 0
    exigir_intent_preenchido: bool = True
    evitar_recursos_repetidos: bool = True
    criterios: CriteriosAprovacao = field(default_factory=CriteriosAprovacao)


def carregar_configuracao_selecao(secao: Dict[str, Any]) -> ConfiguracaoSelecao:
    secao = secao or {}
    cfg = ConfiguracaoSelecao()
    cfg.estrategia = str(secao.get("estrategia", cfg.estrategia))
    cfg.dificuldades_desejadas = [int(d) for d in secao.get("dificuldades_desejadas", cfg.dificuldades_desejadas)]
    cfg.quantidade_de_exemplos = int(secao.get("quantidade_de_exemplos", cfg.quantidade_de_exemplos))
    cfg.linha_inicial = int(secao.get("linha_inicial", cfg.linha_inicial))
    cfg.exigir_intent_preenchido = bool(secao.get("exigir_intent_preenchido", cfg.exigir_intent_preenchido))
    cfg.evitar_recursos_repetidos = bool(secao.get("evitar_recursos_repetidos", cfg.evitar_recursos_repetidos))
    crit = secao.get("criterios", {}) or {}
    c = cfg.criterios
    c.compilability = bool(crit.get("compilability", c.compilability))
    c.deployability = bool(crit.get("deployability", c.deployability))
    c.correctness = bool(crit.get("correctness", c.correctness))
    c.linter = bool(crit.get("linter", c.linter))
    c.security_minima = float(crit.get("security_minima", c.security_minima))
    if cfg.estrategia not in ("uma_por_dificuldade", "sequencial"):
        raise ValueError("selecao.estrategia deve ser 'uma_por_dificuldade' ou 'sequencial'")
    if cfg.estrategia == "uma_por_dificuldade":
        cfg.quantidade_de_exemplos = len(cfg.dificuldades_desejadas)
    return cfg


def selecionar_exemplos(
    cenarios: List[Dict[str, Any]],
    cfg_selecao: ConfiguracaoSelecao,
    cfg_verif: ConfiguracaoVerificadores,
    pasta_resultados: Path,
    log,
) -> List[Dict[str, Any]]:
    """Executa a busca e devolve a lista de exemplos escolhidos."""
    registro = RegistroPassFail(pasta_resultados)
    pasta_verificacoes = pasta_resultados / "verificacoes"
    caminho_relatorio = pasta_resultados / "relatorio_da_busca.csv"

    escolhidos: List[Dict[str, Any]] = []
    dificuldades_pendentes = list(cfg_selecao.dificuldades_desejadas)

    with open(caminho_relatorio, "w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.writer(arquivo_csv)
        escritor.writerow([
            "linha", "linha_na_planilha", "dificuldade", "resource",
            "compilability", "deployability", "correctness", "linter_pass",
            "security_compliance", "aprovada", "criterios_nao_atendidos",
        ])

        for cenario in cenarios:
            if len(escolhidos) >= cfg_selecao.quantidade_de_exemplos:
                break
            linha = cenario["linha"]
            if linha < cfg_selecao.linha_inicial:
                continue

            motivo_pulo = _motivo_para_pular(cenario, cfg_selecao, dificuldades_pendentes, escolhidos)
            if motivo_pulo:
                continue

            log("Avaliando linha {} (dificuldade {}, {})...".format(
                linha, cenario["Difficulty"], cenario["Resource"]))
            resultado = avaliar_configuracao(
                cenario["Reference output"],
                cenario["Rego intent"],
                pasta_verificacoes / "linha_{:04d}".format(linha),
                cfg_verif,
            )
            metricas = resultado["metricas"]

            contexto = {
                "linha": linha,
                "linha_na_planilha": cenario["linha_na_planilha"],
                "dificuldade": cenario["Difficulty"],
                "origem": "Reference output",
            }
            for comando in ORDEM_DOS_COMANDOS:
                registro.registrar(contexto, resultado["_objetos"][comando])

            faltas = cfg_selecao.criterios.avaliar(metricas)
            aprovada = not faltas
            escritor.writerow([
                linha, cenario["linha_na_planilha"], cenario["Difficulty"], cenario["Resource"],
                int(metricas["compilability"]), int(metricas["deployability"]),
                int(metricas["correctness"]), int(metricas["linter_pass"]),
                "{:.4f}".format(metricas["security_compliance"]),
                "sim" if aprovada else "nao", "; ".join(faltas),
            ])
            arquivo_csv.flush()

            if aprovada:
                log("   -> APROVADA. Exemplo {} escolhido.".format(len(escolhidos) + 1))
                escolhidos.append(_montar_exemplo(cenario, resultado, len(escolhidos) + 1))
                if cfg_selecao.estrategia == "uma_por_dificuldade":
                    dificuldades_pendentes.remove(cenario["Difficulty"])
            else:
                log("   -> reprovada: " + "; ".join(faltas))

    return escolhidos


def _tipos_de_recurso(cenario) -> set:
    return {r.strip() for r in str(cenario["Resource"]).split(",") if r.strip()}


def _motivo_para_pular(cenario, cfg: ConfiguracaoSelecao, pendentes: List[int], escolhidos) -> Optional[str]:
    if cfg.estrategia == "uma_por_dificuldade" and cenario["Difficulty"] not in pendentes:
        return "dificuldade nao desejada ou ja preenchida"
    for coluna in ("Prompt", "Rego intent", "Reference output"):
        if not cenario[coluna].strip():
            return "coluna {} vazia".format(coluna)
    if cfg.exigir_intent_preenchido and not cenario["Intent"].strip():
        return "Intent vazio"
    if cfg.evitar_recursos_repetidos:
        ja_usados = set()
        for exemplo in escolhidos:
            ja_usados |= _tipos_de_recurso(exemplo)
        repetidos = _tipos_de_recurso(cenario) & ja_usados
        if repetidos:
            return "recurso ja usado em outro exemplo: " + ", ".join(sorted(repetidos))
    return None


def _montar_exemplo(cenario, resultado, numero: int) -> Dict[str, Any]:
    return {
        "numero_do_exemplo": numero,
        "linha": cenario["linha"],
        "linha_na_planilha": cenario["linha_na_planilha"],
        "Resource": cenario["Resource"],
        "Difficulty": cenario["Difficulty"],
        "Prompt": cenario["Prompt"],
        "Intent": cenario["Intent"],
        "Rego intent": cenario["Rego intent"],
        "Reference output": cenario["Reference output"],
        "verificacao": {
            "metricas": resultado["metricas"],
            "verificacoes": resultado["verificacoes"],
        },
        "data_da_selecao": datetime.now().isoformat(timespec="seconds"),
    }
