"""
Le o arquivo configuracao.yaml e organiza os caminhos das pastas de resultado.

Estrutura das pastas de resultado (tudo dentro de "resultados/"):

  resultados/
    cenarios_selecionados.csv / .json     lista dos 30 cenarios avaliados
    setting_A/                            Setting A (Prompt-only)
      qwen2.5-coder_7b/                   um modelo (":" vira "_" no nome da pasta)
        pass.txt  fail.txt                registros PASS/FAIL deste modelo
        por_comando/1_terraform_validate/pass.txt ... (um par por comando)
        linha_0012/                       um cenario (linha 12 do dataset)
          prompt_enviado.txt              texto exato enviado ao modelo
          resposta_bruta.txt              resposta completa do modelo
          hcl_extraido.tf                 codigo extraido (se houver)
          geracao.json                    dados da geracao (tempo, tokens...)
          avaliacao/                      saidas dos 5 verificadores
          resultado.json                  as 5 metricas deste cenario
    setting_B/                            mesma estrutura, Setting B (Prompt + Intent)
    tabela/                               tabelas finais e calculos
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

from verificadores.comum.configuracao_verificadores import (
    ConfiguracaoVerificadores,
    carregar_configuracao_verificadores,
)


@dataclass
class Modelo:
    nome: str          # nome exatamente como aparece em `ollama list`
    parametros: str    # texto que vai na coluna #Params da tabela


@dataclass
class Projeto:
    pasta: Path
    bruto: Dict[str, Any]
    verificadores: ConfiguracaoVerificadores
    modelos: List[Modelo] = field(default_factory=list)

    # ---------------- atalhos para a configuracao ----------------
    @property
    def settings(self) -> List[str]:
        return [str(s).upper() for s in self.bruto.get("settings", ["A", "B"])]

    @property
    def pasta_resultados(self) -> Path:
        return self.pasta / self.bruto.get("pasta_resultados", "resultados")

    @property
    def arquivo_exemplos_fixos(self) -> Path:
        caminho = Path(self.bruto.get("exemplos_fixos", {}).get("arquivo", "entrada/exemplos_fixos.json"))
        return caminho if caminho.is_absolute() else self.pasta / caminho

    @property
    def ollama(self) -> Dict[str, Any]:
        return self.bruto.get("ollama", {}) or {}

    @property
    def usar_bloco_de_codigo_sem_tags(self) -> bool:
        return bool((self.bruto.get("extracao", {}) or {}).get("usar_bloco_de_codigo_sem_tags", False))

    # ---------------- caminhos ----------------
    @staticmethod
    def nome_de_pasta(modelo: str) -> str:
        """'qwen2.5-coder:7b' -> 'qwen2.5-coder_7b' (':' nao e permitido no Windows)."""
        return modelo.replace(":", "_").replace("/", "_").replace("\\", "_")

    def pasta_modelo(self, setting: str, modelo: str) -> Path:
        return self.pasta_resultados / "setting_{}".format(setting) / self.nome_de_pasta(modelo)

    def pasta_cenario(self, setting: str, modelo: str, linha: int) -> Path:
        return self.pasta_modelo(setting, modelo) / "linha_{:04d}".format(int(linha))

    @property
    def pasta_tabela(self) -> Path:
        return self.pasta_resultados / "tabela"


def carregar_projeto(pasta: Path, arquivo_config: str) -> Projeto:
    caminho = (pasta / arquivo_config).resolve()
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    verificadores = carregar_configuracao_verificadores(bruto.get("verificadores", {}), pasta)
    modelos = []
    for item in bruto.get("modelos", []) or []:
        if isinstance(item, str):
            modelos.append(Modelo(nome=item, parametros=""))
        else:
            modelos.append(Modelo(nome=str(item["nome"]), parametros=str(item.get("parametros", ""))))
    if not modelos:
        raise ValueError("Nenhum modelo listado em 'modelos' no configuracao.yaml")
    for setting in bruto.get("settings", ["A", "B"]):
        if str(setting).upper() not in ("A", "B"):
            raise ValueError("settings so pode conter 'A' e/ou 'B'")
    return Projeto(pasta=pasta, bruto=bruto, verificadores=verificadores, modelos=modelos)
