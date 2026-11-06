# Roteiro

O [estado atual](status-implementacao.md) descreve o produto implementado. Este documento guarda apenas trabalho futuro; o histórico de mudanças pertence ao Git.

## Próxima entrega: tutor e layouts dinâmicos

As integrações são independentes e seguem os [contratos](../contratos-etapa6.md).

- Tutor: integrado à prática (ver [estado](status-implementacao.md)). Falta produzir e aprovar material para as questões publicadas.
- Layout: converter propostas experimentais por adaptador versionado, validar ordem e vínculos e preservar fallback da apresentação publicada. Exigir comparação com as fontes antes de liberar novos blocos.
- Propostas continuam fora do produto até aprovação humana. A preparação dos contratos não equivale a tutor implementado.

## Evolução posterior

- Rotas próprias do Next.js em entrega separada, preservando URLs e autorização.
- Otimizações de consultas somente após benchmark com catálogo e histórico representativos.
- Novos ciclos de classificação/layout sem contaminar as partições reservadas.
- Expansão por área, turmas e recursos multimodais mediante contratos e aceites próprios.

Curadoria independente, publicação externa e piloto não são dependências nem entregas deste roteiro. Estudos de aprendizagem dependem de nova decisão de escopo e protocolo.

## Critério de entrega

Cada incremento deve ser executável a partir de clone, preservar dados e decisões manuais, ter testes do comportamento alterado e atualizar os guias permanentes. Resultados de testes ficam nos artefatos do CI; não criar relatórios por sessão no repositório.
