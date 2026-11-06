# Roteiro

O [estado atual](status-implementacao.md) descreve o produto implementado. Este documento guarda apenas trabalho futuro; o histórico de mudanças pertence ao Git.

## Continuidade da etapa 6

Tutor e layout dinâmico estão integrados (ver [estado](status-implementacao.md) e [contratos](../contratos-etapa6.md)). Falta conteúdo, não código:

- Tutor: produzir e aprovar material para as questões publicadas; a IA gera propostas, e a liberação continua humana.
- Layout: gerar propostas para as questões com apresentação simplificada, comparar com o original e aprovar caso a caso. Fórmulas detectadas pela geometria chegam como texto e precisam de transcrição.
- Propostas continuam fora do produto até aprovação humana.

## Evolução posterior

- Rotas próprias do Next.js em entrega separada, preservando URLs e autorização.
- Otimizações de consultas somente após benchmark com catálogo e histórico representativos.
- Novos ciclos de classificação/layout sem contaminar as partições reservadas.
- Expansão por área, turmas e recursos multimodais mediante contratos e aceites próprios.

Curadoria independente, publicação externa e piloto não são dependências nem entregas deste roteiro. Estudos de aprendizagem dependem de nova decisão de escopo e protocolo.

## Critério de entrega

Cada incremento deve ser executável a partir de clone, preservar dados e decisões manuais, ter testes do comportamento alterado e atualizar os guias permanentes. Resultados de testes ficam nos artefatos do CI; não criar relatórios por sessão no repositório.
