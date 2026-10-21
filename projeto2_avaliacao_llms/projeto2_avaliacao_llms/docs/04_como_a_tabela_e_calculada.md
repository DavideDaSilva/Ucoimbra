# Como a tabela é calculada (passo a passo, com exemplo)

## A tabela final

```
Evaluation on IaC-Eval
| Model | #Params | Correctness(%) | Deployability(%) | Compilability(%) | Linter Pass Rate(%) | SecurityCompliance(%) |
```
Uma linha por modelo. Uma tabela por setting (A e B). O `#Params` é o texto que você colocou em `configuracao.yaml` (o SIZE do `ollama list`).

## Passo 1. Cada cenário recebe 5 notas

Para cada modelo, cada um dos N = 30 cenários recebe:

| Métrica | Valor possível | Vale 1 quando |
|---|---|---|
| Compilability | 0 ou 1 | `terraform init` + `terraform validate` passam |
| Deployability | 0 ou 1 | `terraform plan` passa (só é testado se o validate passou) |
| Correctness | 0 ou 1 | `opa eval` com a Rego intent dá verdadeiro (só é testado se o plan passou) |
| Linter Pass | 0 ou 1 | TFLint não acha problema de gravidade "error" |
| Security | de 0 a 1 | nota do Checkov = passed / (passed + failed) |

Resposta sem HCL (o modelo não usou as tags `<final_terraform_config>`): as 5 notas valem 0.

Essas notas ficam em `resultados/tabela/resultados_por_cenario_setting_A.csv`.

## Passo 2. Somar as notas de cada coluna

Para cada modelo, some as 30 notas de cada métrica.

## Passo 3. Transformar em porcentagem

```
Compilability(%)      = 100 × (soma das notas de Compilability) / N
Deployability(%)      = 100 × (soma das notas de Deployability) / N
Correctness(%)        = 100 × (soma das notas de Correctness) / N
Linter Pass Rate(%)   = 100 × (soma das notas de Linter Pass) / N
SecurityCompliance(%) = 100 × (soma das notas de Security) / N
```
As quatro primeiras são "quantos % dos cenários passaram". A última é "a nota média de segurança, em %". É exatamente a regra dos slides: *"Metric (%) = 100 × instances with value 1 / N"* e *"Security Compliance é a média das notas por instância"*.

O resultado é arredondado para 2 casas decimais, como no paper.

## Exemplo completo (números inventados, só para ensinar a conta)

Imagine um modelo com N = 30 cenários e estas somas:

| Métrica | Soma das 30 notas | Conta | Resultado |
|---|---|---|---|
| Compilability | 21 | 100 × 21 / 30 | **70.00** |
| Deployability | 15 | 100 × 15 / 30 | **50.00** |
| Correctness | 6 | 100 × 6 / 30 | **20.00** |
| Linter Pass | 27 | 100 × 27 / 30 | **90.00** |
| Security | 14.2500 | 100 × 14.25 / 30 | **47.50** |

Para a Security, a soma vem de notas fracionadas. Por exemplo, se três cenários tiveram notas 0,3333, 1,0000 e 0,5000, eles contribuem 0,3333 + 1,0000 + 0,5000 = 1,8333 para a soma.

A linha da tabela fica:
```
| modelo-x | 4.7 GB | 20.00 | 50.00 | 70.00 | 90.00 | 47.50 |
```

## Passo 4. Conferências automáticas

O arquivo `calculos_detalhados_setting_A.md` mostra, para cada modelo:
* a tabela das 30 notas, cenário por cenário, com a linha de soma;
* a conta de cada porcentagem (como no exemplo acima);
* quantas respostas vieram sem HCL;
* a conferência **Correctness ≤ Deployability ≤ Compilability** em cada cenário. Se aparecer "VIOLADA", há erro no pipeline (pela construção da escada isso não deveria acontecer).

Se algum cenário ainda não foi avaliado, ele conta como 0 e a tabela avisa **INCOMPLETO (k/30 avaliados)**. Não publique uma tabela incompleta.

## Passo 5. Conferir na mão (opcional)

1. Abra `resultados/tabela/tabela_resultados.xlsx`, aba `Cenarios_A`.
2. Use o filtro da coluna `modelo` para ver só um modelo (30 linhas).
3. Some a coluna `correctness` (coluna I; ex.: `=SOMA(I2:I31)` no Excel em português ou `=SUM(I2:I31)` em inglês), multiplique por 100 e divida por 30.
4. O número tem que ser igual ao da aba `Tabela_A`.

## Tabela por dificuldade (extra)

`por_dificuldade_setting_A.md` repete as contas só com os 5 cenários de cada dificuldade (N = 5). Exemplo: Correctness da dificuldade 3 = 100 × (cenários de dificuldade 3 com Correctness 1) / 5. Ajuda a ver em que nível de dificuldade cada modelo começa a errar. Com N = 5, cada cenário vale 20 pontos percentuais, então trate essas diferenças com cautela.

## Comparação com o paper

* O paper usa os 455 cenários (N = 455). Aqui N = 30. A conta é a mesma; o número é uma estimativa com mais incerteza. Com N = 30, cada cenário vale 3,33 pontos percentuais.
* Para rodar com os 455, mude `cenarios.estrategia` para `"todos"` (demora cerca de 15 vezes mais).
