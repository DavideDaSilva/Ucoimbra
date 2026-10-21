# Os 5 verificadores (etapa "4. Automatic Evaluation")

Este documento explica, sem supor nenhum conhecimento prévio, o que cada verificador faz, qual comando ele roda, quando o resultado é **PASS** ou **FAIL** e onde ficam os arquivos.

O código de cada verificador fica em **uma pasta própria**:

| Pasta | Verificador | Métrica da tabela |
|---|---|---|
| `verificadores/fv1_terraform_validate/` | `terraform validate` (FV-i) | Compilability |
| `verificadores/fv2_terraform_plan/` | `terraform plan` (FV-ii) | Deployability |
| `verificadores/fv3_opa_eval/` | `opa eval` com a Rego intent (FV-iii) | Correctness |
| `verificadores/tflint_linter/` | TFLint + regras AWS | Linter Pass Rate |
| `verificadores/checkov_seguranca/` | Checkov | Security Compliance |

O arquivo `verificadores/escada_de_avaliacao.py` é o "maestro": ele chama os 5 na ordem certa.

## A escada (Figure 3 dos slides)

```
                    código HCL extraído
                           |
        +------------------+-----------------------------+
        |  ESCADA (um degrau depois do outro)            |  EM PARALELO (sempre que há HCL)
        v                                                v
  [1] terraform validate  -> Compilability          [4] TFLint  -> Linter Pass
        |  só sobe se passou                         [5] Checkov -> Security Compliance
        v
  [2] terraform plan      -> Deployability
        |  só sobe se passou
        v
  [3] opa eval (Rego)     -> Correctness
```

* Se um degrau falha, ele vale **0** e os degraus de cima ficam **NAO_EXECUTADO** (também valem 0). São as setas vermelhas da Figure 3.
* Por isso, em qualquer cenário: **Correctness ≤ Deployability ≤ Compilability**. A tabela final confere isso automaticamente.
* TFLint e Checkov rodam sempre que existe HCL, **mesmo que o código não compile**.
* Se **não existe HCL** (o modelo não respondeu dentro das tags), as 5 métricas valem 0.

## [1] terraform validate → Compilability

**Pergunta que responde:** o código está escrito corretamente? (sintaxe certa, nenhuma referência a algo que não existe)

**Comandos:**
```
terraform init -backend=false -input=false -no-color
terraform validate -no-color
```
O `init` baixa os "providers" (os plugins que conhecem a AWS). Sem ele o `validate` não funciona. Para não baixar tudo de novo a cada cenário, os providers ficam guardados em `ferramentas/cache/terraform_plugins`.

**PASS (1):** os dois comandos terminam sem erro (código de saída 0).
**FAIL (0):** qualquer um dos dois dá erro. O motivo diz qual.

**Arquivos:** `1_terraform_validate/saida_terraform_init.txt` e `saida_terraform_validate.txt`.

## [2] terraform plan → Deployability

**Pergunta que responde:** se fôssemos criar essa infraestrutura na AWS, o Terraform saberia montar um plano válido?

**Comandos:**
```
terraform plan -input=false -lock=false -no-color -out=plan.bin     (limite: 120 s)
terraform show -json plan.bin   -> plan.json
```
**Nada é criado.** O `terraform apply` nunca é executado. Como fazemos isso sem conta AWS está explicado em `06_deployability_sem_credenciais.md`.

**PASS (1):** o `plan` termina sem erro.
**FAIL (0):** erro ou tempo esgotado.
**NAO_EXECUTADO (0):** o validate não passou.

**Arquivos:** `2_terraform_plan/saida_terraform_plan.txt`, `saida_terraform_show.txt` e `plan.json`.

## [3] opa eval → Correctness

**Pergunta que responde:** a infraestrutura faz exatamente o que o usuário pediu?

Quem decide é a coluna **Rego intent** do IaC-Eval: um pequeno programa na linguagem Rego que lê o `plan.json` e responde verdadeiro ou falso para cada exigência. O modelo **nunca vê** essa policy (seta verde tracejada da Figure 1): ela vai direto do dataset para o avaliador.

**Comando:**
```
opa eval [--v0-compatible] -i plan.json -d intent.rego data --format json
```
* `data` pede ao OPA o valor de todas as regras da policy.
* `--v0-compatible`: as policies do IaC-Eval usam a sintaxe antiga do Rego. O OPA 1.x usa a sintaxe nova por padrão e recusaria essas policies. Quando a policy **não** tem `import rego.v1` e o OPA instalado é 1.x, a opção é acrescentada automaticamente.

**Regra de decisão** (a mesma do código original do IaC-Eval, arquivo `evaluation/eval.py`):
* se **alguma** regra der `false` → FAIL (0);
* se nenhuma der `false` → PASS (1);
* proteção extra (pode ser desligada em `opa.exigir_pelo_menos_um_true`): é preciso que pelo menos uma regra dê `true`, para não aprovar uma policy que não produziu resultado nenhum.

**Arquivos:** `3_opa_eval/intent.rego`, `saida_opa_eval.txt` e `regras_avaliadas.json` (cada regra e o seu valor).

## [4] TFLint → Linter Pass Rate

**Pergunta que responde:** o código segue as boas práticas do Terraform e da AWS? (ex.: tipo de instância EC2 que não existe, sintaxe obsoleta)

**Comando** (numa pasta separada, só com o `main.tf` e o arquivo de regras `.tflint.hcl`):
```
tflint --format=json --no-color
```
Na primeira vez é preciso baixar o plugin de regras AWS (`tflint --init`). O comando `verificar-ambiente` faz isso.

**PASS (1):** nenhum problema com gravidade listada em `tflint.gravidades_que_reprovam` (padrão: somente `error`).
**FAIL (0):** um ou mais problemas dessas gravidades, ou o TFLint não conseguiu ler o código.

**Por que o padrão é somente `error`?** Decisão baseada em dados. Medimos os 458 "Reference output" do IaC-Eval (código humano e correto):

| Regra de reprovação | Reference outputs aprovados |
|---|---|
| Qualquer gravidade (error, warning, info) | 150 de 458 (32,8%) |
| Somente `error` | 450 de 458 (98,3%) |

Quase todas as reprovações da primeira linha são avisos do tipo "faltou fixar a versão do Terraform ou do provider" (`terraform_required_version`, `terraform_required_providers`). No paper do TerraFormer, a coluna Linter Pass Rate fica entre 90% e 100% para quase todos os modelos, o que só é compatível com a segunda forma. Para o modo mais rigoroso, use `["error", "warning", "info"]`. Todos os problemas, de qualquer gravidade, ficam salvos em `problemas_tflint.json`.

**Arquivos:** `4_tflint/saida_tflint.txt` e `problemas_tflint.json`.

## [5] Checkov → Security Compliance

**Pergunta que responde:** o código tem configurações inseguras?

O Checkov aplica centenas de regras de segurança (ex.: "o bucket S3 está criptografado?", "o log de acesso está ligado?"). Cada regra que se aplica ao código termina como **passed** (aprovada) ou **failed** (reprovada).

**Comando** (numa pasta separada, só com o `main.tf`):
```
checkov -d . --framework terraform -o json --skip-download
```

**Nota do cenário** (número contínuo de 0 a 1):
```
nota = passed / (passed + failed)
```
Exemplo: 1 regra aprovada e 2 reprovadas → 1 / (1 + 2) = 0,3333.
Se nenhuma regra se aplicar (passed + failed = 0) a nota é 0.

**Status para os arquivos pass.txt / fail.txt:** PASS se nenhuma regra foi reprovada; FAIL caso contrário. A nota aparece sempre no campo `valor`.

**Arquivos:** `5_checkov/saida_checkov.txt` e `resumo_checkov.json` (lista das regras aprovadas e reprovadas).

## Onde ficam os registros PASS e FAIL

Cada resultado é gravado em uma linha de texto:

* **`pass.txt`**: todos os resultados PASS;
* **`fail.txt`**: todos os resultados FAIL e NAO_EXECUTADO;
* **`por_comando/1_terraform_validate/pass.txt`** (e `fail.txt`), e o mesmo para `2_terraform_plan`, `3_opa_eval`, `4_tflint` e `5_checkov`: os mesmos registros, separados por comando.

Exemplo de linha:
```
2026-10-16 19:16:17 | FAIL | comando=checkov | setting=A | modelo=qwen2.5-coder:7b | linha=45 | dificuldade=2 | valor=0.2500 | motivo=1 aprovadas, 3 reprovadas (nota 0.2500); reprovadas: CKV2_AWS_23, CKV2_AWS_38, CKV2_AWS_39
```
Lê-se: "no Setting A, o modelo qwen2.5-coder:7b, no cenário da linha 45 (dificuldade 2), **falhou no Checkov** com nota 0,25, e estas foram as regras reprovadas".
