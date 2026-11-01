# Ampliação do banco e classificação

Implementação de **31/10/2026**, correspondente à etapa 2 do [roteiro](plano-implementacao/proximas-etapas.md). A cobertura integral das fontes e das extrações está no [relatório do acervo](cobertura-acervo.md).

## Conteúdo disponível e conteúdo em revisão

O espelho contém as fontes de todos os anos e aplicações vinculados pelo [acervo oficial do Inep](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos). Cada referência preserva a aplicação, o formato, a URL, o caminho e o hash; a [organização das fontes](../data/sources/README.md) explica a hierarquia.

O catálogo publicado contém **135 questões**: o segundo dia azul de 2024, com 90 itens, e a seção de Matemática azul de 2023, com 45. São **133 itens válidos**: anuladas a 129 de 2024 e a 164 de 2023. A nova seção é identificada como seção completa de 45 itens, com duração de prática de 150 minutos; esse tempo não é uma duração oficial isolada da área.

As extrações históricas ficam disponíveis na **Curadoria → Acervo oficial para curadoria**, com filtros por ano, aplicação e número. A consulta preserva texto selecionável e informa página, fonte, variantes e identidades repetidas. **Uma extração não é uma questão aprovada.** Cabeçalhos, textos compartilhados, figuras, fórmulas, tabelas e alternativas ainda precisam ser conferidos antes de virar um lote publicável. A indexação não importa gabaritos por adivinhação nem publica seus resultados automaticamente.

O banco textual completo fica em `data/bank/raw/{ano}.json.gz`; cada arquivo contém JSON com fontes e questões. O banco não é versionado: é gerado localmente pelo comando abaixo, depois da sincronização do acervo descrita nas [fontes oficiais](../data/sources/README.md). `occurrences.json`, `canonical.json`, `published-links.json` e `coverage.json` fornecem os índices e a ligação com o catálogo conferido. O cache de trabalho em `data/derived/archive/` pode ser regenerado.

```bash
.venv/bin/python scripts/build_bank.py --workers 4
```

O comando verifica os hashes das fontes antes de extrair. PDFs e TXT/DOSVOX permanecem originais. Numeração repetida de língua estrangeira é preservada como ocorrência separada; o índice não decide sozinho qual variante publicar. Casos sem cabeçalho reconhecido ficam explicitamente no relatório.

## Identidade e preservação das ocorrências

`canonical_questions` guarda a identidade do item. `question_versions.canonical_id` liga cada versão a essa identidade. O campo histórico `question_id` continua como identificador estável da ocorrência e suas versões; ele não foi renomeado para preservar clientes e tentativas anteriores.

Na importação nativa, a assinatura ignora número, página, rótulos e ordem das alternativas. Considera texto, fórmulas, tabelas e hashes das figuras. A resposta é comparada pelo conteúdo da alternativa correta, mantendo a letra de cada caderno. Um conflito de gabarito ou duas ocorrências do mesmo item no mesmo caderno gera 409. A ordem e as letras permanecem nos snapshots usados pela correção.

No acervo ainda não revisado, somente texto exatamente normalizado pode ser agrupado automaticamente. Dependências visuais mantêm a identidade vinculada à fonte para evitar juntar gráficos diferentes. Esses casos exigem comparação visual antes da união. As ocorrências dos 135 itens conferidos se ligam às mesmas identidades usadas pelo banco e pelo conjunto de referência. Deduplicação conservadora pode deixar duplicatas por revisar; não é alegada deduplicação semântica completa de todo o acervo.

## Taxonomia e anotações

- [Taxonomia editorial `enem-content-v1`](../data/taxonomy/enem-content-v1.json): disciplinas e temas das quatro áreas; oito temas de Matemática.
- [Matriz oficial de Matemática](../data/taxonomy/enem-official-math.json): identificadores `MT.C1`–`MT.C7` e `MT.H1`–`MT.H30`, com página e hash da fonte oficial. Esses códigos não são temas editoriais.
- [Anotações `reference-v1`](../data/classification/annotations-v1.json): 135 decisões explícitas de disciplina e tema, com versão, fonte, página, trecho, justificativa, autoria técnica e estado de revisão.

As 90 questões de Matemática têm uma habilidade candidata acompanhada de justificativa e referência à matriz. **Essas propostas não são publicadas em `labels.skills`.** Uma segunda anotação independente e a adjudicação ainda estão pendentes; nenhuma discussão entre revisores foi simulada. O painel mostra os temas efetivamente curados e a cobertura real de habilidades, atualmente vazia nos lotes incluídos.

O validador rejeita temas fora da disciplina/área quando a importação declara `enem-content-v1`. Importações de outras taxonomias continuam rastreáveis; não são convertidas silenciosamente. Novos termos ou mudanças de significado exigem versão e evidência.

## Referência inicial para os experimentos

[adaptive-math-reference-v1.json](../data/datasets/adaptive-math-reference-v1.json) reúne **89 questões válidas e distintas em oito temas**. A questão anulada de 2023 permanece no catálogo e nas anotações, mas não entra nos experimentos. Cada item contém identidade canônica, grupo para particionamento, versão da taxonomia e hashes do conteúdo e da fonte.

É uma referência exploratória de curadoria técnica assistida. Não é um benchmark pedagógico independente, conjunto calibrado por TRI ou evidência de eficácia educacional. Os splits de avaliação e as habilidades definitivas ficam para depois da segunda anotação; variantes de um item devem permanecer no mesmo grupo.

```bash
.venv/bin/python scripts/review_2023_math.py
.venv/bin/python scripts/annotate_reference.py
.venv/bin/python scripts/export_reference.py
```

Antes desses comandos, recupere a matriz local com `scripts/archive_enem.py reference` se necessário; o PDF da matriz não é versionado.

O primeiro comando reproduz a conferência de apresentação de 2023 a partir da transcrição automática preservada. As decisões numéricas de anotação são explícitas em `scripts/annotate_reference.py`; não são classificações por palavras-chave. Alterar o texto de um item invalida a anotação vinculada ao hash anterior até nova conferência.

## Instalação e atualizações

Faça backup antes de atualizar uma instalação existente:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.app.cli catalog --publish-curated
```

`make seed` e o início do contêiner também instalam o catálogo incluído. A atualização cria versões para os rótulos novos, preserva os conteúdos anteriores, respostas, resultados e snapshots. Uma segunda execução não cria duplicatas. Edições próprias fora das versões de origem conhecidas interrompem a transação e exigem revisão manual.

Rótulos novos valem para tentativas iniciadas depois da atualização. O histórico mantém a classificação que foi fotografada ao iniciar cada tentativa; ele não é reescrito retroativamente.

## Processo da segunda revisão

1. Um segundo revisor compara a versão exata com o PDF e anota disciplina, tema e habilidades sem consultar a primeira decisão.
2. Registrar `question_id`, hash da versão, rótulos, evidência, justificativa e identificação do revisor.
3. Comparar decisões, medir concordância e registrar cada divergência. Casos como 139/2023 (função versus leitura de tabela), 163/2023 (trajetória versus gráfico) e itens interdisciplinares de Natureza merecem atenção.
4. Adjudicar com justificativa e referência à matriz. Publicar habilidades apenas após esse aceite, por novas versões.
5. Atualizar referência, cobertura e protocolo experimental. Preservar decisões anteriores para auditoria.

Os aceites ainda pendentes estão no final das [próximas etapas](plano-implementacao/proximas-etapas.md).

## Evidências técnicas desta ampliação

66 testes de API em SQLite e 66 em PostgreSQL, migrações e alinhamento de esquema verificados. Os 22 testes de navegador passaram em desktop e viewport móvel, incluindo as 45 questões da nova seção, ausência de erros LaTeX e consulta do acervo. As 150 expressões do caderno de 2024 e as 159 de Matemática de 2023 foram compiladas. O ensaio em contêineres verificou também a atualização do catálogo e a preservação de resposta, resultado, snapshots e recurso após recriação dos serviços.

Esses ensaios são técnicos; não substituem a segunda anotação, a revisão pedagógica e os testes com tecnologias assistivas e aparelhos reais.
