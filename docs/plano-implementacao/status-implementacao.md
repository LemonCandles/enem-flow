# Status da implementação

Atualizado em **01/11/2026**. Visão geral do andamento do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

## Situação atual

**A consolidação técnica da primeira entrega e a parte técnica da etapa 2 foram concluídas.** Já é possível entrar em uma conta, realizar uma prova, retomar respostas, finalizar e consultar o histórico e o desempenho.

O catálogo versionado tem 135 questões conferidas: o segundo dia do ENEM 2024, caderno azul, com 90 questões de Natureza e Matemática, e a seção de Matemática azul de 2023, com 45. Cada item está vinculado às quatro cores da sua aplicação. Com o acervo local, `make acervo` permite publicar cadernos automáticos; o ensaio inicial registrou 96 provas de 2009 a 2025, com 8.595 questões. A origem automática e as pendências conhecidas ficam visíveis no site. Os arquivos gerados não acompanham o clone. Toda a curadoria, inclusive a revisão pedagógica independente, está concentrada na etapa 8, antes da publicação e do piloto. Leitores de tela e aparelhos reais continuam como pendências externas.

O lote processado recebido foi incorporado em 01/11/2026: **98 provas e 8.730 questões estão publicadas na instalação local**, incluindo os dois lotes conferidos. As 96 provas automáticas passaram pela conferência de fontes, gabaritos, LaTeX e figuras e pelo ensaio de resolução em uma cópia isolada. Há 506 pendências de apresentação em 489 questões, identificadas no site. Os detalhes estão em [incorporação do acervo](../banco-classificacao.md#incorporação-do-acervo-processado).

As cinco inconsistências encontradas na revisão posterior foram corrigidas, com regressão em SQLite/PostgreSQL (97 testes em cada), navegador (28 cenários), gateway real e persistência após recriação dos contêineres. Os ajustes preservam os dados históricos e estão descritos no [fechamento da revisão](../revisao-projeto-2026-11-01.md#fechamento-das-correções).

## O que já está disponível

- **Jornada do estudante:** conta individual, preferências, catálogo, resolução de provas, respostas salvas, retomada, correção e histórico.
- **Experiência de resolução:** texto selecionável, fórmulas matemáticas e químicas em LaTeX, figuras com legendas e ampliação dentro do site, navegação por botões, mapa e teclado, com retorno ao topo ao trocar de questão.
- **Acompanhamento:** resultados e evolução pessoal, com recortes conforme a classificação disponível no banco.
- **Gestão do conteúdo:** preparação de novas provas, sinalização de ambiguidades, revisão, aprovação, publicação e controle de versões, preservando tentativas anteriores.
- **Banco e classificação:** acervo oficial de 1998–2025 consultável na curadoria, identidade canônica com as ocorrências de cada cor, taxonomia versionada, 135 anotações com evidências e referência de 89 questões de Matemática para os experimentos.
- **Interface e operação local:** temas claro e escuro, navegação adaptada a telas menores e recursos de backup e recuperação.

## O que está parcial

| Frente | Estado atual | O que falta |
| --- | --- | --- |
| Conteúdo | Dois lotes conferidos e 96 provas automáticas instaladas; 98 provas/8.730 questões no site local. Banco textual de 1998–2025 preservado. | Nas etapas 3 e 8: resolver as 506 pendências em 489 questões, fazer a revisão pedagógica independente e conferir os cadernos automáticos; recuperar os casos ainda sem gabarito ou texto legível. |
| Preparação de provas | Processo reutilizável, ensaiado em cadernos de layouts diferentes (1º dia com opção de língua, PPL, 2012–2024), todos lidos por completo; texto com codificação quebrada é bloqueado. | Para a etapa 3: estruturar tabelas mescladas e relações espaciais e reconstruir fontes com codificação quebrada sem cor legível. Na etapa 8 (curadoria): revisar e importar os cadernos preparados. |
| Classificação e painel | Disciplina e tema publicados com curadoria técnica; o painel mostra a cobertura real. Habilidades estão como propostas. | Na etapa 8 (curadoria): segunda anotação independente, adjudicação e publicação das habilidades. |
| Acessibilidade e usabilidade | Texto nativo, ampliação de figuras e navegação por teclado e em telas menores. | Conferência com leitores de tela, aparelhos reais e estudantes. |
| Operação | Instalação isolada em contêineres, regressão em SQLite/PostgreSQL, volumes persistentes e restauração conferidos; verificações da versão registradas. | Preparar a hospedagem e ensaiar a operação no ambiente escolhido. |

## O que ainda não foi iniciado

Diagnóstico por habilidade, seleção adaptativa de questões, tutor com IA e classificação automática permanecem nas próximas etapas. A preparação de conteúdo já usa regras de automação, mas não constitui um modelo de IA treinado ou avaliado.

Também continuam previstos a expansão para docentes, os recursos multimodais e os estudos de aprendizagem. A publicação externa e o piloto com estudantes ainda não foram realizados.

## Prioridades imediatas

1. Iniciar a etapa 3: linha de base de classificação temática com a referência de 89 questões e anotação de layout dos cadernos preparados no ensaio.
2. Seguir para o diagnóstico por tema e a política adaptativa (etapas 4 e 5) com os rótulos já publicados.
3. Encaminhar os aceites externos: leitores de tela e aparelhos reais.
4. Reunir toda a curadoria na etapa 8, antes da publicação e do piloto (etapas 9 e 10).

A sequência e os critérios de aceite estão em [próximas etapas](proximas-etapas.md).

## Validação e limites

A regressão atual passou por 97 testes de backend em SQLite, 97 em PostgreSQL e 28 testes Playwright no build de produção. A instalação Compose sobre Podman também passou pelos testes de identificação de clientes, proteção contra cabeçalhos falsificados e persistência após recriação dos contêineres. As verificações das correções estão no [fechamento da revisão](../revisao-projeto-2026-11-01.md#fechamento-das-correções); a validação anterior da integração está em [banco e classificação](../banco-classificacao.md#validação-da-integração), e os procedimentos da consolidação em [primeira entrega](../primeira-entrega.md). Os testes de celular usam emulação de tela e não substituem o uso em aparelhos reais.

Essas evidências demonstram o funcionamento técnico dos incrementos verificados. A revisão pedagógica independente, a validação manual de acessibilidade e o piloto continuam necessários. Ainda não há resultados de aprendizagem ou avaliação de eficácia educacional.

## Documentos relacionados

- [Plano e escopo do projeto](enem_adaptativo_plano_do_projeto.md)
- [Próximas etapas e critérios de avanço](proximas-etapas.md)
- [Critérios e evidências da primeira entrega](../primeira-entrega.md)
- [Conteúdo e registro técnico da revisão](../../data/README.md)
- [Arquitetura e contratos](../architecture.md)
- [Operação, backup e recuperação](../operations.md)
