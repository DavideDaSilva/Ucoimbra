"""
Monta o prompt final enviado ao modelo e extrai o codigo Terraform da resposta.

O prompt base fica em config/prompt.txt (exatamente o template do Apendice B
do paper). Os exemplos few-shot ficam em data/few_shot/examples.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List


def load_few_shot_block(examples_file: Path, how_many: int = 3) -> str:
    with open(examples_file, "r", encoding="utf-8") as fh:
        examples: List[dict] = json.load(fh)

    chunks = []
    for idx, ex in enumerate(examples[:how_many], start=1):
        chunks.append(
            f"### Example-{idx}\n"
            f"Prompt: {ex['prompt']}\n"
            f"Configuration:\n"
            f"```hcl\n{ex['config'].rstrip()}\n```\n"
        )
    return "\n".join(chunks)


def build_prompt(template_file: Path, few_shot_block: str, request: str) -> str:
    template = Path(template_file).read_text(encoding="utf-8")
    return template.replace("{few_shot_examples}", few_shot_block).replace(
        "{request}", request.strip()
    )


_TAG_RE = re.compile(
    r"<final_terraform_config>(.*?)</final_terraform_config>",
    re.DOTALL | re.IGNORECASE,
)
_FENCE_RE = re.compile(r"```(?:hcl|terraform|tf)?\s*(.*?)```", re.DOTALL)


def extract_terraform(raw_response: str) -> str:
    """
    Tira o codigo HCL de dentro da resposta do modelo.

    Ordem de tentativa:
      1. conteudo entre <final_terraform_config> e </final_terraform_config>;
      2. primeiro bloco de codigo delimitado por crases;
      3. a resposta inteira (ultimo recurso).

    Se o modelo nao devolver codigo nenhum, o resultado e uma string vazia e a
    instancia sera contada como falha de compilabilidade, exatamente como no
    protocolo pass@1 do paper.
    """
    text = raw_response or ""

    match = _TAG_RE.search(text)
    if match:
        inner = match.group(1).strip()
        fence = _FENCE_RE.search(inner)
        return (fence.group(1) if fence else inner).strip()

    fence = _FENCE_RE.search(text)
    if fence:
        return fence.group(1).strip()

    stripped = text.strip()
    # Heuristica simples: so aceita a resposta crua se parecer HCL.
    if any(kw in stripped for kw in ("resource ", "provider ", "terraform {")):
        return stripped
    return ""
