"""
Cliente para o Ollama (modelos rodando localmente na sua maquina).

Nao existe nenhuma chamada para a internet ou para APIs pagas neste projeto.
Tudo acontece em http://127.0.0.1:11434.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import requests


@dataclass
class GenerationOutput:
    text: str
    ok: bool
    error: str = ""
    raw: Dict[str, Any] | None = None


class OllamaClient:
    def __init__(self, cfg: Dict[str, Any]):
        self.url = cfg.get("url", "http://127.0.0.1:11434/api/generate")
        self.timeout = int(cfg.get("request_timeout_seconds", 900))
        self.options = {
            "temperature": cfg.get("temperature", 0.2),
            "top_p": cfg.get("top_p", 0.9),
            "top_k": cfg.get("top_k", 40),
            "seed": cfg.get("seed", 42),
            "num_predict": cfg.get("num_predict", 2048),
        }

    def generate(self, model: str, prompt: str) -> GenerationOutput:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": self.options,
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            return GenerationOutput(
                text="",
                ok=False,
                error=(
                    f"Falha ao falar com o Ollama em {self.url}: {exc}. "
                    "Verifique se o Ollama esta rodando (comando: ollama serve)."
                ),
            )

        if resp.status_code != 200:
            return GenerationOutput(
                text="",
                ok=False,
                error=f"Ollama respondeu HTTP {resp.status_code}: {resp.text[:500]}",
            )

        data = resp.json()
        return GenerationOutput(text=data.get("response", ""), ok=True, raw=data)

    def is_alive(self) -> bool:
        base = self.url.split("/api/")[0]
        try:
            return requests.get(f"{base}/api/tags", timeout=10).status_code == 200
        except requests.RequestException:
            return False
