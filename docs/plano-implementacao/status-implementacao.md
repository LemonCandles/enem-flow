# Status da implementação

Atualizado em **31/10/2026**. Visão geral do andamento do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

## Situação atual

**A consolidação técnica da primeira entrega foi concluída.** Já é possível entrar em uma conta, realizar uma prova, retomar respostas, finalizar e consultar o histórico e o desempenho.

O catálogo disponível contém o segundo dia do ENEM 2024, caderno azul, com 90 questões de Natureza e Matemática. Revisão pedagógica independente, leitores de tela e aparelhos reais continuam como critérios externos antes da publicação e do piloto, reunidos no final das próximas etapas.

## O que já está disponível

- **Jornada do estudante:** conta individual, preferências, catálogo, resolução de provas, respostas salvas, retomada, correção e histórico.
- **Experiência de resolução:** texto selecionável, fórmulas matemáticas e químicas em LaTeX, figuras com legendas e ampliação dentro do site, navegação por botões, mapa e teclado, com retorno ao topo ao trocar de questão.
- **Acompanhamento:** resultados e evolução pessoal, com recortes conforme a classificação disponível no banco.
- **Gestão do conteúdo:** preparação de novas provas, sinalização de ambiguidades, revisão, aprovação, publicação e controle de versões, preservando tentativas anteriores.
- **Interface e operação local:** temas claro e escuro, navegação adaptada a telas menores e recursos de backup e recuperação.

## O que está parcial

| Frente | Estado atual | O que falta |
| --- | --- | --- |
| Conteúdo | Um caderno disponível e melhorias de fidelidade na apresentação. | Revisão pedagógica independente e ampliação para outros anos, aplicações e áreas. |
| Preparação de provas | Processo reutilizável para organizar novos conteúdos e apontar dúvidas para revisão. | Validar a qualidade em outros cadernos e tratar layouts complexos e documentos digitalizados. |
| Classificação e painel | Estrutura pronta para acompanhar desempenho por diferentes recortes. | Ampliar e revisar os rótulos de disciplina, tema e habilidade para tornar esses recortes úteis. |
| Acessibilidade e usabilidade | Texto nativo, ampliação de figuras e navegação por teclado e em telas menores. | Conferência com leitores de tela, aparelhos reais e estudantes. |
| Operação | Instalação isolada em contêineres, regressão em SQLite/PostgreSQL, volumes persistentes e restauração conferidos; verificações da versão registradas. | Preparar a hospedagem e ensaiar a operação no ambiente escolhido. |

## O que ainda não foi iniciado

Diagnóstico por habilidade, seleção adaptativa de questões, tutor com IA e classificação automática permanecem nas próximas etapas. A preparação de conteúdo já usa regras de automação, mas não constitui um modelo de IA treinado ou avaliado.

Também continuam previstos a expansão para docentes, os recursos multimodais e os estudos de aprendizagem. A publicação externa e o piloto com estudantes ainda não foram realizados.

## Prioridades imediatas

1. Selecionar o próximo caderno e conferir sua preparação pelo fluxo geral.
2. Ampliar a classificação revisada para sustentar o painel e os futuros recursos adaptativos.
3. Encaminhar os aceites externos: revisão pedagógica independente, leitores de tela e aparelhos reais.
4. Preparar a publicação e o piloto conforme as dependências do roteiro.

A sequência e os critérios de aceite estão em [próximas etapas](proximas-etapas.md).

## Validação e limites

A versão integrada passou por 57 testes de API em SQLite e 57 em PostgreSQL, auditoria do caderno e validação da instalação em contêineres, persistência e recuperação. Os testes de navegador incluem o caderno inteiro, a jornada e a auditoria automática de acessibilidade. Procedimentos e execuções estão em [primeira entrega](../primeira-entrega.md). Os testes de celular realizados até aqui usam emulação de tela e não substituem o uso em aparelhos reais.

Essas evidências demonstram o funcionamento técnico dos incrementos verificados. A revisão pedagógica independente, a validação manual de acessibilidade e o piloto continuam necessários. Ainda não há resultados de aprendizagem ou avaliação de eficácia educacional.

## Documentos relacionados

- [Plano e escopo do projeto](enem_adaptativo_plano_do_projeto.md)
- [Próximas etapas e critérios de avanço](proximas-etapas.md)
- [Critérios e evidências da primeira entrega](../primeira-entrega.md)
- [Conteúdo e registro técnico da revisão](../../data/README.md)
- [Arquitetura e contratos](../architecture.md)
- [Operação, backup e recuperação](../operations.md)
