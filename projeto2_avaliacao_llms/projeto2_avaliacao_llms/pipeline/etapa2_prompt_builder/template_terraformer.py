"""
ETAPA 2: template do TerraFormer para GERACAO de IaC, versao few-shot (3 exemplos).

Fonte: paper "TerraFormer: Automated Infrastructure-as-Code with LLMs Fine-Tuned
via Policy-Guided Verifier Feedback", Apendice B, quadro
"Prompt Template for few-shot inference of IaC generation"
(o mesmo prompt usado para todos os LLMs da Table 2).

O texto em ingles abaixo foi copiado do paper SEM ALTERACOES nos blocos
[A], [B], [C], [D] e [F]. Unica adaptacao: no PDF algumas frases quebram de
linha so porque a coluna e estreita (ex.: "**" no fim de uma linha e "valid**"
no inicio da seguinte). Essas quebras artificiais foram desfeitas.

O bloco [E] (user intent) NAO existe no paper: ele foi acrescentado para o
Setting B, conforme a Figure 2 dos slides.

Os blocos (Figure 2):
  [A] Role                    -> quem o modelo deve "ser"
  [B] Task + requirements     -> o que fazer e as regras (Terraform v1.12.0 etc.)
  [C] Few-shot examples       -> os 3 exemplos fixos (Prompt + Configuration)
  [D] User prompt             -> o Prompt do cenario avaliado (Settings A e B)
  [E] User intent (opcional)  -> o Intent do cenario avaliado (somente Setting B)
  [F] Output format           -> pedir a resposta entre <final_terraform_config>

Nunca entram no prompt: a Rego intent e o Reference output do cenario avaliado.
"""

BLOCO_A_ROLE = (
    "You are an expert Infrastructure-as-Code (IaC) developer with deep expertise in "
    "Terraform."
)

BLOCO_B_TAREFA = (
    "Your task is to:\n"
    "Given an user prompt, generate a **single**, **fully self-contained**, and "
    "**valid** Terraform configuration written in HCL. Your configuration must:\n"
    "- Satisfy the intent of the user prompt.\n"
    "- Be compatible with **Terraform v1.12.0**.\n"
    "- Pass both `terraform validate` and `terraform plan`.\n"
    "- Include a valid `provider` block.\n"
    "- Contain no undeclared variables or references.\n"
    "- Avoid the use of `assume_role`, custom `profile` values, or external "
    "dependencies.\n"
    "- Use only the following providers: `aws`, `random`, `null`, `local`, `template`, "
    "`tls`, `time`, `external`, `http`, `archive`, `docker`, `terraform`."
)

BLOCO_C_INTRODUCAO = "Here are a few examples:"

# Um exemplo do bloco [C]. {numero}, {prompt} e {configuracao} sao preenchidos.
# No Setting B acrescentamos a linha "User intent:" (Figure 2 dos slides).
BLOCO_C_EXEMPLO_SETTING_A = (
    "### Example-{numero}\n"
    "Prompt: {prompt}\n"
    "Configuration:\n"
    "```hcl\n"
    "{configuracao}\n"
    "```"
)

BLOCO_C_EXEMPLO_SETTING_B = (
    "### Example-{numero}\n"
    "Prompt: {prompt}\n"
    "User intent: {intent}\n"
    "Configuration:\n"
    "```hcl\n"
    "{configuracao}\n"
    "```"
)

BLOCO_D_USER_PROMPT = (
    "Here is the **actual** user prompt:\n"
    "<user_prompt>\n"
    "{prompt}\n"
    "</user_prompt>"
)

# Bloco [E]: somente Setting B. Texto curto, no mesmo estilo do paper.
BLOCO_E_USER_INTENT = (
    "Here is the user intent, which lists the resources and attributes that the "
    "configuration is expected to contain:\n"
    "<user_intent>\n"
    "{intent}\n"
    "</user_intent>"
)

BLOCO_F_FORMATO_SAIDA = (
    "Now respond to the actual user prompt by returning **one single** Terraform "
    "configuration. Do not repeat or revise the configuration. Importantly, enclose "
    "the final configuration inside the following tags:\n"
    "\n"
    "<final_terraform_config>\n"
    "(Provide your entire Terraform configuration within these tags)\n"
    "</final_terraform_config>"
)
