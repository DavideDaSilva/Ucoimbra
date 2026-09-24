"""
ETAPA 0: CONFERENCIA DO AMBIENTE
================================

Roda uma checagem simples e diz, em portugues, o que ja esta pronto e o que
ainda falta instalar antes de comecar os experimentos.

Uso:
    python -m src.common.check_environment
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.common import shell
from src.common.config import load_config
from src.generation.ollama_client import OllamaClient

OK = "[ OK ]"
FALTA = "[FALTA]"
AVISO = "[AVISO]"


def check_binary(name: str, binary: str, version_args, obrigatorio: bool) -> bool:
    result = shell.run([binary] + list(version_args), timeout=60)
    if result.exit_code == 127:
        tag = FALTA if obrigatorio else AVISO
        print(f"{tag} {name}: nao encontrado (binario '{binary}')")
        return False
    first_line = (result.stdout or result.stderr).strip().splitlines()
    version = first_line[0] if first_line else "versao desconhecida"
    print(f"{OK} {name}: {version}")
    return True


def main() -> int:
    cfg = load_config()
    print("=" * 70)
    print("CONFERENCIA DO AMBIENTE")
    print("=" * 70)

    print(f"{OK} Python: {sys.version.split()[0]}")

    tools = cfg.tools
    faltando = []

    if not check_binary("Terraform", tools["terraform_binary"], ["version"], True):
        faltando.append("terraform")
    if not check_binary("Open Policy Agent", tools["opa_binary"], ["version"], True):
        faltando.append("opa")
    if not check_binary("TFLint", tools["tflint_binary"], ["--version"], False):
        faltando.append("tflint")
    if not check_binary("Checkov", tools["checkov_binary"], ["--version"], False):
        faltando.append("checkov")

    # ---- Ollama ----
    client = OllamaClient(cfg.ollama)
    if client.is_alive():
        base = cfg.ollama["url"].split("/api/")[0]
        import requests

        tags = requests.get(f"{base}/api/tags", timeout=10).json()
        instalados = {m["name"] for m in tags.get("models", [])}
        print(f"{OK} Ollama respondendo em {base}")
        for model in cfg.models:
            nome = model["name"]
            marca = OK if nome in instalados else FALTA
            print(f"   {marca} modelo '{nome}'"
                  + ("" if nome in instalados else f"  -> rode: ollama pull {nome}"))
    else:
        print(f"{FALTA} Ollama nao respondeu em {cfg.ollama['url']}")
        print("        Abra outro terminal e rode: ollama serve")
        faltando.append("ollama")

    # ---- datasets ----
    for key, ds in cfg.datasets.items():
        path = cfg.resolve(ds["instances"])
        if path.exists():
            n = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            print(f"{OK} dataset '{key}': {n} instancias em {path}")
        else:
            print(f"{FALTA} dataset '{key}': arquivo nao encontrado em {path}")

    print("=" * 70)
    if faltando:
        print("Pendencias:", ", ".join(faltando))
        print("Veja a secao de instalacao do GUIA_PASSO_A_PASSO.md")
        return 1
    print("Tudo pronto. Pode seguir para a etapa de geracao.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
