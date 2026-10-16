# Decisões e limitações

Todas as escolhas que não estavam definidas nos documentos de referência, o motivo de cada uma e onde mudar.

| # | Decisão | Padrão | Motivo | Onde mudar (`configuracao.yaml`) |
|---|---|---|---|---|
| 1 | Uma dificuldade por exemplo | dificuldades 1, 2 e 3 | igual aos slides (linhas 2, 56 e 142 = dificuldades 1, 2 e 3) | `selecao.estrategia`, `dificuldades_desejadas` |
| 2 | Ordem da busca | linhas em ordem crescente, a partir da 0 | simples e reproduzível; a busca para no 3º exemplo, como pedido | `selecao.linha_inicial` |
| 3 | Exigir Intent | sim | o Intent dos exemplos é mostrado no Setting B do Projeto 2 | `exigir_intent_preenchido` |
| 4 | Evitar recursos repetidos | sim | sem isso, os 3 exemplos saíram todos de Elastic Beanstalk | `evitar_recursos_repetidos` |
| 5 | Nota mínima do Checkov | 1.0 (100%) | leitura mais estrita de "passar pelos 5 critérios". Atenção: só 58 dos 458 Reference outputs (12,7%) têm nota 100%; a média é 53,9%. Há candidatos suficientes nas dificuldades 1 a 3, mas o critério favorece serviços com poucas regras de segurança | `criterios.security_minima` |
| 6 | TFLint | reprova só gravidade `error` | ver abaixo | `verificadores.tflint.gravidades_que_reprovam` |
| 7 | Deployability | credenciais falsas + simulador moto | não usar conta AWS paga (ver `04_deployability_sem_credenciais.md`) | `verificadores.deployability.modo` |
| 8 | `required_version = "~> 1.9.8"` e `profile = "admin-1"` | mantidos (o código falha) | um exemplo fixo não deve ensinar ao modelo algo que o template proíbe (`profile`) nem uma versão incompatível com Terraform 1.12.0 | `verificadores.neutralizar_required_version_e_profile` |
| 9 | Regra do OPA | igual ao IaC-Eval + exigir pelo menos uma regra `true` | evita aprovar uma policy que não produziu resultado | `verificadores.opa.exigir_pelo_menos_um_true` |

## Por que o TFLint reprova só gravidade "error"

Medimos os 458 Reference outputs:

| Regra | Aprovados |
|---|---|
| reprovar qualquer gravidade | 150 de 458 (32,8%) |
| reprovar só `error` | 450 de 458 (98,3%) |

Quase todas as reprovações da primeira linha são avisos "faltou fixar a versão do Terraform/provider". No paper, o Linter Pass Rate fica entre 90% e 100% para quase todos os modelos, o que só é compatível com a segunda regra. Para o modo rigoroso: `gravidades_que_reprovam: ["error", "warning", "info"]`.

## Achados sobre o dataset

* **Quebras de linha no .ods:** o leitor padrão do pandas junta as linhas de cada célula e destrói o Rego e o HCL. O projeto tem leitor próprio e já entrega `dados/iac_eval.csv` correto (458 linhas, conferido célula por célula contra a planilha).
* **205 Reference outputs** exigem Terraform 1.9.x (`~> 1.9.8`) e usam `profile = "admin-1"`. Não servem como exemplo fixo com a configuração padrão.
* **175 Reference outputs** consultam a AWS com blocos `data` (`aws_availability_zones`, `aws_ami`...). O simulador moto responde a essas consultas; um catálogo extra de imagens (Ubuntu 24.04/22.04/20.04, Amazon Linux 2023) foi acrescentado em `verificadores/fv2_terraform_plan/catalogo_amis_simulador.json`.
* Algumas policies Rego reprovam o próprio Reference output (ex.: linha 55). O Projeto 3 vai quantificar isso.

## Limitações

* O simulador moto não conhece tudo o que a AWS conhece; uma consulta muito específica pode falhar mesmo com o código correto.
* Teste antes da entrega: o projeto foi executado de ponta a ponta num ambiente Linux com OpenTofu 1.9.1 no lugar do Terraform (o site da HashiCorp não estava acessível nesse ambiente). Rode na sua máquina com Terraform 1.12.0 e use o seu resultado como oficial.
* Os verificadores deste projeto são **cópia idêntica** dos do Projeto 2 (pasta `verificadores/`). Os projetos foram mantidos separados, como pedido. Se alterar um verificador, copie a pasta `verificadores/` para o outro projeto, para que os dois avaliem do mesmo jeito.
