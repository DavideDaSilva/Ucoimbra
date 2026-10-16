"""
Liga e desliga o "moto_server", o simulador GRATUITO da AWS usado no terraform plan.

O que e o moto?
  Um programa de codigo aberto (pip install "moto[server]") que finge ser a AWS.
  Ele roda no seu computador, em http://127.0.0.1:5555, e responde as mesmas
  perguntas que a AWS responderia (ex.: "quais zonas de disponibilidade existem
  em us-east-1?"). Nao precisa de conta, de cartao de credito nem de internet.

Catalogo de imagens (AMIs):
  O moto ja vem com 44 imagens de exemplo, mas nao tem, por exemplo, o Ubuntu
  24.04 (noble), procurado por 33 Reference outputs do IaC-Eval. O arquivo
  catalogo_amis_simulador.json (nesta pasta) tem as 44 imagens do moto e mais
  as que o dataset procura (Ubuntu 24.04/22.04/20.04, Amazon Linux 2023 e 2).
  Ele e entregue ao moto pela variavel de ambiente MOTO_AMIS_PATH.
  Se voce ligar o moto manualmente, use:
     Linux/macOS:  MOTO_AMIS_PATH=verificadores/fv2_terraform_plan/catalogo_amis_simulador.json moto_server -p 5555
     Windows:      $env:MOTO_AMIS_PATH="verificadores/fv2_terraform_plan/catalogo_amis_simulador.json"; moto_server -p 5555

Como e usado aqui:
  * Se o modo de deployability for "moto" e "iniciar_moto_automaticamente" for
    true, este arquivo liga o simulador antes das verificacoes e desliga no fim.
  * Se ja existir um simulador rodando no endereco configurado, ele e reaproveitado.
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urlparse

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import montar_ambiente

CATALOGO_AMIS = Path(__file__).resolve().parent / "catalogo_amis_simulador.json"


def simulador_responde(endereco: str) -> bool:
    try:
        with urllib.request.urlopen(endereco.rstrip("/") + "/moto-api/", timeout=3) as resposta:
            return resposta.status == 200
    except Exception:  # noqa: BLE001
        return False


@contextmanager
def simulador_aws(cfg: ConfiguracaoVerificadores, pasta_logs: Path) -> Iterator[Optional[str]]:
    """
    Uso:
        with simulador_aws(cfg, pasta) as situacao:
            ... roda as verificacoes ...
    `situacao` e um texto explicando o que aconteceu (para o log).
    """
    if cfg.modo_deployability != "moto":
        yield "modo 'sem_servidor': simulador AWS nao utilizado"
        return

    if simulador_responde(cfg.endereco_moto):
        yield "simulador AWS (moto) ja estava rodando em " + cfg.endereco_moto
        return

    if not cfg.iniciar_moto_automaticamente:
        raise RuntimeError(
            "O simulador AWS (moto) nao esta respondendo em {}.\n"
            "Ligue-o em outro terminal com:  moto_server -p 5555\n"
            "ou mude 'iniciar_moto_automaticamente' para true no configuracao.yaml.".format(
                cfg.endereco_moto
            )
        )

    porta = urlparse(cfg.endereco_moto).port or 5555
    pasta_logs.mkdir(parents=True, exist_ok=True)
    arquivo_log = open(pasta_logs / "simulador_moto.log", "w", encoding="utf-8")
    try:
        ambiente = montar_ambiente({"MOTO_AMIS_PATH": str(CATALOGO_AMIS)} if CATALOGO_AMIS.exists() else {})
        processo = subprocess.Popen(
            [cfg.comando_moto, "-H", "127.0.0.1", "-p", str(porta)],
            stdout=arquivo_log,
            stderr=subprocess.STDOUT,
            env=ambiente,
        )
    except FileNotFoundError:
        arquivo_log.close()
        raise RuntimeError(
            "Nao encontrei o programa '{}'. Instale com:  pip install \"moto[server]\"".format(
                cfg.comando_moto
            )
        )

    try:
        for _ in range(60):
            if simulador_responde(cfg.endereco_moto):
                break
            if processo.poll() is not None:
                raise RuntimeError("O simulador moto encerrou ao iniciar. Veja simulador_moto.log")
            time.sleep(0.5)
        else:
            raise RuntimeError("O simulador moto nao respondeu em 30 segundos.")
        yield "simulador AWS (moto) iniciado automaticamente em " + cfg.endereco_moto
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processo.kill()
        arquivo_log.close()
