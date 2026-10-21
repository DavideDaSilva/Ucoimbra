# Projeto 2: geração e avaliação de Terraform com LLMs (IaC-Eval, 3-shot, pass@1)

Este projeto produz os números da tabela **"Evaluation on IaC-Eval"** (formato da Table 2 do paper TerraFormer) para 8 modelos open source rodando localmente no computador do usuário pelo **Ollama**:

| Model | #Params | Correctness(%) | Deployability(%) | Compilability(%) | Linter Pass Rate(%) | SecurityCompliance(%) |
|---|---|---|---|---|---|---|
| deepseek-coder-v2:16b | 8.9 GB | ... | ... | ... | ... | ... |
| ... | | | | | | |

Ele implementa a **Figure 1** dos slides (as 5 etapas), usando os **3 exemplos fixos** escolhidos no **Projeto 1**.

## Início rápido

```bash
cd projeto2_avaliacao_llms
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# instale também Terraform 1.12.0, OPA e TFLint (docs/02_instalacao_passo_a_passo.md)

# copie o resultado do Projeto 1:
#   ../projeto1_selecao_exemplos_fixos/resultados/exemplos_fixos.json  ->  entrada/exemplos_fixos.json

python executar.py verificar-ambiente   # tudo [OK]?
python executar.py preparar             # escolhe os 30 cenários; salva um prompt de exemplo
python executar.py gerar                # os modelos respondem (pode levar horas; pode interromper e continuar)
python executar.py avaliar              # os 5 verificadores
python executar.py tabela               # a tabela final em resultados/tabela/
```

## O experimento em números

* 6 dificuldades × 5 cenários = **30 cenários** por modelo (os 3 exemplos fixos ficam de fora)
* 8 modelos × 30 cenários = **240 códigos** por setting
* Setting **A** (Prompt-only, igual ao paper) e Setting **B** (Prompt + Intent): 480 gerações no total
* Uma resposta por cenário (**pass@1**), temperature 0

## As 5 etapas e onde estão

| Etapa (Figure 1) | Pasta |
|---|---|
| 1. IaC-Eval dataset | `pipeline/etapa1_dataset/` |
| 2. Prompt Builder (template do TerraFormer + 3 exemplos) | `pipeline/etapa2_prompt_builder/` |
| 3. Generation (Ollama, extração do HCL) | `pipeline/etapa3_geracao/` |
| 4. Automatic evaluation | `pipeline/etapa4_avaliacao/` + `verificadores/` |
| 5. Results (tabela) | `pipeline/etapa5_resultados/` |

Cada verificador tem a sua pasta: `verificadores/fv1_terraform_validate/`, `fv2_terraform_plan/`, `fv3_opa_eval/`, `tflint_linter/` e `checkov_seguranca/`.

## Onde estão os PASS e FAIL

Para cada setting e modelo, em `resultados/setting_A/<modelo>/`:
* `pass.txt` e `fail.txt`: cada linha diz **qual comando**, qual cenário e o motivo;
* `por_comando/<n>_<comando>/pass.txt` e `fail.txt`: os mesmos registros separados por comando.

## Deployability sem pagar nada

O `terraform plan` roda com **credenciais AWS falsas** e um **simulador gratuito da AWS (moto)** no seu computador. Nada é criado em nuvem nenhuma. Detalhes em `docs/06_deployability_sem_credenciais.md`.

## Documentação (leia nesta ordem)

1. `docs/01_visao_geral_e_fluxo.md`: o que é medido e como o código está organizado
2. `docs/02_instalacao_passo_a_passo.md`: instalação de tudo, do zero
3. `docs/03_passo_a_passo_do_teste.md`: como rodar o teste, comando por comando
4. `docs/04_como_a_tabela_e_calculada.md`: **as contas da tabela, com exemplo**
5. `docs/05_os_5_verificadores.md`: cada verificador, comando e critério de PASS/FAIL
6. `docs/06_deployability_sem_credenciais.md`: como o plan funciona sem conta AWS
7. `docs/07_prompt_builder_e_settings.md`: o prompt, os settings A e B e a extração do HCL
8. `docs/08_estrutura_de_pastas_e_arquivos.md`: o que é cada pasta e arquivo
9. `docs/09_decisoes_reproducao_e_limitacoes.md`: decisões, achados sobre o dataset, reprodutibilidade
10. `docs/10_problemas_comuns.md`: erros comuns e soluções

## Relação com os outros projetos

* **Projeto 1** (`projeto1_selecao_exemplos_fixos`): escolhe os 3 exemplos fixos. Este projeto lê o resultado dele (`entrada/exemplos_fixos.json`).
* **Projeto 3** (a fazer): vai testar o Reference output de cada cenário avaliado aqui. A lista está em `resultados/cenarios_selecionados.csv`.
