# Instalação e execução, passo a passo

Faça a instalação **uma vez**. Os mesmos programas servem para o Projeto 2.

Abra um terminal (Windows: "PowerShell"; macOS: "Terminal"; Linux: o terminal da sua distribuição) e entre na pasta do projeto:

```bash
cd caminho/para/projeto1_selecao_exemplos_fixos
```

## Parte A. Instalação

### 1. Python 3.10 ou mais novo
Confira com `python --version` (ou `python3 --version`). Se não tiver: https://www.python.org/downloads/

### 2. Ambiente virtual (recomendado)
Uma pasta isolada com os pacotes do projeto, para não misturar com outros programas.
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```
Sempre que abrir um terminal novo, rode de novo a linha `activate`.

### 3. Pacotes Python
```bash
pip install -r requirements.txt
```
Instala o leitor de configuração, o **Checkov** (Security Compliance) e o **moto** (simulador gratuito da AWS).

### 4. Terraform (de preferência 1.12.0, a versão do paper)
* Página oficial: https://developer.hashicorp.com/terraform/install
* Versão exata 1.12.0: https://releases.hashicorp.com/terraform/1.12.0/
* Descompacte e coloque o programa `terraform` numa pasta do PATH (ou informe o caminho completo em `configuracao.yaml`, campo `verificadores.programas.terraform`).

### 5. OPA
* macOS: `brew install opa`
* Linux: `curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static && chmod +x opa` (depois mova `opa` para uma pasta do PATH)
* Windows: baixe `opa_windows_amd64.exe` em https://github.com/open-policy-agent/opa/releases , renomeie para `opa.exe` e coloque numa pasta do PATH

### 6. TFLint
* macOS: `brew install tflint`
* Linux: `curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash`
* Windows: `choco install tflint` ou https://github.com/terraform-linters/tflint/releases

### 7. Conferência
```bash
python executar.py --verificar-ambiente
```
Mostra `[OK]` ou `[FALTANDO]` para Terraform, OPA, TFLint, Checkov e moto, e baixa o plugin de regras AWS do TFLint (`tflint --init`). Se der erro de "rate limit" do GitHub, crie um token pessoal gratuito no GitHub e rode antes `export GITHUB_TOKEN=seu_token` (Windows: `$env:GITHUB_TOKEN="seu_token"`).

## Parte B. Execução

### 1. Conferir a configuração
Abra `configuracao.yaml` num editor de texto. O dataset já vem pronto em `dados/iac_eval.csv` (458 cenários, com as quebras de linha preservadas). Para usar o arquivo do Hugging Face, troque `origem` por `"huggingface"` (requer internet e o pacote `datasets`). Também aceita `.ods` e `.xlsx`.

### 2. Rodar a busca
```bash
python executar.py
```
A tela mostra cada linha avaliada:
```
[19:21:45] Avaliando linha 45 (dificuldade 2, aws_route53_record, aws_route53_zone)...
[19:22:05]    -> reprovada: Security (checkov) nota 0.2500 < minimo 1.0000
...
[19:25:42]    -> APROVADA. Exemplo 2 escolhido.
...
[19:27:26] Pronto! Exemplos escolhidos (linha no dataset): 0, 65, 146
```
Tempo típico: 5 a 10 minutos (cerca de 20 segundos por linha avaliada). A busca para sozinha ao encontrar os 3 exemplos. O simulador AWS (moto) é ligado e desligado automaticamente.

Cada nova execução move os resultados anteriores para `resultados_anterior_<data>` (nada é perdido).

### 3. Ver o resultado
* `resultados/exemplos_fixos.md`: os 3 exemplos, com Prompt, Intent, Rego intent, Reference output, linha e o resultado das 5 verificações
* `resultados/relatorio_da_busca.csv`: uma linha por cenário avaliado, com as 5 notas e o motivo da reprovação (abre no Excel)
* `resultados/pass.txt` e `resultados/fail.txt`: os resultados de cada comando

### 4. Levar para o Projeto 2
Copie `resultados/exemplos_fixos.json` para `projeto2_avaliacao_llms/entrada/exemplos_fixos.json`.

### Se não encontrar os 3 exemplos
A tela avisa "so foram encontrados X de 3". Abra `relatorio_da_busca.csv`, veja qual critério mais reprovou e afrouxe-o no `configuracao.yaml` (ex.: `security_minima: 0.5`).
