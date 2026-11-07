# Enem Flow

Plataforma de estudos para o ENEM. Interface, documentação e commits em pt-BR.

## Desenvolvimento

- Leia README para requisitos e `make setup`, `make dev`, `make doctor`.
- Backend FastAPI/SQLAlchemy/Alembic; SQLite local, PostgreSQL no Docker.
- Frontend Next.js/React/TypeScript. Antes de editar, leia `frontend/AGENTS.md` e os guias pertinentes em `frontend/node_modules/next/dist/docs/`.
- Preserve lockfiles e trabalho existente. Execute `make test`, `make lint` e build conforme a mudança. Use bancos descartáveis nos testes, inclusive navegador; nunca migrar o banco de uso para ensaios.
- Commit por decisão lógica, Conventional Commits, descrição pt-BR, minúsculas, verbo na terceira pessoa. Não incluir menções a IA ou Co-Authored-By.

## Organização

`backend/app/main.py` monta routers e políticas HTTP. Domínio fica em `services/`, contratos em `schemas/`, persistência em `models/`, instaladores em `installers/`. Serviços lançam exceções de domínio, sem depender de HTTP. Ingestão offline em `ingestion/`, comandos reutilizáveis em `scripts/` (importar `_bootstrap` primeiro).

Frontend: chamadas nomeadas em `lib/endpoints.ts`, contratos em `lib/types.ts`, diferenças entre prova/diagnóstico/prática em `lib/attempt-source.ts`. Sessão por cookie HttpOnly. Preserve isolamento de redes, cabeçalhos de origem e confiança restrita ao gateway no Docker.

## Integridade

- Correções criam versões. Preserve respostas, resultados, snapshots e decisões manuais; finalização transacional e idempotente. Gabaritos privados até concluir.
- Identidade canônica não altera ordem/letras/gabarito das ocorrências. Bloquear colisões e duplicatas tanto na edição como na publicação.
- Importação comum cria rascunho; pendências bloqueiam publicação. Catálogo automático é exceção explícita e conserva proveniência e diagnósticos. “Disponível” não é aprovação pedagógica.
- Preparação recebida no JSON não é confiável; aprovação/publicação validam conteúdo independentemente. Habilidades candidatas ficam fora dos rótulos publicados.
- Texto nativo selecionável, sem HTML arbitrário; LaTeX/KaTeX para fórmulas e química, figuras originais para estruturas gráficas. Ampliação com teclado, Escape e retorno de foco.
- Anuladas fora do denominador; brancos no denominador. Sem TRI; cobertura e estimativa não significam domínio.
- Fontes oficiais são imutáveis e vinculadas a URL/SHA-256. Nunca substituir gabarito por outra aplicação. Versionar novas provas exige pedido explícito.
- Dois baselines de 2024 são compatibilidade em produção, não caches. Não removê-los sem substituir a leitura segura dos snapshots antigos.

## Documentação

Mantenha guias permanentes e o roteiro atual. Resultados de execução ficam em artefatos de teste/CI e `tmp/`; não criar relatórios por sessão nem scripts de correção por número de questão. Decisões do conteúdo ficam nos dados e versões; histórico de mudanças fica no Git.

Referências: `docs/architecture.md`, `docs/operations.md`, `docs/preparacao-provas.md`, `docs/banco-classificacao.md`, `docs/plano-implementacao/`.
