# Validação

## Verificações reproduzíveis

- `make test`: backend em banco descartável, TypeScript e contratos/hashes/recursos/LaTeX da distribuição.
- `make lint`: Ruff e Prettier; `make build`: frontend de produção.
- `make doctor`: dependências, conteúdo, revisão do banco local e diferenças do perfil. Não reverte decisões manuais.
- `npm --prefix frontend run test:e2e`: navegador desktop/celular, teclado, Axe e jornadas. Inicie serviços em banco descartável; os cenários criam contas e alteram histórico. Instale Chromium/FFmpeg pelo Playwright; Chrome existente pode ser indicado por `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.
- PostgreSQL: configure `TEST_DATABASE_URL` com banco exclusivo cujo nome contenha `test`; a suíte remove suas tabelas. Ensaie migrações e `alembic check` em banco descartável separado.
- Compose: use projeto exclusivo e `compose.test.yaml`, depois `scripts/verify_deployment.py create/check` para verificar persistência entre recriações.

O CI executa esses fluxos e conserva resultados como artefatos. O job `clean-install` parte de checkout novo, executa setup duas vezes e confere seis provas/540 posições. Nenhum teste depende de relatórios datados de execuções anteriores.

## Conteúdo e compatibilidade

`make check-distribution` cobre todos os JSONs distribuídos e figuras referenciadas. Hash alterado exige revisão intencional, não atualização automática do manifesto para ocultar erro. Pendências conhecidas continuam registradas nos dados. Testes dos lotes conferidos comparam gabarito e fontes oficiais; os testes de snapshots asseguram compatibilidade com conteúdo antigo.

Os geradores pontuais de transcrição e decisões editoriais foram removidos; dados conferidos e testes de integridade permanecem. Relatórios experimentais são regenerados por `make experiments` em `tmp/`.

## Medição e limites

`scripts/benchmark_local.py --database CAMINHO` mede consultas em SQLite somente leitura. Informe tamanho do catálogo e existência de histórico ao interpretar os tempos. Não extrapole medições de seis provas para o acervo histórico.

Navegador móvel é emulação; Axe não substitui leitores de tela e aparelhos reais. Integridade técnica não é revisão pedagógica nem demonstra aprendizagem. Contratos da etapa 6 não representam tutor integrado.
