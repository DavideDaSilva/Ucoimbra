"""
"4. Automatic Evaluation": avalia UM codigo Terraform com os 5 verificadores.

Segue exatamente a Figure 3 dos slides:

            codigo HCL
                |
     +----------+--------------------------+
     |  (escada, uma etapa depois da outra) |  (em paralelo, sempre que ha HCL)
     v                                      v
  FV-i  terraform validate -> Compilability     TFLint  -> Linter Pass
     | so continua se passou                    Checkov -> Security Compliance
     v
  FV-ii terraform plan     -> Deployability
     | so continua se passou
     v
  FV-iii opa eval (Rego)   -> Correctness

Se uma etapa da escada falha, ela recebe 0 e as etapas seguintes recebem
NAO_EXECUTADO (tambem 0). Por isso, sempre:
     Correctness <= Deployability <= Compilability

Se NAO ha HCL (o modelo nao respondeu dentro das tags), TODAS as 5 metricas
valem 0 e todas as etapas ficam NAO_EXECUTADO.

Pastas criadas para cada avaliacao (dentro de `pasta_avaliacao`):
  codigo_avaliado.tf             o codigo exatamente como foi recebido
  area_de_trabalho_terraform/    main.tf + arquivos de credenciais simuladas
  1_terraform_validate/          saidas do init e do validate
  2_terraform_plan/              saidas do plan e do show, plan.json
  3_opa_eval/                    intent.rego, saida do opa, regras avaliadas
  4_tflint/                      saida do tflint, problemas encontrados
  5_checkov/                     saida do checkov, resumo com a nota
  resultado_avaliacao.json       resumo das 5 metricas desta avaliacao
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from verificadores.checkov_seguranca import verificador as checkov
from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.resultado_verificacao import PASS, nao_executado
from verificadores.fv1_terraform_validate import verificador as fv1_validate
from verificadores.fv2_terraform_plan import verificador as fv2_plan
from verificadores.fv2_terraform_plan.credenciais_simuladas import (
    preparar_pasta_terraform,
    variaveis_de_ambiente,
)
from verificadores.fv3_opa_eval import verificador as fv3_opa
from verificadores.tflint_linter import verificador as tflint

ORDEM_DOS_COMANDOS = ["terraform validate", "terraform plan", "opa eval", "tflint", "checkov"]

METRICA_DE_CADA_COMANDO = {
    "terraform validate": "compilability",
    "terraform plan": "deployability",
    "opa eval": "correctness",
    "tflint": "linter_pass",
    "checkov": "security_compliance",
}


def avaliar_configuracao(
    hcl: Optional[str],
    policy_rego: str,
    pasta_avaliacao: Path,
    cfg: ConfiguracaoVerificadores,
    apagar_cache_terraform_da_pasta: bool = True,
) -> Dict[str, Any]:
    """Roda os 5 verificadores e devolve um dicionario com tudo."""
    if pasta_avaliacao.exists():
        shutil.rmtree(pasta_avaliacao)
    pasta_avaliacao.mkdir(parents=True)

    resultados = {}

    # ---------------------------------------------------------------
    # Caso especial: nenhum HCL extraido -> tudo 0
    # ---------------------------------------------------------------
    if not hcl or not hcl.strip():
        motivo = "nenhum codigo HCL foi extraido da resposta; todas as metricas valem 0"
        for comando in ORDEM_DOS_COMANDOS:
            resultados[comando] = nao_executado(comando, motivo)
        return _finalizar(pasta_avaliacao, resultados, hcl_extraido=False, arquivos_auxiliares={})

    (pasta_avaliacao / "codigo_avaliado.tf").write_text(hcl, encoding="utf-8")

    # ---------------------------------------------------------------
    # Escada: validate -> plan -> opa
    # ---------------------------------------------------------------
    pasta_tf = pasta_avaliacao / "area_de_trabalho_terraform"
    auxiliares = preparar_pasta_terraform(
        pasta_tf,
        hcl,
        regiao_padrao=cfg.regiao_padrao,
        max_tentativas=cfg.max_tentativas_aws,
        versao_provider_aws=cfg.versao_provider_aws,
        neutralizar_required_version_e_profile=cfg.neutralizar_required_version_e_profile,
    )
    variaveis = variaveis_de_ambiente(cfg.modo_deployability, cfg.regiao_padrao, cfg.endereco_moto)

    r_validate = fv1_validate.verificar(pasta_tf, pasta_avaliacao / "1_terraform_validate", cfg, variaveis)
    resultados["terraform validate"] = r_validate

    plan_json = None
    if r_validate.status == PASS:
        r_plan, plan_json = fv2_plan.verificar(pasta_tf, pasta_avaliacao / "2_terraform_plan", cfg, variaveis)
    else:
        r_plan = nao_executado("terraform plan", "nao executado porque o terraform validate falhou")
    resultados["terraform plan"] = r_plan

    if r_plan.status == PASS and plan_json is not None:
        r_opa = fv3_opa.verificar(plan_json, policy_rego, pasta_avaliacao / "3_opa_eval", cfg)
    elif r_plan.status == PASS:
        r_opa = nao_executado("opa eval", "o plan passou, mas o terraform show nao gerou o plan.json")
    else:
        r_opa = nao_executado("opa eval", "nao executado porque o terraform plan nao passou")
    resultados["opa eval"] = r_opa

    # ---------------------------------------------------------------
    # Em paralelo a escada: TFLint e Checkov (sempre que ha HCL)
    # ---------------------------------------------------------------
    resultados["tflint"] = tflint.verificar(hcl, pasta_avaliacao / "4_tflint", cfg)
    resultados["checkov"] = checkov.verificar(hcl, pasta_avaliacao / "5_checkov", cfg)

    if apagar_cache_terraform_da_pasta:
        # A pasta .terraform e o plan.bin so ocupam espaco; os logs ja foram salvos.
        shutil.rmtree(pasta_tf / ".terraform", ignore_errors=True)
        (pasta_tf / "plan.bin").unlink(missing_ok=True)

    return _finalizar(pasta_avaliacao, resultados, hcl_extraido=True, arquivos_auxiliares=auxiliares)


def _finalizar(pasta: Path, resultados, hcl_extraido: bool, arquivos_auxiliares) -> Dict[str, Any]:
    metricas = {METRICA_DE_CADA_COMANDO[c]: float(resultados[c].valor) for c in ORDEM_DOS_COMANDOS}
    resumo = {
        "hcl_extraido": hcl_extraido,
        "metricas": metricas,
        "verificacoes": {c: resultados[c].como_dicionario() for c in ORDEM_DOS_COMANDOS},
        "arquivos_acrescentados_pela_avaliacao": sorted(arquivos_auxiliares.keys()),
    }
    (pasta / "resultado_avaliacao.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    resumo["_objetos"] = resultados  # usado para gravar pass.txt/fail.txt (nao vai para o JSON)
    return resumo
