# Ampliação do banco e classificação

Implementação de **31/10/2026**, correspondente à etapa 2 do [roteiro](plano-implementacao/proximas-etapas.md). A cobertura integral das fontes e das extrações está no [relatório do acervo](cobertura-acervo.md).

## Conteúdo disponível e conteúdo em revisão

O espelho contém as fontes de todos os anos e aplicações vinculados pelo [acervo oficial do Inep](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos). Cada referência preserva a aplicação, o formato, a URL, o caminho e o hash; a [organização das fontes](../data/sources/README.md) explica a hierarquia.

O catálogo versionado e conferido contém **135 questões**: o segundo dia azul de 2024, com 90 itens, e a seção de Matemática azul de 2023, com 45. São **133 itens válidos**: anuladas a 129 de 2024 e a 164 de 2023. A nova seção é identificada como seção completa de 45 itens, com duração de prática de 150 minutos; esse tempo não é uma duração oficial isolada da área. Provas geradas automaticamente podem ser instaladas à parte, conforme o processo abaixo.

As extrações históricas ficam disponíveis na **Curadoria → Acervo oficial para curadoria**, com filtros por ano, aplicação e número. A consulta preserva texto selecionável e informa página, fonte, variantes e identidades repetidas. **Uma extração não é uma questão aprovada.** Cabeçalhos, textos compartilhados, figuras, fórmulas, tabelas e alternativas ainda precisam ser conferidos antes de virar um lote publicável. A indexação não importa gabaritos por adivinhação nem publica seus resultados automaticamente.

O banco textual completo fica em `data/bank/raw/{ano}.json.gz`; cada arquivo contém JSON com fontes e questões. O banco não é versionado: é gerado localmente pelo comando abaixo, depois da sincronização do acervo descrita nas [fontes oficiais](../data/sources/README.md). `occurrences.json`, `canonical.json`, `published-links.json` e `coverage.json` fornecem os índices e a ligação com o catálogo conferido. O cache de trabalho em `data/derived/archive/` pode ser regenerado.

```bash
.venv/bin/python scripts/build_bank.py --workers 4
```

O comando verifica os hashes das fontes antes de extrair. PDFs e TXT/DOSVOX permanecem originais. Numeração repetida de língua estrangeira é preservada como ocorrência separada; o índice não decide sozinho qual variante publicar. Casos sem cabeçalho reconhecido ficam explicitamente no relatório.

## Publicação automática do acervo

`make acervo` preserva a geração e a publicação local implementadas na outra frente: escolhe uma cor legível por ano, aplicação, dia e língua a partir de 2009, prepara texto e figuras e registra os relatórios. O ensaio inicial dessa frente registrou 96 provas, 8.595 questões e 506 pendências. Essas quantidades descrevem aquela execução; não são uma garantia de instalação em qualquer banco ou clone. Os anos anteriores continuam disponíveis no banco textual, aguardando adaptação de layout.

A API informa `content_quality` com origem, estado de revisão e número de erros registrados. O catálogo identifica **Extração automática** e a resolução informa que o caderno aguarda conferência. Questões com erros conhecidos recebem aviso e vínculo à página original; o gabarito continua privado até finalizar. O conteúdo automático pode conter falhas de texto, figuras ou alternativas mesmo quando não há erro detectado.

Essa publicação usa uma exceção explícita, com identidade de serviço, justificativa e origem registradas. Aprovação e publicação manuais continuam bloqueadas por pendências; a importação normal cria rascunhos. A conferência de conteúdo permanece na etapa 8. Arquivos inválidos falham individualmente sem impedir a instalação dos demais cadernos. Instalações automáticas anteriores recebem o registro de origem sem substituir versões; uma publicação manual válida marca a revisão como concluída.

JSONs, relatórios e figuras gerados permanecem locais e ignorados pelo Git e pelo contexto Docker. Gerar novamente um JSON não substitui questões já instaladas: correções de conteúdo exigem versões e revisão. O [guia da preparação](preparacao-provas.md#publicação-automática-do-acervo) descreve escolhas e limites.

## Identidade e preservação das ocorrências

`canonical_questions` guarda a identidade do item. `question_versions.canonical_id` liga cada versão a essa identidade. O campo histórico `question_id` continua como identificador estável da ocorrência e suas versões; ele não foi renomeado para preservar clientes e tentativas anteriores.

Na importação nativa, a assinatura ignora número, página, rótulos e ordem das alternativas. Considera texto, fórmulas, tabelas e hashes das figuras. A resposta é comparada pelo conteúdo da alternativa correta, mantendo a letra de cada caderno. Um conflito de gabarito ou duas ocorrências do mesmo item no mesmo caderno gera 409. A ordem e as letras permanecem nos snapshots usados pela correção.

Os itens conferidos também estão vinculados às outras cores da mesma aplicação e dia: amarelo, cinza e verde em 2024; amarelo, cinza e rosa em 2023. São 540 ocorrências para 135 itens, registradas em [`occurrences-v1.json`](../data/catalog/occurrences-v1.json). Uma ocorrência só é vinculada quando cumpre todos os critérios:

- o texto nativo conferido está contido na extração da cor (pelo menos 40% dos trigramas) com folga de 30 pontos sobre o segundo candidato;
- o pareamento é único;
- o gabarito oficial daquela cor coincide, inclusive a anulação;
- as figuras raster são equivalentes em miniatura.

Três figuras do caderno amarelo de 2024 foram reprocessadas pelo Inep em outra resolução e ficaram acima do limite automático. Elas foram conferidas visualmente, e o motivo está registrado no script. Desenhos vetoriais não são comparados.

A importação de uma cor vinculada reaproveita a identidade canônica e recusa gabarito divergente. O banco do acervo usa o mesmo vínculo, então a curadoria mostra as quatro ocorrências de cada item. O vínculo é gerado a partir do espelho local:

```bash
.venv/bin/python scripts/link_booklets.py
.venv/bin/python scripts/link_booklets.py --check
```

Os testes conferem o arquivo versionado sem os PDFs: cada item tem uma ocorrência por cor, cada cor é uma permutação dos mesmos números e a identidade coincide com a do conteúdo conferido.

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

Faz parte da curadoria, concentrada na [etapa 8 do roteiro](plano-implementacao/proximas-etapas.md#8-curadoria-do-conteúdo-e-dos-rótulos).

1. Um segundo revisor compara a versão exata com o PDF e anota disciplina, tema e habilidades sem consultar a primeira decisão.
2. Registrar `question_id`, hash da versão, rótulos, evidência, justificativa e identificação do revisor.
3. Comparar decisões, medir concordância e registrar cada divergência. Casos como 139/2023 (função versus leitura de tabela), 163/2023 (trajetória versus gráfico) e itens interdisciplinares de Natureza merecem atenção.
4. Adjudicar com justificativa e referência à matriz. Publicar habilidades apenas após esse aceite, por novas versões.
5. Atualizar referência, cobertura e protocolo experimental. Preservar decisões anteriores para auditoria.

Os aceites ainda pendentes estão na etapa 8 e no final das [próximas etapas](plano-implementacao/proximas-etapas.md).

## Integração das frentes da etapa 2

A integração preserva o vínculo dos 135 itens às quatro cores (540 ocorrências), a preparação por língua estrangeira, os adaptadores de layout e a geração local das provas do acervo. Acrescenta cabeçalhos espaçados de versões acessíveis, identificação correta de cadernos com áreas combinadas, recuperação da matriz pelo manifesto, auditoria limitada aos itens de cada seção e preservação da auditoria de preparação ao acrescentar os rótulos.

A curadoria permanece na etapa 8. A referência técnica mantém 89 itens válidos em oito temas; os vínculos com habilidades continuam propostas. O banco textual local pode ser montado somente para leitura com `compose.archive.yaml`.

Antes de reproduzir as anotações, recupere a matriz, se necessário, com `python scripts/archive_enem.py reference` (o intermediário TLS opcional está no guia das fontes).

## Validação da integração

Integração concluída em **01/11/2026**, na branch `codex/consolidacao-primeira-entrega`, preservando os históricos das duas frentes.

- **81 testes do backend em SQLite e 81 em PostgreSQL**, incluindo identidade entre cores, classificação, auditoria, cabeçalhos acessíveis, origem automática, falhas isoladas e publicação manual com bloqueios. Migrações e `alembic check` aprovados no PostgreSQL, com instalação dos dois lotes.
- **24 testes Playwright**, 12 em desktop e 12 em celular emulado, aprovados no build de produção. Incluem os 90 itens de 2024, a seção de 2023, acessibilidade automatizada, figuras, teclado, retomada e indicação de conteúdo automático. TypeScript aprovado; 150 expressões LaTeX de 2024 e 159 de 2023 compiladas.
- **Índice reconstruído:** 480 PDFs, 10 TXT, 44.524 ocorrências, 43.439 identidades conservadoras e 1.085 ocorrências agrupadas. O vínculo de 540 ocorrências conferidas foi preservado. A auditoria confirmou os hashes disponíveis e manteve as duas URLs oficiais indisponíveis já registradas na cobertura. Os caminhos antigos duplicados das fontes com áreas combinadas foram preservados em `tmp/integracao-fontes-caminhos-antigos/`, fora do espelho organizado.
- **Amostra de geração e instalação:** sete cadernos completos, 630 questões e 67 pendências registradas. Abrange os dois dias de 2009, os dois dias de 2011 (espanhol no segundo), PPL 2012 e as duas línguas do primeiro dia PPL 2024. Todos foram instalados em uma cópia isolada do banco, sem falhas. Essa amostra não substitui a reprodução integral das 96 provas do ensaio inicial nem a conferência humana.
- **Compatibilidade:** migração, atualização do catálogo e instalação do acervo na cópia preservaram a tentativa existente, seus 90 snapshots, respostas e resultado, comparados por hash. O banco de uso foi apenas lido. A configuração Compose com banco textual somente para leitura foi validada; não foi repetido o ensaio completo de persistência em contêineres da consolidação.

A integração da checagem de todas as provas ao fluxo reutilizável continua nas melhorias do roteiro. Leitores de tela, aparelhos reais e segunda revisão permanecem pendentes; a curadoria continua na etapa 8.

## Incorporação do acervo processado

Em **01/11/2026**, os dados recebidos em `/home/cassio/Downloads/data` foram incorporados à instalação local. Foram reaproveitados os **96 cadernos e 8.595 questões**, com **5.066 figuras referenciadas**, evitando repetir a extração dos PDFs. Os originais recebidos foram preservados. O índice `archive-text-v4`, a organização corrigida das fontes, os dois lotes conferidos e as anotações do projeto foram mantidos; o banco recebido usava `archive-text-v3`.

JSONs e relatórios estão em `data/derived/exams/`; somente as figuras referenciadas foram acrescentadas a `data/assets/<prova>/prepared/`. Os derivados permanecem fora do Git. A versão local corrigida de 2009, primeiro dia azul, foi preservada: Natureza nas questões 1–45 e Humanas nas 46–90. Não foram substituídas versões ou figuras já instaladas por arquivos divergentes.

Antes da publicação, todos os cadernos passaram por validação do contrato, numeração, áreas, hashes dos PDFs e gabaritos, comparação de cada resposta com o gabarito oficial da língua escolhida, compilação LaTeX e decodificação das figuras. Nenhuma fonte, resposta ou figura ausente/divergente foi encontrada. A publicação acrescentou 89 cadernos aos sete automáticos já instalados, sem falhas: o catálogo local oferece **98 provas e 8.730 posições de questão**. Opções de língua podem compartilhar itens; esse total não representa questões semanticamente únicas.

Uma cópia isolada do banco passou pelo início, preenchimento de todas as respostas com o gabarito, finalização e repetição da finalização nas **96 provas automáticas**. As 8.595 questões tiveram resultado consistente: 13 anuladas excluídas do desempenho e 100% nas demais, sem duplicar eventos ou alterar snapshots. Foram usadas diretamente as funções que atendem às rotas HTTP; não foram criadas tentativas fictícias no banco do site. O catálogo real também foi conferido em 1.440 e 390 pixels, incluindo os 96 indicadores de origem automática e filtros por ano/aplicação. Isso verifica instalação e correção, sem substituir a comparação pedagógica com cada página original.

Continuam registradas **506 pendências em 489 questões**: 222 relações espaciais, 154 alternativas não separadas e 130 tabelas com células mescladas. Elas permanecem visíveis no site e serão tratadas nas etapas 3 e 8. Os casos sem gabarito ou texto legível e os anos anteriores a 2009 continuam com os limites descritos no guia de preparação; o lote recebido não resolve essas ausências.

O backup anterior à instalação está em `backups/enem-flow-antes-acervo-2026-11-01.db`. A tentativa real existente, seus 90 snapshots, respostas e resultado foram preservados. A conferência de entrada, o resumo de geração e o ensaio integral estão em `data/derived/exams/importacao-processada.report.json`, `resumo.json` e `checagem-integral.report.json`.
