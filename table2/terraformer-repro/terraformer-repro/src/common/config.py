"""
Carrega o arquivo config/config.yaml e resolve os caminhos.

Todo modulo do projeto comeca chamando `load_config()`. Assim existe um unico
lugar de verdade para as configuracoes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

# Raiz do projeto (a pasta que contem config/, src/, data/, results/).
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Config:
    raw: Dict[str, Any] = field(default_factory=dict)

    # ---------------- acesso conveniente -----------------
    @property
    def ollama(self) -> Dict[str, Any]:
        return self.raw["ollama"]

    @property
    def models(self) -> list:
        return self.raw["models"]

    @property
    def datasets(self) -> Dict[str, Any]:
        return self.raw["datasets"]

    @property
    def tools(self) -> Dict[str, Any]:
        return self.raw["tools"]

    @property
    def aws(self) -> Dict[str, Any]:
        return self.raw["aws"]

    @property
    def prompting(self) -> Dict[str, Any]:
        return self.raw["prompting"]

    @property
    def table2(self) -> Dict[str, Any]:
        return self.raw.get("table2", {})

    def path(self, key: str) -> Path:
        """Caminho absoluto de uma entrada da secao `paths`."""
        return self.resolve(self.raw["paths"][key])

    def resolve(self, relative: str) -> Path:
        """Transforma um caminho relativo do YAML em caminho absoluto."""
        p = Path(relative)
        return p if p.is_absolute() else (PROJECT_ROOT / p)

    def model_by_name(self, name: str) -> Dict[str, Any]:
        for m in self.models:
            if m["name"] == name:
                return m
        return {"name": name, "label": name, "params": "UNK"}

    def dataset(self, key: str) -> Dict[str, Any]:
        if key not in self.datasets:
            raise KeyError(
                f"Dataset '{key}' nao existe no config.yaml. "
                f"Disponiveis: {list(self.datasets)}"
            )
        return self.datasets[key]

    def aws_env(self) -> Dict[str, str]:
        """Variaveis de ambiente usadas ao chamar o Terraform."""
        env = dict(os.environ)
        aws = self.aws
        env["AWS_DEFAULT_REGION"] = aws.get("region", "us-east-1")
        env["AWS_REGION"] = aws.get("region", "us-east-1")
        if aws.get("use_fake_credentials", True):
            env["AWS_ACCESS_KEY_ID"] = aws.get("access_key_id", "mock_access_key")
            env["AWS_SECRET_ACCESS_KEY"] = aws.get(
                "secret_access_key", "mock_secret_key"
            )
        # Cache de plugins evita baixar o provider AWS a cada instancia.
        cache = self.path("terraform_plugin_cache")
        cache.mkdir(parents=True, exist_ok=True)
        env["TF_PLUGIN_CACHE_DIR"] = str(cache)
        env["TF_IN_AUTOMATION"] = "1"
        env["TF_INPUT"] = "0"
        env["CHECKPOINT_DISABLE"] = "1"
        return env


def load_config(path: str | Path | None = None) -> Config:
    cfg_path = Path(path) if path else (PROJECT_ROOT / "config" / "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw=raw)
