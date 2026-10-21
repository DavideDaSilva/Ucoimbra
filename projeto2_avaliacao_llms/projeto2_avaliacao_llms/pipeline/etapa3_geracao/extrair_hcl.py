"""
ETAPA 3 (final): extrai o codigo Terraform (HCL) da resposta do modelo.

Regra do protocolo (slides, Figure 1 e Figure 3):
  "HCL is taken from the final_terraform_config tag. No HCL means 0 on every metric."

Passo a passo:
  1. Procura todos os trechos entre <final_terraform_config> e </final_terraform_config>.
  2. Ignora trechos vazios e o texto de exemplo do proprio template
     ("(Provide your entire Terraform configuration within these tags)").
  3. Fica com o ULTIMO trecho valido (se o modelo repetir as tags, vale a resposta final).
  4. Se dentro do trecho houver cercas de codigo ```hcl ... ```, fica so com o
     conteudo delas (as cercas nao sao HCL).
  5. Se nada for encontrado -> "sem HCL" -> todas as metricas valem 0.

Opcao (configuracao.yaml, extracao.usar_bloco_de_codigo_sem_tags):
  false (padrao, igual ao protocolo): sem as tags, nao ha HCL.
  true: se nao houver tags, aceita o ultimo bloco ```hcl ... ``` da resposta.
  Em qualquer caso registramos se a resposta TERIA HCL pela regra alternativa,
  para que voce saiba quantas respostas foram perdidas apenas pela falta das tags.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

_TAGS = re.compile(r"<final_terraform_config>(.*?)</final_terraform_config>", re.DOTALL | re.IGNORECASE)
_CERCA = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.DOTALL)
_TEXTO_DO_TEMPLATE = "provide your entire terraform configuration within these tags"


def _conteudo_das_cercas(texto: str) -> str:
    blocos = [corpo.strip() for _, corpo in _CERCA.findall(texto) if corpo.strip()]
    return "\n\n".join(blocos) if blocos else texto.strip()


def _parece_hcl(texto: str) -> bool:
    return bool(re.search(r'\b(resource|provider|data|terraform|module|variable|output|locals)\b\s*("|\{)', texto))


def extrair_hcl(resposta: str, usar_bloco_de_codigo_sem_tags: bool = False) -> Dict[str, Optional[str]]:
    """
    Devolve:
      hcl                       -> codigo extraido ou None
      metodo                    -> "tags", "bloco_de_codigo" ou "nenhum"
      motivo                    -> explicacao curta
      hcl_pela_regra_alternativa -> o que a regra alternativa teria extraido (informativo)
    """
    resposta = resposta or ""

    candidatos = []
    for trecho in _TAGS.findall(resposta):
        limpo = _conteudo_das_cercas(trecho)
        if limpo and _TEXTO_DO_TEMPLATE not in limpo.lower():
            candidatos.append(limpo)

    alternativo = None
    blocos = [corpo.strip() for _, corpo in _CERCA.findall(resposta) if corpo.strip() and _parece_hcl(corpo)]
    if blocos:
        alternativo = blocos[-1]

    if candidatos:
        return {"hcl": candidatos[-1], "metodo": "tags", "motivo": "HCL extraido das tags <final_terraform_config>",
                "hcl_pela_regra_alternativa": alternativo}

    tem_abertura = "<final_terraform_config>" in resposta.lower()
    motivo = (
        "a tag <final_terraform_config> foi aberta mas nao foi fechada (resposta cortada?)"
        if tem_abertura else "a resposta nao contem as tags <final_terraform_config>"
    )
    if usar_bloco_de_codigo_sem_tags and alternativo:
        return {"hcl": alternativo, "metodo": "bloco_de_codigo",
                "motivo": motivo + "; usado o ultimo bloco ```hcl``` (regra alternativa ligada)",
                "hcl_pela_regra_alternativa": alternativo}
    return {"hcl": None, "metodo": "nenhum", "motivo": motivo, "hcl_pela_regra_alternativa": alternativo}
