# Estado do projeto

O Enem Flow oferece contas, provas oficiais, respostas persistentes, retomada, correção, histórico, painel, diagnóstico e prática adaptativa. As etapas técnicas 1/2, o primeiro ciclo de experimentos (3), diagnóstico (4) e política adaptativa (5) estão implementados.

## Conteúdo e ambientes

- Instalação local nova: seis provas regulares de 2024/2025, caderno azul, 540 posições. Primeiro dia em Inglês/Espanhol compartilha itens; posições não são identidades distintas.
- O segundo dia de 2024 é um lote conferido. As outras cinco provas são extrações automáticas que a equipe conferiu com o caderno e o gabarito originais em 06/11/2026 (`verified` em `data/catalog/profiles.json`); a origem automática e os diagnósticos resolvidos continuam registrados. O selo “Disponível” informa possibilidade de iniciar, não aprovação pedagógica nem segunda revisão independente.
- Docker: dois lotes conferidos, segundo dia de 2024 e Matemática 2023. O acervo histórico é opcional e reconstruído por ferramentas offline.
- Os cinco JSONs automáticos não têm temas publicados; não ampliam o conjunto elegível para diagnóstico/prática. Habilidades candidatas não estão publicadas.

## Limites

As verificações automatizadas não substituem revisão pedagógica, leitores de tela, aparelhos reais ou pesquisa educacional. Não há TRI ou evidência de ganho de aprendizagem. Experimentos e políticas simuladas descrevem comportamento técnico; propostas não são publicadas automaticamente.

O tutor está integrado à prática: material aprovado por questão, níveis de ajuda e IA opcional por API compatível com a OpenAI (Groq por padrão), com fallback para o texto aprovado. Ainda não há material aprovado incluído no repositório; a curadoria o escreve ou revisa as propostas da IA. Propostas de layout são convertidas pelo adaptador versionado `layout-adapter-v1`, comparadas com a apresentação publicada e, se aprovadas por um curador após conferir o original, viram rascunho no fluxo normal de revisão. Curadoria independente, hospedagem externa e piloto estão fora do roteiro atual. O [roteiro](proximas-etapas.md) define a continuidade; [operação](../operations.md) descreve instalação, atualização e recuperação; [validação](../validation.md) reúne os comandos e limites de verificação.
