# Visão geral e fluxo do Projeto 2

## Em uma frase

Medimos o quanto cada LLM (rodando no seu computador pelo Ollama) consegue escrever código Terraform correto a partir de um pedido em linguagem natural, usando o mesmo protocolo da Table 2 do TerraFormer: **3 exemplos fixos no prompt (3-shot)** e **uma única resposta por pedido (pass@1)**.

## Os números do experimento

| Item | Valor | De onde vem |
|---|---|---|
| Dificuldades | 6 (1 a 6) | coluna `Difficulty` do IaC-Eval |
| Cenários por dificuldade | 5 | documento "Instruções-Geração-de-IaC" |
| Cenários por modelo (N) | 6 × 5 = **30** | |
| Modelos | **8** | `ollama list` |
| Códigos gerados por setting | 8 × 30 = **240** | |
| Settings | A (Prompt-only) e B (Prompt + Intent) | slides, Figure 2 |
| Total de gerações | 240 × 2 = **480** | (ou 240 se rodar só um setting) |

## O fluxo (Figure 1 dos slides) e onde está cada parte no código

```
 1. IaC-Eval dataset      2. Prompt Builder        3. Generation         4. Automatic evaluation      5. Results
 ┌───────────────┐       ┌──────────────────┐     ┌──────────────┐      ┌─────────────────────────┐  ┌────────────┐
 │ linha do CSV  │──────>│ template         │────>│ LLM (Ollama) │─────>│ validate -> plan -> opa │─>│ tabela no  │
 │ Prompt        │       │ TerraFormer      │     │ 1 resposta   │      │ TFLint, Checkov         │  │ formato da │
 │ Intent        │       │ + 3 exemplos     │     │ extrai HCL   │      │                         │  │ Table 2    │
 │ Rego intent ──┼───────┼──────────────────┼─────┼──────────────┼─────>│ (Rego vai DIRETO para o │  │            │
 │ Ref. output   │       │                  │     │              │      │  avaliador, nunca ao LLM)│  │            │
 └───────────────┘       └──────────────────┘     └──────────────┘      └─────────────────────────┘  └────────────┘
 pipeline/               pipeline/                pipeline/             pipeline/etapa4_avaliacao/    pipeline/
 etapa1_dataset/         etapa2_prompt_builder/   etapa3_geracao/       + verificadores/ (5 pastas)   etapa5_resultados/
```

| Etapa | Pasta | Arquivos principais | O que faz |
|---|---|---|---|
| 1 | `pipeline/etapa1_dataset/` | `carregar_dataset.py`, `selecionar_cenarios.py` | lê o IaC-Eval; tira os 3 exemplos fixos; sorteia 5 cenários por dificuldade |
| 2 | `pipeline/etapa2_prompt_builder/` | `template_terraformer.py`, `montar_prompt.py` | monta o texto do prompt (blocos A a F) |
| 3 | `pipeline/etapa3_geracao/` | `cliente_ollama.py`, `gerar_respostas.py`, `extrair_hcl.py` | envia ao Ollama, guarda a resposta, extrai o HCL das tags |
| 4 | `pipeline/etapa4_avaliacao/` e `verificadores/` | `avaliar_respostas.py`, `escada_de_avaliacao.py` | roda os 5 verificadores e grava PASS/FAIL |
| 5 | `pipeline/etapa5_resultados/` | `calcular_tabela.py` | calcula as porcentagens e monta a tabela |

## Por que as etapas são separadas em comandos (`gerar`, `avaliar`, `tabela`)

* **Gerar** usa a placa de vídeo / memória (modelos grandes são lentos). **Avaliar** usa Terraform, OPA, TFLint e Checkov. Separando, você pode gerar tudo de noite e avaliar depois.
* As respostas ficam guardadas. Se você mudar algo na avaliação (ex.: a regra do TFLint), basta rodar `avaliar --refazer` e `tabela`, **sem gerar de novo**.
* Tudo pode ser interrompido (Ctrl+C) e continuado: o que já foi feito é pulado.

## O que nunca entra no prompt

* A **Rego intent** do cenário avaliado (é o "gabarito" do teste de Correctness).
* O **Reference output** do cenário avaliado (é a resposta certa).
* Os 3 exemplos fixos são **removidos** da lista de cenários avaliados, para que nenhum modelo seja avaliado num cenário cuja resposta está no próprio prompt.
