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

A API informa `content_quality` com origem, estado de revisão e número de erros registrados. Desde 05/11/2026, o catálogo apresenta todas as provas publicadas como **Disponível**, sem aviso geral de extração automática na resolução. Questões com erros conhecidos recebem aviso e vínculo à página original; o gabarito continua privado até finalizar. O conteúdo automático pode conter falhas de texto, figuras ou alternativas mesmo quando não há erro detectado.

Essa publicação usa uma exceção explícita, com identidade de serviço, justificativa e origem registradas. Aprovação e publicação manuais continuam bloqueadas por pendências; a importação normal cria rascunhos. A conferência de conteúdo continua pendente. Arquivos inválidos falham individualmente sem impedir a instalação dos demais cadernos. Instalações automáticas anteriores recebem o registro de origem sem substituir versões; uma publicação manual válida marca a revisão como concluída.

Os cinco cadernos regulares de 2024/2025 incluídos no Git são instalados por `make seed`; os demais JSONs, relatórios e figuras gerados permanecem locais. Os cadernos automáticos ficam fora do contexto Docker. Gerar novamente um JSON não substitui questões já instaladas: correções de conteúdo exigem versões e revisão. O [guia da preparação](preparacao-provas.md#publicação-automática-do-acervo) descreve escolhas e limites.

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

As anotações versionadas são a entrada das avaliações. A edição de texto invalida seu vínculo por hash e exige conferência. Para exportar o dataset com o contrato atual, use `scripts/export_reference.py`; geradores pontuais de decisões editoriais não fazem parte da manutenção.

## Instalação e atualizações

Faça backup antes de atualizar uma instalação existente:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.app.cli catalog --publish-curated
```

O início do contêiner também instala esses dois lotes conferidos. `make seed` prepara o catálogo local de seis provas regulares de 2024/2025 por `local-catalog`; a seção de 2023 fica fora desse catálogo padrão, com seus arquivos de referência preservados. A atualização de um bootstrap antigo retira a seção publicada pela identidade de serviço sem apagar seu conteúdo ou histórico; uma publicação manual é preservada. Veja [instalação local e atualização](operations.md#atualizar-os-lotes-e-a-classificação).

A atualização cria versões para os rótulos novos, preserva os conteúdos anteriores, respostas, resultados e snapshots. Uma segunda execução não cria duplicatas. Edições próprias fora das versões de origem conhecidas interrompem a transação e exigem revisão manual.

Rótulos novos valem para tentativas iniciadas depois da atualização. O histórico mantém a classificação que foi fotografada ao iniciar cada tentativa; ele não é reescrito retroativamente.

## Processo da segunda revisão

Faz parte da curadoria, que não foi realizada e não tem etapa no [roteiro atual](plano-implementacao/proximas-etapas.md).

1. Um segundo revisor compara a versão exata com o PDF e anota disciplina, tema e habilidades sem consultar a primeira decisão.
2. Registrar `question_id`, hash da versão, rótulos, evidência, justificativa e identificação do revisor.
3. Comparar decisões, medir concordância e registrar cada divergência. Casos como 139/2023 (função versus leitura de tabela), 163/2023 (trajetória versus gráfico) e itens interdisciplinares de Natureza merecem atenção.
4. Adjudicar com justificativa e referência à matriz. Publicar habilidades apenas após esse aceite, por novas versões.
5. Atualizar referência, cobertura e protocolo experimental. Preservar decisões anteriores para auditoria.

Os aceites ainda pendentes não têm etapa no [roteiro atual](plano-implementacao/proximas-etapas.md).
