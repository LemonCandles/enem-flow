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
| `ENEM_PROXY_SUBNET`, `ENEM_PROXY_IP` | Rede privada do gateway e seu IP fixo; padrões `172.30.246.0/24` e `172.30.246.254`. Ajuste os dois se houver conflito com outra rede. |
| `FORWARDED_ALLOW_IPS` | No contêiner da API, recebe somente `ENEM_PROXY_IP`; não deve aceitar clientes ou redes públicas. |
| `TEST_DATABASE_URL` | Banco descartável exclusivo da suíte; o nome precisa conter `test` |

O `.env` é carregado pelo Docker Compose. Para execução Python direta, exporte as variáveis no shell; o backend não lê `.env` automaticamente. Use uma senha de banco compatível com URL ou codifique os caracteres reservados na `DATABASE_URL`.

O Compose disponibiliza o gateway Nginx na porta 3000 e mantém Next, API e PostgreSQL internos. O gateway encaminha páginas ao Next e `/api/*` diretamente à API. As redes separam banco, frontend e proxy. O IP fixo do gateway é o único proxy autorizado pelo Uvicorn; isso preserva os contadores por cliente sem confiar no endereço do contêiner Next.

O gateway substitui `X-Forwarded-For` pelo endereço da conexão e `X-Forwarded-Proto` pelo protocolo recebido, conforme [`proxy_set_header`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header). Não exponha as portas internas para contornar essa entrada. A imagem está fixada em Nginx 1.30.6, versão estável listada nas [publicações oficiais](https://nginx.org/). Atualizações de API ou Next pelo Compose também reiniciam o gateway para renovar os endereços dos serviços.

Para publicar em outro domínio, configure HTTPS, origem autorizada e cookie seguro. Se houver outro proxy antes do gateway, configure explicitamente quais endereços dele são confiáveis para recuperar o IP do cliente. O repositório não contém credenciais ou uma implantação em conta de terceiros. Não use `docker compose down -v` para uma parada rotineira: essa opção remove volumes persistentes.

## Administração e recuperação de acesso

```bash
.venv/bin/python -m backend.app.cli create-admin revisor@exemplo.com
.venv/bin/python -m backend.app.cli recovery-link aluno@exemplo.com --base-url http://localhost:3000
```

Em Docker, substitua o início do comando por `docker compose exec api python`. O operador verifica a identidade fora da aplicação e entrega o link pelo canal combinado com o usuário. O link vale por 30 minutos, é de uso único e invalida sessões anteriores ao alterar a senha. A aplicação não envia e-mails. Somente o hash do token fica no banco.

O link abre o formulário de recuperação mesmo com sessão ativa. O token sai da URL ao abrir, permanece apenas no estado transitório do formulário e é validado pelo backend ao enviar a nova senha. Após a alteração, o cookie é removido e a interface solicita novo login.

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

## Atualizações e volume de recursos

O processo inicial sincroniza os recursos incluídos da imagem para `data/assets/` antes da migração/importação. Só acrescenta arquivos ausentes; arquivos com o mesmo nome e bytes diferentes interrompem a inicialização para evitar invalidar tentativas antigas. Recursos novos devem ter nomes novos. Arquivos próprios no volume são preservados.

Depois da preparação, o servidor substitui o processo de inicialização com `exec`, recebendo o sinal de parada diretamente. O CI exige saída normal da API antes de recriar os contêineres, além de conferir a persistência dos dados.

## Repetir a validação em contêineres

Use um projeto e variáveis exclusivos de teste. O arquivo `compose.test.yaml` muda a porta da interface para 3300; não utiliza o projeto/volumes da instalação normal.

```bash
export POSTGRES_DB=enem_ci_test
export POSTGRES_USER=enem_ci
export POSTGRES_PASSWORD=uma-senha-exclusiva-deste-ensaio
export ALLOWED_ORIGINS=http://localhost:3300,http://127.0.0.1:3300
export COOKIE_SECURE=false

docker compose -p enem-validacao -f compose.yaml -f compose.test.yaml up --build -d --wait
.venv/bin/python scripts/verify_deployment.py create --url http://localhost:3300 --state tmp/ensaio.deployment-state.json

docker compose -p enem-validacao -f compose.yaml -f compose.test.yaml down
docker compose -p enem-validacao -f compose.yaml -f compose.test.yaml up -d --wait
.venv/bin/python scripts/verify_deployment.py check --url http://localhost:3300 --state tmp/ensaio.deployment-state.json
```

O arquivo de estado contém credenciais descartáveis e é criado com permissão 0600; mantenha-o em `tmp/` ou outro diretório privado fora do Git. Use uma nova saída para cada ensaio. A remoção de volumes só deve ocorrer na limpeza desse projeto descartável, após conferir seu nome; nunca na parada rotineira da aplicação.

Com API/interface de teste iniciadas, rode os navegadores com `E2E_BASE_URL=http://localhost:3300`. O relatório de acessibilidade e as capturas ficam em `frontend/test-results/`. A validação no CI usa Docker Engine. Localmente foi usado o Compose oficial 5.6.1 conectado à API temporária de Podman 5.8.9 rootless, sem alterar os serviços locais da aplicação.

## Evidências da consolidação de 31/10/2026

- 57 testes de API em SQLite e 57 em PostgreSQL 17.7; migrações e `alembic check` aprovados.
- Build em Python 3.13/Node 22 com instalação de dependências em ambiente isolado, sem copiar `.venv`, `node_modules`, `.env` ou o banco de execução.
- Compose com três serviços saudáveis. Banco e recursos sobreviveram à substituição dos contêineres; recurso próprio permaneceu no volume após atualização.
- `verify_deployment.py` confirmou resposta B, resultado 1/89, histórico, figura, 90 snapshots e finalização idempotente antes/depois da substituição.
- Backup SQLite restaurado em caminho separado: integridade `ok`, 195 versões de questões, uma prova e uma tentativa preservadas. A origem não foi modificada.
- Dump/restauração PostgreSQL em banco separado: linhas e hashes do conteúdo completo de questões, provas, tentativas, eventos e revisões idênticos no momento da comparação.

As verificações de navegador e CI estão em [primeira entrega](primeira-entrega.md). Estes são ensaios técnicos com dados descartáveis, sem evidência de aprendizagem ou de piloto educacional. Repetir os procedimentos no ambiente escolhido para hospedagem continua parte da implantação.

## Atualizar os lotes e a classificação

Faça backup do banco e dos recursos antes de atualizar. Na versão da etapa 2:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m backend.app.cli catalog --publish-curated
```

`make migrate seed` também aplica as migrações e o catálogo incluído. A migração `f831ef101a02` acrescenta a identidade canônica sem reescrever o conteúdo ou os snapshots. A instalação cria versões dos rótulos dos 90 itens de 2024 e acrescenta os 45 de Matemática de 2023. É idempotente; uma edição própria não reconhecida interrompe a transação em vez de ser sobrescrita. Novas classificações valem para novas tentativas; o histórico mantém seus rótulos originais.

## Instalar o banco histórico local na curadoria

O espelho de PDFs e o banco textual histórico são locais e recuperáveis; não integram a imagem por padrão. Primeiro execute a sincronização e a indexação descritas em [fontes oficiais](../data/sources/README.md). Depois, opcionalmente, monte o banco gerado como somente leitura:

```bash
# Exige data/bank/ já gerado por scripts/build_bank.py.
docker compose -f compose.yaml -f compose.archive.yaml up --build -d
```

Essa composição mantém o volume de figuras e acrescenta `data/bank/` para consulta administrativa. Os PDFs continuam acessíveis pelas URLs oficiais registradas; o banco textual não se torna público. Sem o banco local, a aplicação mantém o catálogo conferido e o inventário de fontes, com zero ocorrências extraídas instaladas nesse ambiente. Não confundir essa ausência local com cobertura histórica vazia.
