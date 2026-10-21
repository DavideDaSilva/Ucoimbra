"""
TFLint (+ regras AWS)  ->  LINTER PASS RATE

O que e verificado:
  O codigo segue as "boas praticas" do Terraform e da AWS?
  Exemplos de problemas: tipo de instancia EC2 que nao existe, variavel
  declarada sem tipo, versao do provider nao fixada, etc.

Quando roda:
  Sempre que existe HCL extraido, MESMO que o codigo nao compile
  (roda "em paralelo" a escada, como na Figure 3).

Como roda:
  O main.tf e copiado para uma pasta separada (sem os arquivos de credenciais
  simuladas, para nao influenciar o resultado), junto com o arquivo de regras
  .tflint.hcl desta pasta. Depois:
     tflint --format=json --no-color

  Na primeira vez e preciso baixar o plugin de regras AWS:
     tflint --init     (feito automaticamente por preparar_tflint())

Resultado:
  PASS (valor 1) se o TFLint rodar e NAO reportar nenhum problema com uma das
                  gravidades listadas em "tflint.gravidades_que_reprovam" do
                  configuracao.yaml (padrao: somente "error").
  FAIL (valor 0) se reportar 1 ou mais desses problemas, ou se nao conseguir
                  ler o codigo.

  Por que o padrao e somente "error"? (decisao baseada em dados)
    O TFLint tem 3 gravidades: error, warning e info. Medimos os 458
    "Reference output" do IaC-Eval (codigo escrito por humanos e correto):
      * contando qualquer gravidade: apenas 150 de 458 passam (32,8%),
        quase sempre por avisos (warning) do tipo "faltou fixar a versao do
        Terraform/provider" (terraform_required_version / _providers);
      * contando somente "error": 450 de 458 passam (98,3%).
    No paper do TerraFormer (Table 2) quase todos os modelos tem Linter Pass
    Rate entre 90% e 100%, o que so e compativel com a segunda forma.
    Para usar a forma mais rigorosa, coloque ["error", "warning", "info"].
    Todos os problemas (de qualquer gravidade) ficam salvos em
    problemas_tflint.json para consulta.

Arquivos salvos na pasta de registro desta etapa:
  main.tf, .tflint.hcl, saida_tflint.txt, problemas_tflint.json
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.comum.resultado_verificacao import FAIL, PASS, ResultadoVerificacao

NOME_COMANDO = "tflint"
ARQUIVO_REGRAS = Path(__file__).resolve().parent / ".tflint.hcl"


def _variaveis(cfg: ConfiguracaoVerificadores):
    cfg.pasta_plugins_tflint.mkdir(parents=True, exist_ok=True)
    return {"TFLINT_PLUGIN_DIR": str(cfg.pasta_plugins_tflint.resolve())}


def preparar_tflint(cfg: ConfiguracaoVerificadores, pasta_temporaria: Path):
    """Executa `tflint --init` uma unica vez para baixar o plugin AWS."""
    pasta_temporaria.mkdir(parents=True, exist_ok=True)
    shutil.copy(ARQUIVO_REGRAS, pasta_temporaria / ".tflint.hcl")
    return executar([cfg.tflint, "--init"], pasta_temporaria, 600, _variaveis(cfg))


def verificar(hcl: str, pasta_registro: Path, cfg: ConfiguracaoVerificadores) -> ResultadoVerificacao:
    pasta_registro.mkdir(parents=True, exist_ok=True)
    (pasta_registro / "main.tf").write_text(hcl, encoding="utf-8")
    shutil.copy(ARQUIVO_REGRAS, pasta_registro / ".tflint.hcl")

    resultado = executar(
        [cfg.tflint, "--format=json", "--no-color"],
        pasta_registro,
        cfg.tempos.tflint,
        _variaveis(cfg),
    )
    (pasta_registro / "saida_tflint.txt").write_text(resultado.como_texto(), encoding="utf-8")

    if resultado.erro_execucao or resultado.estourou_tempo:
        motivo = resultado.erro_execucao or "tflint excedeu o tempo limite"
        return ResultadoVerificacao(comando=NOME_COMANDO, status=FAIL, valor=0, motivo=motivo,
                                    detalhes={"erro_do_verificador": True})

    try:
        dados = json.loads(resultado.stdout or "{}")
    except ValueError:
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0,
            motivo="nao foi possivel ler a saida do TFLint (veja saida_tflint.txt)",
            detalhes={"codigo_saida": resultado.codigo_saida},
        )

    problemas = dados.get("issues") or []
    erros = dados.get("errors") or []
    resumo = [
        {
            "regra": p.get("rule", {}).get("name"),
            "gravidade": p.get("rule", {}).get("severity"),
            "mensagem": p.get("message"),
            "linha": (p.get("range") or {}).get("start", {}).get("line"),
        }
        for p in problemas
    ]
    (pasta_registro / "problemas_tflint.json").write_text(
        json.dumps({"problemas": resumo, "erros": erros}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if erros:
        mensagem = erros[0].get("message", "erro") if isinstance(erros[0], dict) else str(erros[0])
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0,
            motivo="TFLint nao conseguiu analisar o codigo: " + mensagem[:300],
            detalhes={"quantidade_problemas": len(problemas), "quantidade_erros": len(erros)},
        )
    gravidades = [g.lower() for g in cfg.tflint_gravidades_que_reprovam]
    reprovam = [r for r in resumo if str(r["gravidade"]).lower() in gravidades]
    ignorados = [r for r in resumo if str(r["gravidade"]).lower() not in gravidades]
    detalhes = {
        "quantidade_problemas_que_reprovam": len(reprovam),
        "quantidade_problemas_ignorados": len(ignorados),
        "gravidades_que_reprovam": gravidades,
        "regras_que_reprovaram": sorted({r["regra"] for r in reprovam if r["regra"]}),
        "regras_ignoradas": sorted({r["regra"] for r in ignorados if r["regra"]}),
    }
    if reprovam:
        return ResultadoVerificacao(
            comando=NOME_COMANDO, status=FAIL, valor=0,
            motivo="{} problema(s) com gravidade {}: {}".format(
                len(reprovam), "/".join(gravidades), ", ".join(detalhes["regras_que_reprovaram"])
            ),
            detalhes=detalhes,
        )
    texto_ignorados = ""
    if ignorados:
        texto_ignorados = " ({} aviso(s) de gravidade menor ignorado(s): {})".format(
            len(ignorados), ", ".join(detalhes["regras_ignoradas"])
        )
    return ResultadoVerificacao(
        comando=NOME_COMANDO, status=PASS, valor=1,
        motivo="TFLint nao reportou problema com gravidade " + "/".join(gravidades) + texto_ignorados,
        detalhes=detalhes,
    )
