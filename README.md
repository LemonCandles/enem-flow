# Enem Flow

Primeira entrega da plataforma descrita no [plano do projeto](docs/plano-implementacao/enem_adaptativo_plano_do_projeto.md): conta individual, provas oficiais, respostas editáveis, correção, histórico, painel e curadoria versionada.

![Visão geral da plataforma](docs/screenshots/desktop.png)

## Executar localmente

Requisitos: Python 3.13 ou 3.14, Node.js 22 e npm. A execução local usa SQLite e não exige contas externas. Fontes e conteúdo estão incluídos no projeto.

```bash
make setup
```

Em dois terminais, na raiz:

```bash
make api
```

```bash
make web
```

Acesse **http://localhost:3000** e crie sua conta. A documentação interativa da API fica em **http://localhost:8000/docs**. Não existe senha administrativa padrão.

Se preferir `uv`, crie o ambiente com `uv venv .venv` e instale com `uv pip install --python .venv/bin/python -r backend/requirements-dev.lock`; depois execute `make migrate seed` e `npm ci` em `frontend/`.

## Executar com PostgreSQL e Docker

```bash
cp .env.example .env
# Defina POSTGRES_PASSWORD em .env antes de iniciar.
docker compose up --build
```

Abra **http://localhost:3000**. Migrações e importação do conjunto revisado são executadas no início, sem duplicar conteúdo. PostgreSQL e imagens têm volumes persistentes; a API fica na rede interna dos contêineres.

## O que está implementado

- Cadastro, login, sessão por cookie HttpOnly, saída, preferências e recuperação assistida por link de uso único.
- Catálogo com busca e filtros por ano, área, aplicação e caderno; distinção entre caderno completo, seção e coleção.
- Caderno oficial completo **ENEM 2024, segundo dia, azul: 90 questões**. Original e gabarito preservados com SHA-256. A questão 129 está anulada e não entra no desempenho.
- Enunciados e alternativas em texto selecionável a partir do JSON; tabelas em HTML, fórmulas com MathML e imagens apenas para figuras e diagramas.
- Navegação livre, alteração e limpeza de alternativas, salvamento no servidor e retomada após fechar ou recarregar.
- Confirmação de conclusão, correção objetiva, revisão por questão e finalização transacional e idempotente.
- Histórico individual, evolução e painel por área, matéria, tema e habilidade, com quantidade de tentativas e cobertura dos rótulos.
- Curadoria: importar JSON, comparar com o original, editar criando nova versão, aprovar questões, publicar ou retirar provas e consultar decisões.
- Migração inicial, ambiente Docker, testes críticos da API e testes reais de navegador em desktop e celular.

As classificações temáticas e habilidades não foram inventadas: o conjunto inicial tem área e a disciplina Matemática identificadas pelo próprio caderno. Os demais rótulos ficam explicitamente pendentes. Classificadores, adaptação, tutor com LLM e layouts dinâmicos pertencem às próximas etapas.

## Curadoria

```bash
.venv/bin/python -m backend.app.cli create-admin seu-email@exemplo.com
```

A senha é solicitada no terminal. Em Docker: `docker compose exec api python -m backend.app.cli create-admin seu-email@exemplo.com`. Entre com essa conta para acessar **Curadoria**. Novas importações sempre entram como rascunho; todas as versões precisam de aprovação antes de publicar.

## Verificar

```bash
make test
make build
```

Com API e frontend iniciados:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

Para usar o Chrome já instalado, configure `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/caminho/do/google-chrome`. Os testes de navegador criam contas descartáveis e excluem seus históricos ao concluir. Para PostgreSQL, use `TEST_DATABASE_URL` apontando para um **banco exclusivo de testes com `test` no nome**; a suíte cria e remove suas tabelas.

## Documentação da entrega

- [Plano do projeto em Markdown](docs/plano-implementacao/enem_adaptativo_plano_do_projeto.md)
- [O que foi feito e o que falta](docs/plano-implementacao/status-implementacao.md)
- [Próximas etapas](docs/plano-implementacao/proximas-etapas.md)
- [Escopo, critérios de aceite e validação](docs/primeira-entrega.md)
- [Arquitetura, contratos e decisões](docs/architecture.md)
- [Operação, backup e recuperação](docs/operations.md)
- [Origem do conteúdo e conferência](data/README.md)
- [Contrato JSON de importação](docs/content-schema.json)
- [Design implementado — Conhecimento em construção](docs/propostas-design/README.md)
- [Interface em tema escuro](docs/screenshots/desktop-escuro.png)
- [Visualização em celular](docs/screenshots/mobile.png)
- [Questão com texto nativo no celular](docs/screenshots/questao-mobile.png)
- [Vídeo da jornada completa](docs/demo.webm)

Código sob a licença MIT. Textos, figuras e provas de terceiros conservam a origem e os direitos de seus respectivos titulares; consulte a documentação do conjunto. Produto independente, sem vínculo ou endosso do Inep.
