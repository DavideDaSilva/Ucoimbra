# Problemas comuns e soluções

| Mensagem ou sintoma | Causa provável | O que fazer |
|---|---|---|
| `Programa nao encontrado: 'terraform'` (ou opa, tflint, checkov) | programa não instalado ou fora do PATH | instale (ver `02_instalacao_e_execucao_passo_a_passo.md`) ou coloque o caminho completo em `verificadores.programas` |
| `Falta o pacote PyYAML` | pacotes Python não instalados | ative o ambiente virtual e rode `pip install -r requirements.txt` |
| `Nao encontrei o programa 'moto_server'` | moto não instalado | `pip install "moto[server]"` |
| `O simulador moto nao respondeu` | porta 5555 ocupada | mude `endereco_moto` para `http://127.0.0.1:5556` |
| `tflint --init` falha com "rate limit" | limite de downloads anônimos do GitHub | defina `GITHUB_TOKEN` com um token gratuito do GitHub |
| `terraform init` falha em tudo na primeira vez | sem internet (precisa baixar o provider AWS, cerca de 150 MB) | conecte-se; depois o provider fica em `ferramentas/cache/` |
| `Unsupported Terraform Core version` no motivo | o código exige outra versão do Terraform (`~> 1.9.8`) | esperado com a configuração padrão (ver `06_decisoes_e_limitacoes.md`, item 8) |
| `failed to get shared config profile, admin-1` | o código usa um perfil AWS que não existe na sua máquina | mesmo caso acima |
| `Your query returned no results` no terraform plan | o simulador não tem a imagem (AMI) procurada | limitação do simulador; o cenário é reprovado |
| "so foram encontrados X de 3 exemplos" | critérios estritos demais | veja `relatorio_da_busca.csv` e afrouxe o critério que mais reprova |
| Erro ao ler o dataset `.ods` | aba com outro nome | ajuste `dataset.aba_planilha` ou use `dados/iac_eval.csv` |
| Windows: erro ao ativar o ambiente virtual | política do PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (uma vez) |
