"""
ETAPA 3: gera UMA resposta por (modelo, setting, cenario)  ->  protocolo pass@1.

Para cada combinacao:
  1. Monta o prompt (Etapa 2) e salva em prompt_enviado.txt.
  2. Envia ao modelo pelo Ollama e salva a resposta em resposta_bruta.txt.
  3. Extrai o HCL das tags <final_terraform_config> e salva em hcl_extraido.tf.
  4. Salva geracao.json com: modelo, setting, linha, opcoes usadas, tempo,
     quantidade de tokens, como o HCL foi extraido e alertas.

Retomada automatica:
  Se geracao.json ja existe, o cenario e pulado (a menos que use --refazer).
  Assim voce pode interromper (Ctrl+C) e continuar depois sem perder nada.

Ordem: modelo por modelo (o Ollama carrega cada modelo uma vez so).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Dict, List

from pipeline.configuracao import Projeto
from pipeline.etapa2_prompt_builder.montar_prompt import montar_prompt
from pipeline.etapa3_geracao.cliente_ollama import ClienteOllama, ErroOllama
from pipeline.etapa3_geracao.extrair_hcl import extrair_hcl

OPCOES_PADRAO = {
    "temperature": 0,
    "top_p": 0.9,
    "top_k": 40,
    "seed": 42,
    "num_predict": 4096,
    "num_ctx": 8192,
}


def criar_cliente(projeto: Projeto) -> ClienteOllama:
    o = projeto.ollama
    return ClienteOllama(
        url_base=o.get("url", "http://127.0.0.1:11434"),
        tempo_limite=int(o.get("tempo_limite_segundos", 1800)),
        keep_alive=str(o.get("keep_alive", "30m")),
        tentativas=int(o.get("tentativas_em_caso_de_erro", 3)),
    )


def opcoes_de_geracao(projeto: Projeto) -> Dict[str, Any]:
    opcoes = dict(OPCOES_PADRAO)
    opcoes.update(projeto.ollama.get("opcoes", {}) or {})
    return opcoes


def gerar_respostas(
    projeto: Projeto,
    cenarios: List[Dict[str, Any]],
    exemplos_fixos: List[Dict[str, Any]],
    modelos: List[str],
    settings: List[str],
    refazer: bool,
    log: Callable[[str], None],
) -> None:
    cliente = criar_cliente(projeto)
    instalados = cliente.modelos_instalados()
    opcoes = opcoes_de_geracao(projeto)
    log("Modelos instalados no Ollama: " + ", ".join(instalados))
    log("Opcoes de geracao: " + json.dumps(opcoes))

    for modelo in modelos:
        # "llama3.2" e "llama3.2:latest" sao o mesmo modelo para o Ollama.
        if modelo not in instalados and (":" in modelo or modelo + ":latest" not in instalados):
            log("AVISO: o modelo '{}' nao aparece em `ollama list`. Ele sera pulado. "
                "Baixe com: ollama pull {}".format(modelo, modelo))
            continue
        info_modelo = cliente.informacoes_do_modelo(modelo)

        for setting in settings:
            total = len(cenarios)
            for posicao, cenario in enumerate(cenarios, start=1):
                pasta = projeto.pasta_cenario(setting, modelo, cenario["linha"])
                arquivo_geracao = pasta / "geracao.json"
                if arquivo_geracao.exists() and not refazer:
                    continue
                pasta.mkdir(parents=True, exist_ok=True)
                for antigo in ("resultado.json", "hcl_extraido.tf", "erro_geracao.txt"):
                    (pasta / antigo).unlink(missing_ok=True)

                prompt, resumo_prompt = montar_prompt(cenario, exemplos_fixos, setting)
                (pasta / "prompt_enviado.txt").write_text(prompt, encoding="utf-8")

                log("[{}] setting {} | cenario {}/{} (linha {}, dificuldade {})".format(
                    modelo, setting, posicao, total, cenario["linha"], cenario["Difficulty"]))
                try:
                    gerado = cliente.gerar(modelo, prompt, opcoes)
                except ErroOllama as erro:
                    (pasta / "erro_geracao.txt").write_text(str(erro), encoding="utf-8")
                    log("   ERRO: {} (sera tentado de novo na proxima execucao)".format(erro))
                    continue

                resposta = gerado.pop("resposta")
                (pasta / "resposta_bruta.txt").write_text(resposta, encoding="utf-8")
                extracao = extrair_hcl(resposta, projeto.usar_bloco_de_codigo_sem_tags)
                if extracao["hcl"]:
                    (pasta / "hcl_extraido.tf").write_text(extracao["hcl"] + "\n", encoding="utf-8")

                alertas = []
                if gerado.get("motivo_fim") == "length":
                    alertas.append("resposta cortada: atingiu num_predict ({})".format(opcoes.get("num_predict")))
                tokens_prompt = gerado.get("tokens_prompt") or 0
                if tokens_prompt and tokens_prompt >= 0.98 * int(opcoes.get("num_ctx", 0) or 0):
                    alertas.append("o prompt pode ter sido cortado pelo Ollama: aumente num_ctx")

                registro = {
                    "modelo": modelo,
                    "informacoes_do_modelo": info_modelo,
                    "setting": setting,
                    "linha": cenario["linha"],
                    "dificuldade": cenario["Difficulty"],
                    "resource": cenario["Resource"],
                    "opcoes_de_geracao": opcoes,
                    "prompt": resumo_prompt,
                    "geracao": gerado,
                    "extracao": {
                        "metodo": extracao["metodo"],
                        "motivo": extracao["motivo"],
                        "hcl_extraido": extracao["hcl"] is not None,
                        "teria_hcl_pela_regra_alternativa": extracao["hcl_pela_regra_alternativa"] is not None,
                    },
                    "alertas": alertas,
                    "data_hora": datetime.now().isoformat(timespec="seconds"),
                }
                arquivo_geracao.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
                log("   {} em {} s | HCL: {}{}".format(
                    "ok", gerado.get("tempo_total_s"), extracao["metodo"],
                    (" | ALERTA: " + "; ".join(alertas)) if alertas else ""))
