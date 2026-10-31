# Executar, recuperar e continuar

## Configuração

`make setup` cria o ambiente, instala dependências, aplica a migração e importa o conjunto incluído. `make api` e `make web` iniciam os processos locais. O frontend só precisa alcançar o backend; ele não acessa o banco diretamente. Em produção, o Compose usa PostgreSQL com volumes persistentes e migrações no início.

| Variável | Uso |
| --- | --- |
| `DATABASE_URL` | URL SQLAlchemy; ausente significa `enem-flow.db` na raiz |
| `API_INTERNAL_URL` | Destino de `/api` no Next; configure antes do build (padrão `http://127.0.0.1:8000`) |
| `ALLOWED_ORIGINS` | Origens exatas separadas por vírgula, incluindo protocolo e porta |
| `COOKIE_SECURE` | `true` para implantação com HTTPS; `false` permite desenvolvimento HTTP local |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credenciais do Compose; o arquivo `.env` fica fora do Git |
| `TEST_DATABASE_URL` | Banco descartável exclusivo da suíte; o nome precisa conter `test` |

O `.env` é carregado pelo Docker Compose. Para execução Python direta, exporte as variáveis no shell; o backend não lê `.env` automaticamente. Use uma senha de banco compatível com URL ou codifique os caracteres reservados na `DATABASE_URL`.

O Compose disponibiliza a interface na porta 3000 e mantém API e PostgreSQL internos. Para publicar em outro domínio, configure proxy HTTPS, origem autorizada e cookie seguro. O repositório não contém credenciais ou uma implantação em conta de terceiros. Não use `docker compose down -v` para uma parada rotineira: essa opção remove volumes persistentes.

## Administração e recuperação de acesso

```bash
.venv/bin/python -m backend.app.cli create-admin revisor@exemplo.com
.venv/bin/python -m backend.app.cli recovery-link aluno@exemplo.com --base-url http://localhost:3000
```

Em Docker, substitua o início do comando por `docker compose exec api python`. O operador verifica a identidade fora da aplicação e entrega o link pelo canal combinado com o usuário. O link vale por 30 minutos, é de uso único e invalida sessões anteriores ao alterar a senha. A aplicação não envia e-mails. Somente o hash do token fica no banco.

## Migrações e verificação

```bash
.venv/bin/alembic upgrade head
.venv/bin/alembic check
make test
make build
```

Antes de alterações de esquema, faça backup. O rollback da migração inicial remove as tabelas: prefira restaurar um snapshot para recuperar dados. Depois de um novo deploy, confira `/health`, login, catálogo e uma execução. Os logs de requisição incluem um identificador, método, caminho, status e duração; não registram senhas ou corpos de requisição. A API mantém a execução disponível sem dependências de IA.

## Backup local com SQLite

```bash
.venv/bin/python scripts/backup_sqlite.py backups/enem-flow-2026-10-30.db
tar -czf backups/conteudo-2026-10-30.tar.gz data/assets data/sources data/enem-2024-dia2-azul.json
```

O script usa a API de backup do SQLite, que produz uma cópia consistente mesmo com WAL ativo, e verifica sua integridade. O destino não pode existir. Não copie apenas o arquivo `.db` durante gravações em WAL.

Para ensaiar uma restauração, use outro caminho, preserve o banco atual e abra a cópia:

```bash
DATABASE_URL=sqlite:////caminho/absoluto/backups/enem-flow-2026-10-30.db .venv/bin/alembic current
```

Ao recuperar a aplicação, pare as gravações, restaure o banco para um caminho novo, recupere os arquivos de conteúdo correspondentes e configure `DATABASE_URL` para esse caminho. Confira contas, provas, versões e histórico antes de voltar a aceitar tráfego.

## Backup com PostgreSQL

Na instalação Compose:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > enem-flow.dump
docker compose cp api:/app/data/assets ./assets-backup
docker compose cp api:/app/data/sources ./sources-backup
```

Restaure primeiro em um banco separado e vazio, usando `pg_restore --no-owner --no-privileges --dbname=NOME_DO_BANCO enem-flow.dump`, com as variáveis de conexão `PGHOST`, `PGPORT`, `PGUSER` e `PGPASSWORD` configuradas no ambiente. O dump inclui a revisão Alembic e os dados. Não execute migrações antes de restaurar o dump em um banco vazio; depois da restauração, compare a revisão com o código que irá executar.

Mantenha juntos banco, arquivos de conteúdo, configuração e revisão do código. Correções manuais precisam de uma nova versão; os arquivos referenciados por tentativas anteriores devem continuar disponíveis. Em operação contínua, restrinja acesso aos backups e defina retenção de acordo com o uso real.

## Evidências desta versão

Em 30/10/2026, a atualização de apresentação nativa passou com **21 testes no SQLite e 21 no PostgreSQL**, além de **6 testes Playwright** (jornada, falha de salvamento e JSON nativo em desktop e celular). Foram verificadas tabelas HTML, MathML, diagramas nas alternativas, ausência de recortes de texto e preservação de tentativas. O build de produção e a checagem TypeScript passaram. A migração e o alinhamento do esquema continuam verificados com `alembic check`.

O ensaio de `pg_dump`/`pg_restore` foi executado entre dois bancos PostgreSQL temporários e vazios, com o conteúdo inicial e uma tentativa concluída. Na cópia restaurada foram conferidos: 90 versões de questões, a alternativa B na questão 91, resultado de 1 acerto em 89 questões válidas, os 90 snapshots dos itens e 90 eventos, preservando os identificadores. O backup SQLite também passou por `PRAGMA integrity_check` e confirmou as 90 versões. Essas verificações operacionais não são evidência de eficácia educacional ou de um piloto com estudantes.
