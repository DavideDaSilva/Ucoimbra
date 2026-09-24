# Reprodução da Tabela 2 do paper TerraFormer

Este projeto reproduz a **Tabela 2** do artigo *TerraFormer: Automated
Infrastructure-as-Code with LLMs Fine-Tuned via Policy-Guided Verifier
Feedback* (ICSE-SEIP 2026), usando **apenas modelos open source rodando
localmente via Ollama**.

Nesta primeira fase o projeto faz duas coisas:

1. a tarefa de **geração de código IaC** (prompt em linguagem natural para
   código Terraform);
2. a reconstrução dos **três oráculos de verificação formal** do paper.

A tarefa de **mutação de código (IaC mutation)** fica para depois. A estrutura
já está preparada para recebê-la, e a pasta `src/mutation/` explica o que
faltará fazer quando chegar a hora.

---

## 1. A ideia do projeto em cinco frases

1. Pegamos uma lista de pedidos escritos em inglês simples, do tipo "crie um
   bucket S3 com versionamento ligado".
2. Entregamos cada pedido a um modelo de linguagem que roda na sua máquina, e
   ele escreve um arquivo Terraform.
3. Passamos esse arquivo por três juízes automáticos, chamados de oráculos,
   que vão do mais leve ao mais rigoroso.
4. Cada juiz responde apenas "passou" ou "não passou", e quando não passa ele
   também devolve o texto do erro.
5. Contamos quantos pedidos cada modelo acertou e montamos a tabela.

---

## 2. Os três oráculos

O paper (Seção 3) define três verificadores formais. Cada um mora na sua
própria pasta dentro de `src/oracles/`.

| Oráculo | Ferramenta | Pergunta que ele responde | Métrica da tabela |
|---|---|---|---|
| **FV-i** | `terraform validate` | O código está escrito corretamente? | Compilability |
| **FV-ii** | `terraform plan` | Esse código seria realmente implantável? | Deployability |
| **FV-iii** | `opa eval` | O código faz o que o pedido pediu? | Correctness |

A ordem importa e é **hierárquica**, exatamente como no paper: para ser
correto, o código precisa antes ser implantável; para ser implantável, precisa
antes compilar. Se falhar em FV-i, os outros dois nem chegam a rodar e a
instância já conta como reprovada nos três.

Duas métricas auxiliares completam a tabela:

| Métrica | Ferramenta | O que mede |
|---|---|---|
| Linter Pass Rate | TFLint | Se o código segue boas práticas |
| Security Compliance | Checkov | Porcentagem de checagens de segurança aprovadas |

Nada é criado de verdade na nuvem. A verificação é toda **pré-deploy**, como
no paper.

---

## 3. O fluxo, do começo ao fim

```
           config/prompt.txt
                  +
   data/benchmark/<dataset>/instances.jsonl
                  |
                  v
     [ ETAPA 1 ] src/generation/generate.py
       envia o pedido ao modelo no Ollama
                  |
                  v
        results/generations/<modelo>/<dataset>/<id>/main.tf
                  |
                  v
     [ ETAPA 2 ] src/evaluation/evaluate.py
                  |
      +-----------+-----------+-----------+-----------+
      v           v           v           v           v
   FV-i        FV-ii       FV-iii      TFLint      Checkov
 validate       plan      opa eval
      |           |           |           |           |
      +-----------+-----------+-----------+-----------+
                  |
                  v
   results/evaluations/<modelo>/<dataset>/
        oracles/<oraculo>/pass.txt, fail.txt, error.txt
        instances/<id>/...
        resumo.json
                  |
                  v
     [ ETAPA 3 ] src/reporting/build_table2.py
                  |
                  v
          results/tables/tabela2.md (e .csv, .tex, .json)
```

---

## 4. Mapa das pastas

```
terraformer-repro/
├── README.md                      <- este arquivo
├── GUIA_PASSO_A_PASSO.md          <- o tutorial completo, comando por comando
├── requirements.txt
│
├── config/
│   ├── config.yaml                <- ÚNICO arquivo que você edita no dia a dia
│   ├── config.autoteste.yaml      <- cópia usada só pelo autoteste
│   ├── prompt.txt                 <- o prompt de geração (Apêndice B do paper)
│   └── provider_override.tf       <- faz o terraform plan rodar sem conta AWS
│
├── data/
│   ├── few_shot/examples.json     <- os 3 exemplos em contexto
│   └── benchmark/
│       ├── iac_eval/
│       │   ├── instances.jsonl    <- os pedidos
│       │   └── policies/*.rego    <- as políticas (testes unitários)
│       └── tf_gen_test/
│           ├── instances.jsonl
│           └── policies/*.rego
│
├── src/
│   ├── common/                    <- configuração, execução de comandos, logs
│   │   ├── config.py
│   │   ├── shell.py
│   │   ├── logbook.py             <- escreve pass.txt, fail.txt, error.txt
│   │   ├── naming.py
│   │   └── check_environment.py
│   ├── generation/                <- ETAPA 1
│   │   ├── ollama_client.py
│   │   ├── prompt_builder.py
│   │   └── generate.py
│   ├── oracles/                   <- ETAPA 2, cada oráculo em sua pasta
│   │   ├── base.py
│   │   ├── fv1_validate/oracle.py
│   │   ├── fv2_plan/oracle.py
│   │   └── fv3_opa/oracle.py
│   ├── metrics/                   <- métricas auxiliares, também separadas
│   │   ├── tflint/metric.py
│   │   └── checkov/metric.py
│   ├── evaluation/evaluate.py     <- junta oráculos e métricas
│   ├── reporting/build_table2.py  <- ETAPA 3
│   ├── data_tools/import_iac_eval.py
│   └── mutation/README.md         <- fase 2, ainda não implementada
│
├── scripts/                       <- atalhos prontos
│   ├── 00_conferir_ambiente.sh
│   ├── 01_gerar.sh
│   ├── 02_avaliar.sh
│   ├── 03_montar_tabela2.sh
│   ├── 04_autoteste.sh
│   └── 99_pipeline_completo.sh
│
├── tests/                         <- autoteste com ferramentas falsas
└── results/                       <- tudo o que o projeto produz
```

---

## 5. Onde ficam os resultados de pass, fail e error

Este é um requisito central do projeto. Cada informação devolvida pelos
comandos é gravada em arquivo `.txt` separado, em **dois níveis**.

**Nível 1, agregado por oráculo** (bom para ter a visão geral):

```
results/evaluations/<modelo>/<dataset>/oracles/
├── fv1_validate/   pass.txt   fail.txt   error.txt
├── fv2_plan/       pass.txt   fail.txt   error.txt
├── fv3_opa/        pass.txt   fail.txt   error.txt
├── tflint/         pass.txt   fail.txt   error.txt
└── checkov/        pass.txt   fail.txt   error.txt
```

**Nível 2, por instância** (bom para investigar um caso específico):

```
results/evaluations/<modelo>/<dataset>/instances/tfgen_001/
├── fv1_validate/   pass.txt   fail.txt   error.txt
├── fv2_plan/       ...
├── fv3_opa/        ...
├── resultado.json
└── workdir/        main.tf, plan.json, saídas brutas das ferramentas
```

Cada registro dentro desses arquivos identifica o comando ao qual pertence:

```
==============================================================================
DATA/HORA .......: 2026-09-22 19:28:34
INSTANCIA .......: tfgen_002
ORACULO/METRICA .: FV-iii (opa eval)
ETAPA ...........: opa eval da politica formal
COMANDO .........: opa eval --format json --data .../tfgen_002.rego --input .../plan.json data.terraform.policy
CODIGO DE SAIDA .: 0
RESULTADO .......: FAIL
------------------------------------------------------------------------------
Regras da politica: 4
Regras aprovadas ..: 1
Regras reprovadas .: 3
Lista de regras reprovadas:
  - is_valid_dns_hostnames
  - is_valid_internet_gateway
  - is_valid_subnet
==============================================================================
```

O `error.txt` guarda o que o paper chama de **error certificate**: o texto de
diagnóstico que, na fase futura de treinamento, alimenta o laço de reparo
(multi-turn repair loop).

---

## 6. Como as políticas Rego são escritas

A política funciona como um **teste unitário da infraestrutura**. Ela recebe o
JSON do `terraform plan` e verifica se o que o modelo gerou atende ao pedido.

Convenção deste projeto, alinhada com a Figura 4b do paper:

- o pacote é sempre `package terraform.policy`;
- toda regra de verificação se chama `is_valid_<alguma_coisa>`;
- cada regra vale um ponto;
- **Correctness exige que todas as regras passem**;
- a razão (regras aprovadas dividido pelo total) também é gravada, porque é
  exatamente o valor usado na recompensa da Equação 2 do paper, que será útil
  na fase futura de aprendizado por reforço.

Exemplo mínimo:

```rego
package terraform.policy

import rego.v1

resources contains r if {
	walk(input.planned_values, [path, value])
	path[count(path) - 1] == "resources"
	some r in value
}

is_valid_s3_bucket if {
	some r in resources
	r.type == "aws_s3_bucket"
	r.values.bucket == "app-artifacts-2026"
}
```

---

## 7. Por onde começar

Leia o **GUIA_PASSO_A_PASSO.md**. Ele traz, em ordem e sem pular nada:
instalação das ferramentas, verificação do ambiente, geração, avaliação e
construção da Tabela 2.

Se quiser apenas confirmar que o código funciona, sem instalar nada:

```bash
bash scripts/04_autoteste.sh
```

---

## 8. Diferenças honestas em relação ao paper

Vale deixar registrado, para que os resultados não sejam lidos como
equivalentes aos do artigo:

1. **Modelos.** O paper avalia 17 modelos, incluindo Sonnet 3.7, GPT-4.1 e
   DeepSeek-R1 de 671B. Aqui só entram modelos open source que cabem na sua
   máquina via Ollama. Os números serão naturalmente menores.
2. **Linhas TerraFormer.** As linhas do modelo ajustado (SFT e SFT+RL) não
   aparecem, porque o fine-tuning não faz parte desta fase.
3. **Dataset TF-Gen (Test).** O TF-Gen do paper não é público. O projeto vem
   com um conjunto pequeno de instâncias de exemplo no mesmo formato, para
   você validar o pipeline, e você pode substituí-lo pelo seu próprio conjunto.
4. **IaC-Eval.** É público. Use `src/data_tools/import_iac_eval.py` para
   importar as 458 instâncias reais.
5. **Ambiente AWS.** O paper roda `terraform plan` em um ambiente com
   credenciais. Aqui usamos credenciais falsas e um arquivo de override, para
   que a falha medida seja do código gerado, não da falta de conta AWS.
