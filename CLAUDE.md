# Enem Flow

Estudos para o ENEM: contas, provas oficiais, respostas persistentes, correção, histórico, painel e curadoria versionada. Interface, documentação e commits em pt-BR.

## Stack

- **Backend:** Python 3.13/3.14, FastAPI, SQLAlchemy, Alembic; SQLite local, PostgreSQL no Docker.
- **Frontend:** Next.js 16 / React 19 / TypeScript. Antes de editar, leia `frontend/AGENTS.md` e os guias pertinentes em `frontend/node_modules/next/dist/docs/`.
- **Dependências:** preserve lockfiles.

## Comandos

Execute na raiz; API e frontend em terminais separados.

| Comando | Uso |
| --- | --- |
| `make setup` | Instalar dependências e preparar banco |
| `make api` / `make web` | API na porta 8000 / site na 3000 |
| `make migrate seed` | Atualizar esquema e catálogo; faça backup antes |
| `make test` | pytest, TypeScript e validação LaTeX |
| `make lint` / `make format` | Conferir / aplicar ruff e Prettier |
| `make build` | Build de produção |
| `npm --prefix frontend run test:e2e` | Playwright, com serviços iniciados |
| `make acervo` | Gerar/publicar provas locais sem curadoria |

**Testes:** use banco isolado, inclusive ao iniciar serviços para Playwright ou ensaiar migrações. Configure `DATABASE_URL` para esses serviços e `TEST_DATABASE_URL` para pytest/PostgreSQL; este último exige `test` no nome do banco, e a suíte remove suas tabelas. Docker/recuperação: `docs/operations.md`.

## Mapa do código

O backend está organizado por responsabilidade. Caminhos abaixo relativos a `backend/app/`; mantenha `main.py` como montagem da aplicação.

| Caminho | Responsabilidade |
| --- | --- |
| `main.py`, `middleware.py` | Montagem, ciclo de vida, routers, arquivos estáticos e política HTTP |
| `routers/` | Rotas por funcionalidade; `admin/` protege curadoria e acervo com a dependência de administrador no router pai |
| `dependencies.py` | Aliases `Annotated`: `SessionDep`, `CurrentUser`, `AdminUser`; a sessão confirma ou desfaz a transação antes de enviar a resposta |
| `core/` | `config.py`: `ROOT`, banco e ambiente; `db.py`: engine, `Base` e sessão; `security.py`: autenticação e papéis |
| `models/`, `schemas/` | Tabelas e contratos separados por domínio; os pacotes reexportam seus tipos |
| `services/` | Conteúdo/publicação, identidade, apresentação, correção, taxonomia e leitura do banco textual (`archive_reader.py`) |
| `installers/` | `curated.py`: catálogo conferido; `generated.py`: acervo automático; `bundled.py`: atualização do lote incluído; `assets.py`: figuras no volume |
| `preparation/` | Preparador compartilhado, executado na importação e edição |
| `cli.py` | Administração local via `python -m backend.app.cli` |

- **Fontes oficiais — `ingestion/`:** espelho do acervo, extração de PDF e banco textual, sempre offline. `scripts/` guarda os pontos de entrada; cada um importa `_bootstrap` primeiro. Scripts com regras por questão são registro histórico e ficam como estão.

- **Frontend — `frontend/src/`:** `components/`, `lib/`, `app/`. As chamadas da API ficam em `lib/endpoints.ts`, os tipos em `lib/types.ts`; prova e diagnóstico diferem só em `lib/attempt-source.ts`, e as páginas são escolhidas pela tabela de `components/app.tsx`. Sessão por cookie HttpOnly.
- **Entrada HTTP:** no acesso direto ao Next, `/api/*` usa rewrites e `API_INTERNAL_URL` é definido no build. No Compose, o gateway Nginx encaminha `/api/*` diretamente à API e as páginas ao Next. Preserve as redes internas, a substituição dos cabeçalhos de origem e a confiança apenas no IP privado do gateway.
- **Contrato/preparação:** `backend/app/schemas/content.py`, com tipos reexportados por `backend.app.schemas`; mantenha `docs/content-schema.json` correspondente a `ExamImport.model_json_schema()`. PDF offline: `ingestion/exam_pdf/` e `scripts/prepare_exam.py`. Registre ambiguidades; evite regras por questão.
- **Acervo:** `scripts/archive_enem.py` sincroniza originais; `scripts/build_bank.py` gera banco textual. Preserve a indicação de extração automática e suas pendências nas provas geradas.

## Conteúdo e integridade

- Texto/alternativas selecionáveis do JSON, sem HTML arbitrário. Matemática/química em LaTeX, KaTeX/mhchem (`\ce{...}`); preserve fórmulas e distratores da fonte. Estruturas gráficas continuam figuras originais.
- Figura reúne `caption`, `credit`, `equations`. Ampliação em diálogo interno, com teclado, zoom, Escape e retorno do foco.
- Correções criam versões; preserve respostas, resultados e snapshots. Identidade canônica não altera ordem/letras/gabarito das ocorrências. Finalização transacional e idempotente; gabaritos privados até concluir.
- Edição recusa colisões de identidade e conteúdo duplicado na prova; publicação repete a verificação, inclusive para versões antigas. Não remova esses bloqueios ao reorganizar o código.
- Anuladas fora do denominador/cobertura; brancos no denominador. Sem TRI; cobertura de rótulos não significa domínio.
- Importação normal cria rascunho; pendências bloqueiam aprovação/publicação. Acervo automático é exceção explícita, sem equivaler a conteúdo conferido. Habilidades candidatas ficam fora de `labels.skills` até segunda revisão.
- Auditoria recebida no JSON não é confiável: o fingerprint permite reaproveitar apresentação, mas preparação, aprovação e publicação validam o conteúdo independentemente. Preserve os avisos e a origem das extrações automáticas.
- Instalar/publicar o catálogo é idempotente e preserva retiradas, rejeições e edições manuais pendentes, inclusive quando a atualização cria versões.
- Recuperação de senha abre com ou sem sessão, retira o token da URL e mantém uso único e expiração. Após redefinir, revogue as sessões e remova o cookie.

## Dados e fontes

- Lotes conferidos: 2024 dia 2 azul (90) e Matemática 2023 azul (45); 133 válidos, referência matemática de 89 itens. Acervo 1998–2025, todas as aplicações disponíveis: `docs/cobertura-acervo.md`.
- Originais imutáveis: `data/sources/enem/{ano}/{aplicacao}/{modalidade}/dia-*/caderno-*/`; inventário URL/SHA-256: `data/sources/catalogo/acervo.json`. Nunca substitua gabarito por outra aplicação. Organização: `data/sources/README.md`.
- Git: dois lotes conferidos e, como extração automática sem conferência, as provas geradas da aplicação regular de 2024 (1º dia) e 2025 (1º e 2º dias), caderno azul, com JSON, relatório, figuras e PDFs; além de recursos, baselines, anotações, taxonomia, exemplos e catálogo de fontes. Espelho histórico, `data/bank/`, caches e as demais provas geradas ficam locais; o `.dockerignore` mantém essas provas fora da imagem. Confira `.gitignore`; versionar novas provas exige pedido explícito.

## Andamento e roteiro

- Etapas técnicas 1/2, primeiro ciclo de Dados/IA (3), diagnóstico (4) e política adaptativa (5) implementados; próxima: tutor e layouts dinâmicos (6). Experimentos offline em `experiments/`, comando `make experiments`, protocolo em `docs/experimentos/README.md`. Propostas não publicam conteúdo; referência assistida, LLM externo e tempos humanos têm seus limites registrados. Tutor previsto. Política adaptativa: `services/adaptive.py`, função pura e versionada; `docs/politica-adaptativa.md`. Siga `docs/plano-implementacao/proximas-etapas.md`; atualize-o e `status-implementacao.md` após entregas.
- Auditoria integral: `docs/experimentos/auditoria-acervo.md`, `make audit-archive`, `make audit-archive-browser` e `make experiments-all`. Correções locais exigem plano com versões/hashes e ensaio; `scripts/apply_archive_audit.py` preserva histórico, edições posteriores e a revisão independente pendente. Divergências de identidade não podem encobrir alterações de gabarito.
- O roteiro termina na etapa 7: curadoria, publicação externa e piloto saíram dele. Use conteúdo/rótulos disponíveis e não registre esses itens como feitos. Revisão independente, leitores de tela e aparelhos reais exigem validação efetiva.
- Serviços e instaladores não dependem de HTTP: lançam as exceções de `services/errors.py`, que `main.py` converte em resposta.

## Identidade visual

- “Conhecimento em construção”: acolhedor, fundos neutros quentes claro/escuro preservados, verde `#009485`, Manrope, sidebar esquerda. Peças SVG integradas com contornos complementares mesmo separadas; decoração fora das questões.
- Tokens: `frontend/src/app/globals.css` (variáveis, sem hex nos componentes); geometria: `frontend/src/lib/puzzle-geometry.ts`; arte: `frontend/src/components/design.tsx`. Mudanças visuais atualizam `docs/propostas-design/{README.md,paletas.svg}` e capturas afetadas.

## Fluxo de trabalho

- Confira implementação/diff; preserve trabalho alheio. Teste o comportamento alterado; não declare validações não executadas.
- Um commit por decisão lógica: Conventional Commits 1.0.0, `tipo(escopo): descrição`, verbo na 3ª pessoa, minúsculas, ~72 caracteres, sem ponto. Reutilize escopos; incompatibilidades usam `!`/`BREAKING CHANGE`. Sem mensagens genéricas, `Co-Authored-By` ou menções a IA.

## Referências sob demanda

- `README.md`: instalação e uso.
- `docs/architecture.md`: arquitetura e contratos.
- `docs/preparacao-provas.md`: extração e limites.
- `docs/banco-classificacao.md`: identidade, taxonomia e rótulos.
- `docs/revisoes/revisao-projeto-2026-11-01.md`: correções de consistência e validação da integração com a refatoração remota.

Mantenha métricas/evidências nos relatórios.
