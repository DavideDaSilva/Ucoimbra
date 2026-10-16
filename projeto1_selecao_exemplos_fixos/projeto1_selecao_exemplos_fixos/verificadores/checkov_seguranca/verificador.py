"""
Checkov  ->  SECURITY COMPLIANCE

O que e verificado:
  O codigo tem configuracoes inseguras? O Checkov aplica centenas de regras de
  seguranca (ex.: "o bucket S3 esta criptografado?", "o log esta ligado?").
  Cada regra aplicavel ao codigo resulta em "passed" (aprovada) ou "failed"
  (reprovada).

Quando roda:
  Sempre que existe HCL extraido, MESMO que o codigo nao compile
  (roda "em paralelo" a escada, como na Figure 3).

Comando executado (numa pasta separada, apenas com o main.tf):
  checkov -d . --framework terraform -o json --skip-download

Nota por cenario (valor continuo de 0 a 1):
  security = passed / (passed + failed)
  Exemplo: 1 aprovada e 2 reprovadas -> 1 / (1 + 2) = 0,3333 (33,33%).
  Se o Checkov nao executar nenhuma regra (passed + failed = 0), a nota e 0,
  porque nao ha nenhuma evidencia de conformidade.

Status (para os arquivos pass.txt e fail.txt):
  PASS se nenhuma regra foi reprovada (failed = 0) e pelo menos uma foi aprovada.
  FAIL caso contrario. A nota continua aparece no detalhe.

Arquivos salvos na pasta de registro desta etapa:
  main.tf, saida_checkov.txt, resumo_checkov.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.comum.resultado_verificacao import FAIL, PASS, ResultadoVerificacao

NOME_COMANDO = "checkov"


def verificar(hcl: str, pasta_registro: Path, cfg: ConfiguracaoVerificadores) -> ResultadoVerificacao:
    pasta_registro.mkdir(parents=True, exist_ok=True)
    (pasta_registro / "main.tf").write_text(hcl, encoding="utf-8")

    resultado = executar(
        [cfg.checkov, "-d", ".", "--framework", "terraform", "-o", "json", "--skip-download"],
        pasta_registro,
        cfg.tempos.checkov,
        {"CHECKOV_RUN_SCA_PACKAGE_SCAN_V2": "false", "BC_SKIP_MAPPING": "TRUE"},
    )
    texto = resultado.como_texto()
    (pasta_registro / "saida_checkov.txt").write_text(texto, encoding="utf-8")

    if resultado.erro_execucao or resultado.estourou_tempo:
        motivo = resultado.erro_execucao or "checkov excedeu o tempo limite"
        return ResultadoVerificacao(comando=NOME_COMANDO, status=FAIL, valor=0.0, motivo=motivo,
                                    detalhes={"erro_do_verificador": True})

    blocos = _ler_json(resultado.stdout)
    aprovadas: List[str] = []
    reprovadas: List[str] = []
    erros_leitura = 0
    for bloco in blocos:
        resultados = bloco.get("results", {}) or {}
        aprovadas += [c.get("check_id") for c in resultados.get("passed_checks", [])]
        reprovadas += [c.get("check_id") for c in resultados.get("failed_checks", [])]
        erros_leitura += int((bloco.get("summary", {}) or {}).get("parsing_errors", 0) or 0)

    passed, failed = len(aprovadas), len(reprovadas)
    total = passed + failed
    nota = passed / total if total else 0.0

    resumo = {
        "passed": passed,
        "failed": failed,
        "nota": nota,
        "formula": "passed / (passed + failed) = {} / ({} + {})".format(passed, passed, failed),
        "checks_aprovados": aprovadas,
        "checks_reprovados": reprovadas,
        "erros_de_leitura_do_codigo": erros_leitura,
    }
    (pasta_registro / "resumo_checkov.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if total == 0:
        motivo = "Checkov nao executou nenhuma regra (codigo sem recursos ou ilegivel); nota 0"
        status = FAIL
    elif failed == 0:
        motivo = "todas as {} regras de seguranca aprovadas (nota {:.4f})".format(passed, nota)
        status = PASS
    else:
        motivo = "{} aprovadas, {} reprovadas (nota {:.4f}); reprovadas: {}".format(
            passed, failed, nota, ", ".join(sorted(set(reprovadas)))
        )
        status = FAIL
    return ResultadoVerificacao(
        comando=NOME_COMANDO, status=status, valor=nota, motivo=motivo,
        detalhes={"passed": passed, "failed": failed, "erros_de_leitura_do_codigo": erros_leitura},
    )


def _ler_json(stdout: str) -> List[Dict[str, Any]]:
    """O Checkov devolve um objeto JSON (1 framework) ou uma lista (varios)."""
    texto = (stdout or "").strip()
    if not texto:
        return []
    inicio = min([p for p in (texto.find("{"), texto.find("[")) if p >= 0], default=-1)
    if inicio < 0:
        return []
    try:
        dados = json.loads(texto[inicio:])
    except ValueError:
        return []
    if isinstance(dados, dict):
        return [dados]
    if isinstance(dados, list):
        return [d for d in dados if isinstance(d, dict)]
    return []
