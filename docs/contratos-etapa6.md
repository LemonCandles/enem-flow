# Contratos preparatórios da etapa 6

Status: tutor em prática e adaptador de layout integrados conforme as seções abaixo ([tutor](architecture.md#tutor), [layout](architecture.md#layout-dinâmico)). Tutor e layout podem ser liberados independentemente. O tutor funciona sem provedor contratado, apenas com material aprovado.

## Tutor

A unidade de ajuda é tentativa + item + versão do conteúdo + nível (orientação, pista intermediária, resolução). Cada entrega de ajuda registra identificador idempotente, aluno, modo, material aprovado utilizado, versão do provedor/modelo/prompt, horário, custo, latência e resultado. Pedidos repetidos não devem duplicar ajuda nem cobrança deliberadamente. Falhas e respostas não entregues não contam como ajuda utilizada.

Provas abertas não aceitam ajuda que revele gabarito. A primeira integração utilizável será em prática, com material previamente aprovado. Sem material aprovado ou provedor disponível, a prática continua com sua apresentação atual; erros do tutor não finalizam nem bloqueiam respostas.

O servidor deriva `help_used` dos eventos efetivamente entregues, nunca de um booleano enviado pelo cliente. Na finalização, o snapshot da ajuda alimenta LearningEvent; itens assistidos ficam fora da evidência independente. Eventos legados mantêm sua semântica atual. Exportação e exclusão de histórico incluem ajuda; autorização segue a propriedade da tentativa.

O adaptador de provedor recebe somente o contexto necessário e retorna proposta estruturada. Ferramentas permitidas ficam em lista explícita, inicialmente apenas consulta a material aprovado e cálculo determinístico. Não há execução de código arbitrário. Limites de tempo/custo são configuração obrigatória na futura integração, com cancelamento e fallback. Conteúdo gerado continua proposta até aprovação humana; não há aprovação automática por resposta bem formada.

Aceites, cobertos por `backend/tests/test_tutor.py`: acesso de outro aluno negado, repetição idempotente, timeout, resposta inválida, ausência de referência, bloqueio de gabarito, distinção entre ajuda solicitada/entregue, exportação/exclusão e reconstrução da evidência assistida.

## Layout

Um adaptador versionado converte propostas experimentais em blocos de conteúdo existentes. Entrada inclui questão/versão, fingerprint da fonte, blocos, ordem e vínculos. Recusar fonte divergente, recurso ausente, vínculo inválido ou ordem incompleta. Propostas não alteram snapshots nem conteúdo publicado.

A liberação exige aprovação e comparação com o original nos casos de avaliação. Preservar texto nativo, ordem de leitura, relações de tabela/legenda/alternativas, reflow e teclado. Falha usa os blocos publicados existentes. Testes de layout não reajustam o conjunto reservado; mudanças de contrato/modelo preservam proveniência. Os aceites estão em `backend/tests/test_layout.py`.
