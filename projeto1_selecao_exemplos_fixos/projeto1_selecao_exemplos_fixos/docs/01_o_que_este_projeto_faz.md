# O que este projeto faz

## O problema

O template do TerraFormer (Projeto 2) mostra ao modelo **3 exemplos** de "pedido + código Terraform correto" antes de fazer o pedido de verdade (few-shot com 3 exemplos). Esses exemplos são **fixos**: os mesmos para todos os modelos e todos os cenários.

Os exemplos saem do próprio dataset IaC-Eval (colunas Prompt, Intent e Reference output). Mas um exemplo só é bom se o código dele for realmente correto. Por isso, **antes** de usar um exemplo, o seu Reference output precisa passar pelos mesmos 5 critérios usados para avaliar os modelos (etapa "4. Automatic Evaluation").

## O que o projeto faz, passo a passo

```
 dataset IaC-Eval (458 linhas)
          |
          v
 percorre as linhas em ordem: 0, 1, 2, ...
          |
          |  a linha serve? (dificuldade desejada, campos preenchidos,
          |                  recurso ainda não usado em outro exemplo)
          |         não -> pula para a próxima
          v         sim
 avalia o Reference output com os 5 verificadores
   [1] terraform validate   [2] terraform plan   [3] opa eval (Rego intent)
   [4] TFLint               [5] Checkov
          |
          |  passou em todos os critérios?
          |         não -> registra em fail.txt e vai para a próxima
          v         sim
 vira EXEMPLO FIXO (registra em pass.txt)
          |
          v
 já tem os 3? -> PARA a busca e salva os exemplos
```

## O que é salvo para cada exemplo

Conforme pedido: **Prompt, Rego intent, Reference output, Intent e a linha onde o exemplo está no dataset**, além da dificuldade, do tipo de recurso e do resultado das 5 verificações.

* `resultados/exemplos_fixos.json`: arquivo principal, lido pelo Projeto 2
* `resultados/exemplos_fixos.md`: a mesma coisa, para leitura
* `resultados/exemplos/exemplo_N_linha_XXXX/`: cada campo num arquivo (`prompt.txt`, `intent.txt`, `rego_intent.rego`, `reference_output.tf`, `metadados.json`)

### Sobre a "linha"

* **linha** (ou "linha no dataset"): contagem a partir de 0, a mesma numeração dos slides. Exemplo: linha 2 = "Set up an aws_route_53 zone named example53.com".
* **linha_na_planilha**: a linha onde o cenário aparece ao abrir o arquivo no Excel ou LibreOffice (= linha + 2, porque a linha 1 da planilha é o cabeçalho e a contagem começa em 1).

## Regras da busca (configuráveis em `configuracao.yaml`)

| Regra | Padrão | Explicação |
|---|---|---|
| `estrategia` | `uma_por_dificuldade` | 1 exemplo de cada dificuldade em `dificuldades_desejadas` |
| `dificuldades_desejadas` | `[1, 2, 3]` | como nos slides (linhas 2, 56 e 142 tinham dificuldades 1, 2 e 3) |
| `exigir_intent_preenchido` | `true` | o Intent dos exemplos aparece no Setting B do Projeto 2 |
| `evitar_recursos_repetidos` | `true` | não escolhe um cenário que use um tipo de recurso já presente em outro exemplo |
| `criterios.compilability`, `deployability`, `correctness`, `linter` | `true` | o verificador correspondente tem que passar |
| `criterios.security_minima` | `1.0` | nota mínima do Checkov (1.0 = todas as regras de segurança aprovadas) |

A alternativa `estrategia: "sequencial"` pega os primeiros N exemplos aprovados, de qualquer dificuldade (N = `quantidade_de_exemplos`).

## Por que `evitar_recursos_repetidos` vem ligado

Na primeira execução de teste, sem essa regra, os 3 exemplos escolhidos foram **todos de Elastic Beanstalk** (linhas 0, 49 e 142). Motivo: esse serviço tem poucas regras do Checkov e passa facilmente com nota 100%. Três exemplos do mesmo serviço ensinam pouco ao modelo. Com a regra ligada, os exemplos ficam variados.

## Resultado obtido no teste antes da entrega

Com a configuração padrão, a busca escolheu:

| Exemplo | Linha | Dificuldade | Recursos |
|---|---|---|---|
| 1 | 0 | 1 | aws_elastic_beanstalk_application |
| 2 | 65 | 2 | aws_ami (bloco data) |
| 3 | 146 | 3 | aws_iam_role, aws_kinesisanalyticsv2_application |

Esse teste usou OpenTofu 1.9.1 no lugar do Terraform. Na sua máquina, com Terraform 1.12.0, rode de novo: o resultado oficial é o da sua execução.

Por que não as linhas 2, 56 e 142 dos slides? A linha 2 (Route 53) tem nota 0,33 no Checkov (falta DNSSEC e log de consultas), a linha 56 (S3 versioning) tem nota 0,42, e a linha 142 usa Elastic Beanstalk, já usado pela linha 0. Para exigir menos da segurança, diminua `security_minima` (ex.: `0.3`).
