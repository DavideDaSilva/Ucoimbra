# Fase 2 (ainda NAO implementada): IaC Mutation

Esta pasta esta reservada de proposito. Ela existe para deixar claro onde a
segunda tarefa do paper vai morar, sem atrapalhar a fase atual.

## O que e a tarefa de mutacao

Enquanto a geracao parte do zero (prompt em linguagem natural -> codigo
Terraform), a mutacao parte de uma configuracao que ja existe:

    entrada: configuracao inicial + prompt de mudanca
    saida:   configuracao modificada

E a Tabela 3 do paper.

## O que ja esta pronto para ser reaproveitado

Tudo o que e caro de construir ja existe e nao muda:

- os tres oraculos em `src/oracles/` funcionam igual, pois avaliam um
  arquivo Terraform, nao importa como ele nasceu;
- as metricas TFLint e Checkov em `src/metrics/`;
- o registro em pass.txt, fail.txt e error.txt em `src/common/logbook.py`;
- o montador de tabela em `src/reporting/`, que so precisa de outro conjunto
  de colunas.

## O que precisara ser escrito quando chegar a hora

1. `config/prompt_mutacao.txt` com o template de mutacao do Apendice B.
2. `src/mutation/generate_mutation.py`, parecido com
   `src/generation/generate.py`, mas enviando tambem a configuracao inicial.
3. Um dataset em `data/benchmark/tf_mutn_test/` com quatro campos por
   instancia: prompt de mutacao, configuracao inicial, politica inicial e
   politica alvo.
4. `src/reporting/build_table3.py`, uma copia adaptada do montador atual.

Nenhuma dessas mudancas exige mexer nos oraculos.
