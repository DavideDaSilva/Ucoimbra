# Como ler os resultados

Tudo fica na pasta `resultados/`:

```
resultados/
├── exemplos_fixos.json        ARQUIVO PRINCIPAL (vai para o Projeto 2)
├── exemplos_fixos.md          os 3 exemplos, para leitura
├── exemplos/
│   └── exemplo_1_linha_0000/  prompt.txt, intent.txt, rego_intent.rego, reference_output.tf, metadados.json
├── relatorio_da_busca.csv     uma linha por cenário avaliado (abre no Excel)
├── pass.txt                   todos os resultados PASS
├── fail.txt                   todos os resultados FAIL e NAO_EXECUTADO
├── por_comando/
│   ├── 1_terraform_validate/  pass.txt e fail.txt só deste comando
│   ├── 2_terraform_plan/
│   ├── 3_opa_eval/
│   ├── 4_tflint/
│   └── 5_checkov/
├── verificacoes/
│   └── linha_0045/            saída completa dos 5 verificadores para a linha 45
│       ├── codigo_avaliado.tf
│       ├── area_de_trabalho_terraform/   main.tf + arquivos zz_avaliacao_* (credenciais simuladas)
│       ├── 1_terraform_validate/ ... 5_checkov/
│       └── resultado_avaliacao.json
├── log_execucao.txt           tudo o que apareceu na tela
└── simulador_moto.log         mensagens do simulador AWS
```

## relatorio_da_busca.csv

| coluna | significado |
|---|---|
| linha | linha no dataset (a partir de 0) |
| linha_na_planilha | linha no Excel/LibreOffice |
| dificuldade, resource | colunas do IaC-Eval |
| compilability, deployability, correctness, linter_pass | 1 = passou, 0 = falhou |
| security_compliance | nota do Checkov, de 0 a 1 |
| aprovada | `sim` = virou exemplo fixo |
| criterios_nao_atendidos | por que não foi aprovada |

Só aparecem as linhas que foram **avaliadas**. Linhas puladas (dificuldade já preenchida, recurso repetido, Intent vazio) não são avaliadas, para economizar tempo.

## pass.txt e fail.txt

Cada linha é um resultado de um comando:
```
2026-10-16 19:15:58 | PASS | comando=terraform validate | linha=0 | linha_na_planilha=2 | dificuldade=1 | origem=Reference output | valor=1 | motivo=terraform init e terraform validate terminaram sem erro
2026-10-16 19:16:17 | FAIL | comando=checkov | linha=45 | linha_na_planilha=47 | dificuldade=2 | origem=Reference output | valor=0.2500 | motivo=1 aprovadas, 3 reprovadas (nota 0.2500); reprovadas: CKV2_AWS_23, CKV2_AWS_38, CKV2_AWS_39
```
* `comando=` diz qual verificador gerou o resultado.
* `NAO_EXECUTADO` (em fail.txt) = o comando nem rodou porque o degrau anterior da escada falhou.

Para ver só um comando, abra `por_comando/<comando>/pass.txt` ou `fail.txt`.

## Investigando uma reprovação (exemplo)

"Por que a linha 55 foi reprovada no Correctness?"
1. `por_comando/3_opa_eval/fail.txt`, procure `linha=55`: o motivo lista as regras que deram false.
2. `verificacoes/linha_0055/3_opa_eval/regras_avaliadas.json`: o valor de cada regra.
3. Compare `verificacoes/linha_0055/3_opa_eval/intent.rego` com `codigo_avaliado.tf`. Neste caso, a policy exige um recurso chamado `my_bucket`, mas o Reference output o chama de `test`: é um problema do próprio dataset.
