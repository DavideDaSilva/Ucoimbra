# Deployability sem conta AWS e sem pagar nada

## O problema

O `terraform plan` do provider AWS normalmente:

1. confere se as credenciais AWS são válidas (pergunta ao serviço STS da AWS);
2. descobre o número da conta;
3. para blocos `data "aws_..."`, **consulta a AWS de verdade**. Exemplos: `data "aws_ami"` (qual é a imagem mais recente do Amazon Linux?) e `data "aws_availability_zones"` (quais zonas existem na região?).

Sem credenciais válidas (pagas), os três passos falham. Isso importa muito: **175 dos 458** Reference outputs do IaC-Eval usam pelo menos um bloco `data "aws_..."` (99 usam `aws_availability_zones` e 42 usam `aws_ami`).

## A solução adotada (gratuita, local e testada)

### Parte 1: credenciais falsas + "pule a verificação"

Antes de rodar o Terraform, a avaliação coloca, ao lado do `main.tf` gerado pelo modelo, um arquivo extra chamado `zz_avaliacao_credenciais_simuladas_override.tf`:

```hcl
provider "aws" {
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  max_retries                 = 1
}
```

Arquivos terminados em `_override.tf` são um recurso **oficial** do Terraform: eles sobrepõem apenas os campos listados de um bloco que já existe, **sem alterar o código do modelo**. Assim o provider aceita credenciais falsas e não tenta conferi-las.

Detalhes:

* Se o modelo escreveu vários blocos `provider "aws"` (com `alias`), cada um recebe a sua sobreposição.
* Se o modelo **não** escreveu nenhum `provider "aws"` sem alias, é criado `zz_avaliacao_provider_padrao.tf` com um provider padrão (região `us-east-1`, configurável).
* Se o código não declara `required_providers`, é criado `zz_avaliacao_versao_provider.tf` fixando o provider AWS na série `~> 5.0` (a série usada quando o IaC-Eval foi criado). Assim todos os testes usam a mesma versão. Configurável em `versao_provider_aws` (deixe `""` para não fixar).
* Esses arquivos ficam na pasta `area_de_trabalho_terraform/` de cada cenário, para conferência. TFLint e Checkov **não** os veem (rodam numa pasta só com o `main.tf`).

### Parte 2: simulador gratuito da AWS (moto)

As credenciais falsas resolvem os passos 1 e 2, mas não o 3 (blocos `data`). Para isso usamos o **moto**, um programa de código aberto que **finge ser a AWS** no seu computador:

* instalação: `pip install "moto[server]"` (já está no `requirements.txt`);
* ele responde em `http://127.0.0.1:5555`;
* a avaliação liga o moto sozinha no começo e desliga no fim (opção `iniciar_moto_automaticamente`);
* a variável de ambiente `AWS_ENDPOINT_URL=http://127.0.0.1:5555` faz o Terraform mandar **todas** as chamadas da AWS para o simulador, em vez da internet.

Testado com o provider AWS 5.100: `data "aws_ami"`, `data "aws_availability_zones"` e `data "aws_caller_identity"` funcionaram no `plan` sem nenhuma conta AWS.

### Garantias de segurança

* O `terraform apply` **nunca** é executado. Nada é criado em nenhuma nuvem.
* Antes de rodar qualquer verificador, as credenciais AWS reais que existirem no seu computador (variáveis `AWS_ACCESS_KEY_ID`, `AWS_PROFILE` etc.) são **removidas** do ambiente do processo. Mesmo que você tenha uma conta AWS configurada, ela não é usada.

## Modos disponíveis (`verificadores.deployability.modo`)

| Modo | O que faz | Quando usar |
|---|---|---|
| `moto` (padrão) | credenciais falsas + simulador local | sempre que possível |
| `sem_servidor` | apenas credenciais falsas | se não conseguir instalar o moto. Código com `data "aws_..."` que consulta a AWS vai falhar no plan |

## Limitações (seja transparente ao relatar os resultados)

* O moto é um simulador: ele responde às consultas mais comuns, mas não sabe tudo o que a AWS sabe. Uma consulta muito específica (ex.: um filtro de AMI que não existe no catálogo do moto) pode falhar mesmo estando correta.
* O `plan` valida a estrutura do plano, não garante que o `apply` funcionaria (ex.: nome de bucket já usado por outra pessoa). Isso também vale para o paper, que mede Deployability pelo `terraform plan`.
* Ao relatar, escreva algo como: *"Deployability medida com `terraform plan` usando credenciais simuladas e o simulador local moto; nenhum recurso foi criado."*
