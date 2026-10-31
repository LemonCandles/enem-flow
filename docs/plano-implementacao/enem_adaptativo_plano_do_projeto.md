# Enem Adaptativo

**Proposta de desenvolvimento incremental**

Documento de planejamento | 29.10.2026 | v2.0

Origem: conversão do documento de planejamento em PDF, versão 2.0, de 29/10/2026.

Esta versão em Markdown preserva o conteúdo das 21 páginas, com títulos, listas, tabelas e referências. Os cabeçalhos e rodapés repetidos foram reunidos nos dados do documento acima.

## Sumário

- [01. Enem Adaptativo](#01-enem-adaptativo)
- [02. Escopo e organização das entregas](#02-escopo-e-organização-das-entregas)
- [03. Primeira etapa da plataforma](#03-primeira-etapa-da-plataforma)
- [04. Banco de provas e qualidade inicial](#04-banco-de-provas-e-qualidade-inicial)
- [05. Equipes e contratos de integração](#05-equipes-e-contratos-de-integração)
- [06. Classificação temática das questões](#06-classificação-temática-das-questões)
- [07. Identificação e análise do layout](#07-identificação-e-análise-do-layout)
- [08. Diagnóstico e modelo do aluno](#08-diagnóstico-e-modelo-do-aluno)
- [09. Seleção adaptativa e modelos avançados](#09-seleção-adaptativa-e-modelos-avançados)
- [10. Tutor com LLM e ferramentas](#10-tutor-com-llm-e-ferramentas)
- [11. Renderização dinâmica das questões](#11-renderização-dinâmica-das-questões)
- [12. Curadoria assistida e automatizada](#12-curadoria-assistida-e-automatizada)
- [13. Arquitetura e integração dos módulos](#13-arquitetura-e-integração-dos-módulos)
- [14. Modelo de dados e eventos](#14-modelo-de-dados-e-eventos)
- [15. API e telas principais](#15-api-e-telas-principais)
- [16. Avaliação técnica reproduzível](#16-avaliação-técnica-reproduzível)
- [17. Piloto e aprendizagem real](#17-piloto-e-aprendizagem-real)
- [18. Operação custos e continuidade](#18-operação-custos-e-continuidade)
- [19. Desenvolvimento com IA e portfólio](#19-desenvolvimento-com-ia-e-portfólio)
- [20. Roadmap e critérios de conclusão](#20-roadmap-e-critérios-de-conclusão)
- [21. Referências e termos do plano](#21-referências-e-termos-do-plano)

## 01. Enem Adaptativo

Proposta de desenvolvimento incremental da plataforma e do projeto de Dados e Inteligência Artificial

A proposta é construir uma plataforma de resolução de provas e aprendizagem personalizada para o Enem. A primeira entrega permitirá autenticação, realização de provas, correção e acompanhamento do desempenho. Em paralelo, uma equipe de Dados e IA desenvolverá a classificação temática e a análise visual das questões.

**Todo o escopo da proposta original permanece planejado.** Esta revisão reorganiza as entregas e acrescenta os trabalhos de classificação, reconstrução de layouts e curadoria automatizada. Diagnóstico, adaptação, tutor com LLM, expansão de cobertura e pesquisa continuam na evolução do produto.

| Linha de trabalho | Resultado esperado |
| --- | --- |
| Plataforma base | Conta individual, banco de provas, resolução com navegação livre, histórico e painel do aluno. |
| Dados e IA em paralelo | Questões estruturadas, classificação por tema e habilidade, análise do layout e avaliação dos modelos. |
| Integrações progressivas | Diagnóstico, prática adaptativa, tutor com IA, layouts dinâmicos e curadoria assistida. |
| Expansão e pesquisa | Quatro áreas, turmas e docentes, modelos avançados, multimodalidade e exercícios gerados com revisão. |

#### Diretriz da revisão

Entregar uma plataforma utilizável enquanto os modelos são desenvolvidos. A arquitetura inicial deve permitir integrar cada recurso conforme os dados, a avaliação e a prioridade, sem exigir que todas as frentes terminem juntas.

O documento reúne escopo, entregas, responsabilidades, contratos, arquitetura, avaliação e critérios de conclusão. O marco de 15 de novembro de 2026 é mantido como referência de demonstração, com uma proposta de replanejamento compatível com o novo MVP.

Preparado para Cássio Silva. Nome provisório do projeto. Todas as funcionalidades, quantidades e datas são propostas de planejamento; nenhum resultado técnico ou educacional é apresentado como já obtido.

## 02. Escopo e organização das entregas

A divisão por etapas organiza as dependências e preserva a visão completa do produto.

| Entrega ou frente | Capacidades previstas | Posição no plano |
| --- | --- | --- |
| Plataforma base | Contas, histórico, provas por ano, questões com layout padronizado, navegação, correção e painel. | MVP |
| Qualidade inicial | Importação, busca, imagens, gabaritos, revisão, aprovação e versões do conteúdo. | MVP e contínua |
| Classificação temática | Disciplinas, temas e habilidades; investigação de LLMs e alternativas. | Dados em paralelo |
| Análise de layout | Blocos, posições, ordem de leitura e associação de textos, imagens e alternativas. | Dados em paralelo |
| Diagnóstico e adaptação | Modelo do aluno, reforço, revisão, exploração e justificativa da seleção. | Integração progressiva |
| Tutor com LLM | Pistas graduais, explicações, diálogo e recuperação de conteúdo revisado. | Integração progressiva |
| Layouts dinâmicos | Renderização dos elementos a partir da estrutura espacial aprovada. | Integração progressiva |
| Curadoria automatizada | Detecção de problemas, sugestões, correções controladas e revisão humana. | Evolução antecipável |
| Cobertura e docentes | Linguagens, Matemática, Natureza e Humanas; turmas, atividades e visão agregada. | Expansão |
| Modelos e extensões | Knowledge tracing, calibração, políticas avançadas, multimodalidade, análise do raciocínio e geração revisada. | Pesquisa e expansão |
| Avaliação e operação | Testes, benchmarks, métricas, custos, implantação, piloto e relatórios. | Transversal |

#### Planejamento flexível

Adaptação, tutor e layouts dinâmicos podem entrar em momentos diferentes. A curadoria automatizada pode ser antecipada se a qualidade do banco for o principal gargalo. Os critérios de liberação continuam valendo em qualquer ordem.

## 03. Primeira etapa da plataforma

O MVP permite realizar provas e consultar resultados sem depender de classificadores automáticos.

### Jornada do aluno

- **Entrar na conta.** Cadastrar-se, autenticar-se e acessar um ambiente individualizado, com histórico e preferências.

- **Escolher uma prova.** Consultar o catálogo por ano, aplicação, caderno e área; abrir uma prova disponível e começar pela primeira questão.

- **Responder e navegar.** Ver o enunciado, as imagens associadas e as alternativas. Avançar, voltar e modificar escolhas antes de finalizar.

- **Finalizar.** Confirmar a conclusão, corrigir as respostas objetivas pelo gabarito e registrar o resultado da execução.

- **Acompanhar.** Consultar o desempenho geral e por matéria, área e habilidade, conforme os metadados revisados disponíveis.

### Apresentação padronizada das questões

A estrutura visual inicial será: **1. enunciado; 2. imagens associadas, quando houver; 3. alternativas.** A extração precisa manter a pergunta principal, fórmulas, legendas, tabelas e vínculos das figuras. Imagens que integram alternativas devem continuar associadas às respectivas opções.

#### Fidelidade do conteúdo desde o MVP

A padronização não pode alterar o significado da questão. Quando a organização espacial for essencial e ainda não houver uma extração equivalente, revisar manualmente e usar uma representação aprovada do trecho original, ou manter o item em rascunho até resolver o problema.

### Critério de conclusão do MVP

Um aluno consegue entrar, abrir uma prova completa validada, responder, voltar, alterar uma resposta, finalizar e consultar o resultado persistido no próprio histórico e painel. Reenvios da finalização não duplicam resultados. O fluxo funciona no celular e com navegação por teclado.

O painel apresenta número de tentativas e cobertura dos rótulos. Temas ainda não classificados ficam explícitos; ausência de rótulo não é interpretada como ausência de dificuldade.

## 04. Banco de provas e qualidade inicial

A cobertura de todos os anos permanece como objetivo, com publicação progressiva de conteúdo validado.

Usar provas e gabaritos oficiais como referência [1], a matriz do Enem para os códigos de competências e habilidades [2] e, quando úteis, os microdados de cada edição [3]. A taxonomia própria de assuntos deve permanecer distinta dos códigos oficiais.

| Processo | Tratamento e condição para publicar |
| --- | --- |
| Aquisição | Preservar PDF, URL de origem, ano, aplicação, caderno, área, página e hash do arquivo. |
| Extração | Capturar enunciado, comando, fórmulas, tabelas, imagens e alternativas; aplicar OCR quando necessário e conferir com o original. |
| Deduplicação | Identificar a mesma questão em cadernos de cores diferentes; manter um item canônico e o vínculo com cada ocorrência. |
| Organização da prova | Preservar ordem, numeração, versão dos itens, gabarito e eventuais escolhas de língua ou seção. |
| Anotação e solução | Revisar temas e habilidades. Preparar resoluções e pistas aprovadas para os recursos de tutoria. |
| Publicação | Liberar somente o conjunto validado; diferenciar prova completa, seção e coleção parcial no catálogo. |

### Cobertura inicial e expansão

A primeira entrega deve conter pelo menos uma prova completa validada para demonstrar a jornada. O catálogo cresce até abranger os anos e aplicações definidos pelo projeto. Exibir claramente o que já está disponível e o que ainda depende de importação ou revisão.

A meta original de **80 a 150 questões de Matemática em 6 a 8 temas** continua como referência para o primeiro conjunto de experimentos adaptativos. Esse recorte não substitui o objetivo do catálogo de provas nem deve ser apresentado como cobertura de todo o Enem.

#### Curadoria mínima é parte da primeira entrega

Mesmo com automação prevista para depois, o MVP precisa de revisão, aprovação, correção manual e versionamento. Itens anulados, incompletos ou inconsistentes exigem tratamento explícito e não devem distorcer o cálculo de desempenho.

Preservar erratas e condições de uso dos textos e imagens. Uma correção futura não altera silenciosamente o conteúdo vinculado a tentativas antigas.

## 05. Equipes e contratos de integração

Duas equipes avançam em paralelo sobre o mesmo modelo de conteúdo e critérios compartilhados.

| Responsável | Trabalho previsto | Entregas verificáveis |
| --- | --- | --- |
| Equipe de Plataforma | Contas, interfaces, provas, histórico, painel, APIs, adaptação, tutor, renderizador e operação. | Fluxos executáveis, contratos HTTP, persistência, regras de acesso e testes críticos. |
| Equipe de Dados e IA | Extração, classificação temática, análise de layout, conjuntos anotados, experimentos e curadoria assistida. | Dados estruturados, rótulos, layouts, versões de modelos, métricas e casos de erro. |
| Responsabilidade conjunta | Taxonomia, identificadores, formato das questões, critérios de revisão, compatibilidade e aceite das integrações. | Esquemas versionados, exemplos aprovados e acompanhamento de regressões. |

### Contratos definidos antes dos modelos

- **Questão canônica.** Identificador estável, versão, origem, blocos de conteúdo, alternativas e arquivos associados; o gabarito fica protegido no backend.

- **Classificação.** Disciplina, temas e habilidades, versão da taxonomia, origem da anotação, modelo ou revisor e estado de aprovação.

- **Layout.** Tipos de bloco, posições, ordem de leitura, vínculos e versão do esquema; separar proposta automática de estrutura aprovada.

- **Publicação.** Estados como rascunho, em revisão, aprovado e retirado; contratos de entrada, saída, erro e compatibilidade entre versões.

### Como evitar bloqueios entre equipes

A Plataforma começa com questões revisadas e rótulos manuais ou importados. Dados e IA valida os modelos sobre conjuntos anotados e entrega resultados no mesmo contrato. O renderizador e o painel podem ser desenvolvidos com exemplos estruturados antes da conclusão do treinamento.

#### Integração por maturidade

Aceitar uma entrega de dados exige validar o esquema, a integridade e os critérios de qualidade. Processamentos pesados ficam fora da requisição do aluno; uma falha de classificação ou layout não interrompe provas já publicadas.

## 06. Classificação temática das questões

A primeira frente de Dados e IA estrutura o conteúdo que alimentará o painel e a adaptação.

O objetivo é identificar disciplina, conteúdos, temas, competências e habilidades avaliadas. Uma questão pode receber vários rótulos; o vínculo com habilidades oficiais precisa de evidência e revisão, sem ser deduzido apenas pelo nome do assunto.

### Abordagens a investigar

LLMs são candidatos para interpretar semanticamente enunciados e propor rótulos. A escolha será experimental: comparar regras ou revisão assistida, classificadores supervisionados e abordagens com representações de texto, conforme o conjunto disponível. Questões dependentes de figuras exigem informação visual ou encaminhamento para revisão.

| Passo | Resultado esperado |
| --- | --- |
| Taxonomia | Definições, exemplos e critérios para disciplina, tema e habilidade; manter versão e relações entre rótulos. |
| Conjunto de referência | Questões anotadas por pessoas, com divergências discutidas e exemplos difíceis preservados. |
| Experimentos | Comparação de precisão, revocação, F1 por classe, consistência, latência e custo por questão. |
| Saída estruturada | Rótulos propostos, justificativa curta ou evidência, origem, versão e indicação de necessidade de revisão. |
| Publicação | Rótulos revisados e rastreáveis disponíveis para busca, painel, diagnóstico e recomendação. |

### Ligação com as entregas da plataforma

O MVP utiliza as classificações já aprovadas, inclusive manuais. Conforme a cobertura aumenta, o painel ganha detalhamento e a prática adaptativa recebe mais itens elegíveis. Atualizações da taxonomia devem permitir recalcular agregações e explicar mudanças nos relatórios.

#### Confiança precisa de validação

A confiança declarada por um modelo não deve ser tratada automaticamente como probabilidade de acerto da classificação. Definir limites de encaminhamento para revisão com base em um conjunto independente e observar erros por tema.

Classificar o assunto não prova a causa do erro do aluno. A inferência sobre dificuldades exige histórico, contexto e quantidade de evidência.

## 07. Identificação e análise do layout

A segunda frente de Dados e IA representa a estrutura visual e as relações entre os elementos.

O objetivo vai além de atribuir um tipo de layout à questão. É necessário localizar seus componentes, compreender a ordem de leitura e associar imagens, legendas, tabelas e alternativas aos textos corretos, inclusive quando um item atravessa colunas ou páginas.

| Variação encontrada | Informação a preservar |
| --- | --- |
| Texto à esquerda e imagem à direita | Relação entre os blocos e posição da pergunta principal abaixo deles. |
| Texto acima e imagem centralizada | Sequência entre texto de apoio, figura, legenda e comando final. |
| Alternativas em posições variadas | Ordem A a E e vínculo de cada opção com textos, fórmulas ou imagens. |
| Tabelas e elementos compartilhados | Estrutura interna, cabeçalhos, referências e vínculos entre questões quando houver. |

### Tecnologias e experimentação

Investigar extração das coordenadas do PDF, OCR, regras de geometria e visão computacional. Modelos supervisionados de detecção de objetos ou análise de documentos são candidatos quando necessários. Detecção de objetos pode envolver aprendizado profundo; não se assume, antes dos testes, que uma técnica clássica será suficiente.

### Representação estruturada esperada

Cada bloco terá identificador, tipo, conteúdo ou arquivo, página, caixa delimitadora em um sistema de coordenadas documentado, ordem de leitura e vínculos. O resultado inclui a região da questão, associação com alternativas, confiança quando aplicável, estado de revisão e versões do esquema e do modelo.

#### Como medir a qualidade

Comparar a estrutura com anotações humanas: localização dos blocos, ordem de leitura, associação entre elementos, integridade da questão e tempo de correção. Uma categoria como “imagem à direita” ajuda na análise, mas não basta para reconstruir o item.

O original deve permanecer disponível para conferência lado a lado. A análise de layout pode melhorar a extração e a curadoria antes de o renderizador dinâmico entrar na plataforma.

## 08. Diagnóstico e modelo do aluno

A aprendizagem adaptativa usa o histórico e os rótulos revisados para orientar a prática.

Na etapa de integração, o aluno poderá escolher objetivo, área e tempo disponível, realizar um diagnóstico inicial e iniciar sessões personalizadas. O sistema mantém evidências por habilidade e informa quando ainda há poucas respostas para sustentar uma recomendação.

### Estado por habilidade

Registrar tentativas recentes, acertos sem ajuda, uso de pistas, itens vistos, última prática e quantidade de evidência. A confiança informada pelo aluno pode ser opcional. Tempo de resposta pode ser registrado, mas não será interpretado isoladamente como domínio.

### Primeiro estimador explicável

Começar com uma taxa de acerto suavizada por habilidade. Um modelo Beta-Binomial é uma referência possível, atualizado com respostas sem ajuda. Com prior Beta(1,1), a média posterior é **(1 + acertos) / (2 + tentativas)** . O prior é uma escolha inicial a avaliar.

| Evidência observada | Interpretação inicial |
| --- | --- |
| Erros recorrentes em porcentagem | Reforçar o conceito e verificar se a dificuldade aparece em outro contexto. |
| Poucas tentativas em geometria | Explorar o tema antes de concluir que há ou não domínio. |
| Acertos consistentes e revisão antiga | Programar uma retomada para observar retenção. |

#### Desempenho observado e proficiência

A estimativa resume respostas nos itens vistos. Não equivale à nota oficial do Enem nem separa automaticamente dificuldade do item e domínio do aluno. Apresentar número de tentativas e condições de ajuda junto dos indicadores.

- Distribuir o diagnóstico entre temas; não concluir a partir de uma única resposta. Erros em questões com várias habilidades geram hipóteses, sem identificar uma causa única comprovada.

- Em provas, a resposta definitiva passa a compor o resultado na finalização. Alterações antes de finalizar não viram várias tentativas independentes no modelo do aluno.

## 09. Seleção adaptativa e modelos avançados

Cada recomendação deve ter uma função pedagógica e um motivo que possa ser explicado.

Filtrar itens por área, habilidades aprovadas, integridade, exposição prévia e dificuldade provisória. A política inicial combina reforço de dificuldades, revisão de conteúdos e exploração de temas com pouca informação. Os pesos são parâmetros de experimento, sem combinação ótima presumida.

| Função | Critério | Exemplo de motivo |
| --- | --- | --- |
| Reforço | Erros repetidos com evidência suficiente; considerar pré-requisitos. | Praticar aumentos sucessivos em outro contexto. |
| Revisão | Tempo desde a última prática e histórico observado. | Retomar interpretação de gráficos. |
| Exploração | Pouca evidência ou cobertura insuficiente. | Verificar proporcionalidade antes de priorizar o tema. |

Registrar candidatos, componentes da prioridade, escolha, motivo e versão da política. Controlar repetição e exposição para evitar concentrar toda a prática em poucos itens. O painel explicará as recomendações e o volume de evidência usado.

### Evoluções preservadas no plano

- **Predição de acerto.** Modelos supervisionados com aluno, item e histórico, comparados com uma referência simples em interações futuras.

- **Knowledge tracing.** Acompanhar a evolução do conhecimento em sequências de interação; investigar uma abordagem bayesiana antes de métodos sequenciais mais complexos [4].

- **Dificuldade calibrada.** Estudar modelos de resposta ao item quando houver dados adequados e hipóteses documentadas.

- **Políticas avançadas.** Investigar ganho de informação ou bandits com recompensa, exploração e protocolo de avaliação explícitos.

#### Dados necessários

Provas históricas não fornecem, por si só, sequências de aprendizagem dentro da plataforma. Coletar interações reais com cuidado metodológico. Simulações verificam comportamento e hipóteses; não comprovam ganho educacional.

## 10. Tutor com LLM e ferramentas

O tutor permanece no escopo completo e pode ser integrado sem esperar a reconstrução de layouts.

| Modo | Comportamento esperado |
| --- | --- |
| Pista inicial | Destacar um conceito ou informação importante sem entregar a solução. |
| Pista intermediária | Sugerir uma etapa, representação ou pergunta útil para o raciocínio. |
| Explicação após tentativa | Relacionar a resposta à resolução de referência e ao gabarito. |
| Discussão do raciocínio | Analisar o que o aluno escreveu e pedir esclarecimento quando necessário. |
| Revisão direcionada | Recuperar um conceito aprovado e sugerir prática compatível. |

### Contexto revisado e ferramentas limitadas

O backend fornece a versão da questão, habilidade, etapa de ajuda e trechos relevantes de uma resolução aprovada. A recuperação de referências pode usar busca textual e, após comparação, busca semântica. O LLM poderá consultar conceitos, resoluções e uma ferramenta determinística de verificação de cálculos.

A resposta terá estrutura validável: tipo de ajuda, texto, referências, hipótese de erro e necessidade de esclarecimento. Correção das alternativas, seleção de itens, permissões e acesso ao gabarito permanecem controlados por serviços verificáveis.

### Prova e prática têm regras próprias

No modo prova do MVP, o resultado é apresentado após a finalização. No modo de prática com tutor, pistas e feedback seguem a configuração da sessão. Registrar ajuda utilizada e separar desempenho independente de desempenho assistido para não distorcer os indicadores.

#### Continuidade e validação

Se o provedor falhar ou a saída não for validada, preservar a tentativa e oferecer conteúdo previamente aprovado. Avaliar correção, nível de ajuda, referências e erros graves com casos revisados, incluindo dúvidas ambíguas e raciocínios incorretos.

Versionar modelo, prompt, material recuperado, validação, custo e tempo de execução. O tutor é uma integração planejada; não é uma dependência para liberar o MVP de provas.

## 11. Renderização dinâmica das questões

A plataforma usa a estrutura aprovada para reproduzir a organização visual com fidelidade.

A equipe de Dados identifica os elementos e sua disposição; a equipe de Plataforma implementa o mecanismo que transforma essa representação em uma questão navegável. Um classificador de layout não substitui o renderizador, e o renderizador depende de conteúdo e vínculos corretos.

| Camada | Responsabilidade |
| --- | --- |
| Estrutura de conteúdo | Textos, comando, fórmulas, tabelas, imagens, legendas e alternativas semanticamente associados. |
| Descrição do layout | Posições, agrupamentos, relações espaciais, ordem de leitura e referência à página original. |
| Renderizador | Componentes visuais, dimensionamento, responsividade, acessibilidade e seleção das alternativas. |
| Validação | Conferência com o original em telas de referência; detecção de cortes, inversões e relações perdidas. |

### Fidelidade visual e uso em diferentes telas

Em telas amplas, reconstruir posições próximas às originais, como texto à esquerda e imagem à direita. No celular, permitir reorganização responsiva que preserve significado, ordem de leitura e vínculos. Quando a posição for parte da interpretação, usar uma visualização apropriada e revisar o comportamento.

Coordenadas absolutas do PDF não devem ser copiadas diretamente como única estratégia para todas as telas. O contrato precisa permitir agrupamentos e regras de apresentação. Manter ordem semântica, textos alternativos quando cabíveis e interação por teclado.

### Critério de liberação

Cada questão mantém conteúdo completo, alternativas corretas e disposição aprovada para os tamanhos de tela testados. O conjunto de avaliação inclui layouts simples, mistos, imagens em alternativas e questões distribuídas por colunas ou páginas.

#### Entrada independente na plataforma

Liberar o renderizador conforme a maturidade dos layouts, mesmo que o módulo adaptativo ainda esteja em avaliação. Questões sem layout dinâmico aprovado continuam com a representação padronizada validada ou aguardam revisão.

## 12. Curadoria assistida e automatizada

A automação amplia um processo de qualidade que já existe desde a primeira entrega.

O módulo identifica problemas no banco, sugere correções e, em casos delimitados, poderá executá-las conforme regras e evidências de qualidade. Deve manter o original, a versão anterior, a alteração proposta e o responsável pela aprovação ou política aplicada.

| Problema | Ação prevista |
| --- | --- |
| Texto e enunciado | Detectar falhas de extração, caracteres, trechos ausentes e fórmulas corrompidas. |
| Imagens e tabelas | Identificar recursos faltantes, recortes incorretos e associação com a questão ou alternativa errada. |
| Classificação temática | Sinalizar rótulos incompatíveis, cobertura incompleta ou divergências entre métodos. |
| Reconstrução visual | Apontar blocos fora de ordem, elementos sobrepostos e relações espaciais perdidas. |
| Integridade do banco | Encontrar duplicatas, questões incompletas, inconsistências de origem e divergências com o gabarito vigente. |

### Níveis de automação

- **Detecção.** Sinalizar o problema e encaminhá-lo à fila de revisão, sem alterar a questão publicada.

- **Sugestão.** Preparar a correção com evidências e comparação lado a lado para aceite humano.

- **Correção controlada.** Aplicar regras de baixo risco com qualidade medida, validações e possibilidade de reversão; mudanças que afetam a resposta exigem revisão reforçada.

### Critério para antecipar esta frente

Se a revisão manual limitar a cobertura ou impedir a liberação de questões, priorizar automações que reduzam esse gargalo. A antecipação não elimina o conjunto de referência, a medição de falsos positivos nem o controle de versões.

#### Rastreabilidade e reavaliação

Publicar uma nova versão após aprovação. Preservar o conteúdo respondido anteriormente e, quando uma errata afetar resultados, aplicar um processo explícito de reavaliação com justificativa e registro.

## 13. Arquitetura e integração dos módulos

Um monólito modular oferece um ponto inicial simples para o trabalho paralelo.

Organizar os componentes por contratos e responsabilidades, sem exigir serviços separados desde o início. A aplicação atende provas, prática e painel; a administração cuida de importações, revisão, avaliações e publicação. Trabalhadores em segundo plano executam extração, classificação e análise visual.

| Camada | Escolha de referência | Função |
| --- | --- | --- |
| Interface | Next.js e TypeScript | Experiência do aluno, curadoria, celular e renderização das questões. |
| Backend | Python e FastAPI com validação de esquemas | Contas, provas, tentativas, perfil, recomendação, tutor e contratos de dados. |
| Persistência | PostgreSQL | Transações, histórico, versões, eventos e consultas analíticas. |
| Arquivos | Armazenamento de PDFs, imagens e artefatos | Preservação do original, recursos extraídos e evidências dos experimentos. |
| Recuperação | Busca textual; avaliar embeddings e pgvector | Consultar conceitos e resoluções aprovadas para o tutor. |
| Processamento | Comandos reproduzíveis e tarefas em segundo plano | Ingestão, OCR, classificação, layouts, indexação e benchmarks. |
| Execução | Contêineres, migrações e CI | Ambiente reproduzível, implantação e verificações automatizadas. |

### Limites internos

Separar banco e curadoria; provas e tentativas; perfil e adaptação; tutor e acesso ao LLM; renderizador; avaliação e operação. Modelos e provedores devem poder ser substituídos sem reescrever o fluxo de resolução.

#### Base preparada para crescer

Guardar conteúdo semântico e layout em representações distintas, ligadas à versão da questão. Começar com rótulos manuais, apresentação padronizada e serviços determinísticos; integrar os modelos por contratos compatíveis quando aprovados.

As tecnologias são escolhas de referência da proposta, sujeitas à validação. Fixar versões ao implementar e documentar decisões; a arquitetura não pressupõe contratação de provedor específico.

## 14. Modelo de dados e eventos

O histórico deve permitir reconstruir o que o aluno viu, respondeu e recebeu como ajuda.

| Grupo de entidades | Informação principal |
| --- | --- |
| users / profiles | Identificador, preferências, objetivo e configuração de acesso. |
| sources / assets | Origem, arquivos, páginas, hashes, imagens e demais recursos. |
| questions / question_versions | Item canônico, conteúdo, alternativas, gabarito, revisão e versões. |
| exams / exam_items | Ano, aplicação, caderno, sequência, numeração e versão de cada item. |
| skills / question_skills | Taxonomia, códigos oficiais, vínculos múltiplos, origem e aprovação dos rótulos. |
| layout_versions / layout_blocks | Esquema, página, coordenadas, tipos, ordem de leitura, relações e revisão. |
| reference_solutions | Resoluções e pistas aprovadas, autor ou revisor e versão. |
| sessions / draft_answers / attempts | Modo, estado, escolhas editáveis e respostas definitivas com condições de ajuda. |
| skill_states / recommendation_events | Estimativas, evidência, candidatos, escolha, justificativa e versões da política. |
| tutor_runs / feedback | Contexto, referências, versões, custo, tempo e avaliação do usuário. |
| imports / reviews / evaluation_runs | Processamentos, alterações, aprovações, conjuntos e métricas dos experimentos. |

### Invariantes do histórico

- Cada tentativa referencia exatamente a versão exibida. A correção de conteúdo não reescreve o passado.

- No modo prova, alterações de alternativas são rascunhos até a finalização. Registrar resultado e eventos de forma consistente e idempotente.

- Preservar eventos para recalcular perfis. Separar interações reais, simulações e testes em todas as análises.

#### Evento mínimo de aprendizagem

Identificador pseudônimo do aluno, sessão, questão e versão; ordem, instante, resposta, acerto, ajuda utilizada e versões do estimador e da política quando aplicáveis. Dados pessoais e texto livre não precisam acompanhar todo evento.

## 15. API e telas principais

Contratos distintos para provas editáveis e prática adaptativa evitam conflitos de comportamento.

| Operação proposta | Comportamento |
| --- | --- |
| POST /auth/register e /auth/login | Criação e autenticação de contas; definir também sessão, saída e recuperação de acesso. |
| GET /exams e /exams/{id} | Listar provas e consultar o conteúdo publicado, sem expor o gabarito antes da hora. |
| POST /exam-runs | Iniciar uma execução com ordem e versões dos itens fixadas. |
| PUT /exam-runs/{id}/answers/{item_id} | Salvar ou alterar uma escolha enquanto a prova está aberta. |
| POST /exam-runs/{id}/finish | Finalizar uma única vez, corrigir e registrar resultados de forma consistente. |
| GET /me/history e /me/progress | Retornar histórico e desempenho do aluno autenticado, com cobertura e evidência. |
| POST /sessions e GET /sessions/{id}/next | Criar diagnóstico ou prática e obter item elegível com motivo da escolha. |
| POST /attempts e POST /tutor/hints | Registrar tentativa definitiva da prática e solicitar ajuda conforme a etapa. |
| POST /admin/imports e /admin/reviews/{id} | Processar importações e registrar correções, justificativas e aprovações. |
| POST /admin/evaluations | Executar avaliações versionadas de classificadores, layouts, tutor e seletor. |

### Experiência do aluno

Acesso à conta, catálogo por ano, resolução com progresso e navegação, finalização, resultado, histórico e painel. Na evolução: objetivos, diagnóstico, recomendações, pistas, revisão, preferências e relato de problemas.

### Experiência de curadoria

Fila de importações; comparação entre original, extração e layout; edição de rótulos; revisão de soluções; aprovação e painel de regressões. Separar rascunho de conteúdo liberado.

Os caminhos são exemplos de contrato, não APIs já implementadas. Especificar entradas, saídas, erros, autorização e idempotência. O backend controla acesso ao histórico, gabaritos, limites e estados da prova.

## 16. Avaliação técnica reproduzível

Medir os componentes individualmente e comparar cada alternativa com uma referência simples.

| Componente | Referência | Medidas principais |
| --- | --- | --- |
| Extração e integridade | Questões e provas conferidas com o original. | Completude, erros de texto, associação de imagens e tempo de revisão. |
| Classificação temática | Conjunto anotado e revisado por pessoas. | Precisão, revocação e F1 por tema e habilidade; custo e consistência. |
| Layout e renderização | Blocos e relações anotados; telas aprovadas. | Localização, ordem de leitura, vínculos, perdas de conteúdo e erros visuais. |
| Curadoria automática | Problemas e correções com decisão humana. | Erros detectados, falsos positivos, correções aceitas e regressões. |
| Predição de acerto | Taxa por tema e estimador simples. | Log loss, Brier score, calibração e AUC quando adequada. |
| Recuperação e tutor | Trechos relevantes e soluções revisadas. | Recall@k, correção, nível de ajuda, referências e erros graves. |
| Seletor adaptativo | Seleção aleatória e política de reforço simples. | Cobertura, exposição, coerência e robustez em cenários. |
| Sistema | Contratos e carga de referência. | Correção de resultados, latência, falhas, custo e recuperação. |

### Separação dos dados

- Deduplicar antes da divisão e manter variantes do mesmo item no mesmo conjunto. Para layouts, avaliar também anos, cadernos ou padrões reservados.

- Separar desenvolvimento e teste. Reservar estudantes para estudar generalização a novos usuários; respeitar a ordem temporal para previsão futura.

- Usar apenas o histórico anterior em cada previsão. Se avaliar questões novas, reservar também seus itens e soluções.

#### Limite das métricas

Melhor predição de acerto não prova melhor aprendizagem. Logs de uma política não mostram diretamente o resultado de outra. Relatar amostra, distribuição, dispersão quando possível, configuração e casos de erro, sem ganhos presumidos.

## 17. Piloto e aprendizagem real

Validar primeiro a experiência de uso e depois investigar o efeito educacional.

### Piloto do MVP

Convidar inicialmente, por exemplo, 5 a 10 estudantes adultos para entrar na conta, resolver uma prova, voltar a uma questão, alterar uma escolha, finalizar e consultar o painel. Observar dificuldades, falhas, abandono, clareza do resultado e intenção de voltar. O número é uma meta exploratória de recrutamento.

| Momento | Pergunta | Evidência |
| --- | --- | --- |
| Plataforma base | O fluxo de prova funciona? | Conclusão das tarefas, respostas preservadas, correção conferida e histórico individual. |
| Tutor integrado | A ajuda é correta e útil? | Avaliação do estudante e revisão por alguém com conhecimento da matéria. |
| Adaptação integrada | O motivo da escolha é compreensível? | Compreensão do aluno e análise de recomendações inadequadas. |
| Layouts dinâmicos | A apresentação preserva a interpretação? | Comparação com o original, leitura no celular e verificação das relações. |
| Investigação educacional | Há sinal de aprendizagem? | Pré e pós-teste com itens novos, comparáveis e reservados. |

### Estudo posterior de eficácia

Comparar prática adaptativa com uma condição de referência sob duração e cobertura controladas. Definir hipótese, grupos, teste comum e análise antes dos resultados. Usar alocação aleatória quando viável e acompanhamento posterior de retenção; distinguir efeitos da tutoria e da política de seleção.

- Usar avaliações equivalentes para reduzir o efeito de memorizar o próprio teste. Medir desempenho em avaliação comum, além do acerto nas questões selecionadas pelo sistema.

- Registrar conclusão, desistências, uso de pistas e diferenças iniciais entre os grupos. Tratar sinais do piloto como exploratórios.

#### Relato por estágio

Documentar o que foi testado em cada versão. Um piloto do MVP sustenta conclusões sobre usabilidade e funcionamento; alegações de ganho educacional dependem de método e dados apropriados.

## 18. Operação custos e continuidade

A plataforma precisa permanecer utilizável quando arquivos, modelos ou serviços externos falham.

| Área | Implementação prevista |
| --- | --- |
| Implantação | Ambiente local reproduzível, CI, migrações e aplicação publicada com dados persistentes. |
| Observabilidade | Correlacionar prova, sessão, tentativa, processamento e tutor; medir latência p50/p95, falhas, tokens e custo. |
| Orçamento | Definir limites por sessão e processo, teto de gasto e registro por modelo; consultar preços antes de contratar ou implantar. |
| Continuidade | Timeout, tentativas limitadas, cache compatível e conteúdo aprovado como alternativa ao LLM. |
| Acesso e dados | Verificar autorização por usuário, separar administração e minimizar dados enviados a provedores. |
| Rastreabilidade | Fixar versões de conteúdo, esquema, modelo, prompt, política e avaliação nas execuções relevantes. |
| Recuperação | Backup, teste de restauração, migrações verificadas e retorno à versão anterior. |

### Conta de custo proposta

Separar o custo de preparação do banco, como OCR, classificação e análise de layout, do custo de uso por aluno. Por sessão, considerar chamadas ao LLM, recuperação, processamento e infraestrutura. Medir valores reais no piloto antes de projetar volume.

O cache de uma pista pronta depende da questão, versão e nível de ajuda. Respostas personalizadas exigem chaves compatíveis com o contexto. Uma falha na preparação de novos itens não deve afetar questões já publicadas.

### Qualidade ligada ao produto

- Proteger gabaritos e soluções finais conforme o modo de estudo. Conteúdo recuperado serve de referência; permissões e ferramentas ficam sob controle do backend.

- Oferecer exclusão do histórico e usar identificadores pseudônimos em relatórios. A expansão para turmas e menores exige desenho próprio de acesso e tratamento de dados.

Este plano propõe requisitos de engenharia. Não estabelece orçamento, provedor ou modelo comercial já contratado.

## 19. Desenvolvimento com IA e portfólio

Apoio intensivo de IA continua previsto, acompanhado de verificação independente e domínio técnico.

| Atividade | Uso de IA | Evidência para aceitar |
| --- | --- | --- |
| Dados | Extrair, normalizar e propor rótulos, layouts e resoluções. | Conferência com o original e conjunto revisado. |
| Implementação | Construir módulos a partir de contratos e exemplos. | Fluxo executável e testes das regras críticas. |
| Avaliação | Propor cenários e casos difíceis. | Separação entre desenvolvimento e teste; referência humana. |
| Interface | Criar telas, estados vazios, erros e responsividade. | Uso no celular, teclado e feedback do piloto. |
| Documentação | Preparar contratos, diagramas e relatos de experimento. | Coerência com código, dados e resultados reproduzíveis. |

Construir primeiro um ciclo completo do MVP: importar, revisar, publicar, responder, finalizar e consultar o resultado. Depois ampliar o ciclo com diagnóstico, recomendação e pistas. Incrementos pequenos facilitam revisão e regressão. A equipe deve conseguir explicar, testar e alterar os pontos centrais do sistema.

### Extensões que permanecem planejadas

Cobrir as quatro áreas do Enem; criar turmas, atividades e visão agregada para docentes; investigar modelos avançados; incorporar multimodalidade, análise do raciocínio escrito pelo aluno e geração de exercícios submetidos a revisão. Investigar ajuste de modelo aberto com PEFT/LoRA quando houver dados, avaliação e recursos [7].

### Evidências do projeto

- **GitHub e aplicação.** Código, decisões, contratos, testes, instruções, demonstração publicada e vídeo de uma jornada completa.

- **Relatório.** Métricas reais, referências de comparação, erros, custos e resultados do piloto por versão.

- **Hugging Face.** Publicar um modelo realmente treinado ou ajustado, com artefato, dados, métricas, uso e limitações [5, 6]. Classificadores temáticos ou de layout são candidatos.

O TCC pode fornecer um artefato separado, enquanto o Enem demonstra integração de IA em produto. Mantém-se a referência de portfólio da Trilha AI Engineer citada no plano original [8], sem vínculo ou endosso institucional.

## 20. Roadmap e critérios de conclusão

Proposta de replanejamento com o marco de demonstração de 15 de novembro de 2026 como referência.

O plano original concentrava adaptação e tutor na primeira entrega. Com o novo modelo incremental, propõe-se priorizar o MVP no marco inicial e apresentar os experimentos de Dados e IA em paralelo. O restante do escopo segue planejado e recebe marcos próprios conforme os critérios de maturidade.

| Janela de 2026 | Equipe de Plataforma | Equipe de Dados e IA |
| --- | --- | --- |
| 29/10 a 01/11 | Contratos, esquema, autenticação e primeiro fluxo de prova. | Taxonomia, fontes, amostra anotada e contrato de layout. |
| 02 a 04/11 | Navegação, respostas editáveis, finalização e histórico. | Extração, revisão inicial e referências de classificação e layout. |
| 05 a 07/11 | Painel por rótulos disponíveis, catálogo e administração. | Experimentos temáticos e visuais; medição dos primeiros erros. |
| 08 a 10/11 | Validação integrada, celular, teclado e consistência. | Ampliação do banco e comparação de abordagens. |
| 11 a 13/11 | Piloto do MVP, correções e teste de recuperação. | Revisão dos casos difíceis e relatório experimental. |
| 14 e 15/11 | Demonstração, vídeo e documentação da versão disponível. | Artefatos, métricas e próximos critérios de integração. |

As janelas são uma referência ajustável, sem compromisso de concluir todos os modelos até 15/11. Recursos adicionais prontos podem ser demonstrados separadamente, com seu estado de validação explícito.

### Integrações após o MVP

Diagnóstico e adaptação exigem histórico consistente, cobertura temática e comparação da política com uma referência. O tutor exige conteúdo revisado, avaliação e continuidade em falhas. Os layouts dinâmicos exigem estrutura e renderização aprovadas. Cada integração segue os critérios detalhados nas respectivas seções.

Curadoria automatizada pode ser antecipada quando reduzir um gargalo de qualidade. Cobertura das quatro áreas, recursos docentes e modelos avançados continuam como marcos de expansão. Definir suas datas a partir da capacidade real das equipes e dos resultados de cada entrega.

#### Definição de entrega pronta

O comportamento prometido está executável, o conteúdo foi revisado, as decisões são rastreáveis, as avaliações são reproduzíveis e os resultados relatados correspondem às medições. A ordem das integrações pode mudar sem reduzir o escopo.

## 21. Referências e termos do plano

Referências do documento original preservadas e termos usados nesta revisão.

### [1] Inep Provas e gabaritos do Enem

Fonte das provas e respostas de edições anteriores.

### [2] Inep Matrizes de Referência do Enem

Competências, habilidades e objetos de conhecimento.

### [3] Inep Microdados do Enem

Conferir os dicionários e campos de cada edição antes do uso.

### [4] Corbett e Anderson 1992 Knowledge Tracing in the ACT Programming Tutor

Referência de pesquisa mantida do plano original sobre acompanhamento do conhecimento.

### [5] Hugging Face Model Cards

Documentação do modelo, treinamento, uso, avaliação e limitações.

### [6] Hugging Face Uploading models

Publicação e versionamento de artefatos de modelos.

### [7] Hugging Face PEFT

Técnicas de adaptação de modelos com ajuste de parte dos parâmetros.


### Glossário

| Termo | Significado no projeto |
| --- | --- |
| LLM e RAG | Modelo de linguagem; recuperação de material de referência para apoiar a geração da resposta. |
| OCR e layout | Reconhecimento de texto em imagens; organização espacial e relações entre os elementos. |
| Knowledge tracing | Estimativa da evolução do conhecimento a partir de sequências de interação. |
| Baseline e calibração | Abordagem de comparação; avaliação da correspondência entre probabilidades previstas e frequências observadas. |
| Model card | Documento que descreve uso, dados, treinamento, avaliação e limitações de um modelo. |
