# Problemas comuns e soluções

| Mensagem ou sintoma | Causa provável | O que fazer |
|---|---|---|
| `Programa nao encontrado: 'terraform'` (ou opa, tflint, checkov) | programa não instalado ou fora do PATH | instale (ver `02_instalacao_passo_a_passo.md`) ou coloque o caminho completo em `configuracao.yaml`, seção `verificadores.programas` |
| `Nao consegui falar com o Ollama` | Ollama fechado | abra o aplicativo do Ollama ou rode `ollama serve` |
| `Modelo 'X' nao encontrado no Ollama` | modelo não baixado ou nome diferente | rode `ollama list` e copie o nome exato para `configuracao.yaml`; ou `ollama pull X` |
| `Nao encontrei o programa 'moto_server'` | moto não instalado | `pip install "moto[server]"` (com o ambiente virtual ativado) |
| `O simulador moto nao respondeu` | porta 5555 ocupada | mude `endereco_moto` para outra porta, ex.: `http://127.0.0.1:5556` |
| `tflint --init` falha com "rate limit" | limite de downloads anônimos do GitHub | crie um token gratuito no GitHub e defina `GITHUB_TOKEN` (ver instalação, passo 8) |
| `terraform init` falha em todos os cenários | sem internet na primeira execução (precisa baixar o provider AWS, cerca de 150 MB) | conecte-se e rode de novo; depois disso o provider fica em `ferramentas/cache/` |
| Correctness 0 em quase tudo, até em respostas que parecem certas | as policies do IaC-Eval são muito exigentes (nomes, atributos exatos) | é esperado. O Projeto 3 vai medir quanto o próprio Reference output passa |
| `opa eval terminou com erro` | erro de sintaxe na policy Rego do dataset | veja `3_opa_eval/saida_opa_eval.txt`. É um problema do dataset, não do modelo. O Projeto 3 identifica esses casos |
| Muitas respostas com `HCL: nenhum` | o modelo não usa as tags `<final_terraform_config>` | é uma falha do modelo pelo protocolo. Veja em `geracao.json` o campo `teria_hcl_pela_regra_alternativa` |
| Alerta "o prompt pode ter sido cortado" | prompt maior que `num_ctx` | aumente `ollama.opcoes.num_ctx` (ex.: 16384) e rode `gerar --refazer` para o modelo afetado |
| Alerta "resposta cortada" | resposta maior que `num_predict` | aumente `ollama.opcoes.num_predict` |
| A tabela diz `INCOMPLETO` | ainda há cenários não gerados ou não avaliados | rode `gerar` e `avaliar` de novo (só o que falta é feito) |
| Quero apagar tudo e começar do zero | | apague a pasta `resultados/` (não apague `ferramentas/cache/`) |
| Windows: erro de permissão ao ativar o ambiente virtual | política do PowerShell | rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` uma vez |
