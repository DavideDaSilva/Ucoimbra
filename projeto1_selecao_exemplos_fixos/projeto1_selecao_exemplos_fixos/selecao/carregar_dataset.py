"""
Carrega o dataset IaC-Eval (458 cenarios AWS).

O dataset pode vir de 4 lugares (escolha no configuracao.yaml, campo "dataset.origem"):

  1. "huggingface"        -> baixa direto do Hugging Face (autoiac-project/iac-eval,
                             split "test"). E o mesmo dado usado pelo IaC-Eval original.
                             Precisa de internet e do pacote "datasets".
  2. caminho para .csv    -> arquivo CSV com as colunas do IaC-Eval.
  3. caminho para .ods    -> planilha do LibreOffice (como a que voce enviou).
  4. caminho para .xlsx   -> planilha do Excel.

Colunas esperadas (nomes exatamente iguais ao IaC-Eval):
  Resource, Prompt, Rego intent, Difficulty, Reference output, Intent

ATENCAO (problema real encontrado e resolvido aqui):
  O leitor de .ods padrao do pandas JUNTA as linhas de cada celula sem a quebra
  de linha. Isso destroi o codigo Rego e o codigo Terraform (eles deixam de ser
  validos). Por isso este arquivo tem um leitor de .ods proprio, que preserva
  as quebras de linha, os espacos e as tabulacoes de cada celula.

Numeracao das linhas ("linha"):
  Usamos a mesma numeracao dos slides: a primeira linha de dados e a linha 0.
  Exemplo: linha 2 = "Set up an aws_route_53 zone named example53.com".
  Tambem guardamos "linha_na_planilha" = linha + 2 (porque na planilha a linha 1
  e o cabecalho e a contagem comeca em 1).
"""

from __future__ import annotations

import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

COLUNAS_IAC_EVAL = [
    "Resource",
    "Prompt",
    "Rego intent",
    "Difficulty",
    "Reference output",
    "Intent",
]

NOME_DATASET_HUGGINGFACE = "autoiac-project/iac-eval"


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------
def carregar_dataset(origem: str, pasta_base: Path, aba_planilha: str = "dataset") -> List[Dict]:
    """
    Devolve uma lista de cenarios. Cada cenario e um dicionario com as colunas
    do IaC-Eval e mais dois campos: "linha" e "linha_na_planilha".
    """
    if str(origem).strip().lower() == "huggingface":
        linhas = _ler_huggingface()
    else:
        caminho = Path(origem)
        if not caminho.is_absolute():
            caminho = (pasta_base / caminho).resolve()
        if not caminho.exists():
            raise FileNotFoundError(
                "Arquivo do dataset nao encontrado: {}\n"
                "Ajuste 'dataset.origem' no configuracao.yaml.".format(caminho)
            )
        sufixo = caminho.suffix.lower()
        if sufixo == ".csv":
            linhas = _ler_csv(caminho)
        elif sufixo == ".ods":
            linhas = _ler_ods(caminho, aba_planilha)
        elif sufixo in (".xlsx", ".xlsm"):
            linhas = _ler_xlsx(caminho, aba_planilha)
        else:
            raise ValueError("Formato de dataset nao suportado: " + sufixo)

    cenarios = []
    for indice, linha in enumerate(linhas):
        cenario = {coluna: _limpar(linha.get(coluna, "")) for coluna in COLUNAS_IAC_EVAL}
        cenario["Difficulty"] = _para_inteiro(cenario["Difficulty"])
        cenario["linha"] = indice
        cenario["linha_na_planilha"] = indice + 2
        cenarios.append(cenario)

    if not cenarios:
        raise ValueError("O dataset foi lido, mas esta vazio.")
    return cenarios


# ---------------------------------------------------------------------------
# Leitores de cada formato
# ---------------------------------------------------------------------------
def _ler_huggingface() -> List[Dict]:
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as erro:
        raise ImportError(
            "Para baixar do Hugging Face instale o pacote: pip install datasets"
        ) from erro
    dados = load_dataset(NOME_DATASET_HUGGINGFACE, split="test")
    return [dict(linha) for linha in dados]


def _ler_csv(caminho: Path) -> List[Dict]:
    import pandas as pd

    tabela = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    _conferir_colunas(list(tabela.columns), caminho)
    return tabela.to_dict(orient="records")


def _ler_xlsx(caminho: Path, aba: str) -> List[Dict]:
    import pandas as pd

    abas = pd.read_excel(caminho, sheet_name=None, dtype=str, engine="openpyxl")
    tabela = abas.get(aba)
    if tabela is None:
        tabela = _primeira_aba_com_colunas(abas)
    _conferir_colunas(list(tabela.columns), caminho)
    return tabela.fillna("").to_dict(orient="records")


def _ler_ods(caminho: Path, aba: str) -> List[Dict]:
    """Leitor de .ods que preserva quebras de linha, espacos e tabulacoes."""
    ns = {
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    }
    with zipfile.ZipFile(caminho) as arquivo_zip:
        raiz = ET.fromstring(arquivo_zip.read("content.xml"))

    tabelas = raiz.findall(".//table:table", ns)
    escolhida = None
    for tabela in tabelas:
        if tabela.get("{%s}name" % ns["table"]) == aba:
            escolhida = tabela
            break
    linhas_por_tabela = []
    if escolhida is not None:
        linhas_por_tabela.append(_linhas_da_tabela_ods(escolhida, ns))
    else:
        linhas_por_tabela = [_linhas_da_tabela_ods(t, ns) for t in tabelas]

    for linhas in linhas_por_tabela:
        if linhas and all(c in linhas[0] for c in COLUNAS_IAC_EVAL):
            cabecalho = linhas[0]
            registros = []
            for valores in linhas[1:]:
                if not any(v.strip() for v in valores):
                    continue  # pula linhas vazias
                registro = {}
                for posicao, nome in enumerate(cabecalho):
                    if nome:
                        registro[nome] = valores[posicao] if posicao < len(valores) else ""
                registros.append(registro)
            return registros
    raise ValueError(
        "Nenhuma aba do arquivo {} tem as colunas {}".format(caminho, COLUNAS_IAC_EVAL)
    )


def _linhas_da_tabela_ods(tabela, ns, max_colunas: int = 30) -> List[List[str]]:
    t = "{%s}" % ns["table"]
    linhas = []
    for linha in tabela.iter(t + "table-row"):
        valores: List[str] = []
        for celula in linha:
            if celula.tag not in (t + "table-cell", t + "covered-table-cell"):
                continue
            repeticoes = int(celula.get(t + "number-columns-repeated", "1"))
            texto = _texto_da_celula_ods(celula, ns)
            for _ in range(min(repeticoes, max_colunas)):
                valores.append(texto)
            if len(valores) >= max_colunas:
                break
        linhas.append(valores)
    return linhas


def _texto_da_celula_ods(celula, ns) -> str:
    office = "{%s}" % ns["office"]
    tx = "{%s}" % ns["text"]
    tipo = celula.get(office + "value-type")
    if tipo in ("float", "percentage", "currency"):
        valor = celula.get(office + "value", "")
        if valor.endswith(".0"):
            valor = valor[:-2]
        return valor
    paragrafos = []
    for filho in celula:
        if filho.tag in (tx + "p", tx + "h"):
            paragrafos.append(_texto_do_elemento_ods(filho, tx))
    return "\n".join(paragrafos)


def _texto_do_elemento_ods(elemento, tx: str) -> str:
    partes = [elemento.text or ""]
    for filho in elemento:
        if filho.tag == tx + "s":
            partes.append(" " * int(filho.get(tx + "c", "1")))
        elif filho.tag == tx + "tab":
            partes.append("\t")
        elif filho.tag == tx + "line-break":
            partes.append("\n")
        else:
            partes.append(_texto_do_elemento_ods(filho, tx))
        partes.append(filho.tail or "")
    return "".join(partes)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _primeira_aba_com_colunas(abas):
    for tabela in abas.values():
        if all(c in tabela.columns for c in COLUNAS_IAC_EVAL):
            return tabela
    raise ValueError("Nenhuma aba tem as colunas " + str(COLUNAS_IAC_EVAL))


def _conferir_colunas(colunas: List[str], caminho: Path) -> None:
    faltando = [c for c in COLUNAS_IAC_EVAL if c not in colunas]
    if faltando:
        raise ValueError("O arquivo {} nao tem as colunas: {}".format(caminho, faltando))


def _limpar(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and math.isnan(valor):
        return ""
    texto = str(valor).replace("\r\n", "\n").replace("\r", "\n")
    return texto.strip("\n") if texto.strip() else ""


def _para_inteiro(valor: str) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return 0
