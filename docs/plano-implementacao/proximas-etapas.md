# Próximas etapas

Atualizado em **30/10/2026**. Este roteiro parte do [status da implementação](status-implementacao.md) e organiza a continuidade do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

As etapas abaixo são propostas de execução, com dependências e critérios de aceite. O marco de 15/11/2026 permanece como referência do PDF; a definição das datas operacionais depende da capacidade disponível e das evidências de cada entrega.

## 1. Consolidar a primeira entrega

**Prioridade imediata — Plataforma e curadoria.**

1. Conferir o caderno inicial com revisão pedagógica independente, incluindo as fórmulas normalizadas, as tabelas, as figuras e as alternativas com diagramas.
2. Corrigir os problemas encontrados por meio de novas versões e registrar a justificativa da revisão.
3. Executar a instalação desde um checkout limpo; validar o Docker Compose e seus volumes persistentes.
4. Revisar os arquivos novos, registrar a versão no Git e confirmar a execução dos workflows de CI no serviço remoto.
5. Conferir teclado, leitor de tela, zoom, gráficos e interação em aparelhos reais.

**Critério de aceite:** uma instalação limpa permite cadastrar-se, iniciar o caderno, navegar, alterar uma escolha, recarregar, finalizar e consultar o mesmo resultado no histórico. O conteúdo está revisado e os checks da versão estão registrados.

## 2. Publicar uma versão para o piloto

**Dependência: etapa 1. Frente principal: Plataforma.**

1. Definir o ambiente de hospedagem e configurar domínio, HTTPS e origens autorizadas.
2. Provisionar PostgreSQL e armazenamento persistente para os recursos das questões.
3. Aplicar as migrações e importar o conjunto revisado; conferir os papéis de aluno e curadoria.
4. Validar a recuperação assistida de acesso e os registros de falhas e latência.
5. Fazer backup e ensaiar a restauração nesse ambiente, preservando banco, versões e arquivos associados.
6. Publicar uma identificação da versão e atualizar o README e o vídeo com o endereço da demonstração.

**Critério de aceite:** a aplicação publicada preserva uma tentativa após reinício dos serviços, permite recuperar os dados de um backup e mantém o acesso individual ao histórico.

## 3. Executar o piloto e ajustar a experiência

**Dependência: versão utilizável da etapa 2. Frente conjunta.**

1. Convidar aproximadamente 5–10 estudantes adultos, conforme a proposta exploratória do plano.
2. Observar entrada na conta, localização da prova, marcação e alteração de resposta, retomada e consulta do resultado.
3. Registrar conclusão das tarefas, falhas, dificuldades, abandono e clareza do painel.
4. Priorizar e corrigir os problemas observados, preservando as tentativas existentes.
5. Produzir um relato com a versão testada, quantidade de participantes, resultados e limitações.

**Critério de aceite:** os problemas encontrados têm encaminhamento registrado e existe um relato reproduzível do funcionamento e da usabilidade. A investigação de ganho de aprendizagem terá protocolo próprio em uma etapa posterior.

## 4. Ampliar o banco e a classificação revisada

**Pode avançar em paralelo à preparação do piloto. Frentes: Dados e IA, curadoria e integração de Plataforma.**

1. Definir os próximos cadernos, anos e aplicações a importar, mantendo explícita a cobertura disponível.
2. Generalizar a preparação do JSON: enunciado, comando, alternativas, tabelas, fórmulas, créditos e figuras associados.
3. Identificar questões repetidas entre cores e preservar um identificador canônico com suas ocorrências.
4. Definir uma taxonomia versionada de disciplinas e temas, separada das competências e habilidades oficiais.
5. Anotar uma amostra de referência, discutir divergências e registrar evidências dos vínculos com habilidades.
6. Revisar e publicar os rótulos para que o painel passe a mostrar recortes com cobertura útil.
7. Construir o conjunto inicial dos experimentos adaptativos: a referência do plano é de 80–150 questões de Matemática em 6–8 temas, ampliando as 45 questões de Matemática atualmente disponíveis.

**Critério de aceite:** o novo conteúdo está revisado, tem origem e versões rastreáveis, não duplica itens canônicos e apresenta a cobertura real dos rótulos no painel.

## 5. Iniciar os experimentos de Dados e IA

**Dependência: contratos e amostras revisadas da etapa 4. Duas frentes podem avançar em paralelo.**

### Classificação temática

- Estabelecer uma referência simples, como regras ou revisão assistida.
- Comparar classificadores supervisionados, representações de texto e LLMs conforme os dados disponíveis.
- Separar desenvolvimento e teste depois da deduplicação; manter variantes do mesmo item no mesmo conjunto.
- Medir precisão, revocação, F1 por classe, consistência, latência, custo e tipos de erro.
- Definir o encaminhamento para revisão com base nas medições e preservar a origem dos rótulos propostos.

### Análise de layout

- Anotar blocos, páginas, posições, agrupamentos, ordem de leitura e associação das imagens e alternativas.
- Comparar extração de coordenadas, OCR, regras de geometria e métodos visuais quando necessários.
- Reservar exemplos difíceis e padrões de layout para avaliação independente.
- Medir localização, ordem, vínculos, integridade e tempo de correção humana.

**Critério de aceite:** cada frente entrega dados no contrato acordado, comparação com uma referência, configuração versionada, métricas reproduzíveis e casos de erro. Propostas automáticas passam pelo processo de revisão antes de entrar no conteúdo publicado.

## 6. Implementar diagnóstico e estado por habilidade

**Dependências: histórico consistente e cobertura revisada de rótulos. Frente principal: Plataforma.**

1. Criar sessões de diagnóstico com objetivo, área e tempo disponível.
2. Distribuir os itens pelos temas disponíveis e registrar a quantidade de evidência por habilidade.
3. Manter tentativas recentes, acertos independentes, itens vistos e última prática.
4. Implementar e avaliar um estimador explicável. O plano sugere uma taxa suavizada ou Beta-Binomial; com prior Beta(1,1), a média seria `(1 + acertos) / (2 + tentativas)`.
5. Mostrar quando há poucas respostas para sustentar uma interpretação e separar desempenho independente de desempenho assistido.

**Critério de aceite:** o estado do aluno pode ser reconstruído a partir de eventos e versões, informa a quantidade de evidência e respeita o momento de finalização das provas.

## 7. Integrar uma política adaptativa inicial

**Dependência: etapa 6 e itens elegíveis com rótulos revisados. Frente conjunta.**

1. Definir os filtros de área, integridade, habilidade, exposição e dificuldade provisória.
2. Combinar reforço, revisão e exploração com parâmetros explícitos.
3. Registrar candidatos, componentes da prioridade, escolha, justificativa e versão da política.
4. Controlar repetição e concentração da prática em poucos itens.
5. Comparar o comportamento com seleção aleatória e uma referência simples de reforço.

**Critério de aceite:** cada recomendação tem um motivo compreensível e um registro que permite auditar a seleção; cobertura e exposição foram avaliadas nos cenários definidos.

## 8. Integrar tutor, layouts dinâmicos e curadoria assistida

Essas integrações podem ser liberadas de forma independente, conforme suas evidências de qualidade. A curadoria assistida pode ser antecipada se a revisão manual se tornar o gargalo do banco.

| Integração | Próximo trabalho | Critério de liberação |
| --- | --- | --- |
| Tutor com LLM | Preparar resoluções e pistas aprovadas; recuperar referências; definir níveis de ajuda, validação e ferramentas limitadas; registrar ajuda utilizada, versões, custo e latência. | Avaliação com casos revisados, respeito à etapa de ajuda e continuidade com conteúdo aprovado quando o provedor falhar. |
| Layouts dinâmicos | Consumir agrupamentos e relações espaciais aprovadas, preservando texto nativo, ordem de leitura e vínculos em desktop e celular. | Comparação visual com o original e ausência de cortes, inversões e relações perdidas nos layouts de avaliação. |
| Curadoria assistida | Detectar falhas de extração, recursos ausentes, duplicatas e inconsistências; propor correções com evidência e revisão humana. | Falsos positivos medidos, alterações rastreáveis e possibilidade de reversão; mudanças que afetem a resposta têm revisão reforçada. |

## 9. Expandir o produto e a pesquisa

Após estabilizar as integrações, preservar no backlog:

- Cobertura das quatro áreas e dos anos e aplicações definidos pelo projeto.
- Turmas, atividades e visão agregada para docentes, com regras próprias de acesso e tratamento de dados.
- Predição de acerto, knowledge tracing, dificuldade calibrada e políticas avançadas com referências e protocolos de avaliação.
- Multimodalidade, análise do raciocínio escrito e exercícios gerados com revisão.
- Treinamento ou ajuste de modelos quando houver dados e recursos suficientes, com artefato, documentação e avaliação; publicação no Hugging Face quando aplicável.
- Estudo educacional com pré e pós-teste, itens novos e comparáveis, condição de referência e acompanhamento de retenção.

**Critério de aceite por incremento:** comportamento executável, conteúdo revisado, decisões rastreáveis e resultados correspondentes às medições realizadas.

## Primeiro bloco de trabalho recomendado

Começar pela revisão pedagógica do caderno e pela reprodução da instalação em Docker. Esses dois trabalhos permitem fechar as pendências imediatas da primeira entrega e preparar a versão publicada para o piloto. A definição da taxonomia e a anotação de uma amostra podem avançar em paralelo, preparando o painel detalhado e as integrações adaptativas.

## Referências locais

- [Estado atual e pendências](status-implementacao.md)
- [Plano original](enem_adaptativo_plano_do_projeto.md)
- [Critérios da primeira entrega](../primeira-entrega.md)
- [Arquitetura e contratos](../architecture.md)
- [Implantação, backup e recuperação](../operations.md)
- [Preparação e origem do banco](../../data/README.md)
