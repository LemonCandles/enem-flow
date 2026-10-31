# Conjunto inicial

Inclui o caderno completo do segundo dia do ENEM 2024, aplicação regular, caderno 7 azul, com as 90 questões de 91 a 180. Não representa os dois dias nem todos os anos do ENEM. São 45 questões de Ciências da Natureza e 45 de Matemática.

Fontes primárias:

- [Caderno oficial do Inep](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D2_CD7.pdf)
- [Gabarito oficial correspondente](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D2_CD7.pdf)
- [Catálogo do Inep para 2024](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/2024)

Os PDFs ficam em `sources/`. O arquivo JSON guarda URLs, hashes SHA-256, página, numeração, gabarito, identificador canônico, rótulos e os retângulos em pontos PDF (origem no canto superior esquerdo). As imagens ficam em `assets/`. O gabarito e o JSON não são servidos como arquivos públicos pela aplicação.

## Apresentação e conferência

A fonte dos enunciados e das alternativas é o próprio JSON. Cada questão contém blocos tipados de parágrafo, imagem, tabela ou fórmula. O site renderiza os textos como HTML selecionável, as tabelas como tabelas reais e as expressões matemáticas com KaTeX e MathML. Imagens ficam restritas a fotografias, quadrinhos, gráficos, esquemas e diagramas das alternativas. O caderno não é exibido como uma imagem de texto.

Foram conferidos os 90 números únicos, a sequência, a correspondência de cada resposta com o gabarito oficial e a presença dos recursos. A transcrição inicial foi separada em enunciados e cinco alternativas reais. As tabelas foram estruturadas a partir dos dados do JSON; frações, raízes, potências e expressões cuja extração perdeu a disposição espacial foram conferidas com o original e normalizadas. Gráficos das alternativas continuam vinculados às opções A–E. A extração anterior e os 92 recortes integrais ficam preservados para rastreabilidade de versões antigas, mas não são usados como apresentação do enunciado.

A questão **129 é anulada**. Seu gabarito é `null` e `annulled=true`; ela não entra no denominador, nos acertos, nos erros nem na cobertura dos rótulos. Não se calcula nota TRI.

Em 31/10/2026, uma revisão de apresentação comparou 15 questões com o PDF, incluindo a química das questões 92, 94, 97, 114, 116, 118, 123, 128, 133 e 135. O [registro por questão](#revisão-de-apresentação) identifica as alterações e os limites da conferência. Texto continua selecionável, com fórmulas em LaTeX matemático/químico (`\ce{...}`), renderizadas por KaTeX com mhchem. Estruturas moleculares desenhadas permanecem nas figuras originais.

Blocos `image` podem conter `caption`, `credit` e `equations`: legenda, fonte e equações pertencem à mesma figura. A questão 92 usa esse rodapé para suas duas semirreações. A ampliação abre um diálogo na própria página, preservando esses vínculos e oferecendo zoom. Parágrafos revisados têm `role: body` ou `role: credit` explícito.

A área vem do caderno oficial; as questões 136–180 recebem a disciplina Matemática. Natureza não recebe subdivisão automática em Física, Química ou Biologia. Temas e habilidades oficiais estão vazios, explicitamente aguardando anotação e revisão. Não houve validação pedagógica independente, experimento de classificação ou estudo de ganho de aprendizagem.

## Preparar novas provas

Use o fluxo geral em [Preparação de novas provas](../docs/preparacao-provas.md). `scripts/prepare_exam.py` aceita uma prova no contrato JSON e, opcionalmente, PDF com regiões ou manifesto de metadados/layout. A importação pela curadoria executa o mesmo preparador automaticamente e mostra transformações e pendências antes da aprovação.

O [manifesto de exemplo](examples/manifesto-prova.json) permite ensaiar questões, áreas, figuras e alternativas sem regras por número. Resultados automáticos são rascunhos; casos ambíguos exigem conferência. Os scripts abaixo ficam preservados para reproduzir a transcrição conferida do caderno inicial.

## Reproduzir a transcrição conferida do caderno inicial

```bash
.venv/bin/python scripts/structure_questions.py
```

O comando lê `data/derived/baselines/enem-2024-dia2-azul-extraction.json`, a cópia preservada da transcrição inicial. Todo o texto vem desse JSON. O PDF associado é consultado apenas para isolar fotografias e diagramas; os enunciados não são rasterizados. O resultado estruturado fica em `data/enem-2024-dia2-azul.json` e as figuras isoladas em `assets/enem-2024-dia2-azul/native/`.

A estruturação aplica também as correções de `scripts/review_presentation.py`. Para reconstruir somente este lote a partir da apresentação anterior preservada em `derived/baselines/enem-2024-dia2-azul-native-v1.json`, execute:

```bash
.venv/bin/python scripts/review_presentation.py
cd frontend && npm run check:content
```

O teste de reprodução compara o JSON inteiro. Cada questão alterada registra motivo, página, data e hash do conteúdo anterior em `layout.presentation_review`. Esse registro é uma conferência técnica com a fonte; não substitui revisão pedagógica independente.

Para reconstruir a transcrição bruta a partir da fonte oficial, existe também o comando inicial:

```bash
.venv/bin/python scripts/import_official.py
```

É necessário instalar `backend/requirements-dev.lock`. A preparação ocorre fora das requisições do aluno. Os scripts são específicos desse caderno; outros anos exigem conferir suas particularidades de layout. A extração bruta falha se não encontrar exatamente os 90 itens e os 90 registros de gabarito. Após executá-la, aplique a estruturação do JSON para recuperar a apresentação nativa.

```bash
.venv/bin/python -m backend.app.cli seed
```

Importa o conjunto como rascunho. `seed --publish-reviewed` publica exclusivamente o conjunto incluído após registrar as decisões de conferência com uma identidade técnica sem senha conhecida. Para atualizar uma instalação anterior, faça backup e use `seed --publish-reviewed --refresh-bundled`: ele compara a assinatura do conteúdo completo com os arquivos anteriores conhecidos, confere os dados de avaliação e cria novas versões sem modificar respostas, snapshots ou resultados. Edições próprias, inclusive em blocos ou alternativas, são recusadas e exigem revisão manual. Repetir o comando com o mesmo JSON não cria versões adicionais. A atualização native-v1 → native-v2 cria 15 versões.

Tentativas antigas cujo conteúdo completo coincide exatamente com uma das versões anteriores incluídas também recebem a apresentação revisada na leitura, mantendo os mesmos identificadores, conteúdo de avaliação, gabarito e resultados. Essa adaptação de apresentação não grava alterações no histórico. Um conteúdo com edição própria não é substituído.

Novos arquivos podem ser importados pela interface de curadoria conforme `docs/content-schema.json`. Recursos de imagem referenciados precisam estar em `data/assets/` antes da importação; o MVP não faz download de URLs arbitrárias nem recebe upload de imagens. A URL do PDF de origem continua disponível para comparação. Novos cadernos podem reutilizar o mesmo identificador canônico quando o conteúdo é idêntico; a conferência de duplicatas semânticas é manual nesta entrega.

## Revisão de apresentação

Data: **31/10/2026**. Lote: `native-v2-2026-10-31`.

Este lote iniciou a etapa 1 do [roteiro](../docs/plano-implementacao/proximas-etapas.md). Mantém o enunciado em texto selecionável, com fórmulas matemáticas e químicas em LaTeX, figuras originais e legendas associadas. A conferência técnica compara este lote com o [caderno fonte](sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf); não é revisão pedagógica independente.

### Questões alteradas

As páginas abaixo são as páginas do PDF, contadas a partir de 1. Numeração, área, gabarito, anulação, rótulos, ordem das alternativas e valores das respostas foram preservados. As alternativas incorretas de química mantêm as expressões da prova; não foram balanceadas nem corrigidas conceitualmente.

| Questão | Página | Alteração |
| --- | --- | --- |
| 91 | 2 | “Momentum and Car safety. GCSE Physics Revision.” passa a ser legenda da figura, com URL e data de acesso no mesmo `figcaption`. A referência de DAY continua ligada ao texto. |
| 92 | 2 | Duas semirreações em LaTeX no rodapé destacado da figura, separadas da referência de QUINTO. Cargas, índices, coeficientes e estados físicos conferidos; fase líquida escrita com `l`. Alternativas químicas em LaTeX. |
| 94 | 3 | Próton com carga em LaTeX. Legenda Nimesulida e crédito junto à estrutura molecular original. |
| 97 | 3 | Massas molares de NaCl e Na, concentração e unidades em LaTeX. Continuidade do parágrafo das massas molares restaurada. |
| 99 | 4 | Frequências `f_r` e `f_0` e suas comparações nas alternativas em LaTeX. |
| 100 | 4 | Título separado do parágrafo, índices dos espelhos em LaTeX e referência associada ao esquema. |
| 114 | 8 | Espécies CO₂, HC, CO, NO e O₂ em LaTeX no texto e nas alternativas; referência associada ao gráfico. |
| 116 | 9 | Equação química em bloco separado do comando, com cargas e estados físicos em LaTeX. |
| 118 | 9 | Hidroxiapatita e espécies do equilíbrio em LaTeX químico, com rótulos Desmineralização e Mineralização preservados. |
| 123 | 11 | As três partes da referência bibliográfica acompanham a imagem das fórmulas estruturais. |
| 128 | 13 | Cargas genéricas `m+`, `n−` e elétron em LaTeX; referência associada à figura. |
| 132 | 14 | Índices das lâmpadas e da tensão `V_QR` em LaTeX. |
| 133 | 14 | Parágrafo unido no trecho interrompido; grandezas e unidades em LaTeX no texto e nas alternativas. |
| 135 | 15 | Título separado, alumina, alumínio, unidades, porcentagem e notação científica em LaTeX. |
| 170 | 27 | Índices das magnitudes e energias no texto coerentes com a equação; valor de `M_1` em LaTeX. |

As outras **75 questões não tiveram seu JSON alterado neste lote**. O visualizador novo atende às figuras de enunciados renderizadas pelo componente comum, incluindo questões fora deste lote.

### Apresentação e acessibilidade

- KaTeX com mhchem renderiza fórmulas matemáticas/químicas e gera MathML. Texto comum continua em HTML; nenhuma imagem do enunciado foi criada.
- `image.caption`, `image.credit` e `image.equations` mantêm legenda, crédito e rodapé no bloco da figura. Imagem e legenda são associadas também por `aria-describedby`.
- “Ampliar figura” e o clique na imagem abrem um diálogo na própria página, com zoom de 50% a 300%, restauração do tamanho e rolagem interna. Legendas, créditos e semirreações acompanham a ampliação.
- O diálogo prende o foco pelo comportamento modal nativo; Escape fecha e devolve o foco ao controle que abriu a figura. O conteúdo de fundo fica indisponível enquanto o diálogo está aberto.
- Reações podem quebrar entre espécies, preservando cada fórmula molecular e suas cargas. Equações que excedam a largura disponível têm rolagem acessível por teclado.

### Reprodução e segurança das versões

`data/derived/baselines/enem-2024-dia2-azul-native-v1.json` preserva a apresentação anterior. `scripts/review_presentation.py` reproduz o lote a partir dela e também é aplicado pela estruturação completa. Cada questão guarda data, motivo, página e hash do conteúdo anterior em `layout.presentation_review`.

```bash
.venv/bin/python scripts/review_presentation.py
cd frontend && npm run check:content
```

Antes de atualizar uma instalação, faça backup. `seed --publish-reviewed --refresh-bundled` cria 15 novas versões quando parte de native-v1 e registra os motivos no banco. A assinatura considera o conteúdo completo normalizado, incluindo blocos, alternativas e metadados, e recusa edições próprias ou mudanças de dados de avaliação. Repetir a atualização não cria versões adicionais.

Snapshots, respostas, resultados e eventos anteriores não são regravados. A leitura de um snapshot antigo conhecido pode aplicar a apresentação revisada, preservando seus identificadores, versão e dados de avaliação. Snapshots com edições próprias permanecem como foram registrados.

### Validação e limites

- 27 testes de API aprovados em SQLite, incluindo reprodução integral do JSON, atualização de apenas 15 versões, idempotência, preservação de snapshots e recusa de alterações próprias.
- 150 expressões matemáticas/químicas do caderno compiladas sem erro pelo comando `npm run check:content`, agora incluído no workflow de CI.
- TypeScript e build de produção aprovados.
- 12 testes Playwright aprovados no build de produção, em desktop e viewport móvel. Incluem as 15 questões revisadas, ausência de erros KaTeX e de transbordamento da página, ampliação sem nova guia, zoom, Escape, foco e jornada completa com persistência e finalização. Usam banco temporário separado.
- Conferência visual das questões 91/92, estruturas químicas da 94, equilíbrio da 118 e notação científica da 135, nos temas claro e escuro. [Questão 92 no celular](../docs/screenshots/questao-92-latex-mobile.png) e [ampliação](../docs/screenshots/ampliacao-figura.png).
- Banco local atualizado após backup consistente em `backups/enem-flow-antes-native-v2-2026-10-31.db` (ignorado pelo Git). Criadas 15 versões; segunda execução criou zero. Histórico e conteúdo/status das 180 versões anteriores conferidos contra o backup e preservados; integridade SQLite `ok`.
- [Vídeo da jornada atualizado](../docs/demo.webm) e [vídeo das figuras/LaTeX](../docs/demo-figuras.webm), sem narração e com conta descartável. Capturas e vídeos são evidências técnicas de teste, sem dados de estudantes reais.

Este lote passou a integrar a [consolidação técnica da primeira entrega](../docs/primeira-entrega.md), com instalação isolada, PostgreSQL, recuperação, CI e auditoria automatizada. Revisão pedagógica independente, descrições científicas com leitores de tela e uso em aparelhos reais permanecem nas pendências externas ao final das próximas etapas.

## Origem e direitos

Preservam-se as referências e os créditos contidos nas questões oficiais. A licença MIT do código não se estende automaticamente aos textos e às imagens desses documentos. Não foi atribuída uma licença aberta nova ao conteúdo de terceiros. Os PDFs originais permitem conferir os avisos e a procedência; alterações e futuras erratas devem criar versões, sem substituir tentativas antigas. A plataforma não é um produto oficial do Inep.

## Ampliação do acervo e classificação

A organização atual das fontes está em [sources/README.md](sources/README.md). As transcrições de 2024 antes guardadas em `sources/` passaram, sem alteração de bytes, para `derived/baselines/`; somente originais permanecem em `sources`.

O [relatório do acervo](../docs/cobertura-acervo.md) apresenta a cobertura de 1998–2025 e as falhas registradas. O banco textual histórico fica em `bank/raw/`, em JSON comprimido por ano, com ocorrências e fonte rastreável. Ele é gerado localmente por `scripts/build_bank.py` a partir do acervo sincronizado e não é versionado. Extração pendente não é publicação aprovada.

O [catálogo conferido](catalog/manifest.json) instala o segundo dia azul de 2024 e Matemática azul de 2023: 135 questões, 133 válidas. A curadoria de 2023 abrange as questões 136–180, com a 164 anulada. O conjunto de referência tem 89 questões válidas de Matemática em oito temas. Disciplinas/temas e propostas de habilidades têm [evidências próprias](classification/annotations-v1.json), separadas da matriz oficial e sem reescrever snapshots anteriores. Consulte o [processo de classificação](../docs/banco-classificacao.md).
