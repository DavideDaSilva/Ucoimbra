# Pasta dados

`iac_eval.csv`: o dataset IaC-Eval completo (458 cenários; colunas Resource, Prompt,
Rego intent, Difficulty, Reference output, Intent), extraído da planilha enviada
(aba "dataset") com um leitor que preserva as quebras de linha de cada célula.
O conteúdo foi conferido célula por célula contra a planilha.

Para usar outro arquivo (.csv, .ods ou .xlsx) ou baixar do Hugging Face
(`autoiac-project/iac-eval`), mude `dataset.origem` no `configuracao.yaml`.
