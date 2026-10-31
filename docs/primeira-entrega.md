# Primeira entrega — MVP executável

Implementação dos itens de Plataforma base e Qualidade inicial do [plano do projeto](plano-implementacao/enem_adaptativo_plano_do_projeto.md), principalmente seções 3–5, 13–15 e 18–20. O [status da implementação](plano-implementacao/status-implementacao.md) e as [próximas etapas](plano-implementacao/proximas-etapas.md) ficam reunidos com o plano em `docs/plano-implementacao/`. A frente experimental de Dados e IA fica preparada pelos contratos e pelo conteúdo versionado; não se apresenta nenhum modelo como treinado ou avaliado.

## Aceite

| Critério do plano | Implementação e evidência |
| --- | --- |
| Entrar em conta individual | Cadastro, login, sessão e teste de isolamento entre dois usuários |
| Abrir prova completa validada | ENEM 2024, segundo dia, 90 itens; originais, hashes e conferência documentados em `data/README.md` |
| Avançar, voltar e alterar | Execução com ordem fixa, mapa de questões, alternativas editáveis e limpeza |
| Retomar após fechar | Escolhas no banco; teste de recarga do navegador preserva a alternativa |
| Finalizar sem duplicação | Testes sequenciais e concorrentes conferem o mesmo resultado e uma única série de eventos |
| Correção explícita | Gabarito oficial, brancos e anulação tratados separadamente, sem nota TRI |
| Histórico e painel próprios | Resultado persistido e agregações autorizadas pelo usuário autenticado |
| Matéria, área e habilidade | Agregações por rótulos disponíveis, denominadores e cobertura; ausência fica visível |
| Curadoria mínima | Importar, editar, versionar, aprovar e publicar, com decisões rastreáveis |
| Histórico imutável | Teste altera conteúdo e gabarito da versão atual e confere que uma execução anterior mantém o original |
| Celular e teclado | Mesma jornada testada em Chrome desktop e viewport de iPhone; rádio alterado por tecla de seta, diálogo nativo e foco visível |
| Ambiente reproduzível | Migração Alembic, manifests fixados, npm lockfile, Makefile, Docker Compose e CI |

## Consolidação técnica de 31/10/2026

| Verificação | Resultado e escopo |
| --- | --- |
| API e migrações | 57 testes em SQLite e 57 em PostgreSQL 17.7; `alembic check` sem divergências. |
| Conteúdo publicado | 90 itens e gabarito oficial conferidos por script, 89 válidos e questão 129 anulada; hashes das duas fontes e recursos verificados. 45 figuras, 10 tabelas e 3 blocos de equação; 150 expressões LaTeX compiladas. |
| Navegador | 18 testes Playwright em Chrome desktop e viewport móvel: jornada, temas, falha de salvamento, preparação, encaixes, figuras, teclado, reflow e passagem pelos 90 itens. |
| Acessibilidade automática | Auditorias axe nas telas de conta, início, catálogo, histórico, desempenho, configurações, questão respondida, figura ampliada, confirmação e resultado. Contraste, nome acessível da marca, hierarquia de títulos, identificação e retenção de foco dos diálogos corrigidos. Relatórios JSON registram também verificações inconclusivas para revisão humana. |
| Instalação limpa | Imagens Python 3.13/Node 22 construídas com dependências instaladas do zero a partir de snapshot isolado. Compose 5.6.1 com Podman 5.8.9 rootless; PostgreSQL/API/interface saudáveis. |
| Persistência | Contêineres substituídos sem remover volumes; login, resposta B, resultado 1/89, histórico, 90 snapshots, figura e recurso próprio preservados. Repetir finalização devolve o mesmo resultado. |
| Recuperação | Backup/restauração SQLite íntegro e migrações alinhadas. `pg_dump`/`pg_restore` em banco separado preservam conteúdo completo de questões, provas, tentativas, eventos e revisões. |
| Git e CI | Commits por responsabilidade e workflow ampliado com auditoria do conteúdo, relatórios de acessibilidade e ensaio de recriação de contêineres. [Execuções da branch de consolidação](https://github.com/LemonCandles/enem-flow/actions?query=branch%3Acodex%2Fconsolidacao-primeira-entrega). |

`python scripts/audit_content.py` faz a conferência técnica do caderno. `scripts/verify_deployment.py` permite repetir o ensaio de persistência descrito em [operação](operations.md). O CI também executa o Compose com Docker Engine no runner, complementando o ensaio local com Podman.

Os ensaios de navegador/contêineres usam usuários e bancos descartáveis, separados do banco de uso da aplicação. A cópia SQLite do banco local foi restaurada em outro caminho, sem alterar a origem. A correção de volume acrescenta recursos novos e recusa sobrescrever um arquivo diferente com o mesmo nome, preservando os recursos de versões antigas.

A [revisão de apresentação](../data/README.md#revisão-de-apresentação) documenta as 15 questões alteradas. A preparação automática de outros PDFs continua sujeita a seus relatórios; os cinco bloqueios do ensaio de reextração não pertencem ao caderno revisado publicado.

As capturas e os vídeos são evidências técnicas de teste, sem dados de estudantes reais. O [vídeo da jornada](demo.webm) e o [vídeo de figuras/LaTeX](demo-figuras.webm) acompanham a apresentação nativa e o design implementado.

## Roteiro de demonstração

1. Inicie os dois processos ou o Compose e crie uma conta.
2. Abra Banco de provas, filtre por 2024 e inicie o caderno azul.
3. Marque uma opção na questão 91, avance, volte e altere. Recarregue para comprovar a persistência.
4. Use Tab e as setas no grupo de alternativas; no celular, abra o mapa de questões.
5. Finalize confirmando os itens em branco. Confira a exclusão da anulada: 89 questões válidas.
6. Abra histórico e desempenho; observe a cobertura zero de habilidades, explicitamente indicada.
7. Com uma conta de curadoria, abra o original, registre uma justificativa, crie uma nova versão e aprove antes de republicar. Confira a tentativa anterior inalterada.

## Limites e atividades externas

A consolidação técnica está concluída com instalação isolada em contêineres, regressão integrada e ensaios de persistência/recuperação. A execução local usa o Compose oficial sobre Podman; a execução do workflow verifica Docker Engine no GitHub Actions. Implantação em uma conta de hospedagem, piloto com 5–10 estudantes adultos e resultados reais de uso dependem dos respectivos ambientes e participantes; não foram simulados. A revisão realizada foi de integridade e fidelidade ao original, sem revisão pedagógica independente ou comprovação de eficácia.

O catálogo inicial é um caderno completo de um dia; Linguagens, Humanas, redação, outras cores/anos/aplicações não estão disponíveis ainda. O processo de novos cadernos é manual e versionado. Enunciados, alternativas, tabelas e fórmulas são conteúdo nativo do site a partir do JSON. Figuras e diagramas mantêm descrições textuais; a acessibilidade integral de gráficos complexos exige revisão especializada dessas descrições.

Não integram esta entrega: diagnóstico, seleção adaptativa, tutor, classificação automática, reconstrução dinâmica de layout, turmas, modelos treinados, métricas de aprendizagem ou custos de LLM. O contrato de rótulos e layout mantém os pontos de integração para essas etapas.

## Aceites manuais ainda necessários

As pendências externas estão no [final das próximas etapas](plano-implementacao/proximas-etapas.md#pendências-externas-da-primeira-entrega) e continuam necessárias antes da publicação/piloto:

1. Um revisor independente compara os 90 itens com o caderno/gabarito, incluindo símbolos, coeficientes, legendas, estruturas moleculares e diagramas das alternativas; cada correção deve ter evidência, nova versão e aprovação.
2. Uma pessoa usuária de leitor de tela executa cadastro, navegação, marcação/alteração, retomada, leitura de tabelas e matemática/química, ampliação e resultado. Registrar leitor, sistema, navegador e como os conteúdos são anunciados.
3. Executar a mesma jornada em Android e iPhone físicos, com rotação, teclado/touch e retorno após fechar; conferir zoom real do navegador e ampliação do sistema no desktop. Registrar aparelhos, versões, tarefas e falhas.

A inspeção automática da árvore acessível e o reflow em 320/640 pixels ajudam a encontrar problemas, mas não certificam acessibilidade integral nem substituem experiência manual com tecnologia assistiva. Revisão pedagógica independente e participação de estudantes não foram simuladas.
