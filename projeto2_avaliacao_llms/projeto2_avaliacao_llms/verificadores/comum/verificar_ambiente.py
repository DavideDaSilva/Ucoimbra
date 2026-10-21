"""
Confere se todos os programas necessarios estao instalados e prepara o TFLint.

Rode antes da primeira execucao (o executar.py tem a opcao --verificar-ambiente).
Para cada programa mostra: OK / FALTANDO e a versao encontrada.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List, Tuple

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.fv2_terraform_plan.simulador_moto import simulador_responde
from verificadores.tflint_linter.verificador import preparar_tflint

VERSAO_TERRAFORM_DO_PAPER = "1.12"


def _versao(comando: List[str]) -> Tuple[bool, str]:
    resultado = executar(comando, Path("."), 120)
    if resultado.erro_execucao:
        return False, resultado.erro_execucao
    texto = (resultado.stdout + "\n" + resultado.stderr).strip()
    primeira = next((l for l in texto.splitlines() if l.strip()), "")
    return resultado.codigo_saida == 0, primeira


def verificar_ambiente(cfg: ConfiguracaoVerificadores, pasta_temporaria: Path) -> bool:
    print("\n=== Verificacao do ambiente ===\n")
    tudo_ok = True
    itens = [
        ("Terraform", [cfg.terraform, "version"]),
        ("OPA", [cfg.opa, "version"]),
        ("TFLint", [cfg.tflint, "--version"]),
        ("Checkov", [cfg.checkov, "--version"]),
    ]
    for nome, comando in itens:
        ok, versao = _versao(comando)
        print("  [{}] {:<10} {}".format("OK" if ok else "FALTANDO", nome, versao))
        tudo_ok &= ok
        if nome == "Terraform" and ok and VERSAO_TERRAFORM_DO_PAPER not in versao:
            print(
                "       Aviso: o paper usou Terraform v1.12.0. Versao encontrada: {}.\n"
                "       Funciona, mas para reproduzir o paper prefira a serie 1.12.".format(versao)
            )

    if cfg.modo_deployability == "moto":
        instalado = shutil.which(cfg.comando_moto) is not None
        rodando = simulador_responde(cfg.endereco_moto)
        situacao = "rodando" if rodando else ("instalado (sera ligado automaticamente)" if instalado else "")
        ok = instalado or rodando
        print("  [{}] {:<10} {}".format("OK" if ok else "FALTANDO", "moto", situacao or 'instale com: pip install "moto[server]"'))
        tudo_ok &= ok
    else:
        print("  [--] moto       nao utilizado (modo 'sem_servidor')")

    if tudo_ok:
        print("\n  Preparando o TFLint (tflint --init: baixa o plugin de regras AWS)...")
        init = preparar_tflint(cfg, pasta_temporaria)
        if init.sucesso:
            print("  [OK] TFLint pronto. Plugins em: {}".format(cfg.pasta_plugins_tflint))
        else:
            tudo_ok = False
            print("  [FALHOU] tflint --init. Saida:\n" + init.como_texto())
            print(
                "  Dica: se a mensagem falar de 'rate limit' do GitHub, defina a variavel\n"
                "  de ambiente GITHUB_TOKEN com um token pessoal (gratuito) e tente de novo."
            )

    print("\nResultado: " + ("TUDO PRONTO." if tudo_ok else "corrija os itens acima antes de continuar.") + "\n")
    return tudo_ok


def versao_terraform(cfg: ConfiguracaoVerificadores) -> str:
    ok, texto = _versao([cfg.terraform, "version"])
    achado = re.search(r"v(\d+\.\d+\.\d+)", texto)
    return achado.group(1) if (ok and achado) else texto
