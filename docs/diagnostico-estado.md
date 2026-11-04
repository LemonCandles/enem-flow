# Diagnóstico e estado por tema e habilidade

Implementação técnica da etapa 4 em 04/11/2026. O diagnóstico usa os rótulos já publicados, sem promover propostas dos experimentos ou antecipar a curadoria da etapa 8. A política adaptativa permanece na etapa 5.

## Jornada e seleção

A entrada **Diagnóstico** pede objetivo (1–120 caracteres), área e tempo disponível (3–180 minutos). O servidor fixa `min(20, floor(minutos / 3))` itens ao iniciar, reduzindo a quantidade ao acervo elegível. O tempo não encerra a sessão. Respostas são salvas, podem ser alteradas e a sessão pode ser retomada pelo histórico. Gabaritos, resultado e eventos de aprendizagem só ficam disponíveis após a finalização. Cada item preserva a versão, os rótulos e a URL de seu caderno de origem; a numeração da sessão é independente da numeração original.

O seletor `diagnostic-coverage-v1` considera questões aprovadas vinculadas a provas publicadas, com tema, gabarito válido e sem pendências bloqueantes verificadas no conteúdo. A origem automática pode participar se cumprir esses requisitos; propostas externas não participam. Identidades canônicas são deduplicadas, escolhendo a versão elegível mais recentemente criada e, no empate, o maior identificador. A identidade histórica ausente usa `question_id`, conservadoramente.

A cada escolha, o seletor busca itens de um dos temas menos representados, prefere identidades ainda não apresentadas e desempata pela ordem embaralhada com a semente persistida. Todos os rótulos temáticos do item atualizam a cobertura. A sessão guarda versão, semente, quantidade solicitada/obtida, disponibilidade, cobertura por tema (incluindo zeros) e itens repetidos. Questões de provas e sessões iniciadas já contam como apresentadas, sem produzir evidência de desempenho antes da finalização. A sessão pode conter menos itens que temas; a interface informa essa lacuna.

## Contratos

Todas as rotas abaixo exigem autenticação e acessam apenas a própria conta:

| Rota | Contrato |
| --- | --- |
| `GET /diagnostic-options` | `areas`: área, quantidade elegível e mapa tema → quantidade, sem gabarito. |
| `POST /sessions` | `objective`, `area`, `available_minutes`, `idempotency_key` (8–80 caracteres). Retorna sessão e itens públicos. A chave é única por aluno; parâmetros diferentes retornam 409. |
| `GET /sessions/{id}` | Snapshot, respostas e metadados; resultado/gabaritos apenas após finalizar. |
| `PUT /sessions/{id}/answers/{item_id}` | `choice`: A–E ou null; retorna respostas salvas. Recusa alterações após finalizar (409). |
| `POST /sessions/{id}/finish` | Finalização idempotente e transacional, retorna sessão corrigida. |
| `GET /me/sessions` | Histórico de diagnósticos, com respostas e resumo, sem carregar os itens. |
| `GET /me/knowledge-state` | Configuração `estimator`, grupos `themes` e `skills`. |

Área sem itens elegíveis retorna 422; sessão de outra conta retorna 404. O frontend integra os diagnósticos ao histórico e à exportação JSON (`exams` e `diagnostics`). `DELETE /me/history` remove eventos, provas e diagnósticos da conta. Os contratos existentes de `/exam-runs`, `/me/history` e `/me/progress` são mantidos.

## Reconstrução e evidência

`diagnostic_sessions` guarda snapshots e respostas. A migração `d410a4e02001` acrescenta origem de diagnóstico a `learning_events`, exige exatamente uma origem (prova ou diagnóstico) e unicidade por origem/item. Os eventos anteriores são preservados. Finalização, resultado e eventos são gravados na mesma transação, protegida contra finalizações concorrentes. O downgrade elimina os eventos e sessões de diagnóstico, mantendo os eventos de prova; exige backup se for utilizado.

Novos eventos usam contexto `2.0`, com identidade canônica, versão da questão, área, modalidade, ajuda e rótulos/taxonomia. Eventos `1.0` são lidos com seu contexto e o snapshot original para campos ausentes. Informação de ajuda ausente permanece desconhecida. A publicação de novos rótulos não reclassifica evidência anterior.

O estado é reconstruído sob demanda, sem cache ou tabela materializada. Eventos de origens concluídas são ordenados pela finalização, modalidade, identificador da origem, posição e identificador do evento. Temas são separados por área, disciplina e versão de taxonomia; habilidades usam área e identificador oficial. Um item conta uma vez por rótulo distinto e pode contribuir para vários grupos, sem identificar a causa de um erro.

O estimador `beta-first-independent-v1` usa apenas a **primeira resposta marcada, válida e explicitamente sem ajuda por identidade canônica**, considerando conjuntamente provas e diagnósticos. Em branco, anuladas e respostas com ajuda desconhecida não consomem essa primeira evidência. Repetições permanecem nas métricas observadas e na prática recente; uma resposta assistida não altera a estimativa.

- `alpha = 1 + independent_correct`; `beta = 1 + independent_attempts - independent_correct`.
- Média: `alpha / (alpha + beta)`. Sem evidência independente, `estimate = null`.
- `evidence_status`: `none` com zero itens, `low` abaixo de cinco, `available` a partir de cinco. O limiar é uma convenção operacional, sem validação pedagógica.
- Cada grupo informa tentativas/acertos, contagens independentes e assistidas, ajuda desconhecida, repetições, brancos/anuladas, itens apresentados/distintos respondidos, última prática concluída e últimas 20 respostas válidas (incluindo assistidas e repetições).
- Grupos elegíveis atuais aparecem mesmo sem evidência; grupos históricos continuam presentes. Exposição de sessões abertas aparece somente em `seen_items`.

O filtro do painel inicia na área com prática concluída mais recente ou, sem prática, na primeira área disponível. As demais áreas e a opção de mostrar todas continuam acessíveis.

A etapa atual não oferece pistas. Seus eventos novos têm `help_used=false`; o redutor já separa eventos assistidos para a futura integração do tutor. A estimativa descreve respostas observadas, sem calibrar dificuldade ou produzir nota TRI.

## Avaliação e verificação

Os testes sintéticos comparam a taxa bruta e o prior Beta(1,1):

| Acertos / itens independentes | Taxa bruta | Estimativa |
| --- | --- | --- |
| 0 / 0 | Indefinida | Sem estimativa pública |
| 0 / 5 | 0% | 14,29% |
| 2 / 5 | 40% | 42,86% |
| 5 / 5 | 100% | 85,71% |

O prior reduz extremos em amostras pequenas. Uma sequência com 25 respostas ao mesmo item, incluindo ajuda e contexto desconhecido, produz apenas uma evidência independente e preserva as últimas 20 respostas. Esses ensaios validam comportamento técnico, sem demonstrar capacidade preditiva ou ganho de aprendizagem.

Comandos reproduzíveis:

```bash
.venv/bin/pytest -q
# Usar exclusivamente banco descartável com "test" no nome:
TEST_DATABASE_URL=postgresql+psycopg://.../enem_test .venv/bin/pytest -q
DATABASE_URL=sqlite:////tmp/enem-diagnostic-check.sqlite .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:////tmp/enem-diagnostic-check.sqlite .venv/bin/alembic check
cd frontend
npm run typecheck
npm run check:content
npm run build
npm run test:e2e -- --workers=1
```

A migração também é testada com banco SQLite populado na revisão anterior: preserva os eventos campo a campo, reconstrói a estimativa esperada e passa por downgrade/upgrade. A regressão cobre seleção/deduplicação, distribuição temática, concorrência, isolamento de contas, snapshots, assistência, brancos, múltiplos rótulos e taxonomias, além da jornada de navegador em desktop e viewport móvel. Leitores de tela reais e aparelhos físicos permanecem nas pendências externas do projeto.

A implantação requer `alembic upgrade head` antes de iniciar a nova aplicação. As validações locais usam bancos descartáveis; não migram nem alteram o banco de uso.

Em 04/11/2026, passaram 160 testes em SQLite, 160 em PostgreSQL e 30 testes de navegador em desktop/celular, além da tipagem, build de produção e validação das 150 expressões LaTeX do lote incluído. Migrações e alinhamento de esquema foram conferidos em bancos descartáveis.
