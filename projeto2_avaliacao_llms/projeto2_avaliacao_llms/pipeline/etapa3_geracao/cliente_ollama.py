"""
ETAPA 3: conversa com o Ollama (os modelos rodam no SEU computador).

Usa a API local do Ollama:  POST http://127.0.0.1:11434/api/generate
  * "stream": false   -> recebe a resposta inteira de uma vez
  * "options"         -> parametros de geracao (temperature, seed, ...)
  * "keep_alive"      -> mantem o modelo carregado na memoria entre os pedidos

Parametros importantes (definidos no configuracao.yaml, secao ollama.opcoes):
  temperature = 0     -> sem "criatividade": o modelo escolhe sempre a palavra
                         mais provavel (protocolo pass@1 dos slides).
  seed = 42           -> semente fixa, para repetir o resultado.
  num_ctx = 8192      -> TAMANHO MAXIMO do texto que o modelo le (em tokens).
                         IMPORTANTE: o padrao do Ollama e pequeno (2048 ou 4096
                         conforme a versao). O prompt com 3 exemplos pode passar
                         disso e o Ollama CORTA O INICIO DO PROMPT sem avisar.
                         Por isso definimos 8192 explicitamente.
  num_predict = 4096  -> tamanho maximo da resposta (em tokens).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import requests


class ErroOllama(RuntimeError):
    pass


class ClienteOllama:
    def __init__(self, url_base: str, tempo_limite: int, keep_alive: str, tentativas: int):
        self.url_base = url_base.rstrip("/")
        self.tempo_limite = tempo_limite
        self.keep_alive = keep_alive
        self.tentativas = max(1, tentativas)

    # ------------------------------------------------------------------
    def modelos_instalados(self) -> List[str]:
        """Equivale ao comando `ollama list`."""
        try:
            resposta = requests.get(self.url_base + "/api/tags", timeout=15)
            resposta.raise_for_status()
        except requests.RequestException as erro:
            raise ErroOllama(
                "Nao consegui falar com o Ollama em {}. Ele esta aberto? "
                "(rode 'ollama serve' ou abra o aplicativo do Ollama)\nDetalhe: {}".format(self.url_base, erro)
            )
        return sorted(m.get("name", "") for m in resposta.json().get("models", []))

    def informacoes_do_modelo(self, modelo: str) -> Dict[str, Any]:
        """Equivale a `ollama show MODELO`: tamanho em parametros, quantizacao..."""
        try:
            resposta = requests.post(self.url_base + "/api/show", json={"model": modelo}, timeout=30)
            resposta.raise_for_status()
            detalhes = resposta.json().get("details", {}) or {}
            return {
                "parameter_size": detalhes.get("parameter_size"),
                "quantization_level": detalhes.get("quantization_level"),
                "family": detalhes.get("family"),
            }
        except requests.RequestException:
            return {}

    # ------------------------------------------------------------------
    def gerar(self, modelo: str, prompt: str, opcoes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envia o prompt e devolve um dicionario com:
          resposta, motivo_fim (done_reason), tokens_prompt, tokens_resposta,
          tempo_total_s, tentativas_usadas
        """
        corpo = {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": opcoes,
        }
        ultimo_erro = None
        for tentativa in range(1, self.tentativas + 1):
            inicio = time.time()
            try:
                resposta = requests.post(
                    self.url_base + "/api/generate", json=corpo, timeout=self.tempo_limite
                )
                if resposta.status_code == 404:
                    raise ErroOllama(
                        "Modelo '{}' nao encontrado no Ollama. Baixe com: ollama pull {}".format(modelo, modelo)
                    )
                resposta.raise_for_status()
                dados = resposta.json()
                return {
                    "resposta": dados.get("response", ""),
                    "motivo_fim": dados.get("done_reason"),
                    "tokens_prompt": dados.get("prompt_eval_count"),
                    "tokens_resposta": dados.get("eval_count"),
                    "tempo_total_s": round(time.time() - inicio, 2),
                    "tentativas_usadas": tentativa,
                }
            except ErroOllama:
                raise
            except (requests.RequestException, ValueError) as erro:
                ultimo_erro = erro
                time.sleep(min(30, 5 * tentativa))
        raise ErroOllama("Falha ao gerar com '{}' apos {} tentativas: {}".format(
            modelo, self.tentativas, ultimo_erro))
