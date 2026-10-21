# Prompt Builder: como o prompt é montado (Figure 2)

## O template

O texto é o do paper TerraFormer, Apêndice B, quadro *"Prompt Template for few-shot inference of IaC generation"* (o prompt usado para todos os LLMs da Table 2). Está em `pipeline/etapa2_prompt_builder/template_terraformer.py`, dividido em blocos:

| Bloco | Conteúdo | Setting A | Setting B |
|---|---|---|---|
| [A] Role | "You are an expert Infrastructure-as-Code (IaC) developer..." | sim | sim |
| [B] Task + requirements | Terraform v1.12.0, passar em validate e plan, providers permitidos | sim | sim |
| [C] Few-shot examples | os 3 exemplos fixos: Prompt + Configuration | sim | sim, e cada exemplo também mostra "User intent:" |
| [D] User prompt | `<user_prompt>` Prompt do cenário `</user_prompt>` | sim | sim |
| [E] User intent | `<user_intent>` Intent do cenário `</user_intent>` | não | sim |
| [F] Output format | pedir a resposta entre `<final_terraform_config>` | sim | sim |

Única adaptação no texto do paper: no PDF algumas frases quebram de linha apenas porque a coluna é estreita (ex.: `**` no fim de uma linha e `valid**` no começo da seguinte). Essas quebras artificiais foram desfeitas. O bloco [E] não existe no paper; foi criado para o Setting B, como mostra a Figure 2.

## De onde vem cada pedaço

| Coluna do IaC-Eval | Vai para o prompt? |
|---|---|
| Prompt (do cenário avaliado) | sim, bloco [D] |
| Intent (do cenário avaliado) | só no Setting B, bloco [E] |
| Rego intent (do cenário avaliado) | **nunca**. Vai direto para o `opa eval` |
| Reference output (do cenário avaliado) | **nunca** |
| Prompt, Intent e Reference output dos **3 exemplos fixos** | sim, bloco [C] |

## Os dois settings

* **Setting A (Prompt-only):** o principal. Igual ao paper.
* **Setting B (Prompt + Intent):** complementar. Mede quanto ajuda dizer ao modelo, explicitamente, quais recursos e atributos serão conferidos. A diferença entre as tabelas A e B é "o ganho de informar o Intent".

19 dos 458 cenários do IaC-Eval não têm Intent. No Setting B, para esses cenários o bloco [E] é omitido e isso fica registrado em `geracao.json` (`bloco_E_intent_incluido: false`).

## Como conferir o prompt

* `python executar.py preparar` salva um exemplo de cada setting em `resultados/exemplo_de_prompt_setting_A.txt` e `_B.txt`.
* `python executar.py ver-prompt --linha 12 --setting B` mostra o prompt de qualquer cenário.
* Depois de gerar, o prompt exato de cada resposta fica em `resultados/setting_X/<modelo>/linha_XXXX/prompt_enviado.txt`.

## Parâmetros de geração (Ollama)

| Parâmetro | Valor | Por quê |
|---|---|---|
| `temperature` | 0 | sem aleatoriedade: protocolo pass@1 dos slides. (Seu script de exemplo usava 0.2; os slides pedem 0.) |
| `seed` | 42 | mesma semente para todos |
| `top_p`, `top_k` | 0.9, 40 | iguais ao seu script (com temperature 0 quase não têm efeito) |
| `num_ctx` | 8192 | **importante**: o padrão do Ollama é pequeno (2048 ou 4096 conforme a versão). O prompt com 3 exemplos pode passar disso e o Ollama corta o **começo** do prompt sem avisar. Se o número de tokens do prompt chegar perto do limite, `geracao.json` registra um alerta |
| `num_predict` | 4096 | tamanho máximo da resposta. Se a resposta for cortada por esse limite, `geracao.json` registra um alerta |

A chamada é feita para `POST http://127.0.0.1:11434/api/generate` com `"stream": false`, em `pipeline/etapa3_geracao/cliente_ollama.py`.

## Extração do HCL

Regra do protocolo: o HCL é o conteúdo entre `<final_terraform_config>` e `</final_terraform_config>`.

1. Se houver várias ocorrências, vale a última que não seja vazia nem o texto de exemplo do template.
2. Se dentro das tags houver cercas ```` ```hcl ... ``` ````, só o conteúdo delas é usado.
3. Sem tags: não há HCL (todas as métricas valem 0).

A opção `extracao.usar_bloco_de_codigo_sem_tags: true` aceita o último bloco ```` ```hcl ``` ```` quando não há tags. Mesmo com a opção desligada, `geracao.json` registra se a resposta **teria** HCL por essa regra (`teria_hcl_pela_regra_alternativa`), para você saber quantas respostas foram perdidas só por falta das tags.
