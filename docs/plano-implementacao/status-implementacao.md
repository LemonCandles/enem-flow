# Status da implementação

Atualizado em **04/11/2026**. Visão geral do andamento do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

## Situação atual

A **etapa 4 está implementada tecnicamente**: diagnóstico fixo com objetivo, área e tempo disponível, retomada e finalização; estado reconstruído por tema/habilidade com Beta(1,1), primeira resposta independente por identidade, exposição, prática recente e separação da assistência. O painel, o histórico, a exportação e a exclusão incluem diagnósticos. As habilidades entram conforme sua publicação, que depende de segunda revisão. [Contratos e limites](../diagnostico-estado.md).

**A consolidação técnica da primeira entrega e a parte técnica da etapa 2 foram concluídas.** Já é possível entrar em uma conta, realizar uma prova, retomar respostas, finalizar e consultar o histórico e o desempenho.

O **primeiro ciclo técnico da etapa 3** também está implementado: classificação temática com cinco abordagens, partições por identidade antes da avaliação, comparação de coordenadas/geometria/CART em 13 questões e 145 blocos, recuperação experimental de alternativas/tabelas/fontes/gabarito visual e OCR local opcional. Configurações, contratos, modelos, métricas e erros são reproduzíveis por `make experiments`; os [resultados](../experimentos/resultados-2026-11-03.json) e o [protocolo](../experimentos/README.md) preservam os limites da referência assistida. Propostas continuam fora do conteúdo publicado.

A [auditoria integral de 03/11](../experimentos/auditoria-acervo.md) ampliou o trabalho às 98 provas/8.730 posições publicadas. Foram aplicadas 993 correções técnicas por novas versões, incluindo 63 gabaritos de 2009; 294 cenários de correção passaram e os gabaritos coincidiram nas duas leituras oficiais. Os dados das sete tabelas protegidas ficaram idênticos, e o catálogo ativo coincide com a cópia de ensaio. Os experimentos produziram 99.187 blocos e 2.017 propostas temáticas. O navegador concluiu as 17.460 apresentações em desktop/celular, nos dois temas, sem falhas nas verificações automatizadas; a revisão manual integral continua pendente.

O catálogo versionado tem 135 questões conferidas: o segundo dia do ENEM 2024, caderno azul, com 90 questões de Natureza e Matemática, e a seção de Matemática azul de 2023, com 45. Cada item está vinculado às quatro cores da sua aplicação. Com o acervo local, `make acervo` permite publicar cadernos automáticos; o ensaio inicial registrou 96 provas de 2009 a 2025, com 8.595 questões. A origem automática e as pendências conhecidas ficam visíveis no site. Os arquivos gerados não acompanham o clone. A curadoria, inclusive a revisão pedagógica independente, não foi realizada e, assim como a publicação e o piloto, está fora do roteiro atual, que termina na etapa 7. Leitores de tela e aparelhos reais também não foram conferidos.

O lote processado recebido foi incorporado em 01/11/2026: **98 provas e 8.730 questões estão publicadas na instalação local**, incluindo os dois lotes conferidos. O ensaio daquele lote registrou 506 pendências de apresentação em 489 questões. A auditoria de 03/11 corrigiu falhas e acrescentou verificações que faltavam; agora há 928 diagnósticos de preparação em 441 posições, incluindo alternativas incompletas antes não contabilizadas. A fila também preserva achados de triagem e revisão de identidade, sem confundir ausência de diagnóstico com aprovação. Os detalhes históricos estão em [incorporação do acervo](../banco-classificacao.md#incorporação-do-acervo-processado) e os atuais na [auditoria integral](../experimentos/auditoria-acervo.md).

As cinco inconsistências encontradas na revisão posterior foram corrigidas, com regressão em SQLite/PostgreSQL (97 testes em cada), navegador (28 cenários), gateway real e persistência após recriação dos contêineres. Os ajustes preservam os dados históricos e estão descritos no [fechamento da revisão](../revisoes/revisao-projeto-2026-11-01.md#fechamento-das-correções).

A refatoração remota do backend foi integrada preservando essas correções, o contrato HTTP e o banco instalado. A regressão passou a **101 testes em SQLite e 101 em PostgreSQL**; a atualização foi ensaiada em uma cópia das 98 provas, sem modificar os registros existentes. Veja a [validação da integração](../revisoes/revisao-projeto-2026-11-01.md#integração-com-a-refatoração-remota).

## O que já está disponível

- **Jornada do estudante:** conta individual, preferências, catálogo, resolução de provas, respostas salvas, retomada, correção e histórico.
- **Experiência de resolução:** texto selecionável, fórmulas matemáticas e químicas em LaTeX, figuras com legendas e ampliação dentro do site, navegação por botões, mapa e teclado, com retorno ao topo ao trocar de questão.
- **Acompanhamento:** resultados e evolução pessoal, com recortes conforme a classificação disponível no banco.
- **Gestão do conteúdo:** preparação de novas provas, sinalização de ambiguidades, revisão, aprovação, publicação e controle de versões, preservando tentativas anteriores.
- **Banco e classificação:** acervo oficial de 1998–2025 consultável na curadoria, identidade canônica com as ocorrências de cada cor, taxonomia versionada, 135 anotações com evidências e referência de 89 questões de Matemática para os experimentos.
- **Experimentos de Dados e IA:** modelos locais de texto e layout avaliados, separação de treino/desenvolvimento/teste, relatórios por classe e casos de erro, proveniência, propostas e revisão visual offline; comparação com previsões externas de LLM disponível por arquivo.
- **Interface e operação local:** temas claro e escuro, navegação adaptada a telas menores e recursos de backup e recuperação.

## O que está parcial

| Frente | Estado atual | O que falta |
| --- | --- | --- |
| Conteúdo | Dois lotes conferidos e 96 provas automáticas; 993 correções instaladas, gabaritos conferidos nas 8.730 posições e banco histórico preservado. | Resolver/adjudicar os 928 diagnósticos de preparação em 441 posições, as ambiguidades de identidade e os achados de triagem; realizar revisão pedagógica independente. |
| Preparação de provas | Extração, gabaritos, seções e colunas corrigidos por regras gerais; alternativas pendentes são verificadas no conteúdo exibido; recursos e snapshots têm evidências por versão. | Recuperar alternativas ainda incompletas, células mescladas e relações espaciais, conferir descrições e adjudicar as propostas. |
| Classificação e painel | Disciplina e tema publicados com curadoria técnica; o painel mostra a cobertura real. Habilidades estão como propostas. | Segunda anotação independente, adjudicação e publicação das habilidades. |
| Dados e IA | Cinco comparações temáticas e três de layout executadas; referência técnica assistida e teste reservado. Palavras-chave selecionadas por desenvolvimento, com 55,6% de acerto nos 18 itens de teste. | Comparação com LLM, medição da correção por pessoas reais e revisão independente não foram realizadas e estão fora do roteiro atual. |
| Acessibilidade e usabilidade | Texto nativo, ampliação de figuras e navegação por teclado e em telas menores. | Conferência com leitores de tela, aparelhos reais e estudantes. |
| Operação | Instalação isolada em contêineres, regressão em SQLite/PostgreSQL, volumes persistentes e restauração conferidos; verificações da versão registradas. | Preparar a hospedagem e ensaiar a operação no ambiente escolhido. |

## O que ainda não foi iniciado

Seleção adaptativa de questões, tutor com IA e classificação automática integrada ao produto permanecem nas próximas etapas. O suporte técnico ao estado por habilidade já existe; sua cobertura depende da publicação dos rótulos, que exige segunda revisão. Já existem modelos clássicos treinados e avaliados offline na etapa 3; isso não representa diagnóstico educacional, classificação aprovada ou integração de tutor/LLM.

Também continuam previstos a expansão para docentes, os recursos multimodais e os estudos de aprendizagem. A publicação externa e o piloto com estudantes ainda não foram realizados.

## Prioridades imediatas

1. Integrar a política adaptativa (etapa 5) ao estado reconstruível e aos temas já publicados.
2. Usar os erros medidos na etapa 3 para novos ciclos de classificação/layout, preservando o teste e sem publicar as propostas.

A sequência e os critérios de aceite estão em [próximas etapas](proximas-etapas.md).

## Validação e limites

Em 04/11/2026, a etapa 4 passou em **160 testes em SQLite e 160 em PostgreSQL**, com migrações e alinhamento de esquema conferidos em bancos descartáveis. O teste de migração populada preserva os eventos legados e verifica a reconstrução. Passaram também os **30 testes de navegador** em desktop/celular, incluindo a jornada de diagnóstico, verificações Axe, teclado, reflow, exportação e exclusão, além da tipagem, build de produção e 150 expressões LaTeX do lote incluído. A avaliação do estimador é sintética e não demonstra validade pedagógica ou ganho de aprendizagem. O banco de uso não foi migrado por esses ensaios.

Em 03/11/2026, **127 testes passaram em SQLite**, incluindo 26 cenários dos experimentos. A execução offline percorreu os 89 itens temáticos, os 13 exemplos de layout e os 96 cadernos automáticos. O CI ganhou um job reprodutível com os dados incluídos; a execução remota desse job ainda não foi verificada. PostgreSQL, Playwright e contêineres não foram repetidos nesta entrega, que não altera a API, o esquema ou a interface do produto.

Na extensão de auditoria, passaram **144 testes na suíte completa**, seguidos de **42 regressões de contratos** após o tratamento de interrupções do detector e a inclusão de achados assistidos com evidências. Foram compiladas 6.716 expressões LaTeX do catálogo inteiro, conferidos 5.285 recursos com coordenadas declaradas e executados 294 cenários nas rotas de correção em banco descartável. O navegador inspecionou as 8.730 questões nos dois viewports e temas, armazenando 1.070 capturas conforme a política de pendências e primeiro item. Esses resultados não constituem aprovação pedagógica ou revisão visual manual de todos os itens automáticos; as pendências de conteúdo e layout continuam na fila por versão.

As evidências anteriores incluem 101 testes em PostgreSQL, 28 testes Playwright e a instalação Compose sobre Podman com identificação de clientes, proteção contra cabeçalhos falsificados e persistência após recriação. Veja a [integração](../revisoes/revisao-projeto-2026-11-01.md#integração-com-a-refatoração-remota), [banco e classificação](../banco-classificacao.md#validação-da-integração) e [primeira entrega](../primeira-entrega.md). Os testes de celular usam emulação de tela e não substituem o uso em aparelhos reais.

Essas evidências demonstram o funcionamento técnico dos incrementos verificados. A revisão pedagógica independente, a validação manual de acessibilidade e o piloto não foram realizados. Ainda não há resultados de aprendizagem ou avaliação de eficácia educacional.

## Documentos relacionados

- [Plano e escopo do projeto](enem_adaptativo_plano_do_projeto.md)
- [Próximas etapas e critérios de avanço](proximas-etapas.md)
- [Experimentos e protocolo da etapa 3](../experimentos/README.md)
- [Critérios e evidências da primeira entrega](../primeira-entrega.md)
- [Conteúdo e registro técnico da revisão](../../data/README.md)
- [Arquitetura e contratos](../architecture.md)
- [Operação, backup e recuperação](../operations.md)
