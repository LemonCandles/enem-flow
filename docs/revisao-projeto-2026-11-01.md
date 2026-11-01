# Revisão de consistência do projeto

Revisão de 01/11/2026 sobre a versão `b66fd06`, na branch `codex/consolidacao-primeira-entrega`. Foram examinados backend, interface, contratos, identidade das questões, preparação, catálogo, acervo, persistência, configuração de contêineres, CI e documentação. A alteração paralela de `CLAUDE.md` foi preservada.

Foram confirmadas **cinco inconsistências**, descritas abaixo. Os reprodutores usaram bancos descartáveis e respostas simuladas de autenticação no navegador. Não foram executadas alterações, exclusões, redefinições de senha ou tentativas fictícias no banco do site. **Os cinco pontos foram corrigidos e validados em 01/11/2026.** A descrição original e seus locais correspondem à versão revisada; o fechamento registra a implementação posterior.

## R1 — Alta: auditoria recebida no JSON pode contornar os bloqueios de preparação

**Local:** [preparação](../backend/app/preparation/__init__.py), `prepare_content`, linha 51; aprovação em [main.py](../backend/app/main.py), linha 378.

O preparador retorna o conteúdo sem inspecioná-lo quando a versão e o fingerprint recebidos coincidem. O fingerprint exclui a própria auditoria. Assim, o JSON pode declarar `issues: []`, embora o conteúdo contenha uma expressão inválida. A aprovação consulta essa lista recebida, sem validar novamente o conteúdo.

**Reprodução confirmada:** a expressão `Expressão inválida $x^2 sem fechamento.` gera pendência quando preparada normalmente. Com auditoria e fingerprint fornecidos no JSON, a importação retorna 201 e a aprovação retorna **200**, em vez de bloquear a versão. O cenário exige acesso de curadoria; não foi demonstrado acesso indevido de aluno.

**Impacto:** a integridade do relatório de um arquivo externo passa a determinar a liberação da versão. Isso contradiz a garantia de bloqueio automático da importação/aprovação manual. A exceção explícita do acervo automático é um fluxo separado e não justifica o comportamento do fluxo manual.

**Correção indicada:** separar o reaproveitamento de auditorias internas da validação de entrada externa. Validar o conteúdo no servidor e preservar as evidências de extração sem tratar o checksum como autenticação do relatório.

**Aceite:** o mesmo conteúdo inválido deve continuar bloqueado com auditoria ausente, alterada ou produzida externamente; conteúdo válido já normalizado deve manter apresentação e idempotência.

## R2 — Alta no Docker: limite de autenticação compartilhado entre usuários

**Local:** [main.py](../backend/app/main.py), `throttle`, linha 72; [Dockerfile da API](../backend/Dockerfile), linha 17; [Compose](../compose.yaml).

O contador usa exclusivamente `request.client.host`. Na topologia Compose, as requisições chegam pelo contêiner do Next. A API não recebe configuração de proxies confiáveis, e o Uvicorn instalado confia por padrão apenas em loopback. O endereço do contêiner web fica, portanto, como identificador comum dos clientes.

**Reprodução confirmada no nível da aplicação:** simular o mesmo IP de proxy com 30 endereços diferentes em `X-Forwarded-For` consome um único contador. Uma tentativa seguinte, com outro endereço encaminhado e credenciais válidas, recebe **429**. A inspeção da configuração confirma a ausência do ajuste necessário para a topologia Docker. Os contêineres não foram reiniciados nesta revisão.

**Impacto:** cadastro, login e recuperação compartilham o bloqueio de 15 minutos entre usuários distintos. Tráfego de um usuário pode impedir o acesso dos demais.

**Correção indicada:** configurar a cadeia de proxies confiáveis e a identificação do cliente para a implantação, mantendo proteção contra cabeçalhos falsificados. Avaliar separadamente os limites por origem e por conta.

**Aceite:** clientes distintos atrás do proxy devem ter contadores independentes; tentativas repetidas da mesma origem devem continuar limitadas.

## R3 — Média: edição contorna a deduplicação e deixa a identidade inconsistente

**Local:** [main.py](../backend/app/main.py), `edit_question`, linha 345; publicação em [content.py](../backend/app/content.py), linha 70.

A edição copia o `canonical_id` anterior, independentemente do conteúdo novo. A publicação verifica aprovação, total e recursos, mas não reconcilia a assinatura do conteúdo editado nem detecta a duplicata resultante.

**Reprodução confirmada:** copiar o conteúdo da primeira questão para a segunda, mantendo o número da segunda, permite salvar, aprovar e republicar a prova com resposta **200**. As duas versões passam a ter assinaturas idênticas e identificadores canônicos diferentes. A mesma duplicação é rejeitada na importação normal.

**Impacto:** questões iguais podem ser contadas como itens distintos, comprometendo a rastreabilidade, a deduplicação e futuros grupos de particionamento dos experimentos.

**Correção indicada:** verificar colisões de identidade na edição e na publicação, com uma política explícita para correções legítimas de versões. Preservar os snapshots anteriores.

**Aceite:** uma cópia acidental deve ser recusada ou encaminhada à reconciliação; correções de apresentação devem preservar a identidade e o histórico sem criar duplicatas.

## R4 — Média: publicar o catálogo depende de haver conteúdo novo

**Local:** [catalog.py](../backend/app/catalog.py), `install_catalog`, linha 80; opção `--publish-curated` em [cli.py](../backend/app/cli.py), linha 28.

A aprovação/publicação fica dentro de `if changed`. Quando o catálogo foi instalado sem publicação, uma segunda execução com publicação solicitada encontra conteúdos iguais, mantém `changed=False` e ignora a solicitação.

**Reprodução confirmada:** `install_catalog(db, publish=False)` seguido por `install_catalog(db, publish=True)` deixa os dois lotes em **`in_review`**, com zero novas versões. O segundo comando não os disponibiliza.

**Impacto:** uma sequência válida de instalação e publicação pode terminar sem provas disponíveis, embora a operação informe sucesso. A mesma condição pode afetar o bootstrap de uma instalação anteriormente preparada sem publicação.

**Correção indicada:** distinguir atualização de conteúdo de uma solicitação explícita de publicação, respeitando retiradas e decisões manuais anteriores.

**Aceite:** instalar sem publicar e depois publicar deve funcionar; repetir a publicação deve ser idempotente e não criar versões ou decisões duplicadas desnecessárias.

## R5 — Média: recuperação de senha não abre com sessão ativa

**Local:** [app.tsx](../frontend/src/components/app.tsx), linha 77; leitura do token em [auth.tsx](../frontend/src/components/auth.tsx), linha 16.

A leitura de `?recovery=...` ocorre somente no componente `Auth`, que não é montado quando `/me` retorna uma sessão válida.

**Reprodução confirmada no Chrome:** a mesma URL com token sintético apresenta o formulário de nova senha sem sessão e apresenta a página inicial com sessão ativa. Nesse segundo caso, o parâmetro permanece na URL e o fluxo de recuperação não é iniciado. Nenhuma senha foi alterada no teste.

**Impacto:** quem abre um link assistido em navegador com sessão existente não consegue usar o fluxo esperado diretamente. Sair da conta também navega para `/`, perdendo o parâmetro.

**Correção indicada:** tratar a rota/intenção de recuperação antes de escolher a interface pela sessão, mantendo a validação e o consumo do token no backend.

**Aceite:** o link deve abrir o fluxo apropriado com e sem sessão, e o backend deve manter expiração, uso único e revogação das sessões após a alteração.

## Verificações que passaram

- 81 testes de backend em SQLite. A suíte existente não cobre os cinco cenários acima.
- Quatro reprodutores de backend confirmaram R1–R4; a reprodução de R1 incluiu o controle de que a preparação normal bloqueia a mesma expressão.
- Comparação de recuperação com e sem sessão no Chrome confirmou R5.
- TypeScript e compilação das 150 expressões do lote de 2024 e das 159 de 2023.
- Auditoria técnica dos dois lotes conferidos: gabaritos, fontes e recursos verificados.
- Correspondência exata de `docs/content-schema.json` com `ExamImport.model_json_schema()`.
- Reprodução exata do conjunto de referência de 89 itens de Matemática.
- Consistência de contagens, identidades, ocorrências e hashes dos 28 arquivos anuais do banco textual: 44.524 ocorrências e 43.439 identidades conservadoras.
- Auditoria Axe do diálogo de exclusão aberto nas configurações, com autenticação simulada: nenhuma violação reportada nesse cenário.
- Catálogo local com 98 provas publicadas; a tentativa anterior ao carregamento do acervo mantém seus snapshots, respostas e resultado.

Os reprodutores e relatórios temporários desta sessão estão em `tmp/revisao-projeto/`, fora do Git. A revisão atual não repetiu a suíte PostgreSQL, a reconstrução integral do acervo ou o ensaio de contêineres; as evidências anteriores desses trabalhos permanecem nos documentos de entrega.

## Limitações já registradas

As 506 pendências de apresentação em 489 questões, as fontes oficiais indisponíveis, os casos sem gabarito/texto legível e os aceites de leitores de tela/aparelhos reais continuam descritos nos documentos anteriores. São pendências conhecidas, não achados novos desta revisão. A conferência humana permanece na etapa 8.

## Fechamento das correções

| Achado | Implementação | Commit |
| --- | --- | --- |
| R1 | Validação independente dos campos renderizados e dos diagnósticos estruturais, inclusive ao reaproveitar uma auditoria. Aprovação e publicação revalidam registros antigos; apresentação e operações válidas são preservadas. | `2cdd5cb` |
| R2 | Gateway Nginx 1.30.6 como única entrada do Compose. Substitui cabeçalhos enviados pelo cliente; a API confia apenas no IP privado do gateway. Redes e teste de integração com dois clientes incluídos no CI. | `63e9577` |
| R3 | Edição recusa colisões com identidades conhecidas e conteúdo repetido na prova. Publicação verifica identidades e assinaturas atuais, incluindo duplicatas legadas. Revisões legítimas preservam identidade e snapshots. | `db7c810` |
| R4 | Publicação explícita também atende um catálogo já instalado, sem criar versões ou decisões duplicadas. Retiradas, rejeições e edições pendentes continuam preservadas, inclusive durante atualizações do catálogo. | `d1aafe7` |
| R5 | Token tratado antes de carregar a sessão, retirado da URL e encaminhado ao formulário. Após o reset, o backend remove o cookie e a interface solicita login. | `766ee7a` |

Validação posterior às correções:

- **97 testes de backend em SQLite e 97 em PostgreSQL**, com regressões para auditoria alterada, edições duplicadas, versões legadas, publicação posterior e decisões manuais.
- **28 testes Playwright**, em desktop e celular, no build de produção da instalação Compose sobre Podman, com gateway e PostgreSQL. Quatro cenários verificam recuperação com/sem sessão e retorno ao login.
- **Proxy real:** um cliente foi bloqueado após 30 tentativas, mesmo alternando cabeçalhos falsificados; outro contêiner conseguiu cadastrar e entrar. Os mesmos comandos foram incluídos no workflow de CI.
- **Persistência:** API encerrada com código 0; contêineres removidos e recriados sem apagar volumes. Login, resposta, resultado, histórico, 90 snapshots, figura e finalização idempotente preservados.
- **Compatibilidade:** as 98 provas da instalação local continuam compatíveis com a nova verificação de identidade. Os lotes conferidos continuam sem bloqueios; as 506 pendências do acervo automático mantiveram os mesmos tipos e contagens.
- TypeScript e build de produção aprovados. API e frontend locais reiniciados com as correções; backup anterior em `backups/enem-flow-antes-correcoes-2026-11-01.db`.

Os resultados acima foram obtidos localmente. O workflow foi atualizado, mas uma nova execução remota do GitHub Actions não foi verificada nesta etapa. A publicação externa e os aceites humanos continuam nas etapas previstas. O registro e as correções não reescrevem os snapshots nem os resultados históricos.
