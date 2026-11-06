# Experimentos de Dados e IA — etapa 3

Primeiro ciclo implementado em **03/11/2026**. Os experimentos são offline, usam CPU e as dependências já fixadas em `backend/requirements-dev.lock`. Não acessam o banco de execução, não publicam conteúdo e não fazem chamadas a provedores. Os relatórios ficam na pasta de saída de cada execução.

A extensão de [auditoria integral](auditoria-acervo.md) lê uma cópia do catálogo instalado, verifica fontes, gabaritos, figuras, resultados e aparência e aplica os métodos selecionados às posições publicadas no banco escolhido. Seu instalador de correções técnicas é uma operação explícita, separada dos experimentos; propostas temáticas e de layout continuam sem publicação automática.

## Executar e reproduzir

```bash
make experiments

# Uma saída nova preserva as execuções anteriores.
make experiments EXPERIMENT_OUTPUT=tmp/experiments/ensaio-02

# Inclui os cadernos automáticos e desafios históricos disponíveis localmente.
make experiments-archive EXPERIMENT_OUTPUT=tmp/experiments/acervo-01
```

O clone contém tudo para a comparação temática e a amostra de layout. O comando do acervo usa os arquivos já gerados em `data/derived/exams/` e as fontes locais. Se faltarem, o relatório registra a ausência; não baixa arquivos nem confunde ausência com zero erros. A geração do acervo continua no [fluxo próprio](../preparacao-provas.md).

Comando completo e opções:

```bash
.venv/bin/python scripts/run_experiments.py \
  --config experiments/config.json \
  --output tmp/experiments/meu-ensaio \
  --archive --ocr --proposal-limit 500
```

`--only classification` e `--only layout` executam uma frente. Uma saída não vazia exige `--force`; apenas pastas dentro de `tmp/` ou `/tmp/` são aceitas. Configuração, seed, hashes dos dados e do código, versões do Python/pacotes, opções e horários ficam em `run.json`. Latências dependem da máquina e da carga; não são um teste de capacidade da aplicação. Somente um manifesto com `status: complete` identifica a conclusão; uma interrupção deixa `running`, inclusive ao regravar uma saída.

O workflow de CI executa o ciclo dos dados incluídos e guarda os relatórios, o modelo selecionado e a revisão local como artefato. A matriz de testes de backend também cobre as fronteiras dos experimentos. Não depende de acervo histórico, OCR ou conta externa.

Para gerar novamente o registro compacto de uma execução concluída, verificando seus hashes:

```bash
.venv/bin/python scripts/summarize_experiments.py tmp/experiments/meu-ensaio \
  --output tmp/experiments/meu-ensaio/resumo.json
```

## Classificação temática

O conjunto `adaptive-math-reference-v1` fornece **89 itens válidos em oito temas de Matemática**, com anotação técnica assistida. Os hashes do conteúdo classificado, das fontes e das identidades são conferidos antes da execução. Não é um benchmark pedagógico independente.

O protocolo inicial é de **um tema principal por item**. Natureza, habilidades oficiais e classificação multirrótulo exigem outro conjunto de avaliação; nenhuma habilidade candidata é promovida.

### Partições e entradas

- Agrupar primeiro por identidade canônica, `split_group` e assinatura textual conservadora, incluindo ligações transitivas. Duplicatas com rótulos conflitantes interrompem a divisão.
- Estratificar os grupos por tema, usando a seed versionada e hashes ordenados: **53 itens de treino, 18 de desenvolvimento e 18 de teste**. Os oito temas estão nas três partições.
- Usar somente os blocos de texto, tabelas, fórmulas explícitas e textos das alternativas. Não duplicar `statement` quando há `blocks`.
- Excluir rótulos, gabarito, anulação, ano, página, nome do arquivo, créditos, legendas e descrições editoriais de figuras. Os modelos textuais não observam a imagem.
- Ajustar vocabulário, contagens, IDF e centróides exclusivamente no treino. O manifesto exportado registra os grupos e hashes, permitindo auditar a separação.

A assinatura de texto é deliberadamente conservadora: pode exigir adjudicação adicional antes de um conjunto maior. Os vínculos conferidos entre cores continuam no catálogo; não se alega deduplicação semântica de todo o acervo.

### Comparação

| Abordagem | Entrada e ajuste |
| --- | --- |
| Maioria | Classe mais frequente do treino; referência mínima. |
| Palavras-chave | Regras por tema, fixadas no arquivo de configuração antes da avaliação. |
| Naive Bayes multinomial | Contagens de palavras, prior por classe e suavização aditiva. |
| Centróides TF-IDF de palavras | Unigramas/bigramas; média dos vetores por classe e similaridade cosseno. |
| Centróides TF-IDF de caracteres | N-gramas de 3–5 caracteres; mesma regra de classificação. |

A escolha usa **macro-F1 de desenvolvimento**, com desempate pela ordem da configuração. O modelo selecionado não é reajustado no teste. Macro-F1 considera classes com suporte, que permanecem discriminadas na matriz completa. Os relatórios contêm precisão, revocação, F1 e suporte por classe, matriz de confusão, acurácia, latência p50/p95, consistência de três previsões determinísticas e os itens errados. Presença de figura é um diagnóstico do contexto ausente, não uma causa de erro demonstrada.

O custo externo é zero nos modelos locais. Custo de processamento local não medido fica `null`; não se inventa preço a partir do tempo. Margens são diferenças de escores, **não probabilidades calibradas**.

### Comparação com LLM

O ciclo local não escolhe provedor/modelo nem contrata serviço. Há um contrato para comparar previsões produzidas externamente, incluindo modelo, hash do prompt, grupos usados como demonstração/treino, política de dados, evidência, latência, custo e pelo menos duas repetições adicionais por item.

`llm-input.json` contém apenas identificadores opacos, hashes e texto dos itens de desenvolvimento/teste, com a taxonomia. Não inclui a resposta de referência, a partição, o número original ou o gabarito. Um executor externo pode produzir o arquivo no [contrato](external-predictions.schema.json):

```bash
.venv/bin/python scripts/run_experiments.py \
  --only classification --output tmp/experiments/comparacao-llm \
  --external-predictions tmp/previsoes-externas.json
```

Previsões incompletas, repetidas, com hashes/classes divergentes ou grupos de avaliação declarados como treino são recusadas. A comparação externa fica separada da seleção dos cinco modelos locais. Conhecimento prévio das provas públicas pelo provedor permanece desconhecido e é registrado como limitação. Sem arquivo, o resultado é `not_run`, com o motivo; não é apresentado como modelo avaliado.

### Propostas para revisão

O [contrato de proposta temática](classification-proposal.schema.json) preserva questão, identidade, versão pelo hash, fonte, taxonomia, modelo e hash do modelo, evidência e necessidade de revisão. `review_status` só aceita `proposed`; `needs_review` é obrigatório e as habilidades ficam vazias.

`classification-proposals.json` contém as 89 previsões da referência para auditoria. Com `--archive`, acrescenta até `--proposal-limit` ocorrências válidas de Matemática dos cadernos automáticos, identificadas como `unlabeled_archive`. Esse limite é de ocorrências, não de identidades semanticamente únicas; a identidade acompanha cada proposta. Não se mede acurácia nos itens sem anotação.

Política deste ciclo: encaminhar o resultado do modelo escolhido no desenvolvimento para conferência humana; itens com figuras exigem conferência visual e margem zero exige anotação manual sem tratar a previsão como evidência suficiente. Todas as propostas continuam sujeitas à comparação com a fonte. O conjunto pequeno e a ausência de adjudicação não sustentam um limiar de aprovação automática.

## Análise de layout

`layout-reference-v1` contém **13 questões e 145 blocos**: parágrafos, créditos, legendas, figuras, tabelas, fórmulas e alternativas, com página, caixa, grupo, ordem e vínculos. As coordenadas usam pontos PDF, origem no canto superior esquerdo, com rotação da página aplicada.

É uma amostra intencional e assistida, conferida com as páginas e os recortes já revisados. Não é anotação independente nem uma amostra aleatória dos 96 cadernos.

| Partição | Fontes e padrões |
| --- | --- |
| Treino | 2024, páginas 2, 7, 16 e 17: figura/legenda/créditos, alternativas gráficas verticais, tabela mesclada e texto simples. |
| Desenvolvimento | 2024, páginas 19 e 27: alternativas com matemática espacial e fórmula em página larga. |
| Teste reservado | 2023, páginas 16, 17, 24, 30 e 31: figuras vetoriais, camada acessível duplicada, tabela larga, continuidade entre colunas e gráficos com rótulos girados. |

Identidades e páginas inteiras não atravessam partições. O teste reserva outro ano e padrões difíceis. A anotação e a implementação são da mesma frente técnica; uma avaliação independente ainda exige novos casos e revisores.

### Métodos e métricas

1. **Coordenadas:** blocos de texto e imagens raster do PDF, ordenados por posição; referência sem reconstrução semântica.
2. **Geometria:** vetores e raster, tabelas, separação de alternativas, regras de tipo e associação de legendas/créditos por proximidade.
3. **CART:** a mesma localização geométrica, com árvore de classificação numérica dos blocos textuais. Gini, profundidade e mínimo de folha são explícitos; treino usa apenas pares geométricos da partição de treino.

As regiões de cada questão são entradas comuns aos métodos. **Localização da questão na página não é avaliada por este benchmark.** A árvore recebe dimensões/posições normalizadas, tamanho de fonte e características observáveis do texto; nunca o identificador, a partição ou o rótulo de referência.

O avaliador faz pareamento geométrico um a um por IoU ≥ 0,5, sem usar o tipo para escolher os pares. Mede localização (precisão/recall/F1 e IoU), tipos, ordem de leitura por pares, vínculos de legenda/crédito, associação às alternativas e preservação dos tokens de texto. Também registra blocos perdidos/extras, tipos errados e vínculos ausentes. Integridade exige o conjunto completo de blocos, tipos, ordem e vínculos; não equivale a uma revisão científica de fórmulas.

A seleção usa localização e macro-F1 dos tipos no desenvolvimento. O teste não ajusta parâmetros. `layout-proposals.json` segue o [contrato experimental](layout-proposal.schema.json), mantendo estado de proposta e estruturas de tabela separadas do renderizador publicável.

### Revisão e tempo humano

Abra `review.html` da saída experimental em um navegador. Ele mostra recortes originais e caixas da referência/proposta com controles para alternar as sobreposições. Identifique o revisor, clique **Iniciar revisão**, registre decisão e justificativa e exporte o arquivo antes de fechar. Nada é enviado a servidor.

```bash
.venv/bin/python scripts/run_experiments.py --only layout \
  --output tmp/experiments/com-tempos --review-log tmp/correction-times.json
```

O importador valida segundos positivos, decisão, justificativa, versão exata e duplicatas por alvo/método. Sem registros, tempo humano fica **não medido / `null`**. O cronômetro não representa a qualidade ou a independência da revisão; isso depende de quem executou e do protocolo de anotação.

## Recuperação dos casos difíceis

Com `--archive`, `archive-layout-proposals.json` preserva os diagnósticos recebidos e acrescenta candidatos separados. Na primeira execução, a entrada continha 506 diagnósticos em 489 questões; uma nova execução usa o estado do acervo disponível:

- **Alternativas:** cinco marcadores únicos A–E delimitam regiões que preservam todos os componentes gráficos, inclusive múltiplas figuras. Limites inferidos precisam de comparação visual; não se declara transcrição ou equivalência semântica concluída.
- **Tabelas mescladas:** caixas reais das células permitem propor `rowspan`/`colspan`. O verificador exige cobertura da grade sem lacunas ou sobreposição. Não preenche células copiando valores vizinhos.
- **Relações espaciais:** permanecem pendentes quando só é possível preservar a região original. Um recorte não é uma fórmula ou tabela reconstruída.
- **Fontes quebradas:** comparação com mapas de glifos embutidos e hipóteses limitadas de deslocamento. Os caracteres já decodificados são preservados; ligaturas, acentos e hipóteses concorrentes continuam sinalizados. Não há regra por ano ou número de questão.
- **OCR:** comparação local opcional com Tesseract, em worker com timeout. Pode usar a biblioteca nativa do PyMuPDF e `tessdata` existente, ou o executável local. `TESSDATA_PREFIX` permite indicar outra instalação. Idioma solicitado, efetivo, ausentes, hashes dos dados e latência são registrados; dados/modelos não são baixados automaticamente.
- **Gabarito visual de 2010:** círculos verdes/cianos são associados a exatamente cinco marcadores vetoriais na região. Cadernos com opção de língua preservam essa escolha. Grupos ambíguos ficam sem resposta proposta; ausência de marca nunca vira anulação. A recuperação usa o caderno com gabarito da própria cor/aplicação.

`recovery-reference-v1` guarda hashes e anotações técnicas de 11 respostas visuais e de uma linha com fonte quebrada, além de um caso diagnóstico de 2021 sem transcrição adjudicada. Ausência de fontes históricas no clone fica registrada. A comparação de caracteres usa distância de edição normalizada pelo comprimento da transcrição; valores podem exceder 1 quando há muitas inserções.

**Cobertura de candidatos não significa pendências resolvidas.** Uma revisão humana precisa adjudicar limites, transcrições, células, figuras e respostas; somente depois cabem novas versões no fluxo normal. Nenhuma saída do experimento substitui conteúdo/gabarito instalado ou remove bloqueios de preparação.

## Organização dos arquivos

- `experiments/config.json`: configuração e regras congeladas do ciclo.
- `experiments/classification.py`: partições, modelos, avaliação e propostas temáticas.
- `experiments/layout.py`: localização, árvore, relações e métricas.
- `experiments/recovery.py` e `ocr_worker.py`: casos difíceis e OCR local isolado.
- `experiments/contracts.py`: contratos das referências, propostas e medições.
- `experiments/review.py`: relatório visual e registro de tempo.
- `scripts/run_experiments.py`: execução e proveniência.
- `scripts/summarize_experiments.py`: registro compacto com verificação dos hashes da execução.
- `data/datasets/{layout,recovery}-reference-v1.json`: amostras técnicas versionadas; sem novos cadernos completos.

## Referências de método

As implementações seguem a formulação de [Naive Bayes multinomial](https://nlp.stanford.edu/IR-book/html/htmledition/naive-bayes-text-classification-1.html), [classificação vetorial](https://nlp.stanford.edu/IR-book/html/htmledition/vector-space-classification-1.html) e [avaliação de classificação](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-text-classification-1.html) de Manning, Raghavan e Schütze. A extração usa as APIs documentadas de [texto e geometria](https://pymupdf.readthedocs.io/en/latest/recipes-text.html), [tabelas](https://pymupdf.readthedocs.io/en/latest/page.html) e [OCR](https://pymupdf.readthedocs.io/en/latest/pixmap.html) do PyMuPDF. Os critérios de liberação continuam no [roteiro](../plano-implementacao/proximas-etapas.md).

## Política adaptativa

`make experiments` também compara `adaptive-v1` com seleção aleatória e reforço simples, em alunos simulados, e grava `adaptive-report.json`; `--only adaptive` roda só essa frente. O protocolo está em [política adaptativa](../politica-adaptativa.md). Os alunos são sintéticos: o relatório descreve o comportamento da seleção, sem medir aprendizagem.
