# Decisões, reprodutibilidade e limitações

Este documento registra **todas** as escolhas que não estavam definidas nos documentos de referência (paper, slides, guia e instruções), o motivo de cada uma e como mudá-la. Use-o para escrever a seção de metodologia.

## 1. Decisões tomadas

| # | Decisão | Padrão | Motivo | Onde mudar |
|---|---|---|---|---|
| 1 | Número de cenários | 5 por dificuldade (30 no total) | documento "Instruções-Geração-de-IaC" | `cenarios.quantidade_por_dificuldade` |
| 2 | Como escolher os 5 cenários | sorteio com semente 42 | no dataset, cenários parecidos ficam em linhas vizinhas (ex.: linhas 45 a 48 são todas Route 53). O sorteio dá uma amostra mais representativa e, com semente fixa, é sempre o mesmo | `cenarios.estrategia`, `cenarios.semente` |
| 3 | Settings | A e B | slides, Figure 2. A = paper; B = complementar | `settings` |
| 4 | Temperature | 0 | slides ("temperature 0", pass@1). Seu script usava 0.2 | `ollama.opcoes.temperature` |
| 5 | `num_ctx` | 8192 | o padrão do Ollama pode cortar o prompt de 3 exemplos sem avisar | `ollama.opcoes.num_ctx` |
| 6 | Extração sem tags | não aceita | slides: "No HCL means 0 on every metric" | `extracao.usar_bloco_de_codigo_sem_tags` |
| 7 | Deployability sem conta AWS | credenciais falsas + simulador moto | pedido explícito de não pagar nada (ver `06_deployability_sem_credenciais.md`) | `verificadores.deployability.modo` |
| 8 | Versão do provider AWS | `~> 5.0` quando o código não declara | o IaC-Eval foi escrito para a série 5.x; todos os testes ficam na mesma versão | `versao_provider_aws` |
| 9 | Regra do OPA | igual ao IaC-Eval + exigir pelo menos uma regra `true` | evita aprovar uma policy que não produziu resultado | `opa.exigir_pelo_menos_um_true` |
| 10 | TFLint | reprova só gravidade `error` | dados: com qualquer gravidade só 32,8% dos Reference outputs passariam; com `error`, 98,3%, compatível com os 90 a 100% do paper | `tflint.gravidades_que_reprovam` |
| 11 | Checkov sem nenhuma regra aplicável | nota 0 | não há evidência de conformidade | código: `verificadores/checkov_seguranca/verificador.py` |
| 12 | `required_version = "~> 1.9.8"` e `profile = "admin-1"` | mantidos (código falha) | o template exige Terraform 1.12.0 e proíbe `profile` | `neutralizar_required_version_e_profile` |
| 13 | #Params | SIZE do `ollama list` | pedido seu. Atenção: o paper usa número de parâmetros (ex.: 7B), não tamanho em disco | `modelos[].parametros` |

## 2. Achados sobre o dataset IaC-Eval (importantes para o Projeto 3)

Medidos sobre os 458 cenários:

* **Quebras de linha:** ao abrir o `.ods` com o leitor padrão do pandas, as quebras de linha de cada célula somem e o Rego e o HCL deixam de ser válidos. Este projeto tem um leitor próprio que preserva as quebras, e já entrega `dados/iac_eval.csv` correto.
* **205 Reference outputs** têm, ao mesmo tempo, `required_version = "~> 1.9.8"` (só aceita Terraform 1.9.x) e `profile = "admin-1"` (um perfil AWS do computador dos autores). Com o Terraform 1.12.0 do paper, eles falham já no `terraform init`.
* **175 Reference outputs** usam blocos `data "aws_..."` que consultam a AWS (99 `aws_availability_zones`, 42 `aws_ami`). Por isso o simulador moto é necessário. 33 procuram a imagem Ubuntu 24.04, que foi acrescentada ao catálogo do simulador.
* Há policies Rego que **reprovam o próprio Reference output**. Exemplo: linha 55, a policy exige um recurso chamado `my_bucket`, mas o Reference output o chama de `test`. É exatamente o que o Projeto 3 vai quantificar.
* Checkov nos próprios Reference outputs: só 58 de 458 (12,7%) têm nota 100%; a nota média é 53,9%. Ou seja, mesmo o código "de referência" do IaC-Eval tem Security Compliance perto de 54%. Isso ajuda a interpretar a coluna SecurityCompliance dos modelos.
* TFLint nos próprios Reference outputs: 450 de 458 (98,3%) passam com a regra padrão (só `error`).
* 19 cenários não têm Intent.
* 32 policies usam a sintaxe nova do Rego (`import rego.v1`); as outras 426 usam a sintaxe antiga (tratada com `--v0-compatible`).

## 3. Como garantir que o teste é reproduzível

1. **Fixe as versões das ferramentas** e anote-as no relatório: Terraform (1.12.0), OPA, TFLint e plugin AWS (0.40.0, em `.tflint.hcl`), Checkov, moto e a versão do Ollama. O comando `verificar-ambiente` mostra todas.
2. **Fixe os modelos**: o `ollama list` mostra um ID para cada modelo (ex.: `dae161e27b0e` para o qwen2.5-coder:7b). Se o modelo for atualizado, o ID muda. Anote os IDs.
3. **Não mude** `semente`, `temperature`, `seed`, `num_ctx` e `num_predict` entre modelos.
4. **Guarde a pasta `resultados/` inteira**: ela tem o prompt exato, a resposta exata e a saída de cada verificador. Com ela, qualquer pessoa confere qualquer número da tabela sem rodar os modelos de novo.
5. **Guarde `entrada/exemplos_fixos.json` e `resultados/cenarios_selecionados.csv`**: definem exatamente o que foi testado.
6. Se mudar uma regra de avaliação, rode `avaliar --refazer` e `tabela`; as respostas dos modelos não mudam.
7. Sugestão de organização para publicar: um repositório Git com os dois projetos, o `configuracao.yaml` usado e um arquivo `VERSOES.md` com a saída de `verificar-ambiente` e do `ollama list`. A pasta `resultados/` pode ir num arquivo .zip anexado.

## 4. Limitações (diga isso ao relatar)

* **N = 30** por modelo. Cada cenário vale 3,33 pontos percentuais; diferenças pequenas entre modelos podem ser acaso. O paper usa N = 455.
* **Deployability** foi medida com `terraform plan` usando credenciais simuladas e o simulador moto; nenhum recurso foi criado. O simulador não conhece tudo o que a AWS conhece.
* **Temperature 0 no Ollama** reduz muito, mas não elimina totalmente, variações entre execuções em hardwares diferentes.
* **Teste deste código:** antes da entrega, o pipeline completo (Projeto 1 e Projeto 2) foi executado de ponta a ponta num ambiente Linux, usando OpenTofu 1.9.1 no lugar do Terraform (o site da HashiCorp não estava acessível nesse ambiente) e um servidor falso do Ollama. Na sua máquina, com Terraform 1.12.0 e o Ollama real, os comandos são os mesmos.
