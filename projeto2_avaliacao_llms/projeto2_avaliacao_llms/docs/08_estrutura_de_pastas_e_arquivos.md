# Estrutura de pastas e arquivos

## O projeto

```
projeto2_avaliacao_llms/
├── README.md                      comece por aqui
├── executar.py                    ÚNICO programa que você roda (todos os comandos)
├── configuracao.yaml              TODAS as opções, comentadas
├── requirements.txt               pacotes Python
├── docs/                          esta documentação
├── dados/
│   └── iac_eval.csv               dataset IaC-Eval (458 cenários), com quebras de linha preservadas
├── entrada/
│   └── exemplos_fixos.json        os 3 exemplos fixos (vem do Projeto 1)
├── pipeline/                      as 5 etapas da Figure 1
│   ├── configuracao.py            lê o configuracao.yaml e define os caminhos
│   ├── etapa1_dataset/            1. IaC-Eval dataset
│   ├── etapa2_prompt_builder/     2. Prompt Builder (template do TerraFormer)
│   ├── etapa3_geracao/            3. Generation (Ollama + extração do HCL)
│   ├── etapa4_avaliacao/          4. Automatic evaluation (chama os verificadores)
│   └── etapa5_resultados/         5. Results (tabela)
├── verificadores/                 um verificador por pasta
│   ├── escada_de_avaliacao.py     o "maestro" da escada (Figure 3)
│   ├── fv1_terraform_validate/    Compilability
│   ├── fv2_terraform_plan/        Deployability (+ credenciais simuladas + simulador moto)
│   ├── fv3_opa_eval/              Correctness
│   ├── tflint_linter/             Linter Pass Rate (+ arquivo de regras .tflint.hcl)
│   ├── checkov_seguranca/         Security Compliance
│   └── comum/                     peças usadas por todos (executar comando, pass/fail...)
├── ferramentas/cache/             criada sozinha: plugins baixados (não apague à toa)
└── resultados/                    criada sozinha: tudo o que o experimento produz
```

## Os resultados

```
resultados/
├── log_execucao.txt                     tudo o que apareceu na tela, com data e hora
├── cenarios_selecionados.csv / .json    os 30 cenários avaliados (usado no Projeto 3)
├── exemplo_de_prompt_setting_A.txt      um prompt de exemplo, para leitura
├── setting_A/
│   └── qwen2.5-coder_7b/                um modelo (":" vira "_" no nome da pasta)
│       ├── pass.txt                     todos os PASS deste modelo (uma linha por comando e cenário)
│       ├── fail.txt                     todos os FAIL e NAO_EXECUTADO
│       ├── por_comando/
│       │   ├── 1_terraform_validate/pass.txt e fail.txt
│       │   ├── 2_terraform_plan/pass.txt e fail.txt
│       │   ├── 3_opa_eval/pass.txt e fail.txt
│       │   ├── 4_tflint/pass.txt e fail.txt
│       │   └── 5_checkov/pass.txt e fail.txt
│       └── linha_0016/                  um cenário (linha 16 do dataset)
│           ├── prompt_enviado.txt       o texto exato enviado ao modelo
│           ├── resposta_bruta.txt       a resposta completa do modelo
│           ├── hcl_extraido.tf          o código extraído (só existe se houve HCL)
│           ├── geracao.json             modelo, opções, tempo, tokens, como o HCL foi extraído, alertas
│           ├── resultado.json           as 5 métricas e o motivo de cada uma
│           └── avaliacao/
│               ├── codigo_avaliado.tf
│               ├── area_de_trabalho_terraform/   main.tf + arquivos zz_avaliacao_* (credenciais simuladas)
│               ├── 1_terraform_validate/         saída do init e do validate
│               ├── 2_terraform_plan/             saída do plan e do show, plan.json
│               ├── 3_opa_eval/                   intent.rego, saída do opa, regras_avaliadas.json
│               ├── 4_tflint/                     saída do tflint, problemas_tflint.json
│               ├── 5_checkov/                    saída do checkov, resumo_checkov.json
│               └── resultado_avaliacao.json
├── setting_B/                           mesma estrutura
└── tabela/
    ├── tabela_setting_A.md / .csv       A TABELA FINAL
    ├── calculos_detalhados_setting_A.md a conta de cada número
    ├── resultados_por_cenario_setting_A.csv
    ├── por_dificuldade_setting_A.md / .csv
    └── tabela_resultados.xlsx           tudo numa planilha
```

## Como investigar um resultado (exemplo)

"Por que o qwen2.5-coder:7b falhou no Correctness da linha 16?"

1. Abra `resultados/setting_A/qwen2.5-coder_7b/por_comando/3_opa_eval/fail.txt` e procure `linha=16`. O `motivo` diz quais regras deram false.
2. Abra `linha_0016/avaliacao/3_opa_eval/regras_avaliadas.json` para ver cada regra.
3. Compare `linha_0016/hcl_extraido.tf` com o que a policy `intent.rego` exige.
