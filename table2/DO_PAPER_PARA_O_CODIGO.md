# De onde veio cada parte: o paper mapeado no código

Esta tabela liga cada decisão do projeto ao trecho correspondente do artigo.
Serve para conferência e para quem for continuar o trabalho depois.

| Trecho do paper | O que diz | Onde está no projeto |
|---|---|---|
| Seção 3, FV-i | `terraform validate` verifica sintaxe e consistência estrutural | `src/oracles/fv1_validate/oracle.py` |
| Seção 3, FV-ii | `terraform plan` gera o grafo de execução e checa viabilidade | `src/oracles/fv2_plan/oracle.py` |
| Seção 3, FV-iii | `opa eval` checa a política Rego contra o grafo do FV-ii | `src/oracles/fv3_opa/oracle.py` |
| Seção 3 | "cada estágio é estritamente mais forte que o anterior" | hierarquia em `src/evaluation/evaluate.py` |
| Seção 3 | error certificates produzidos na falha | `error.txt` escrito por `src/common/logbook.py` |
| Seção 6, métricas | Compilability, Deployability, Correctness | função `summarize` em `src/evaluation/evaluate.py` |
| Seção 6, métricas | Linter Pass Rate via TFLint | `src/metrics/tflint/metric.py` |
| Seção 6, métricas | Security Compliance via Checkov, média por instância | `src/metrics/checkov/metric.py` |
| Seção 6, protocolo | pass@1, uma única geração por instância | `src/generation/generate.py`, sem repetição |
| Seção 6, baselines | inferência few-shot com três exemplos em contexto | `data/few_shot/examples.json` |
| Equação 2 | recompensa em [0, 2] a partir do verificador | campo `reward` em `resultado.json` |
| Figura 4b | regras nomeadas `is_valid_*` dentro da política | convenção em `src/oracles/fv3_opa/oracle.py` |
| Apêndice A | Terraform v1.12.0 | `config/prompt.txt` e nota no guia |
| Apêndice B | template de prompt para geração de IaC | `config/prompt.txt` |
| Apêndice B | template de prompt para mutação de IaC | reservado para a fase 2, ver `src/mutation/` |
| Tabela 2 | negrito no melhor, sublinhado no segundo melhor | `rank_marks` em `src/reporting/build_table2.py` |
| Tabela 2 | ganhos entre parênteses sobre o modelo base | suportado por `table2.baseline_for_improvement`, sem uso nesta fase |

## Decisões que tivemos que tomar por conta própria

O paper não detalha tudo. Onde foi preciso decidir, decidimos assim e
registramos o motivo:

1. **Como contar regras de política reprovadas.** Em Rego, uma regra falsa fica
   indefinida e simplesmente some da saída. Por isso o projeto lê os nomes das
   regras direto do arquivo `.rego` e trata como reprovada toda regra declarada
   que não apareceu como verdadeira.

2. **Credenciais AWS.** O paper roda em um ambiente com credenciais. Aqui
   injetamos um arquivo de override com credenciais falsas e desligamos as
   chamadas de rede do provider, para que a falha medida seja do código gerado.
   O arquivo só é injetado quando o código realmente declara `provider "aws"`,
   porque o Terraform recusa um override de bloco inexistente.

3. **Denominador do Linter Pass Rate.** O paper não diz se instâncias que nem
   compilam entram na conta. Como o TFLint precisa conseguir ler o arquivo,
   adotamos por padrão o denominador das instâncias que passaram em FV-i, e
   deixamos a escolha configurável em `table2.denominators`.

4. **Instâncias sem nenhuma checagem do Checkov.** Elas ficam fora da média de
   Security Compliance por padrão, para não puxar a média para baixo com zeros
   artificiais. Também é configurável.

5. **Resposta sem código.** Quando o modelo não devolve nenhum bloco de código,
   a instância conta como reprovada nos três oráculos, o que é a leitura
   natural do protocolo pass@1.
