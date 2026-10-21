"""
ETAPA 4: "Automatic Evaluation" de todas as respostas geradas na Etapa 3.

Para cada (modelo, setting, cenario) que ja tem geracao.json:
  1. Le o HCL extraido (hcl_extraido.tf). Se nao existir -> "sem HCL" (tudo 0).
  2. Pega a Rego intent DIRETO DO DATASET (seta verde tracejada da Figure 1:
     a policy vai para o avaliador e nunca passou pelo modelo).
  3. Roda a escada de 5 verificadores (pasta verificadores/, mesma do Projeto 1).
  4. Grava cada PASS/FAIL em pass.txt / fail.txt da pasta do modelo
     (e tambem em por_comando/<comando>/pass.txt ou fail.txt).
  5. Salva resultado.json com as 5 metricas do cenario.

Retomada automatica: se resultado.json ja existe, o cenario e pulado
(a menos que use --refazer).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Dict, List

from pipeline.configuracao import Projeto
from verificadores.comum.registro_pass_fail import RegistroPassFail
from verificadores.escada_de_avaliacao import ORDEM_DOS_COMANDOS, avaliar_configuracao
from verificadores.fv2_terraform_plan.simulador_moto import simulador_aws


def avaliar_respostas(
    projeto: Projeto,
    cenarios: List[Dict[str, Any]],
    modelos: List[str],
    settings: List[str],
    refazer: bool,
    log: Callable[[str], None],
) -> None:
    faltando_geracao = 0
    with simulador_aws(projeto.verificadores, projeto.pasta_resultados) as situacao:
        log(situacao)
        for setting in settings:
            for modelo in modelos:
                registro = RegistroPassFail(projeto.pasta_modelo(setting, modelo))
                for posicao, cenario in enumerate(cenarios, start=1):
                    pasta = projeto.pasta_cenario(setting, modelo, cenario["linha"])
                    if not (pasta / "geracao.json").exists():
                        faltando_geracao += 1
                        continue
                    if (pasta / "resultado.json").exists() and not refazer:
                        continue

                    geracao = json.loads((pasta / "geracao.json").read_text(encoding="utf-8"))
                    arquivo_hcl = pasta / "hcl_extraido.tf"
                    hcl = arquivo_hcl.read_text(encoding="utf-8") if arquivo_hcl.exists() else None

                    log("[{}] setting {} | avaliando cenario {}/{} (linha {})".format(
                        modelo, setting, posicao, len(cenarios), cenario["linha"]))
                    avaliacao = avaliar_configuracao(
                        hcl, cenario["Rego intent"], pasta / "avaliacao", projeto.verificadores
                    )

                    contexto = {
                        "setting": setting,
                        "modelo": modelo,
                        "linha": cenario["linha"],
                        "dificuldade": cenario["Difficulty"],
                    }
                    for comando in ORDEM_DOS_COMANDOS:
                        registro.registrar(contexto, avaliacao["_objetos"][comando])

                    resultado = {
                        "setting": setting,
                        "modelo": modelo,
                        "linha": cenario["linha"],
                        "dificuldade": cenario["Difficulty"],
                        "resource": cenario["Resource"],
                        "hcl_extraido": hcl is not None,
                        "metodo_extracao": geracao.get("extracao", {}).get("metodo"),
                        "metricas": avaliacao["metricas"],
                        "status": {c: avaliacao["verificacoes"][c]["status"] for c in ORDEM_DOS_COMANDOS},
                        "motivos": {c: avaliacao["verificacoes"][c]["motivo"] for c in ORDEM_DOS_COMANDOS},
                        "data_hora": datetime.now().isoformat(timespec="seconds"),
                    }
                    (pasta / "resultado.json").write_text(
                        json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
                    )
                    m = avaliacao["metricas"]
                    log("   compil={:.0f} deploy={:.0f} correct={:.0f} linter={:.0f} security={:.4f}".format(
                        m["compilability"], m["deployability"], m["correctness"],
                        m["linter_pass"], m["security_compliance"]))
    if faltando_geracao:
        log("AVISO: {} combinacoes ainda nao foram geradas (rode a etapa 'gerar').".format(faltando_geracao))
