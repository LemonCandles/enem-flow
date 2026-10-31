# Enem Flow

MVP de estudos para o ENEM: provas oficiais, correção, histórico, painel e curadoria versionada.

- **Backend:** Python, FastAPI, SQLAlchemy e Alembic em `backend/`. Usa SQLite localmente e PostgreSQL no Docker.
- **Frontend:** Next.js 16 e React 19 em `frontend/`. Antes de alterar o frontend, leia `frontend/AGENTS.md`: a versão do Next.js tem APIs diferentes das conhecidas.
- **Idioma:** interface, documentação e mensagens de commit em português do Brasil.
- **Comandos:** `make setup`, `make api`, `make web`, `make test` e `make build`. O README traz o roteiro completo, incluindo o Playwright.
- **Dados no Git:** só os dois lotes conferidos (2024, 2º dia azul; Matemática 2023 azul), com figuras, PDFs de prova e gabarito, bases de revisão, anotações e o dataset de referência, além de taxonomia, exemplos e catálogo de fontes. O acervo histórico, o banco textual (`data/bank/`) e os caches de `data/derived/` ficam locais. Não versione novas provas sem pedido explícito. A lista liberada fica no `.gitignore`.

## Commits — Conventional Commits 1.0.0

Siga https://www.conventionalcommits.org/pt-br/v1.0.0/ em todos os commits.

```
<tipo>[(escopo)][!]: <descrição>

[corpo opcional]

[rodapé(s) opcional(is)]
```

**Tipos**
- `feat`: nova funcionalidade (MINOR).
- `fix`: correção de bug (PATCH).
- `docs`, `test`, `build`, `ci`, `chore`, `refactor`, `perf`, `style`, `revert`.

**Escopo**: um substantivo curto, em minúsculas e sem acento, entre parênteses. Reutilize os escopos já usados no histórico antes de criar outro: `api`, `web`, `auth`, `persistencia`, `conteudo`, `curadoria`, `correcao`, `questoes`, `navegacao`, `design`, `operacao`, `qualidade`, `dev`, `git`, `repo`, `mvp`, `plano`, `consolidacao`. Para `ci`, o escopo pode ser omitido.

**Descrição**
- Verbo no presente da 3ª pessoa: "adiciona", "corrige", "documenta", "refina".
- Inicial minúscula e sem ponto final.
- Até cerca de 72 caracteres.
- Exemplos do histórico:
  - `feat(navegacao): adiciona atalhos e foco acessível na prova`
  - `fix(operacao): preserva recursos em volumes persistentes`
  - `docs(consolidacao): registra validações e adia aceites externos`

**Corpo**: separado da descrição por uma linha em branco. Explica o quê e o porquê, não o como.

**Rodapés**: separados do corpo por uma linha em branco, no formato `Token: valor`. Use hífen no lugar de espaços no token (`Refs: #12`, `Reviewed-by: Nome`). A exceção é `BREAKING CHANGE`.

**Mudanças incompatíveis**: indique com `!` antes dos dois-pontos (`feat(api)!: ...`), com o rodapé `BREAKING CHANGE: <descrição>`, ou com os dois. Isso vale para mudanças de API, do contrato JSON (`docs/content-schema.json`) e para migrações que exigem ação manual.

**Regras do projeto**
- Faça um commit por mudança lógica. Se ela abrange vários tipos, divida em commits.
- Nunca use mensagens genéricas como "commit temp", "ajustes" ou "wip".
- Não adicione `Co-Authored-By` nem menção a IA ou ao Claude.

## Identidade visual — "Conhecimento em construção"

**Fonte de verdade:** `frontend/src/app/globals.css`. Os tokens de cor ficam em `:root` (tema claro) e em `:root[data-theme='dark']` (tema escuro). Use sempre as variáveis (`--bg`, `--panel`, `--sidebar`, `--ink`, `--muted`, `--line`, `--line-strong`, `--teal`, `--teal-ink`, `--mint`, `--success`, `--danger`, `--warning` e as variantes `-bg`). Não use hex soltos nos componentes.

**Documentação do design:** `docs/propostas-design/`
- `README.md`: direção visual, geometria dos encaixes, paleta e caminhos do código.
- `paletas.svg`: paleta dos dois temas.
- `proposta-clara.png`, `proposta-escura.png` e `proposta-mobile.png`: capturas atuais.
- Outras capturas ficam em `docs/screenshots/`.

**Código da identidade**
- `frontend/src/lib/puzzle-geometry.ts`: geometria das peças de encaixe.
- `frontend/src/components/design.tsx`: marca (`Brand`), peças (`LearningPieces`) e divisória dos cartões (`CardSeam`).
- `frontend/src/components/dashboard.tsx`: página inicial.
- `frontend/src/components/theme-toggle.tsx`: troca de tema.
- `frontend/src/app/layout.tsx`: script do tema inicial. Lê a chave `enem-flow:theme` do `localStorage` e, se ela não existir, segue `prefers-color-scheme`.

**Resumo**
- Fonte Manrope Variable (`@fontsource-variable/manrope`).
- Títulos de entrada com peso 300, texto com peso regular e botões com peso 600.
- Fundos neutros e quentes, com acento verde `#009485` (`--teal`). O texto sobre o acento é `#131313`.
- Três peças de encaixe com contornos complementares representam leitura, raciocínio e prática.
- Ilustrações em SVG com o mesmo traço e as mesmas cores dos componentes.
- Ícones do `lucide-react`.
- Barra lateral fixa no desktop e menu recolhido em telas menores.
- Os enunciados e as alternativas são conteúdo nativo do JSON. A decoração fica fora da área de leitura das questões.

**Ao alterar a identidade**, atualize no mesmo commit (`feat(design)` ou `fix(design)`) o `globals.css`, o `docs/propostas-design/README.md`, o `paletas.svg` e as capturas afetadas.
