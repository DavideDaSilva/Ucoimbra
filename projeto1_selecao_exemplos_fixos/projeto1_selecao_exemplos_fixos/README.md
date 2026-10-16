# Projeto 1: seleção dos 3 exemplos fixos do IaC-Eval

Este projeto encontra, no dataset **IaC-Eval**, os **3 exemplos fixos** que serão colocados no bloco de exemplos do template do TerraFormer (etapa "2. Prompt Builder" do Projeto 2).

Regra: um cenário só vira exemplo fixo se o seu **Reference output** passar pelos **5 critérios** da etapa "4. Automatic Evaluation":

| # | Verificador | Critério |
|---|---|---|
| 1 | `terraform validate` | Compilability |
| 2 | `terraform plan` | Deployability |
| 3 | `opa eval` com a Rego intent | Correctness |
| 4 | TFLint | Linter |
| 5 | Checkov | Security Compliance |

A busca percorre o dataset em ordem e **para quando encontra os 3 exemplos**. Para cada exemplo são salvos o **Prompt**, o **Intent**, a **Rego intent**, o **Reference output** e a **linha** onde ele está no dataset.

## Início rápido

```bash
cd projeto1_selecao_exemplos_fixos
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# instale também Terraform 1.12.0, OPA e TFLint (docs/02_instalacao_e_execucao_passo_a_passo.md)

python executar.py --verificar-ambiente   # tudo [OK]?
python executar.py                        # faz a busca (5 a 10 minutos)
```

Resultado:
* `resultados/exemplos_fixos.md`: para ler
* `resultados/exemplos_fixos.json`: **copie para `projeto2_avaliacao_llms/entrada/`**

## Estrutura

```
projeto1_selecao_exemplos_fixos/
├── README.md                  este arquivo
├── executar.py                ÚNICO programa que você roda
├── configuracao.yaml          todas as opções, comentadas
├── requirements.txt           pacotes Python
├── dados/iac_eval.csv         dataset IaC-Eval (458 cenários), pronto para uso
├── docs/                      documentação (leia na ordem)
├── selecao/                   a lógica da busca
│   ├── carregar_dataset.py    lê .csv, .ods, .xlsx ou baixa do Hugging Face
│   ├── selecionar_exemplos.py percorre as linhas e aplica os critérios
│   └── salvar_exemplos.py     grava os exemplos (.json, .md e uma pasta por exemplo)
├── verificadores/             um verificador por pasta
│   ├── escada_de_avaliacao.py     o "maestro" (Figure 3 dos slides)
│   ├── fv1_terraform_validate/    Compilability
│   ├── fv2_terraform_plan/        Deployability (+ credenciais simuladas + simulador moto)
│   ├── fv3_opa_eval/              Correctness
│   ├── tflint_linter/             Linter (+ regras .tflint.hcl)
│   ├── checkov_seguranca/         Security Compliance
│   └── comum/                     peças comuns (executar comando, pass/fail, configuração)
├── ferramentas/cache/         criada sozinha: plugins baixados
└── resultados/                criada sozinha: tudo o que a busca produz
```

## PASS e FAIL

* `resultados/pass.txt`: todos os resultados PASS
* `resultados/fail.txt`: todos os FAIL e NAO_EXECUTADO
* `resultados/por_comando/<n>_<comando>/pass.txt` e `fail.txt`: separados por comando

Cada linha diz **qual comando**, qual linha do dataset e o motivo.

## Documentação

1. `docs/01_o_que_este_projeto_faz.md`: o problema, o fluxo da busca e o resultado do teste
2. `docs/02_instalacao_e_execucao_passo_a_passo.md`: instalar e rodar, do zero
3. `docs/03_os_5_verificadores.md`: cada verificador, o comando e o critério
4. `docs/04_deployability_sem_credenciais.md`: o `terraform plan` sem conta AWS e sem custo
5. `docs/05_como_ler_os_resultados.md`: cada arquivo de resultado
6. `docs/06_decisoes_e_limitacoes.md`: escolhas feitas, achados sobre o dataset
7. `docs/07_problemas_comuns.md`: erros comuns e soluções

## Deployability sem pagar nada

O `terraform plan` roda com credenciais AWS **falsas** e um **simulador gratuito da AWS (moto)** no seu computador. Nada é criado em nuvem nenhuma e nenhuma credencial real é usada.
