# Roteiro

O [estado atual](status-implementacao.md) descreve o produto implementado. Este documento guarda apenas trabalho futuro; o histórico de mudanças pertence ao Git.

## Continuidade da etapa 6

Tutor e layout dinâmico estão integrados (ver [estado](status-implementacao.md) e [contratos](../contratos-etapa6.md)). Falta conteúdo, não código:

- Tutor: o material das questões publicadas é gerado e aprovado automaticamente pela IA (`tutor-material`); questões anuladas e as que o provedor não resolver dentro das regras ficam sem ajuda até nova execução ou material escrito pela equipe.
- Layout: gerar propostas para as questões com apresentação simplificada, comparar com o original e aprovar caso a caso. Fórmulas detectadas pela geometria chegam como texto e precisam de transcrição.
- Propostas de layout continuam fora do produto até aprovação humana.
- Tipos de layout: publicar a rede imagem → tipo no Hugging Face (modelo e Space públicos, tags da versão do modelo e do catálogo) após a conferência dos exemplos e das 34 decisões manuais, e verificar a cópia baixada num venv limpo. A rede ainda fica abaixo do adaptador e da regra sobre o JSON; um backbone pré-treinado ou mais rótulos revisados são o próximo ciclo. Depois, renderizar os tipos representáveis no frontend e estruturar as oito questões de 2025 que o JSON guarda como imagem única. Linhas numeradas, blocos lado a lado e alternativas mistas exigem mudança no contrato de conteúdo.

## Evolução posterior

- Rotas próprias do Next.js em entrega separada, preservando URLs e autorização.
- Otimizações de consultas somente após benchmark com catálogo e histórico representativos.
- Novos ciclos de classificação/layout sem contaminar as partições reservadas.
- Tipos de layout com o acervo histórico: mais edições para dar suporte à cauda do catálogo e às marcas, hoje só no treino.
- Expansão por área, turmas e recursos multimodais mediante contratos e aceites próprios.

Curadoria independente, publicação de conteúdo das provas e piloto não são dependências nem entregas deste roteiro; a publicação externa prevista é só a da rede de tipos de layout, com até dez questões de exemplo de autoria do Inep, sem conteúdo de terceiros e com a fonte e o SHA-256 do caderno. Estudos de aprendizagem dependem de nova decisão de escopo e protocolo.

## Critério de entrega

Cada incremento deve ser executável a partir de clone, preservar dados e decisões manuais, ter testes do comportamento alterado e atualizar os guias permanentes. Resultados de testes ficam nos artefatos do CI; não criar relatórios por sessão no repositório.
