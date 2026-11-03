# Auditoria integral do acervo

Execução concluída em **03/11/2026**, com verificação técnica de fontes, gabaritos, apresentação, correção e aplicação dos experimentos da etapa 3. As evidências completas ficam em `tmp/acervo-validacao/`; o [resumo versionado](auditoria-resultados-2026-11-03.json) guarda contagens, limites e hashes. As fontes oficiais permanecem imutáveis. As 993 correções foram aplicadas na base de uso; a revisão pedagógica independente continua pendente.

## Escopo e evidências

- **Catálogo do site:** 98 provas e 8.730 posições de questão. Cada posição mantém número, língua, cor, versão, identidade e hashes das fontes.
- **Banco histórico:** 44.524 ocorrências, 43.439 identidades conservadoras, 490 extrações e 28 arquivos anuais compactados. Os 884 arquivos baixados passaram pela conferência de SHA-256; dois registros anteriores de erro de download continuam explícitos, sem nova consulta aos links nesta rodada.
- **Gabaritos:** leitura independente com PyMuPDF e `pdftotext -layout`, escolhendo a coluna da cor e da língua. As anulações são conferidas separadamente.
- **Figuras:** existência, decodificação, hash e comparação dos pixels com a página/caixa declarada. Diferenças de até um nível por canal, com dimensões iguais, são registradas como arredondamento; diferenças maiores continuam como divergência.
- **Conteúdo:** alternativas incompletas, caracteres ilegíveis, controle, trechos de redação indevidos, regiões inválidas, figuras extraídas que não chegaram ao conteúdo e cobertura textual usada apenas como triagem. O indicador compara parágrafos, alternativas, tabelas, legendas e créditos com o texto extraído da região; texto dentro de figuras e fórmulas em blocos próprios podem reduzir essa cobertura sem constituir perda. A compilação de fórmulas é verificada separadamente.
- **Site:** o Next de produção recebe snapshots exportados da cópia de ensaio, por interceptação local das rotas de sessão/tentativa/recursos. Os componentes reais são percorridos em 1.440 e 390 pixels, nos temas claro e escuro. Conferem-se alternativas, gabarito visível, anulação, avisos, imagens, KaTeX e transbordamento. Nenhuma conta ou tentativa de aluno é criada na base de uso.
- **Resultados:** as rotas reais de início/finalização são exercitadas em banco descartável, com todos os acertos, todos em branco e todos os erros. A expectativa vem do gabarito oficial independente. A segunda finalização deve devolver o mesmo resultado e preservar a quantidade de eventos.

As capturas podem ser guardadas para cada questão ou apenas para questões sinalizadas e o primeiro item de cada prova. O relatório informa a política e a quantidade efetivamente capturada. A passagem automatizada por todas as questões não equivale a revisão pedagógica independente de todas elas.

A passagem final concluiu **196 combinações de prova/tela e 17.460 apresentações de questão**, cada uma inspecionada nos temas claro e escuro, sem erros de execução ou achados nas verificações automatizadas de renderização. Foram armazenadas **1.070 capturas**, cobrindo questões com pendências e o primeiro item de cada prova. Os snapshots, as versões e os hashes das 8.730 posições coincidem com o catálogo ativo depois da instalação. A [fila visual local](../../tmp/acervo-validacao/conferencia-final/review.html) reúne originais, capturas disponíveis, gabaritos e diagnósticos; seus filtros e sua apresentação foram conferidos em desktop e celular.

## Correções técnicas

Foram aplicadas **993 novas versões em 84 provas**, incluindo **63 correções de gabarito de 2009**. A leitura anterior sobrescrevia respostas quando o PDF reunia várias cores. A seleção de cor agora é obrigatória nesses documentos; respostas conflitantes não são aceitas silenciosamente. O backup anterior contém 8.925 versões; a base corrigida contém 9.918. Os hashes de sete tabelas protegidas, incluindo contas, sessões, tentativas e eventos, permaneceram idênticos após a aplicação. Os 84 caches derivados também foram sincronizados.

Também foram corrigidas regras gerais de extração:

1. Letras A–E em fonte separada são associadas ao texto da mesma linha impressa, evitando deslocar todas as alternativas.
2. Textos explicitamente compartilhados são vinculados a cada questão indicada e retirados do item anterior.
3. A proposta/instrução de redação interrompe a região da questão anterior.
4. Páginas com margem larga e texto atravessando o centro permanecem em uma coluna, quando os cabeçalhos confirmam esse padrão.
5. Grades gráficas quase vazias são preservadas como figuras; não se inventa uma tabela de dados a partir de diagramas.
6. Alternativas de transcrição pendente e caracteres de controle tornam-se pendências verificadas no conteúdo exibido, mesmo quando o relatório importado está em cache.

O PyMuPDF 2.0 instalado usa análise neural de layout por padrão na busca de tabelas. Os métodos geométricos agora declaram `use_layout=False`. A rodada com esse backend explícito manteve geometria como método selecionado; na referência reservada de seis questões, a localização teve F1 de 0,522 e a integridade completa ocorreu em 1/6. Esses números pertencem à referência anotada, não às 8.730 questões sem adjudicação.

O instalador exige a versão anterior e seu hash, fonte/gabarito idênticos aos auditados, ausência de edição posterior e justificativa com evidência. A transação cria versões e registros de revisão; mantém os snapshots, respostas e resultados anteriores. A origem automática e a revisão pedagógica pendente são preservadas. O ensaio encontrou **20 identidades existentes** cujas ocorrências passaram a ter assinaturas diferentes após ampliar a extração. Os vínculos históricos ficam preservados, com adjudicação sinalizada; a assinatura canônica não é substituída por uma escolha arbitrária. Esse encaminhamento não pode encobrir uma mudança de gabarito conflitante.

As duas leituras oficiais coincidiram nas **8.730 posições**, com **15 anulações** e nenhuma divergência após as correções. Passaram os **294 cenários de resultado**, os **144 testes da suíte completa**, seguidos de **42 regressões de contratos**, e a compilação de **6.716 expressões LaTeX** de todo o catálogo. A inspeção técnica de 14 recortes com diferenças de rasterização encontrou equivalência visual local; isso não aprova a montagem das alternativas nem substitui a revisão integral das questões.

Permanecem **928 diagnósticos de preparação em 441 posições**: 470 alternativas incompletas no conteúdo nativo, 216 relações espaciais, 93 tabelas com células mescladas, 85 problemas de alternativas e 64 ocorrências de caracteres de controle. São diagnósticos, não quantidades de questões distintas. A triagem adicional identifica 129 questões com alternativas de transcrição pendente, 41 com possíveis figuras omitidas (75 indicações) e quatro com trechos de redação indevidos. Os 1.064 indicadores de cobertura textual baixa precisam de adjudicação: podem incluir texto em figuras ou fórmulas, além de perdas reais. Ao reunir preparação, triagem, identidade e os casos inspecionados, a fila contém 1.464 posições com algum achado, preservado por versão.

Há limites visuais que os testes de transbordamento não detectam. A inspeção assistida registrou quatro achados em três versões: rodapé anexado à alternativa E e linhas fragmentadas na questão 1 de 2009; cabeçalho repetido como figura na questão 91 do ENEM digital 2020; cartão inteiro em uma imagem na questão 176 do digital 2022. Outros gráficos continuam separados em recortes. Esses casos precisam de segmentação e conferência do conteúdo na etapa 8. A ausência de falha automatizada de navegador não elimina essas pendências.

## Aplicação da etapa 3

`experiment_archive_all.py` aplica o método de layout selecionado a todas as posições publicadas, vinculando cada proposta à versão e à fonte. Geometrias que excedem o limite ficam registradas e usam uma proposta de coordenadas explicitamente identificada.

A aplicação integral concluiu **98 provas, 8.730 questões e 99.187 blocos propostos**, com um fallback de geometria registrado e nenhuma falha de prova restante. Foram produzidas **2.017 propostas temáticas**; 6.713 posições receberam motivo de não aplicação temática. Uma retomada por `--retry-failed` revalidou versões/modelo e preservou os hashes dos 95 artefatos completos da rodada anterior.

O classificador temático é aplicado aos itens válidos de Matemática. As outras áreas recebem o motivo de não aplicação: a referência disponível só cobre oito temas de Matemática. Nenhuma habilidade ou classificação sugerida é promovida ao conteúdo publicado. A aplicação integral mede cobertura e latência; acurácia e F1 continuam restritos aos conjuntos anotados, com treino/desenvolvimento/teste separados.

O inventário histórico encaminha oito ocorrências com texto vazio e 4.403 com suspeita de codificação para recuperação. Isso é triagem do banco bruto; não significa que todos esses itens estejam no site ou que seus gabaritos e layouts tenham sido aprovados. OCR, mapeamentos de fonte e gabaritos visuais continuam com os limites do [protocolo experimental](README.md).

## Reproduzir

Requer o banco local, o espelho e as provas geradas. Use uma pasta nova por execução. Faça backup e ensaie as correções em uma cópia antes de aplicá-las à base de uso.

```bash
.venv/bin/python scripts/backup_sqlite.py backups/antes-auditoria.db
.venv/bin/python scripts/backup_sqlite.py tmp/auditoria/ensaio.db

# Auditoria inicial; --render-sources guarda os recortes das questões.
.venv/bin/python scripts/audit_archive.py \
  --output tmp/auditoria/inicial --render-sources

# Plano de correções; ambiguidades permanecem propostas.
.venv/bin/python scripts/propose_archive_repairs.py \
  --audit tmp/auditoria/inicial --output tmp/auditoria/correcoes

.venv/bin/python scripts/apply_archive_audit.py \
  --plan tmp/auditoria/correcoes/corrections-plan.json \
  --database tmp/auditoria/ensaio.db --apply

# Confere fontes e simula a correção com as versões corrigidas.
.venv/bin/python scripts/audit_archive.py \
  --database tmp/auditoria/ensaio.db \
  --output tmp/auditoria/final --scoring --render-sources

# Compare modelos antes de aplicar o selecionado ao acervo.
.venv/bin/python scripts/run_experiments.py --output tmp/auditoria/modelos
.venv/bin/python scripts/experiment_archive_all.py \
  --database tmp/auditoria/ensaio.db --output tmp/auditoria/etapa3 \
  --model tmp/auditoria/modelos/classification-model.json

# Em outro terminal: npm --prefix frontend run start -- --port 3100
node scripts/audit_archive_browser.cjs \
  --input tmp/auditoria/final --url http://127.0.0.1:3100 \
  --workers 1 --capture-issues

.venv/bin/python scripts/report_archive_audit.py \
  --audit tmp/auditoria/final --experiments tmp/auditoria/etapa3 \
  --initial tmp/auditoria/inicial \
  --plan tmp/auditoria/correcoes/corrections-plan.json
```

`--resume` na auditoria revalida versões, fontes, recursos e recortes antes de reutilizar um relatório. O ensaio de resultados também associa o cache aos itens, gabaritos e código da correção. `--retry-failed` no gerador retoma provas sem relatório completo, validando as versões dos candidatos preservados. Uma falha por prova fica registrada; um relatório parcial não é apresentado como conclusão integral.

O navegador também reaproveita provas completas compatíveis com o build, a versão, o gabarito, o viewport e os recursos do manifesto. Para retomar após alterar somente a orquestração, `--compatible-harness caminho/do/auditor-anterior.cjs` exige que a função de inspeção seja textualmente idêntica; o relatório guarda os dois hashes. O tempo de execução corresponde à rodada registrada, incluindo seu cache, e não é tempo humano de revisão.

O consolidador aceita `--figure-review` para decisões sobre equivalência local de recortes e `--visual-review` para acrescentar achados assistidos. Ambos vinculam as decisões à versão, à fonte e aos bytes das evidências; uma decisão antiga não acompanha conteúdo ou arquivos alterados. A inspeção assistida não remove os demais diagnósticos nem aprova questões. No registro desta rodada, `pixel-review/decisions.json` contém 14 decisões sobre recortes e `conferencia-final/visual-review.json` contém os três casos visuais selecionados.

Sem `--apply`, o instalador valida e desfaz a transação. Depois de conferir o ensaio e o relatório visual, o mesmo plano pode ser aplicado à base de uso:

```bash
.venv/bin/python scripts/apply_archive_audit.py \
  --plan tmp/auditoria/correcoes/corrections-plan.json \
  --apply --sync-derived
```

`--sync-derived` atualiza apenas caches compatíveis com a versão anterior/atual, recalcula os relatórios e guarda um mapa das identidades estáveis. Edições próprias não são sobrescritas. A revisão independente de conteúdo, descrições científicas, rótulos e vínculos continua na etapa 8.

## Arquivos de saída

| Arquivo | Conteúdo |
| --- | --- |
| `sources/<prova>.json` | Questões, versões, gabaritos oficiais, recursos, coordenadas e achados |
| `runs/<prova>.json` | Snapshots usados pelo navegador, sem usuários reais |
| `originals/` | Recortes das fontes |
| `browser/{desktop,mobile}/` | Resultado de cada questão nos dois temas |
| `screenshots/` | Capturas conforme a política escolhida |
| `scoring-report.json` | Resultados e idempotência dos cenários descartáveis |
| `all-proposals/<prova>.json` | Layout e classificação temática por versão |
| `historical-inventory.json` | Integridade e limites do banco histórico |
| `historical-recovery-queue.json` | Ocorrências encaminhadas para recuperação |
| `review.html`, `review-index.json` | Fila local com original, site e diagnósticos |
| `visual-review.json` | Achados assistidos selecionados, com hashes do conteúdo, das fontes e das evidências |
| `complete-report.json` | Cobertura, evidências, correções e pendências consolidadas |

O relatório completo preserva `manual_semantic_review_complete: false` e `independent_pedagogical_review: false`. Não registra tempo humano fictício nem transforma ausência de medição em aprovação.
