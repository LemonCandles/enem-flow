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

## Validação executada

- A atualização de apresentação passou com 21 testes da API em SQLite e 21 em PostgreSQL, incluindo JSON nativo, tabelas, recursos e preservação das versões.
- Oito testes Playwright aprovados no build de produção cobrem jornada completa, falha de salvamento, apresentação nativa do JSON e persistência dos temas, em desktop e celular. O fluxo cobre cadastro → início → marcar → avançar → voltar → alterar pelo teclado → recarregar → finalizar → reenviar finalização → histórico → painel por habilidade. A validação de design também cobre troca de tema durante uma prova, retomada e foco no menu móvel.
- TypeScript e build de produção verificados.
- Conferência visual das telas de início e resolução, figuras isoladas, tabelas e fórmulas nos temas claro e escuro. O design [Conhecimento em construção](propostas-design/README.md) foi implementado com encaixes em SVG/CSS e navegação lateral.
- Migrações e ensaios de backup/restauração conferidos; resultados em `docs/operations.md`.

As capturas em `docs/screenshots/` mostram uma conta de teste com indicadores zerados. Não são dados de um piloto educacional.

O vídeo `docs/demo.webm` foi atualizado com o design implementado e registra a jornada automatizada em desktop, sem narração. Os dados e a conta são de teste; o histórico é excluído ao final. A validação do design usou um banco temporário separado do banco da aplicação.

## Roteiro de demonstração

1. Inicie os dois processos ou o Compose e crie uma conta.
2. Abra Banco de provas, filtre por 2024 e inicie o caderno azul.
3. Marque uma opção na questão 91, avance, volte e altere. Recarregue para comprovar a persistência.
4. Use Tab e as setas no grupo de alternativas; no celular, abra o mapa de questões.
5. Finalize confirmando os itens em branco. Confira a exclusão da anulada: 89 questões válidas.
6. Abra histórico e desempenho; observe a cobertura zero de habilidades, explicitamente indicada.
7. Com uma conta de curadoria, abra o original, registre uma justificativa, crie uma nova versão e aprove antes de republicar. Confira a tentativa anterior inalterada.

## Limites e atividades externas

O MVP está executável localmente. O Compose e os Dockerfiles estão incluídos, mas a execução em contêineres não foi testada neste ambiente, que não dispõe do Docker. PostgreSQL foi testado diretamente em uma instância temporária. Implantação em uma conta de hospedagem, piloto com 5–10 estudantes adultos e resultados reais de uso dependem dos respectivos ambientes e participantes; não foram simulados. A revisão realizada foi de integridade e fidelidade ao original, sem revisão pedagógica independente ou comprovação de eficácia.

O catálogo inicial é um caderno completo de um dia; Linguagens, Humanas, redação, outras cores/anos/aplicações não estão disponíveis ainda. O processo de novos cadernos é manual e versionado. Enunciados, alternativas, tabelas e fórmulas são conteúdo nativo do site a partir do JSON. Figuras e diagramas mantêm descrições textuais; a acessibilidade integral de gráficos complexos exige revisão especializada dessas descrições.

Não integram esta entrega: diagnóstico, seleção adaptativa, tutor, classificação automática, reconstrução dinâmica de layout, turmas, modelos treinados, métricas de aprendizagem ou custos de LLM. O contrato de rótulos e layout mantém os pontos de integração para essas etapas.
