# Arquitetura da primeira entrega

Monólito modular em dois processos: Next.js 16 / React 19 / TypeScript para a experiência e FastAPI / SQLAlchemy para domínio, autorização e persistência. Os manifests têm versões diretas fixadas e os lockfiles do npm e Python fixam também as transitivas. PostgreSQL é a referência de implantação. SQLite, com WAL e chaves estrangeiras, permite desenvolvimento local sem serviços extras.

O frontend encaminha `/api/*` para a API configurada por `API_INTERNAL_URL`. Esse destino é definido no build de produção; ao mudá-lo, gere um novo build. O navegador usa uma única origem, sem tokens em localStorage ou exposição de credenciais de banco. As fontes são servidas pelo próprio frontend.

A unidade de trabalho confirma a transação antes de enviar a resposta HTTP, usando o [escopo de função das dependências FastAPI](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#early-exit-and-scope). Uma falha de commit pode assim retornar erro ao cliente antes de indicar sucesso.

```mermaid
flowchart LR
  Aluno[Aluno / Curadoria] --> Web[Next.js]
  Web --> API[FastAPI]
  API --> Auth[Contas e sessões]
  API --> Content[Banco e revisão]
  API --> Runs[Execuções e correção]
  API --> Progress[Histórico e agregações]
  Auth --> DB[(PostgreSQL / SQLite)]
  Content --> DB
  Runs --> DB
  Progress --> DB
  Content --> Assets[Recursos locais e PDFs originais]
```

## Limites e contratos

`schemas.py` define o contrato 1.0 de conteúdo: item canônico, versão, enunciado, imagens com descrição, alternativas, área, rótulos, página e layout separado. O campo opcional `blocks` estende o contrato com parágrafos, imagens, tabelas e fórmulas tipados, sem quebrar importações antigas. O texto do JSON é renderizado como HTML; KaTeX usa entrada não confiável, expansão limitada e saída HTML/MathML. Não se aceita HTML arbitrário. O gabarito existe apenas no backend até a conclusão. As respostas públicas usam uma lista explícita de campos permitidos; o layout e os links de gabarito não são expostos durante a prova.

Fórmulas explícitas usam `$...$`, `$$...$$`, `\(...\)` ou `\[...\]`; química usa mhchem (`\ce{...}`). Texto comum permanece selecionável. `image.caption`, `image.credit` e `image.equations` associam legenda, fonte e rodapé matemático à figura em `figure`/`figcaption`. A mesma apresentação acompanha a ampliação em diálogo nativo, com zoom e rolagem internos, Escape e restauração do foco. Não há navegação para uma nova guia ao ampliar.

`presentation.py` adapta apenas snapshots antigos conhecidos que coincidam pelo SHA-256 do conteúdo completo normalizado pelo contrato. Extração inicial e apresentação native-v1 ficam preservadas em `data/derived/baselines/`. A adaptação também confere número, área, gabarito, anulação, rótulos e página. Substitui somente os campos de apresentação; identificadores, versões, escolhas e resultados permanecem os do snapshot. A atualização do catálogo cria novas versões com `seed --publish-reviewed --refresh-bundled`, recusando edições próprias e alterações de dados de avaliação. O lote native-v2 tem motivos por questão em `layout.presentation_review` e na trilha `reviews` do banco.

`content.py` valida recursos existentes, importa rascunhos e impede publicação incompleta ou sem revisão. Correções geram novas versões; a prova fica em revisão até aprovação e republicação. Rejeitar uma versão vinculada a uma prova publicada também suspende sua publicação. A trilha `reviews` guarda autor, ação, justificativa e instante. Reutilizar um item canônico permite ligá-lo a vários cadernos; detecção automática de duplicatas permanece futura.

`exam_runs` fixa ordem, conteúdo completo, versão e metadados da prova no início. Isso preserva também as tentativas ainda abertas quando uma questão é corrigida ou uma prova é retirada. O resultado, as escolhas definitivas e os eventos são registrados na mesma transação.

Antes de alterar respostas ou finalizar, um UPDATE inócuo adquire o bloqueio da execução. Funciona no PostgreSQL e no SQLite, onde SELECT FOR UPDATE seria ignorado. A finalização verifica o estado após obter o bloqueio: chamadas concorrentes retornam o mesmo resultado, com uma única série de eventos. O início usa chave de idempotência única por usuário; reutilizá-la para outra prova retorna conflito.

`scoring.py` corrige exclusivamente por gabarito: brancos contam no denominador e não como respostas; anuladas ficam fora do desempenho. O painel soma tentativas de provas concluídas, inclusive repetições; não deduplica um item que o aluno resolveu novamente. Rótulos múltiplos podem sobrepor grupos. Cobertura significa a fração de tentativas válidas com pelo menos um rótulo do tipo considerado, não domínio de conhecimento.

## Preparação de conteúdo

`backend/app/preparation/` é o preparador compartilhado de JSON, sem dependência de PDF/Node nas requisições da API e sem regras por número de questão. `POST /admin/imports` e a edição de versões o executam automaticamente; `/admin/imports/prepare` oferece prévia sem gravação. Converte notação reconhecida, associa blocos adjacentes às figuras e registra hashes, operações e pendências em `layout.preparation`. Agrupamentos/delimitadores LaTeX inválidos e perdas de layout conhecidas bloqueiam aprovação e publicação. Os avisos ficam na curadoria; o aluno recebe a lista permitida de campos de apresentação.

O adaptador offline `scripts/exam_pdf.py` usa PyMuPDF, regiões, cabeçalhos, posição dos caracteres e marcadores A–E para preparar PDFs textuais. `scripts/prepare_exam.py` aceita JSON ou manifesto, produz um rascunho e relatório, confere recursos e compila o LaTeX com o KaTeX/mhchem do frontend. Saída automática não equivale a aprovação. [Uso e limites](preparacao-provas.md).

## HTTP

A especificação OpenAPI executável está em `/openapi.json` e `/docs` na API. Erros usam `detail`; validações acrescentam `errors`, sem devolver a entrada bruta de senhas.

As rotas seguem a organização de [aplicações maiores do FastAPI](https://fastapi.tiangolo.com/pt/tutorial/bigger-applications/). `backend/app/main.py` só monta a aplicação: log, política de requisições, tratamento de validação, arquivos de `/assets` e inclusão dos routers. Cada funcionalidade tem seu router em `backend/app/routers/`:

| Router | Rotas |
| --- | --- |
| `health.py` | `/health` |
| `auth.py` | `/auth/*` e limite de tentativas |
| `account.py` | `/me` e `/me/preferences` |
| `exams.py` | `/exams` e `/exams/{id}` |
| `runs.py` | `/exam-runs/*` |
| `progress.py` | `/me/history` e `/me/progress` |
| `admin/content.py` | importação, edição, revisão, publicação e auditoria em `/admin` |
| `admin/archive.py` | `/admin/archive/*` e `/admin/taxonomy` |

A lógica de domínio continua nos módulos de `backend/app/`, como `content.py`, `scoring.py`, `security.py` e `preparation/`, que também servem a CLI e os scripts.

| Operação | Acesso | Comportamento |
| --- | --- | --- |
| `POST /auth/register`, `/auth/login` | Público, limitado por tentativas | Cadastro ou sessão por cookie |
| `POST /auth/logout`, `/auth/reset-password` | Sessão / token de uso único | Revogação; redefinição invalida sessões |
| `GET /me`, `PUT /me/preferences` | Conta | Dados próprios e preferências |
| `GET /exams`, `/exams/{id}` | Público | Somente provas publicadas, sem gabarito |
| `POST /exam-runs` | Conta | Início com `exam_id` e `idempotency_key` |
| `GET /exam-runs/{id}` | Dono da execução | Conteúdo fixado e rascunhos ou resultado |
| `PUT /exam-runs/{id}/answers/{item_id}` | Dono, prova aberta | `choice` A–E ou null para limpar |
| `POST /exam-runs/{id}/finish` | Dono | Finalização transacional, repetível |
| `GET /me/history`, `/me/progress` | Conta | Histórico e agregações próprias |
| `DELETE /me/history` | Conta | Remove execuções e eventos próprios |
| `POST /admin/imports` | Curadoria | Valida JSON e recursos, cria rascunho |
| `GET /admin/exams`, `/admin/exams/{id}` | Curadoria | Inclui conteúdo e estados de revisão |
| `PUT /admin/questions/{version_id}` | Curadoria | Nova versão, com justificativa |
| `POST /admin/reviews/{target_id}` | Curadoria | Aprovar, rejeitar, publicar ou retirar |
| `GET /admin/audit` | Curadoria | Últimas 200 decisões |

Respostas: 401 para sessão inválida; 403 para papel/origem inadequados; 404 para recurso inacessível (inclusive execução alheia); 409 para conflito de estado/idempotência; 422 para contrato inválido; 429 para excesso de autenticações. Os testes verificam essas fronteiras.

## Segurança e continuidade implementadas

Senhas usam scrypt com sal individual; tokens opacos têm apenas o hash persistido. Cookies são HttpOnly e SameSite Strict, com Secure configurável para HTTPS. As mutações validam Origin contra uma lista explícita. Login, cadastro e redefinição têm limite persistido de 30 tentativas por IP em 15 minutos. O IP é guardado como hash; cabeçalhos encaminhados não alteram esse identificador. Em proxy com muitos usuários, planeje limitação por cliente no proxy antes de um piloto maior.

O banco, os arquivos originais e o gabarito nunca entram no diretório público do frontend. A API serve apenas `data/assets`. Campos de importação rejeitam chaves extras; caminhos de recursos não aceitam travessia de diretório. Não há chamadas a provedores de IA nem jobs pesados na requisição do aluno.

Cada requisição recebe `X-Request-ID`, controle de cache e registro de método, caminho, status e latência. A autenticação por recuperação é assistida pelo operador, sem envio de e-mail nesta versão. Observabilidade p50/p95, trabalhadores de extração genérica e provedores externos serão acrescentados conforme o volume exigir.
