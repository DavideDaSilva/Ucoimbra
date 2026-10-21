"""
Configuracao usada pelos 5 verificadores.

Os valores vem da secao "verificadores:" do arquivo configuracao.yaml.
Se algum campo nao estiver no YAML, o valor padrao abaixo e usado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TemposLimite:
    """Tempo maximo (em segundos) de cada comando."""

    terraform_init: int = 300  # o 1o init baixa o provider AWS (~150 MB)
    terraform_validate: int = 60
    terraform_plan: int = 120  # mesmo valor da Figure 3 dos slides
    terraform_show: int = 60
    opa_eval: int = 60
    tflint: int = 120
    checkov: int = 300


@dataclass
class ConfiguracaoVerificadores:
    # Programas (nome no PATH ou caminho completo)
    terraform: str = "terraform"
    opa: str = "opa"
    tflint: str = "tflint"
    checkov: str = "checkov"

    tempos: TemposLimite = field(default_factory=TemposLimite)

    # Deployability sem conta AWS (ver verificadores/fv2_terraform_plan/credenciais_simuladas.py)
    modo_deployability: str = "moto"  # "moto" ou "sem_servidor"
    regiao_padrao: str = "us-east-1"
    endereco_moto: str = "http://127.0.0.1:5555"
    iniciar_moto_automaticamente: bool = True
    comando_moto: str = "moto_server"
    max_tentativas_aws: int = 1
    versao_provider_aws: str = "~> 5.0"
    neutralizar_required_version_e_profile: bool = False

    # OPA
    opa_exigir_pelo_menos_um_true: bool = True

    # TFLint: gravidades que reprovam o codigo (ver tflint_linter/verificador.py)
    tflint_gravidades_que_reprovam: List[str] = field(default_factory=lambda: ["error"])

    # Pasta onde ficam caches (plugins do Terraform e do TFLint)
    pasta_cache: Path = Path("ferramentas/cache")

    @property
    def pasta_cache_terraform(self) -> Path:
        return self.pasta_cache / "terraform_plugins"

    @property
    def pasta_plugins_tflint(self) -> Path:
        return self.pasta_cache / "tflint_plugins"

    def variaveis_terraform(self) -> Dict[str, str]:
        """Variaveis de ambiente comuns a todos os comandos terraform."""
        self.pasta_cache_terraform.mkdir(parents=True, exist_ok=True)
        return {
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
            "CHECKPOINT_DISABLE": "1",
            "TF_PLUGIN_CACHE_DIR": str(self.pasta_cache_terraform.resolve()),
            "TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE": "1",
        }


def carregar_configuracao_verificadores(secao: Dict[str, Any], pasta_projeto: Path) -> ConfiguracaoVerificadores:
    """Cria a configuracao a partir da secao 'verificadores' do YAML."""
    secao = secao or {}
    programas = secao.get("programas", {}) or {}
    tempos = secao.get("tempos_limite_segundos", {}) or {}
    deploy = secao.get("deployability", {}) or {}
    opa = secao.get("opa", {}) or {}
    tfl = secao.get("tflint", {}) or {}

    cfg = ConfiguracaoVerificadores()
    cfg.terraform = programas.get("terraform", cfg.terraform)
    cfg.opa = programas.get("opa", cfg.opa)
    cfg.tflint = programas.get("tflint", cfg.tflint)
    cfg.checkov = programas.get("checkov", cfg.checkov)

    for nome in vars(cfg.tempos):
        if nome in tempos:
            setattr(cfg.tempos, nome, int(tempos[nome]))

    cfg.modo_deployability = str(deploy.get("modo", cfg.modo_deployability))
    cfg.regiao_padrao = str(deploy.get("regiao_padrao", cfg.regiao_padrao))
    cfg.endereco_moto = str(deploy.get("endereco_moto", cfg.endereco_moto))
    cfg.iniciar_moto_automaticamente = bool(
        deploy.get("iniciar_moto_automaticamente", cfg.iniciar_moto_automaticamente)
    )
    cfg.comando_moto = str(deploy.get("comando_moto", cfg.comando_moto))
    cfg.max_tentativas_aws = int(deploy.get("max_tentativas_aws", cfg.max_tentativas_aws))
    cfg.versao_provider_aws = str(deploy.get("versao_provider_aws", cfg.versao_provider_aws) or "")

    cfg.neutralizar_required_version_e_profile = bool(
        secao.get("neutralizar_required_version_e_profile", cfg.neutralizar_required_version_e_profile)
    )
    cfg.opa_exigir_pelo_menos_um_true = bool(
        opa.get("exigir_pelo_menos_um_true", cfg.opa_exigir_pelo_menos_um_true)
    )

    gravidades = tfl.get("gravidades_que_reprovam", cfg.tflint_gravidades_que_reprovam)
    cfg.tflint_gravidades_que_reprovam = [str(g).lower() for g in (gravidades or [])]

    pasta_cache = Path(secao.get("pasta_cache", "ferramentas/cache"))
    cfg.pasta_cache = pasta_cache if pasta_cache.is_absolute() else (pasta_projeto / pasta_cache)

    if cfg.modo_deployability not in ("moto", "sem_servidor"):
        raise ValueError(
            "verificadores.deployability.modo deve ser 'moto' ou 'sem_servidor' "
            "(valor atual: {})".format(cfg.modo_deployability)
        )
    return cfg
