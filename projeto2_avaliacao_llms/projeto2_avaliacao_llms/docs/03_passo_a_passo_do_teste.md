# Passo a passo do teste (do zero até a tabela)

Pré-requisito: instalação concluída (`02_instalacao_passo_a_passo.md`) e `python executar.py verificar-ambiente` mostrando **TUDO PRONTO**.

Todos os comandos são digitados no terminal, dentro da pasta `projeto2_avaliacao_llms`, com o ambiente virtual ativado.

## Passo 1. Conferir a configuração

Abra `configuracao.yaml` num editor de texto. Os pontos que você talvez queira mudar:

| Campo | Padrão | Para que serve |
|---|---|---|
| `settings` | `["A", "B"]` | quais settings rodar. Para só o do paper: `["A"]` |
| `modelos` | os 8 modelos | nomes como em `ollama list` e o texto da coluna #Params |
| `cenarios.quantidade_por_dificuldade` | `5` | 5 × 6 dificuldades = 30 cenários |
| `cenarios.semente` | `42` | muda o sorteio dos cenários (mantenha fixo para reproduzir) |
| `ollama.opcoes.temperature` | `0` | 0 = sem aleatoriedade (protocolo pass@1) |

## Passo 2. Preparar (escolher os cenários)

```bash
python executar.py preparar
```
O que acontece:
1. lê o dataset (`dados/iac_eval.csv`, 458 cenários);
2. lê os 3 exemplos fixos (`entrada/exemplos_fixos.json`) e os tira da lista;
3. sorteia 5 cenários de cada dificuldade (sempre o mesmo sorteio, por causa da semente);
4. salva a lista em `resultados/cenarios_selecionados.csv` (abra no Excel para ver);
5. salva um prompt de exemplo de cada setting em `resultados/exemplo_de_prompt_setting_A.txt` e `_B.txt`. **Leia um deles**: é exatamente o que os modelos vão receber.

Para ver o prompt de qualquer cenário sem chamar modelo nenhum:
```bash
python executar.py ver-prompt --linha 12 --setting A
```

## Passo 3. Gerar as respostas (Etapas 2 e 3)

```bash
python executar.py gerar
```
Para cada modelo, setting e cenário: monta o prompt, envia ao Ollama, guarda a resposta e extrai o HCL. A tela mostra uma linha por cenário, por exemplo:
```
[qwen2.5-coder:7b] setting A | cenario 3/30 (linha 16, dificuldade 1)
   ok em 12.4 s | HCL: tags
```
`HCL: tags` = o código foi encontrado entre as tags. `HCL: nenhum` = o modelo não usou as tags (vai valer 0 em tudo).

Dicas:
* Pode demorar horas (o qwen2.5-coder:32b é o mais lento). Pode interromper com **Ctrl+C** e rodar o mesmo comando depois: o que já foi gerado é pulado.
* Para um modelo só: `python executar.py gerar --modelos "qwen2.5-coder:7b"`
* Para um setting só: `python executar.py gerar --settings A`
* Teste rápido primeiro: rode só o menor modelo (`qwen2.5:0.5b`) para ver se tudo funciona.

## Passo 4. Avaliar (Etapa 4)

```bash
python executar.py avaliar
```
Para cada resposta gerada, roda os 5 verificadores (ver `05_os_5_verificadores.md`). O simulador AWS (moto) é ligado e desligado automaticamente. A tela mostra:
```
[qwen2.5-coder:7b] setting A | avaliando cenario 3/30 (linha 16)
   compil=1 deploy=1 correct=0 linter=1 security=0.5000
```
Tempo: cerca de 15 a 30 segundos por cenário. Para 480 avaliações, conte algumas horas. Também pode ser interrompido e retomado.

Onde olhar os resultados de PASS/FAIL:
* `resultados/setting_A/<modelo>/pass.txt` e `fail.txt`
* `resultados/setting_A/<modelo>/por_comando/<comando>/pass.txt` e `fail.txt`
* `resultados/setting_A/<modelo>/linha_XXXX/avaliacao/` (saída completa de cada comando)

## Passo 5. Montar a tabela (Etapa 5)

```bash
python executar.py tabela
```
A tabela aparece na tela e é salva em `resultados/tabela/`:
* `tabela_setting_A.md` e `.csv`: **a tabela final**, no formato pedido;
* `calculos_detalhados_setting_A.md`: a conta de cada número;
* `por_dificuldade_setting_A.md`: os mesmos números separados por dificuldade;
* `tabela_resultados.xlsx`: tudo numa planilha.

Como cada número é calculado está em `04_como_a_tabela_e_calculada.md`.

## Atalho: tudo de uma vez

```bash
python executar.py tudo
```
Equivale a `preparar`, `gerar`, `avaliar` e `tabela`, nesta ordem.

## Se mudar alguma regra de avaliação depois

As respostas dos modelos ficam guardadas. Basta:
```bash
python executar.py avaliar --refazer
python executar.py tabela
```
