# Status da implementação

Atualizado em **30/10/2026**. Referência: [plano do projeto](enem_adaptativo_plano_do_projeto.md), versão 2.0, de 29/10/2026.

O projeto possui um MVP executável localmente para realizar provas e consultar resultados. O fluxo principal da primeira entrega está implementado e testado. A publicação, o piloto com estudantes e as frentes experimentais de Dados e IA permanecem pendentes.

Este documento registra o estado atual. A ordem proposta para continuar o trabalho está em [próximas etapas](proximas-etapas.md).

## O que foi feito

| Frente | Implementação disponível | Evidência no projeto |
| --- | --- | --- |
| Base técnica | Next.js, React e TypeScript na interface; FastAPI e SQLAlchemy no backend; SQLite local e suporte a PostgreSQL. | [Arquitetura](../architecture.md), `frontend/` e `backend/`. |
| Design da interface | Direção Conhecimento em construção aplicada: encaixes em SVG/CSS, Manrope, barra lateral, temas claro/escuro com preferência persistida e menu móvel com controle de foco. | [Design e paleta](../propostas-design/README.md), `frontend/src/components/design.tsx` e `globals.css`. |
| Contas | Cadastro, login, sessão por cookie HttpOnly, saída e isolamento dos dados entre usuários. | `backend/app/security.py`, rotas de autenticação e testes da API. |
| Preferências e dados pessoais | Nome, objetivo de estudo, meta pessoal de questões, exportação dos resultados e exclusão do próprio histórico. | Tela de configurações e rotas `/me`. |
| Recuperação de acesso | Link assistido, de uso único e com validade de 30 minutos; alteração de senha revoga as sessões anteriores. | CLI administrativa e [operação](../operations.md). |
| Catálogo | Busca e filtros por ano, área, aplicação e caderno; identificação de caderno completo, seção e coleção. | Tela Banco de provas e rotas `/exams`. |
| Conteúdo inicial | Caderno completo do segundo dia do ENEM 2024, aplicação regular, azul: 90 questões, sendo 45 de Natureza e 45 de Matemática. | [Origem e conferência do conteúdo](../../data/README.md). |
| Apresentação das questões | Enunciados e alternativas em texto selecionável a partir do JSON; tabelas em HTML; fórmulas com KaTeX e MathML. Imagens ficam vinculadas às figuras e aos diagramas. | JSON estruturado, `scripts/structure_questions.py` e componente `question-content.tsx`. |
| Resolução | Navegação livre, mapa de questões, alteração e limpeza de alternativas, salvamento no servidor e retomada após recarregar ou sair. | Tela de execução e testes de navegador. |
| Finalização e correção | Confirmação de conclusão, correção pelo gabarito, brancos e anuladas tratados explicitamente e finalização transacional e idempotente. | `backend/app/scoring.py` e testes sequenciais e concorrentes. |
| Histórico e desempenho | Resultados próprios, revisão por questão, evolução e agregações por área, matéria, tema e habilidade, conforme os rótulos disponíveis. | Telas Histórico e Meu desempenho. |
| Cobertura dos rótulos | Exibição da quantidade de tentativas e da cobertura de classificação; ausência de rótulo aparece como não classificado. | Painel e agregações da API. |
| Curadoria mínima | Importação de JSON como rascunho, consulta ao original, edição com nova versão, aprovação, publicação, retirada e registro das decisões. | Tela Curadoria, contratos e rotas administrativas. |
| Preservação do histórico | Execuções fixam conteúdo, ordem e versões; novas revisões preservam respostas e resultados anteriores. A apresentação de transcrições antigas compatíveis pode ser adaptada para texto nativo sem gravar alterações no histórico. | `exam_runs`, `bundled_content.py`, `presentation.py` e testes. |
| Rastreabilidade | PDFs de origem, URLs, hashes SHA-256, páginas, regiões de extração e decisões de revisão preservados. | `data/sources/`, JSON e registros de revisão. |
| Ambiente e operação | Migração Alembic, dependências fixadas, lockfiles, Makefile, Dockerfiles, Compose, endpoint de saúde e logs com identificador e duração da requisição. | [Instruções de execução](../../README.md) e [operação](../operations.md). |
| Recuperação de dados | Backup consistente do SQLite e ensaio de backup/restauração no PostgreSQL. | `scripts/backup_sqlite.py` e evidências operacionais. |
| Evidências da entrega | Documentação, capturas e vídeo da jornada atualizado para a apresentação nativa do JSON. | [Primeira entrega](../primeira-entrega.md), [capturas](../screenshots/) e [vídeo](../demo.webm). |

## Validações já executadas

- **21 testes da API aprovados com SQLite e 21 com PostgreSQL.** Incluem autenticação, autorização, publicação, persistência, idempotência, concorrência, anulações, versões e conteúdo nativo.
- **8 testes Playwright aprovados no build de produção.** Cobrem a jornada completa, a falha de salvamento, a apresentação do JSON, a persistência dos temas e o menu móvel acessível em desktop e celular. A validação do design usou um banco temporário separado.
- Verificação TypeScript e build de produção aprovados.
- Migração e alinhamento entre esquema e modelos verificados com `alembic check`.
- Conferência visual de texto, figuras, tabelas e fórmulas; validação da sintaxe das expressões matemáticas normalizadas.
- Restauração PostgreSQL conferida com questões, versões, resposta, resultado e eventos de uma tentativa. Backup SQLite verificado com `PRAGMA integrity_check`.

São resultados das execuções locais registradas nesta sessão de desenvolvimento. O workflow de CI está configurado no repositório; sua execução no serviço remoto ainda precisa ser confirmada.

## O que está parcial

| Frente | Estado atual | O que falta |
| --- | --- | --- |
| Cobertura do banco | Um caderno completo de um dia de aplicação. | Outros anos, aplicações, cores e o primeiro dia, incluindo suas escolhas de língua; ampliar a cobertura das quatro áreas. |
| Classificação | Área identificada pelo caderno e disciplina Matemática nas questões 136–180. | Revisar disciplinas de Natureza, estabelecer a taxonomia de temas e anotar competências e habilidades com evidência. |
| Painel detalhado | A infraestrutura agrega os rótulos disponíveis. | Ampliar a cobertura dos rótulos para que os recortes por tema e habilidade tenham evidências úteis. |
| Importação | Contrato JSON validado, scripts específicos do caderno inicial e revisão manual. | Processo generalizável a outros layouts, aquisição de recursos, OCR quando necessário e deduplicação entre cadernos. Novas imagens ainda precisam ser disponibilizadas em `data/assets/`. |
| Layout | Blocos semânticos nativos e referências à origem; figuras e alternativas associadas. | Identificação automática de componentes e reconstrução responsiva de agrupamentos e relações espaciais aprovadas. |
| Acessibilidade | Texto selecionável, tabelas HTML, MathML, descrições de imagens e fluxo testado por teclado e em viewport móvel. | Revisão especializada de gráficos complexos, leitores de tela e uso em aparelhos reais. |
| Conteúdo revisado | Conferência técnica de integridade, gabarito e fidelidade ao original. | Revisão pedagógica independente e validação das descrições e normalizações matemáticas. |
| Implantação | Configuração Docker e PostgreSQL pronta para ensaio. | Executar os contêineres em ambiente limpo e implantar a aplicação com persistência e configuração de produção. |
| Recuperação de acesso | Procedimento assistido pelo operador. | Envio de e-mail e fluxo autônomo, caso sejam priorizados para a operação. |

## O que falta para concluir a demonstração e o piloto do MVP

- [ ] Revisar pedagogicamente o caderno inicial e registrar eventuais correções como novas versões.
- [ ] Validar o Docker Compose em uma máquina com Docker disponível.
- [x] Revisar os arquivos novos e registrar a entrega em commits separados por responsabilidade, seguindo Conventional Commits.
- [ ] Confirmar os checks de CI no repositório remoto.
- [ ] Publicar a aplicação em um ambiente definido, com HTTPS, banco e recursos persistentes, origens autorizadas e cookies adequados ao domínio.
- [ ] Ensaiar backup e restauração no ambiente escolhido para a implantação.
- [ ] Testar o fluxo em aparelhos reais e com leitor de tela.
- [ ] Realizar o piloto exploratório previsto no plano, com aproximadamente 5–10 estudantes adultos.
- [ ] Registrar dificuldades, abandono, falhas, conclusão das tarefas e sugestões; corrigir os problemas identificados.
- [ ] Produzir o relato do piloto e atualizar as evidências da versão publicada.

O Docker não estava disponível no ambiente usado para esta implementação. PostgreSQL foi validado diretamente em uma instância temporária. O piloto e a hospedagem externa ainda não foram realizados.

## Funcionalidades e pesquisas ainda previstas no plano completo

| Frente pendente | Trabalho necessário |
| --- | --- |
| Classificação temática | Taxonomia, conjunto anotado, comparação entre regras, classificadores e LLMs, métricas por classe e revisão das propostas. |
| Análise de layout | Anotações de blocos, posições, ordem de leitura e vínculos; avaliação de extração, OCR e métodos visuais. |
| Diagnóstico e modelo do aluno | Sessões de diagnóstico, estado por habilidade, evidência disponível, prática recente e estimador inicial explicável. |
| Seleção adaptativa | Política de reforço, revisão e exploração; controle de repetição e exposição; registro dos candidatos, motivo e versão da política. |
| Tutor com LLM | Resoluções e pistas aprovadas, recuperação de referências, ajuda por etapas, validação da saída e continuidade quando o provedor falhar. |
| Layouts dinâmicos | Renderizador que utilize agrupamentos e relações espaciais aprovadas, preservando o significado em diferentes telas. |
| Curadoria assistida | Detecção de falhas, propostas de correção e automações delimitadas com evidência, revisão e rastreabilidade. |
| Avaliação dos componentes de IA | Conjuntos de desenvolvimento e teste, referências simples, métricas, casos de erro, custo e latência. |
| Avaliação educacional | Protocolo com avaliações comparáveis e itens novos, desenho de comparação e acompanhamento de retenção. |
| Expansão para docentes | Turmas, atividades e acompanhamento agregado, com regras próprias de acesso. |
| Modelos avançados | Predição de acerto, knowledge tracing, calibração de dificuldade e políticas como ganho de informação ou bandits. |
| Multimodalidade e geração | Análise do raciocínio escrito, processamento multimodal e geração de exercícios com revisão. |
| Artefatos de pesquisa e portfólio | Treinar ou ajustar um modelo quando houver dados e avaliação adequados; publicar artefato e documentação, incluindo Hugging Face quando aplicável. |

O estado atual comprova o funcionamento técnico da jornada implementada. Resultados de aprendizagem, modelos treinados e métricas experimentais dependem das etapas correspondentes.

## Documentos relacionados

- [Plano original](enem_adaptativo_plano_do_projeto.md)
- [Próximas etapas](proximas-etapas.md)
- [Critérios de aceite e demonstração](../primeira-entrega.md)
- [Arquitetura e contratos](../architecture.md)
- [Operação e recuperação](../operations.md)
- [Origem e preparação do conteúdo](../../data/README.md)
