"""
ETAPA 2: "Prompt Builder". Monta o texto exato que sera enviado ao LLM.

Entrada:
  * os 3 exemplos fixos (Projeto 1)
  * o cenario avaliado (linha do IaC-Eval)
  * o setting:  "A" = Prompt-only (principal, igual ao paper)
                "B" = Prompt + Intent (complementar)

Saida:
  * o prompt completo (texto)
  * um pequeno resumo do que foi usado (para ficar registrado)

Garantias:
  * Todos os modelos recebem EXATAMENTE o mesmo texto para o mesmo cenario.
  * A Rego intent e o Reference output do cenario avaliado NUNCA entram.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pipeline.etapa2_prompt_builder import template_terraformer as T

SETTINGS_VALIDOS = ("A", "B")


def montar_prompt(
    cenario: Dict[str, Any],
    exemplos_fixos: List[Dict[str, Any]],
    setting: str,
) -> Tuple[str, Dict[str, Any]]:
    if setting not in SETTINGS_VALIDOS:
        raise ValueError("Setting invalido: {} (use 'A' ou 'B')".format(setting))

    # Bloco [C]: exemplos fixos
    modelo_exemplo = T.BLOCO_C_EXEMPLO_SETTING_B if setting == "B" else T.BLOCO_C_EXEMPLO_SETTING_A
    exemplos_formatados = []
    for numero, exemplo in enumerate(exemplos_fixos, start=1):
        exemplos_formatados.append(
            modelo_exemplo.format(
                numero=numero,
                prompt=exemplo["Prompt"].strip(),
                intent=_intent_em_uma_linha(exemplo.get("Intent", "")),
                configuracao=exemplo["Reference output"].strip(),
            )
        )
    bloco_c = T.BLOCO_C_INTRODUCAO + "\n\n" + "\n\n".join(exemplos_formatados)

    # Bloco [D]: prompt do cenario
    bloco_d = T.BLOCO_D_USER_PROMPT.format(prompt=cenario["Prompt"].strip())

    blocos = [T.BLOCO_A_ROLE, T.BLOCO_B_TAREFA, bloco_c, bloco_d]

    # Bloco [E]: intent do cenario (somente Setting B e somente se existir)
    intent_usado = False
    intent = (cenario.get("Intent") or "").strip()
    if setting == "B" and intent:
        blocos.append(T.BLOCO_E_USER_INTENT.format(intent=intent))
        intent_usado = True

    blocos.append(T.BLOCO_F_FORMATO_SAIDA)
    prompt = "\n\n".join(blocos) + "\n"

    resumo = {
        "setting": setting,
        "linhas_dos_exemplos_fixos": [e["linha"] for e in exemplos_fixos],
        "linha_do_cenario": cenario["linha"],
        "bloco_E_intent_incluido": intent_usado,
        "observacao": (
            "Setting B, mas o cenario nao tem Intent no dataset: bloco E omitido"
            if setting == "B" and not intent else ""
        ),
        "quantidade_de_caracteres": len(prompt),
    }
    return prompt, resumo


def _intent_em_uma_linha(intent: str) -> str:
    """O Intent do dataset tem varias linhas; nos exemplos ele vira uma linha so."""
    return " ".join((intent or "").split())
