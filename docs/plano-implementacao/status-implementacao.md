# Status da implementação

Atualizado em **31/10/2026**. Visão geral do andamento do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

## Situação atual

**A consolidação técnica da primeira entrega e a ampliação técnica do banco estão implementadas.** Já é possível entrar em uma conta, realizar uma prova, retomar respostas, finalizar e consultar o histórico e o desempenho.

O catálogo inclui 135 questões: segundo dia azul de 2024 (90) e Matemática azul de 2023 (45), com 133 itens válidos. O acervo de 1998–2025 foi preservado e indexado para curadoria: 44.524 ocorrências, com cobertura e limites no [relatório](../cobertura-acervo.md). Revisão pedagógica independente, leitores de tela e aparelhos reais continuam como critérios externos antes da publicação e do piloto, reunidos no final das próximas etapas.

## O que já está disponível

- **Jornada do estudante:** conta individual, preferências, catálogo, resolução de provas, respostas salvas, retomada, correção e histórico.
- **Experiência de resolução:** texto selecionável, fórmulas matemáticas e químicas em LaTeX, figuras com legendas e ampliação dentro do site, navegação por botões, mapa e teclado, com retorno ao topo ao trocar de questão.
- **Acompanhamento:** resultados e evolução pessoal, com recortes conforme a classificação disponível no banco.
- **Gestão do conteúdo:** preparação de novas provas, sinalização de ambiguidades, revisão, aprovação, publicação e controle de versões, preservando tentativas anteriores.
- **Interface e operação local:** temas claro e escuro, navegação adaptada a telas menores e recursos de backup e recuperação.

## O que está parcial

| Frente | Estado atual | O que falta |
| --- | --- | --- |
| Conteúdo | Dois lotes conferidos, 135 itens, acervo de 28 anos organizado e indexado. | Conferir e publicar progressivamente o restante; resolver fontes indisponíveis e duas observações de extração. |
| Preparação de provas | Regras comuns para texto, LaTeX, química e vínculos; layouts históricos e acessíveis adicionais; seção de 2023 conferida. | OCR e curadoria de casos ambíguos, incluindo o PDF de codificação corrompida. |
| Classificação e painel | Taxonomia versionada e 135 anotações técnicas; referência de 89 questões válidas em oito temas. | Segunda anotação e adjudicação das 90 habilidades candidatas, ainda fora dos rótulos publicados. |
| Acessibilidade e usabilidade | Texto nativo, ampliação de figuras e navegação por teclado e em telas menores. | Conferência com leitores de tela, aparelhos reais e estudantes. |
| Operação | Instalação isolada em contêineres, regressão em SQLite/PostgreSQL, volumes persistentes e restauração conferidos; verificações da versão registradas. | Preparar a hospedagem e ensaiar a operação no ambiente escolhido. |

## O que ainda não foi iniciado

Diagnóstico por habilidade, seleção adaptativa de questões, tutor com IA e classificação automática permanecem nas próximas etapas. A preparação de conteúdo já usa regras de automação, mas não constitui um modelo de IA treinado ou avaliado.

Também continuam previstos a expansão para docentes, os recursos multimodais e os estudos de aprendizagem. A publicação externa e o piloto com estudantes ainda não foram realizados.

## Prioridades imediatas

1. Conferir o próximo lote do acervo indexado e resolver as pendências antes de publicar.
2. Realizar segunda anotação e adjudicação da referência temática e das habilidades candidatas.
3. Encaminhar os aceites externos: revisão pedagógica independente, leitores de tela e aparelhos reais.
4. Preparar a publicação e o piloto conforme as dependências do roteiro.

A sequência e os critérios de aceite estão em [próximas etapas](proximas-etapas.md).

## Validação e limites

A consolidação anterior passou por 57 testes de API em SQLite e 57 em PostgreSQL, auditoria do caderno e validação da instalação em contêineres, persistência e recuperação. Os testes de navegador incluem o caderno inteiro, a jornada e a auditoria automática de acessibilidade. Procedimentos e execuções estão em [primeira entrega](../primeira-entrega.md). Os testes de celular realizados até aqui usam emulação de tela e não substituem o uso em aparelhos reais.

Essas evidências demonstram o funcionamento técnico dos incrementos verificados. A revisão pedagógica independente, a validação manual de acessibilidade e o piloto continuam necessários. Ainda não há resultados de aprendizagem ou avaliação de eficácia educacional.

## Documentos relacionados

- [Plano e escopo do projeto](enem_adaptativo_plano_do_projeto.md)
- [Próximas etapas e critérios de avanço](proximas-etapas.md)
- [Critérios e evidências da primeira entrega](../primeira-entrega.md)
- [Conteúdo e registro técnico da revisão](../../data/README.md)
- [Arquitetura e contratos](../architecture.md)
- [Operação, backup e recuperação](../operations.md)

## Evidências da ampliação

Os novos fluxos passaram por 66 testes de API em SQLite e 66 em PostgreSQL, migração e verificação de esquema. Os 22 testes de navegador passaram em desktop e viewport móvel, incluindo as 45 questões de 2023 e a consulta de extrações na curadoria. As 150 expressões LaTeX do caderno de 2024 e as 159 da seção de 2023 foram compiladas. Uma regressão adicional cobre os cabeçalhos espaçados das versões para ledor.

A revisão técnica não equivale à revisão pedagógica independente. O [processo de classificação](../banco-classificacao.md) e as [pendências finais](proximas-etapas.md#pendências-da-ampliação-do-banco-e-da-classificação) registram o que ainda impede o aceite integral do acervo.
