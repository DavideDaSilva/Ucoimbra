# Instalação passo a passo

Faça isto **uma vez** por computador. Se você já instalou tudo para o Projeto 1, só falta o passo 6 (Ollama) e o passo 7.

Abra um terminal (no Windows: "PowerShell"; no macOS: "Terminal"; no Linux: o terminal da sua distribuição) e entre na pasta do projeto:

```bash
cd caminho/para/projeto2_avaliacao_llms
```

## 1. Python 3.10 ou mais novo

Confira com `python --version` (ou `python3 --version`). Se não tiver, baixe em https://www.python.org/downloads/ .

## 2. Ambiente virtual (recomendado)

Um "ambiente virtual" é uma pasta isolada com os pacotes do projeto, para não misturar com outros programas.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```
Sempre que abrir um terminal novo para usar o projeto, rode de novo a linha `activate`.

## 3. Pacotes Python

```bash
pip install -r requirements.txt
```
Isso instala, entre outros, o **Checkov** (Security Compliance) e o **moto** (simulador gratuito da AWS).

## 4. Terraform (de preferência a versão 1.12.0, a mesma do paper)

* Página oficial: https://developer.hashicorp.com/terraform/install
* Versões antigas (para pegar exatamente a 1.12.0): https://releases.hashicorp.com/terraform/1.12.0/
* Baixe o arquivo do seu sistema, descompacte e coloque o programa `terraform` numa pasta que esteja no PATH (ou informe o caminho completo em `configuracao.yaml`, campo `verificadores.programas.terraform`).

Confira: `terraform version`

## 5. OPA e TFLint

**OPA** (avalia a Rego intent):
* macOS: `brew install opa`
* Linux: `curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static && chmod +x opa` e mova o arquivo `opa` para uma pasta do PATH
* Windows: baixe `opa_windows_amd64.exe` em https://github.com/open-policy-agent/opa/releases , renomeie para `opa.exe` e coloque numa pasta do PATH

**TFLint** (Linter):
* macOS: `brew install tflint`
* Linux: `curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash`
* Windows: `choco install tflint` ou baixe em https://github.com/terraform-linters/tflint/releases

Confira: `opa version` e `tflint --version`

## 6. Ollama e os modelos

Você já usa o Ollama. Confira se ele está aberto e com os 8 modelos:

```bash
ollama list
```
Se faltar algum: `ollama pull NOME_DO_MODELO` (ex.: `ollama pull qwen2.5-coder:7b`).

## 7. Exemplos fixos do Projeto 1

Copie o arquivo `resultados/exemplos_fixos.json` do Projeto 1 para a pasta `entrada/` deste projeto. (Esta entrega já traz uma cópia, gerada no teste; ao rodar o Projeto 1 na sua máquina, substitua pela sua.)

## 8. Conferência final

```bash
python executar.py verificar-ambiente
```
A saída mostra `[OK]` ou `[FALTANDO]` para cada item: Terraform, OPA, TFLint, Checkov, moto, Ollama, cada um dos 8 modelos e os exemplos fixos. Na primeira vez esse comando também baixa o plugin de regras AWS do TFLint (`tflint --init`).

Se aparecer erro de "rate limit" do GitHub no `tflint --init`, crie um token pessoal gratuito no GitHub e rode antes:
```bash
export GITHUB_TOKEN=seu_token          # Linux/macOS
$env:GITHUB_TOKEN="seu_token"          # Windows PowerShell
```
