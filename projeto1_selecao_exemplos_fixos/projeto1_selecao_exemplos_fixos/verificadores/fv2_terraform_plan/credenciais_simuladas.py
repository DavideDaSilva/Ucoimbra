"""
Credenciais AWS SIMULADAS para rodar `terraform plan` sem conta AWS e sem pagar nada.

Por que isso e necessario?
  O `terraform plan` do provider AWS normalmente:
    (a) confere se as credenciais sao validas (chamada ao servico STS da AWS);
    (b) descobre o numero da conta;
    (c) para blocos `data "aws_..."` (ex.: aws_ami, aws_availability_zones),
        CONSULTA a AWS de verdade.
  Sem credenciais validas, tudo isso falha.

Como resolvemos (sem criar nenhum recurso e sem custo):
  1. Colocamos ao lado do main.tf um arquivo extra que da ao provider AWS
     credenciais falsas ("mock") e manda ele PULAR as conferencias (a) e (b).
     Esse arquivo usa o recurso oficial de "override files" do Terraform
     (arquivos terminados em _override.tf), que sobrepoe apenas os campos
     listados, sem mexer no codigo gerado pelo modelo.
  2. Modo "moto" (padrao): todas as chamadas a AWS sao enviadas para o
     "moto_server", um SIMULADOR GRATUITO da AWS que roda no seu computador
     (http://127.0.0.1:5555). Ele responde perguntas como "quais zonas de
     disponibilidade existem?" ou "qual AMI do Amazon Linux mais recente?".
     Assim os blocos `data` tambem funcionam.
     Modo "sem_servidor": apenas as credenciais falsas. Codigo com blocos
     `data` que consultam a AWS vai falhar no plan (limitacao conhecida).

  O comando `terraform apply` NUNCA e executado. Nada e criado em nuvem nenhuma.

Arquivos que podem ser criados na pasta de trabalho do Terraform:
  * zz_avaliacao_credenciais_simuladas_override.tf
        sobrepoe cada bloco provider "aws" que o modelo escreveu.
  * zz_avaliacao_provider_padrao.tf
        criado SOMENTE quando o codigo nao tem nenhum provider "aws" sem alias
        (o Terraform usaria um provider implicito, sem credenciais).
  * zz_avaliacao_versao_provider.tf
        fixa a versao do provider AWS (padrao "~> 5.0") SOMENTE quando o codigo
        nao declara "required_providers". O IaC-Eval foi escrito para a serie 5.x.
  * zz_avaliacao_versao_terraform_override.tf  e  profile = null
        SOMENTE se a opcao "neutralizar_required_version_e_profile" estiver ligada.
        Motivo: 205 dos 458 Reference outputs do IaC-Eval tem, ao mesmo tempo,
          required_version = "~> 1.9.8"  (so aceita Terraform 1.9.x; o Terraform
                                         1.12.0 do paper recusa no init) e
          profile = "admin-1"            (perfil AWS do computador dos autores
                                         do IaC-Eval; nao existe no seu).
        Com a opcao ligada, a exigencia de versao vira ">= 1.0.0" e o profile e
        anulado (profile = null) no arquivo de sobreposicao.
        Padrao: DESLIGADA. O template do TerraFormer pede compatibilidade com
        Terraform 1.12.0 e proibe "profile", entao, para avaliar modelos e para
        escolher exemplos fixos, esses codigos devem continuar falhando.
        (Sera util no Projeto 3, que testa os proprios Reference outputs.)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

PREFIXO_ARQUIVOS = "zz_avaliacao_"

_INICIO_PROVIDER_AWS = re.compile(r'(^|\n)\s*provider\s+"?aws"?\s*\{')
_ALIAS = re.compile(r'^\s*alias\s*=\s*"([^"]+)"', re.MULTILINE)


def atributos_simulados(max_tentativas: int) -> List[str]:
    """Linhas HCL com as credenciais falsas e os 'pule a verificacao'."""
    return [
        '  access_key                  = "mock_access_key"',
        '  secret_key                  = "mock_secret_key"',
        "  skip_credentials_validation = true",
        "  skip_requesting_account_id  = true",
        "  skip_metadata_api_check     = true",
        "  skip_region_validation      = true",
        "  max_retries                 = {}".format(int(max_tentativas)),
    ]


def encontrar_aliases_provider_aws(hcl: str) -> List[Optional[str]]:
    """
    Procura todos os blocos `provider "aws" { ... }` no codigo.
    Devolve uma lista com o alias de cada bloco (None = bloco sem alias).
    """
    sem_comentarios = _remover_comentarios(hcl)
    aliases: List[Optional[str]] = []
    for achado in _INICIO_PROVIDER_AWS.finditer(sem_comentarios):
        inicio_corpo = achado.end()
        corpo = _corpo_ate_chave_final(sem_comentarios, inicio_corpo)
        alias = _alias_no_nivel_superior(corpo)
        aliases.append(alias)
    return aliases


def preparar_pasta_terraform(
    pasta: Path,
    hcl: str,
    regiao_padrao: str,
    max_tentativas: int,
    versao_provider_aws: str,
    neutralizar_required_version_e_profile: bool = False,
) -> Dict[str, str]:
    """
    Escreve main.tf e os arquivos auxiliares na pasta de trabalho.
    Devolve {nome_do_arquivo: conteudo} dos arquivos auxiliares criados,
    para que fique registrado exatamente o que foi acrescentado.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "main.tf").write_text(hcl, encoding="utf-8")
    criados: Dict[str, str] = {}

    aliases = encontrar_aliases_provider_aws(hcl)
    atributos = atributos_simulados(max_tentativas)
    if neutralizar_required_version_e_profile and re.search(r"\bprofile\s*=", _remover_comentarios(hcl)):
        atributos.append("  profile                     = null")

    # 1) Override para cada bloco provider "aws" escrito pelo modelo.
    if aliases:
        blocos = []
        for alias in aliases:
            linhas = ['provider "aws" {']
            if alias:
                linhas.append('  alias                       = "{}"'.format(alias))
            linhas += atributos
            linhas.append("}")
            blocos.append("\n".join(linhas))
        conteudo = (
            "# Arquivo criado AUTOMATICAMENTE pela avaliacao (nao faz parte da resposta do modelo).\n"
            "# Sobrepoe somente as credenciais: credenciais falsas + pular verificacoes.\n\n"
            + "\n\n".join(blocos)
            + "\n"
        )
        nome = PREFIXO_ARQUIVOS + "credenciais_simuladas_override.tf"
        (pasta / nome).write_text(conteudo, encoding="utf-8")
        criados[nome] = conteudo

    # 2) Provider padrao, caso o modelo nao tenha escrito um provider "aws" sem alias.
    if None not in aliases:
        linhas = ['provider "aws" {', '  region                      = "{}"'.format(regiao_padrao)]
        linhas += atributos
        linhas.append("}")
        conteudo = (
            "# Arquivo criado AUTOMATICAMENTE pela avaliacao (nao faz parte da resposta do modelo).\n"
            "# O codigo nao tinha um bloco provider \"aws\" padrao; este bloco usa credenciais falsas.\n\n"
            + "\n".join(linhas)
            + "\n"
        )
        nome = PREFIXO_ARQUIVOS + "provider_padrao.tf"
        (pasta / nome).write_text(conteudo, encoding="utf-8")
        criados[nome] = conteudo

    # 3) Versao do provider AWS (somente se o codigo nao declarou required_providers).
    if versao_provider_aws and "required_providers" not in _remover_comentarios(hcl):
        conteudo = (
            "# Arquivo criado AUTOMATICAMENTE pela avaliacao (nao faz parte da resposta do modelo).\n"
            "# O codigo nao declarou required_providers; fixamos a serie do provider AWS\n"
            "# para que todos os testes usem a mesma versao.\n\n"
            "terraform {\n"
            "  required_providers {\n"
            "    aws = {\n"
            '      source  = "hashicorp/aws"\n'
            '      version = "' + versao_provider_aws + '"\n'
            "    }\n"
            "  }\n"
            "}\n"
        )
        nome = PREFIXO_ARQUIVOS + "versao_provider.tf"
        (pasta / nome).write_text(conteudo, encoding="utf-8")
        criados[nome] = conteudo

    # 4) Exigencia de versao do Terraform (somente se a opcao estiver ligada).
    if neutralizar_required_version_e_profile and re.search(r"\brequired_version\s*=", _remover_comentarios(hcl)):
        conteudo = (
            "# Arquivo criado AUTOMATICAMENTE pela avaliacao (nao faz parte da resposta do modelo).\n"
            "# Opcao neutralizar_required_version_e_profile ligada: aceita qualquer Terraform >= 1.0.0.\n\n"
            "terraform {\n"
            '  required_version = ">= 1.0.0"\n'
            "}\n"
        )
        nome = PREFIXO_ARQUIVOS + "versao_terraform_override.tf"
        (pasta / nome).write_text(conteudo, encoding="utf-8")
        criados[nome] = conteudo

    return criados


def variaveis_de_ambiente(modo: str, regiao_padrao: str, endereco_moto: str) -> Dict[str, str]:
    """Variaveis de ambiente usadas no init/validate/plan."""
    variaveis = {
        "AWS_REGION": regiao_padrao,
        "AWS_DEFAULT_REGION": regiao_padrao,
        "AWS_ACCESS_KEY_ID": "mock_access_key",
        "AWS_SECRET_ACCESS_KEY": "mock_secret_key",
        "AWS_EC2_METADATA_DISABLED": "true",
    }
    if modo == "moto":
        # Envia TODAS as chamadas a AWS para o simulador local.
        variaveis["AWS_ENDPOINT_URL"] = endereco_moto
    return variaveis


# ---------------------------------------------------------------------------
# Funcoes auxiliares de leitura do HCL (simples, sem dependencias externas)
# ---------------------------------------------------------------------------
def _remover_comentarios(hcl: str) -> str:
    """Remove comentarios (#, //, /* */) fora de strings."""
    resultado = []
    i, n = 0, len(hcl)
    em_string = False
    while i < n:
        c = hcl[i]
        if em_string:
            resultado.append(c)
            if c == "\\" and i + 1 < n:
                resultado.append(hcl[i + 1])
                i += 2
                continue
            if c == '"':
                em_string = False
            i += 1
            continue
        if c == '"':
            em_string = True
            resultado.append(c)
            i += 1
        elif c == "#" or hcl.startswith("//", i):
            fim = hcl.find("\n", i)
            i = n if fim == -1 else fim
        elif hcl.startswith("/*", i):
            fim = hcl.find("*/", i + 2)
            i = n if fim == -1 else fim + 2
        else:
            resultado.append(c)
            i += 1
    return "".join(resultado)


def _corpo_ate_chave_final(texto: str, inicio: int) -> str:
    """Devolve o conteudo entre a '{' ja aberta e a '}' correspondente."""
    profundidade = 1
    i = inicio
    em_string = False
    while i < len(texto):
        c = texto[i]
        if em_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                em_string = False
        elif c == '"':
            em_string = True
        elif c == "{":
            profundidade += 1
        elif c == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:i]
        i += 1
    return texto[inicio:]


def _alias_no_nivel_superior(corpo: str) -> Optional[str]:
    """Procura 'alias = "..."' apenas no nivel superior do bloco provider."""
    nivel_superior = []
    profundidade = 0
    for linha in corpo.splitlines():
        if profundidade == 0:
            nivel_superior.append(linha)
        profundidade += linha.count("{") - linha.count("}")
        profundidade = max(profundidade, 0)
    achado = _ALIAS.search("\n".join(nivel_superior))
    return achado.group(1) if achado else None
