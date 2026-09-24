# Guia passo a passo: como rodar os testes e montar a Tabela 2

Este guia não pressupõe conhecimento prévio. Cada passo diz o que digitar, o
que deve aparecer na tela e o que fazer quando der errado.

Sumário:

- [Passo 0. Preparar a máquina](#passo-0-preparar-a-máquina)
- [Passo 1. Conferir se está tudo no lugar](#passo-1-conferir-se-está-tudo-no-lugar)
- [Passo 2. Teste rápido do pipeline sem instalar nada](#passo-2-teste-rápido-do-pipeline-sem-instalar-nada)
- [Passo 3. Escolher os modelos](#passo-3-escolher-os-modelos)
- [Passo 4. Gerar o código Terraform](#passo-4-gerar-o-código-terraform)
- [Passo 5. Rodar os três oráculos](#passo-5-rodar-os-três-oráculos)
- [Passo 6. Ler os resultados de pass, fail e error](#passo-6-ler-os-resultados-de-pass-fail-e-error)
- [Passo 7. Montar a Tabela 2](#passo-7-montar-a-tabela-2)
- [Passo 8. Como ler a tabela pronta](#passo-8-como-ler-a-tabela-pronta)
- [Passo 9. Usar o IaC-Eval de verdade](#passo-9-usar-o-iac-eval-de-verdade)
- [Passo 10. Criar suas próprias instâncias](#passo-10-criar-suas-próprias-instâncias)
- [Problemas comuns](#problemas-comuns)

---

## Passo 0. Preparar a máquina

Você precisa de seis coisas. Instale uma de cada vez e confira cada uma antes
de passar para a próxima.

### 0.1 Python 3.10 ou mais novo

```bash
python3 --version
```

Deve aparecer algo como `Python 3.12.3`.

### 0.2 As bibliotecas Python do projeto

Entre na pasta do projeto e rode:

```bash
cd terraformer-repro
pip install -r requirements.txt
```

São apenas duas bibliotecas: `requests` (para falar com o Ollama) e `PyYAML`
(para ler o arquivo de configuração).

Se o seu sistema reclamar de "externally managed environment", use um ambiente
virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Lembre de rodar `source .venv/bin/activate` toda vez que abrir um terminal novo.

### 0.3 Terraform

O paper usa a versão 1.12.0. Página oficial de instalação:
https://developer.hashicorp.com/terraform/install

No Ubuntu ou Debian:

```bash
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

No macOS com Homebrew:

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

Confira:

```bash
terraform version
```

### 0.4 OPA (Open Policy Agent)

É o programa que roda as políticas Rego, ou seja, o oráculo FV-iii.

Linux:

```bash
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static
chmod +x opa
sudo mv opa /usr/local/bin/
```

macOS com Homebrew:

```bash
brew install opa
```

Confira:

```bash
opa version
```

### 0.5 TFLint

Serve para a métrica Linter Pass Rate.

```bash
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
tflint --version
```

No macOS: `brew install tflint`.

### 0.6 Checkov

Serve para a métrica Security Compliance.

```bash
pip install checkov
checkov --version
```

### 0.7 Ollama e os modelos

Instale o Ollama em https://ollama.com/download e depois deixe o servidor
rodando em um terminal separado:

```bash
ollama serve
```

Em outro terminal, baixe os modelos que quiser avaliar. Comece por um pequeno
para testar o fluxo:

```bash
ollama pull qwen2.5-coder:7b
```

Veja o que você já tem:

```bash
ollama list
```

---

## Passo 1. Conferir se está tudo no lugar

```bash
bash scripts/00_conferir_ambiente.sh
```

A saída mostra uma linha por item:

```
[ OK ] Python: 3.12.3
[ OK ] Terraform: Terraform v1.12.0
[ OK ] Open Policy Agent: Version: 1.4.2
[ OK ] TFLint: TFLint version 0.53.0
[ OK ] Checkov: 3.2.0
[ OK ] Ollama respondendo em http://127.0.0.1:11434
   [ OK ] modelo 'qwen2.5-coder:7b'
   [FALTA] modelo 'mistral'  -> rode: ollama pull mistral
[ OK ] dataset 'tf_gen_test': 5 instancias
```

Resolva tudo que aparecer como `[FALTA]` antes de seguir. O que aparece como
`[AVISO]` é opcional: sem TFLint e sem Checkov o pipeline roda, mas as duas
últimas colunas da tabela ficam zeradas.

---

## Passo 2. Teste rápido do pipeline sem instalar nada

Este passo existe para separar dois tipos de problema: problema do código do
projeto e problema de instalação de ferramenta. Ele usa versões falsas do
terraform, do opa, do tflint e do checkov.

```bash
bash scripts/04_autoteste.sh
```

No fim deve aparecer uma tabela de exemplo. **Os números desse teste não têm
valor científico**, eles apenas confirmam que o encanamento funciona.

---

## Passo 3. Escolher os modelos

Abra `config/config.yaml` e mexa na seção `models`. Deixe ali somente os
modelos que você já baixou com `ollama pull`:

```yaml
models:
  - name: "qwen2.5-coder:7b"      # nome exato no Ollama
    label: "Qwen2.5-Coder-7B"     # nome que aparece na tabela
    params: "7B"                  # coluna #Params.
```

Dica prática: comece com dois modelos e cinco instâncias. Depois que o fluxo
inteiro funcionar, aumente.

---

## Passo 4. Gerar o código Terraform

### 4.1 Um modelo só, para testar

```bash
bash scripts/01_gerar.sh tf_gen_test qwen2.5-coder:7b
```

Saída esperada:

```
[GERACAO] modelo=qwen2.5-coder:7b dataset=tf_gen_test instancias=5
  (1/5) tfgen_001: OK  842 chars em 12.4s
  (2/5) tfgen_002: OK  1103 chars em 15.1s
  ...
[GERACAO] concluida. Saida em: results/generations/qwen2.5-coder_7b/tf_gen_test
```

`VAZIO` no lugar de `OK` significa que o modelo respondeu, mas não devolveu
código Terraform nenhum. Isso é comum em modelos pequenos e conta como falha,
exatamente como no protocolo do paper.

### 4.2 Todos os modelos do config

```bash
bash scripts/01_gerar.sh tf_gen_test
```

### 4.3 O que foi criado

```
results/generations/qwen2.5-coder_7b/tf_gen_test/
├── manifest.jsonl              <- registro de tudo que foi gerado
└── tfgen_001/
    ├── prompt_enviado.txt      <- o prompt exato enviado ao modelo
    ├── resposta_bruta.txt      <- a resposta completa do modelo
    └── main.tf                 <- só o código Terraform extraído
```

Abra o `main.tf` de uma instância e veja com os próprios olhos o que o modelo
escreveu. Isso ajuda muito a entender os números depois.

Observações úteis:

- Se você rodar o comando de novo, o projeto **pula** o que já foi gerado. Para
  refazer tudo, acrescente `--overwrite` usando o comando direto:
  `python3 -m src.generation.generate --dataset tf_gen_test --model qwen2.5-coder:7b --overwrite`
- Para testar rápido com poucas instâncias, use `--limit 3` no comando direto.

---

## Passo 5. Rodar os três oráculos

```bash
bash scripts/02_avaliar.sh tf_gen_test qwen2.5-coder:7b
```

Saída esperada:

```
[AVALIACAO] modelo=qwen2.5-coder:7b dataset=tf_gen_test instancias=5
  (1/5) tfgen_001: compilavel=sim implantavel=sim correto=sim
  (2/5) tfgen_002: compilavel=sim implantavel=sim correto=nao
  (3/5) tfgen_003: compilavel=nao implantavel=nao correto=nao
  ...
[AVALIACAO] qwen2.5-coder:7b / tf_gen_test: Correctness=20.0% Deployability=60.0% Compilability=80.0%
```

O que acontece por baixo, para cada instância, na ordem:

1. copia o `main.tf` gerado para uma pasta de trabalho isolada;
2. se o código declara `provider "aws"`, acrescenta o arquivo de override com
   credenciais falsas;
3. **FV-i**: roda `terraform init -backend=false` e `terraform validate -json`;
4. **FV-ii**: se FV-i passou, roda `terraform plan` com limite de 30 segundos e
   converte o plano para `plan.json`;
5. **FV-iii**: se FV-ii passou, roda `opa eval` com a política Rego da instância
   sobre o `plan.json`;
6. roda TFLint e Checkov;
7. grava tudo em pass.txt, fail.txt e error.txt.

Para avaliar todos os modelos de uma vez, omita o nome do modelo:

```bash
bash scripts/02_avaliar.sh tf_gen_test
```

**Aviso sobre a primeira execução:** o `terraform init` baixa o provider da AWS,
o que pode levar alguns minutos e exige internet. Depois disso, o download fica
em cache na pasta `.terraform-plugin-cache/` e as execuções seguintes são
rápidas.

---

## Passo 6. Ler os resultados de pass, fail e error

Visão geral de um modelo:

```bash
ls results/evaluations/qwen2.5-coder_7b/tf_gen_test/oracles/
# fv1_validate  fv2_plan  fv3_opa  tflint  checkov
```

Quantas instâncias passaram em cada oráculo (cada registro começa com uma
linha DATA/HORA):

```bash
grep -c "DATA/HORA" results/evaluations/qwen2.5-coder_7b/tf_gen_test/oracles/fv1_validate/pass.txt
```

Ver por que o `terraform plan` falhou:

```bash
less results/evaluations/qwen2.5-coder_7b/tf_gen_test/oracles/fv2_plan/error.txt
```

Investigar uma instância específica do começo ao fim:

```bash
ls results/evaluations/qwen2.5-coder_7b/tf_gen_test/instances/tfgen_002/
cat results/evaluations/qwen2.5-coder_7b/tf_gen_test/instances/tfgen_002/fv3_opa/fail.txt
cat results/evaluations/qwen2.5-coder_7b/tf_gen_test/instances/tfgen_002/workdir/main.tf
```

Cada registro dentro dos arquivos .txt traz o comando exato que foi executado,
o código de saída e o resultado, então sempre dá para saber a que comando
aquele "passou" ou "não passou" se refere.

---

## Passo 7. Montar a Tabela 2

Depois de gerar e avaliar **todos** os modelos que você quer comparar:

```bash
bash scripts/03_montar_tabela2.sh
```

Se você rodou só um dataset, diga qual:

```bash
bash scripts/03_montar_tabela2.sh --datasets tf_gen_test
```

O comando cria quatro arquivos em `results/tables/`:

| Arquivo | Para que serve |
|---|---|
| `tabela2.md` | ler na tela e colar em documentos Markdown |
| `tabela2.csv` | abrir no Excel ou no LibreOffice Calc |
| `tabela2.tex` | colar direto em um artigo LaTeX |
| `tabela2.json` | reprocessar os números em outro script |

O script já faz por você, coluna por coluna:

- coloca o melhor valor em negrito;
- sublinha o segundo melhor;
- mantém a ordem dos modelos definida no `config.yaml`;
- escreve `n/d` quando um modelo não tem resultado para aquele dataset.

### Se você preferir montar a tabela à mão

Os números crus estão em
`results/evaluations/<modelo>/<dataset>/resumo.json`, assim:

```json
{
  "instances": 5,
  "correctness": 20.0,
  "deployability": 60.0,
  "compilability": 80.0,
  "linter_pass_rate": 75.0,
  "security_compliance": 58.33
}
```

Para ver todos de uma vez:

```bash
find results/evaluations -name resumo.json -exec sh -c 'echo "== $1"; cat "$1"' _ {} \;
```

E as fórmulas, caso queira conferir na calculadora:

```
Compilability       = (instâncias que passaram em FV-i        / total) * 100
Deployability       = (instâncias que passaram em FV-i e FV-ii / total) * 100
Correctness         = (instâncias que passaram em FV-iii       / total) * 100
Linter Pass Rate    = (instâncias sem alerta do TFLint / instâncias compiláveis) * 100
Security Compliance = média de (checagens aprovadas / checagens totais) do Checkov * 100
```

O denominador das duas últimas linhas pode ser trocado em `config.yaml`, na
seção `table2.denominators`.

---

## Passo 8. Como ler a tabela pronta

Exemplo de saída:

| Model | #Params. | Correctness (%) | Deployability (%) | Compilability (%) | Linter Pass Rate (%) | Security Compliance (%) |
|---|---|---|---|---|---|---|
| Qwen2.5-Coder-32B | 32B | **12.50** | **48.00** | **55.00** | **98.00** | 51.20 |
| Qwen2.5-Coder-7B | 7B | 6.25 | 30.00 | 38.00 | 95.00 | **58.30** |

Como interpretar:

- **Correctness** é a métrica mais dura e sempre a menor das três. No paper, os
  melhores modelos comerciais ficam em torno de 35% no IaC-Eval, e os modelos
  abertos de 7B ficam abaixo de 5%. Números baixos aqui são esperados.
- **Deployability** e **Compilability** são sempre maiores ou iguais à
  Correctness. Se algum dia aparecer Correctness maior que Deployability, há um
  erro em algum lugar, porque a hierarquia foi violada.
- **Linter Pass Rate** costuma ser alta mesmo em modelos ruins, porque o linter
  só avalia estilo e boas práticas do código que conseguiu ser lido.
- **Security Compliance** é uma média de porcentagens, não uma contagem de
  aprovados e reprovados.

---

## Passo 9. Usar o IaC-Eval de verdade

O projeto vem com três instâncias de exemplo do IaC-Eval apenas para teste. O
dataset verdadeiro tem 458 instâncias e é público.

```bash
pip install datasets

# 1) primeiro olhe os nomes das colunas do dataset
python3 -m src.data_tools.import_iac_eval --inspecionar

# 2) depois converta, informando as colunas que você viu no passo anterior
python3 -m src.data_tools.import_iac_eval --coluna-prompt Prompt --coluna-policy Policy
```

Depois disso, abra dois ou três arquivos em
`data/benchmark/iac_eval/policies/` e confira se as regras fazem sentido. As
políticas do IaC-Eval seguem uma convenção um pouco diferente, e o importador
adapta o que consegue, mas a revisão humana continua sendo necessária.

---

## Passo 10. Criar suas próprias instâncias

Uma instância é composta de duas partes: o pedido e a política que testa o
pedido.

### 10.1 Acrescente uma linha no arquivo de instâncias

Em `data/benchmark/tf_gen_test/instances.jsonl`, uma linha por instância:

```json
{"id": "tfgen_006", "prompt": "Create an ECR repository named 'app-images' with image scanning on push enabled.", "policy": "policies/tfgen_006.rego"}
```

### 10.2 Crie a política correspondente

Em `data/benchmark/tf_gen_test/policies/tfgen_006.rego`:

```rego
package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_ecr_repository if {
	some r in resources
	r.type == "aws_ecr_repository"
	r.values.name == "app-images"
}

is_valid_scan_on_push if {
	some r in resources
	r.type == "aws_ecr_repository"
	some cfg in r.values.image_scanning_configuration
	cfg.scan_on_push == true
}
```

Regras de ouro ao escrever políticas:

1. o nome de toda regra de verificação começa com `is_valid_`;
2. uma regra para cada exigência do prompt, nem mais nem menos;
3. evite exigir coisas que o prompt não pediu, senão você mede o gosto pessoal
   do avaliador e não a capacidade do modelo;
4. teste a política antes de usá-la em larga escala.

### 10.3 Como testar uma política sozinha

Pegue um `plan.json` que já existe e rode o OPA na mão:

```bash
opa eval --format pretty \
  --data data/benchmark/tf_gen_test/policies/tfgen_006.rego \
  --input results/evaluations/qwen2.5-coder_7b/tf_gen_test/instances/tfgen_001/workdir/plan.json \
  "data.terraform.policy"
```

Você verá quais regras deram verdadeiro. Regras que não aparecem na saída são
consideradas reprovadas pelo projeto.

---

## Problemas comuns

**"Ollama nao respondeu"**
O servidor não está rodando. Abra outro terminal e deixe `ollama serve` aberto.

**"Binario nao encontrado: 'terraform'"**
A ferramenta não está instalada ou não está no PATH. Volte ao Passo 0. Se ela
estiver em um caminho estranho, informe o caminho completo em `config.yaml`, na
seção `tools`.

**Todas as instâncias falham em FV-i com erro de provider**
Quase sempre é falta de internet na primeira execução: o `terraform init`
precisa baixar o provider da AWS uma vez. Rode `terraform init` manualmente
dentro de qualquer pasta `workdir` para ver a mensagem completa.

**Muitas falhas com "timed out" no terraform plan**
O Terraform ficou esperando alguém digitar o valor de uma variável sem valor
padrão. É uma falha legítima do código gerado e o paper conta do mesmo jeito.
Se quiser dar mais folga, aumente `plan_timeout_seconds` em `config.yaml`, mas
registre isso ao relatar seus resultados, porque muda a comparação.

**Correctness igual a zero em todos os modelos**
Antes de concluir que os modelos são ruins, teste uma política à mão com o
comando do Passo 10.3. Uma política escrita de forma exigente demais zera a
métrica sozinha.

**A tabela saiu com "n/d"**
Falta avaliação para aquele modelo naquele dataset. Rode a etapa 2 para ele, ou
tire o modelo da lista do `config.yaml`.

**Os scripts .sh não rodam**
Dê permissão de execução uma vez: `chmod +x scripts/*.sh`. Ou simplesmente
chame com `bash scripts/01_gerar.sh ...`, que funciona sempre.
