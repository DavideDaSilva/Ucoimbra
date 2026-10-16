"""
FV-ii  terraform plan  ->  DEPLOYABILITY

O que e verificado:
  O Terraform consegue montar um "plano de execucao" valido para a AWS?
  (ou seja: se fossemos criar a infraestrutura, o Terraform saberia o que fazer)
  Nada e criado: o `terraform apply` NUNCA e executado.

Pre-requisito:
  So roda se o terraform validate (FV-i) passou. Se nao passou, esta etapa
  recebe NAO_EXECUTADO (valor 0), conforme as setas vermelhas da Figure 3.

Credenciais:
  Usa credenciais FALSAS e, no modo "moto", um simulador local da AWS.
  Veja credenciais_simuladas.py nesta mesma pasta.

Comandos executados:
  1. terraform plan -input=false -lock=false -no-color -out=plan.bin
       (tempo limite padrao: 120 s, como na Figure 3)
  2. terraform show -json plan.bin   ->  plan.json
       O plan.json e o arquivo que o OPA (FV-iii) vai analisar.

Resultado:
  PASS (valor 1) se o plan terminar com codigo 0.
  FAIL (valor 0) caso contrario.

Arquivos salvos na pasta de registro desta etapa:
  saida_terraform_plan.txt
  saida_terraform_show.txt
  plan.json   (copia do plano em JSON, usado pelo OPA)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from verificadores.comum.configuracao_verificadores import ConfiguracaoVerificadores
from verificadores.comum.executar_comando import executar
from verificadores.comum.resultado_verificacao import FAIL, PASS, ResultadoVerificacao

NOME_COMANDO = "terraform plan"


def verificar(
    pasta_terraform: Path,
    pasta_registro: Path,
    cfg: ConfiguracaoVerificadores,
    variaveis: Dict[str, str],
) -> Tuple[ResultadoVerificacao, Optional[Path]]:
    """Devolve (resultado, caminho_do_plan_json ou None)."""
    pasta_registro.mkdir(parents=True, exist_ok=True)
    ambiente = dict(cfg.variaveis_terraform())
    ambiente.update(variaveis)

    plan = executar(
        [cfg.terraform, "plan", "-input=false", "-lock=false", "-no-color", "-out=plan.bin"],
        pasta_terraform,
        cfg.tempos.terraform_plan,
        ambiente,
    )
    (pasta_registro / "saida_terraform_plan.txt").write_text(plan.como_texto(), encoding="utf-8")

    if not plan.sucesso:
        if plan.erro_execucao:
            motivo = "terraform plan: " + plan.erro_execucao
        elif plan.estourou_tempo:
            motivo = "terraform plan excedeu o tempo limite de {} s".format(cfg.tempos.terraform_plan)
        else:
            motivo = "terraform plan falhou (codigo {}): {}".format(
                plan.codigo_saida, _primeira_linha_de_erro(plan.stderr or plan.stdout)
            )
        return (
            ResultadoVerificacao(
                comando=NOME_COMANDO,
                status=FAIL,
                valor=0,
                motivo=motivo,
                detalhes={"codigo_saida": plan.codigo_saida, "estourou_tempo": plan.estourou_tempo},
            ),
            None,
        )

    # Converte o plano para JSON (necessario para o OPA).
    show = executar(
        [cfg.terraform, "show", "-json", "-no-color", "plan.bin"],
        pasta_terraform,
        cfg.tempos.terraform_show,
        ambiente,
    )
    caminho_json: Optional[Path] = None
    texto_show = show.como_texto()
    if show.sucesso and show.stdout.strip().startswith("{"):
        caminho_json = pasta_registro / "plan.json"
        caminho_json.write_text(show.stdout, encoding="utf-8")
        texto_show = texto_show.replace(show.stdout, "(conteudo salvo em plan.json)")
    (pasta_registro / "saida_terraform_show.txt").write_text(texto_show, encoding="utf-8")

    return (
        ResultadoVerificacao(
            comando=NOME_COMANDO,
            status=PASS,
            valor=1,
            motivo="terraform plan gerou um plano de execucao valido (nada foi criado)",
            detalhes={
                "codigo_saida": plan.codigo_saida,
                "plan_json_gerado": caminho_json is not None,
            },
        ),
        caminho_json,
    )


def _primeira_linha_de_erro(texto: str) -> str:
    for linha in texto.splitlines():
        if "Error" in linha:
            return linha.strip()[:300]
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    return linhas[0][:300] if linhas else "(sem mensagem)"
