# Próximas etapas

Atualizado em **31/10/2026**. Este roteiro parte do [status da implementação](status-implementacao.md) e organiza a continuidade do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

As etapas abaixo são propostas de execução, com dependências e critérios de aceite. A publicação e a execução do piloto ficam para o final, após o desenvolvimento e a validação dos incrementos priorizados. O marco de 15/11/2026 permanece como referência do PDF; a definição das datas operacionais depende da capacidade disponível e das evidências de cada entrega.

## 1. Consolidar a primeira entrega

**Consolidação técnica concluída em 31/10/2026.** Os aceites que dependem de pessoas ou aparelhos externos estão reunidos no final deste roteiro.

- [x] Conferir integridade dos 90 itens, gabarito oficial, anulação, hashes das fontes e recursos; compilar as 150 expressões LaTeX do caderno publicado.
- [x] Corrigir o lote de 15 questões com novas versões e justificativas; preservar respostas, resultados e snapshots anteriores.
- [x] Integrar preparação generalizada, curadoria, navegação, figuras e LaTeX na mesma regressão.
- [x] Executar 57 testes de API em SQLite e 57 em PostgreSQL, com migrações e alinhamento de esquema verificados.
- [x] Construir e iniciar uma instalação isolada com dependências instaladas do zero, Compose, PostgreSQL e volumes persistentes. Substituir os contêineres e conferir login, resposta, resultado, histórico, 90 snapshots e arquivos próprios.
- [x] Ensaiar backup/restauração de SQLite e PostgreSQL sem alterar o banco de uso da aplicação.
- [x] Conferir as 90 questões em desktop e viewport móvel; verificar teclado, foco, diálogos, ampliação de figuras e reflow em larguras reduzidas. Corrigir contraste, nomes acessíveis e hierarquia de títulos encontrados pela auditoria automatizada.
- [x] Revisar os arquivos, registrar commits por decisão lógica e incluir verificações de conteúdo, acessibilidade e persistência de contêineres no CI. As execuções da versão estão vinculadas nas [evidências](../primeira-entrega.md).

**Resultado:** a base técnica da primeira entrega está consolidada. Isso não equivale à revisão pedagógica independente nem à validação de uso em aparelhos reais. Esses critérios de liberação permanecem nas [pendências externas](#pendências-externas-da-primeira-entrega).

O registro completo de procedimentos e limites está em [primeira entrega](../primeira-entrega.md) e [operação](../operations.md). A comparação do lote de apresentação com a fonte permanece em [origem do conteúdo](../../data/README.md#revisão-de-apresentação).

## 2. Ampliar o banco e a classificação revisada

**Ampliação técnica implementada em 31/10/2026.** O escopo cobre todos os anos e aplicações com arquivos vinculados pelo Inep. A publicação segue a curadoria: o acervo extraído não foi liberado automaticamente como questão revisada.

- [x] Inventariar 1998–2025: 886 referências em 822 URLs, preservando aplicações, línguas e versões acessíveis. Obter 884 referências; registrar dois links oficiais que retornam 404.
- [x] Organizar os originais por ano, aplicação, modalidade, dia, caderno e formato; separar fontes de transcrições/cache e guardar URLs, páginas oficiais e SHA-256. O acervo histórico e o banco extraído permanecem locais, conforme a política do repositório.
- [x] Indexar 480 PDFs e 10 TXT em 44.524 ocorrências de questões, incluindo numerações repetidas de língua estrangeira. Disponibilizar a consulta na curadoria.
- [x] Ampliar o adaptador para marcadores sobrepostos, cabeçalhos numéricos antigos e letras/números espaçados das versões acessíveis; conferir e preparar a seção de Matemática de 2023, questões 136–180, com texto nativo, LaTeX, tabelas e figuras separadas.
- [x] Separar identidade canônica e ocorrências, mantendo números, ordem das alternativas, letras do gabarito e snapshots; recusar conflitos. Vincular os lotes conferidos ao índice do acervo. A união de duplicatas visuais ainda requer conferência.
- [x] Definir `enem-content-v1`, com disciplinas/temas separados da matriz oficial, e registrar 135 anotações técnicas com evidência. Manter 90 propostas de habilidades fora dos rótulos publicados até segunda revisão.
- [x] Instalar os dois lotes conferidos e seus rótulos por versões imutáveis: 135 questões, 133 válidas. Repetições da instalação não duplicam versões e edições próprias são preservadas por recusa da atualização automática.
- [x] Formar a referência exploratória com 89 questões válidas de Matemática em oito temas e grupos canônicos para futuros splits. A questão 164/2023, anulada, permanece fora dos experimentos.

**Aceite parcial:** origem, versões, referência temática e publicação dos dois lotes estão rastreáveis. O aceite de todo o acervo como conteúdo revisado permanece pendente: extração, curadoria e aprovação são estados distintos. As pendências estão reunidas no final deste documento.

Consulte [banco e classificação](../banco-classificacao.md), [cobertura por ano e aplicação](../cobertura-acervo.md) e [organização das fontes](../../data/sources/README.md).

## 3. Iniciar os experimentos de Dados e IA

Avanço da preparação da etapa 2: o [fluxo geral](../preparacao-provas.md) está implementado para novas importações JSON e PDFs textuais com manifesto. Casos ambíguos são reportados, e perdas de layout conhecidas bloqueiam publicação. A etapa 2 acrescenta identidade canônica, indexação histórica e referência temática curada tecnicamente. OCR dos casos não legíveis, união de duplicatas visuais e segunda revisão dos rótulos ainda são necessários para ampliar a avaliação.

**Dependência: contratos e amostras revisadas da etapa 2. Duas frentes podem avançar em paralelo.**

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

## 4. Implementar diagnóstico e estado por habilidade

**Dependências: histórico consistente e cobertura revisada de rótulos. Frente principal: Plataforma.**

1. Criar sessões de diagnóstico com objetivo, área e tempo disponível.
2. Distribuir os itens pelos temas disponíveis e registrar a quantidade de evidência por habilidade.
3. Manter tentativas recentes, acertos independentes, itens vistos e última prática.
4. Implementar e avaliar um estimador explicável. O plano sugere uma taxa suavizada ou Beta-Binomial; com prior Beta(1,1), a média seria `(1 + acertos) / (2 + tentativas)`.
5. Mostrar quando há poucas respostas para sustentar uma interpretação e separar desempenho independente de desempenho assistido.

**Critério de aceite:** o estado do aluno pode ser reconstruído a partir de eventos e versões, informa a quantidade de evidência e respeita o momento de finalização das provas.

## 5. Integrar uma política adaptativa inicial

**Dependência: etapa 4 e itens elegíveis com rótulos revisados. Frente conjunta.**

1. Definir os filtros de área, integridade, habilidade, exposição e dificuldade provisória.
2. Combinar reforço, revisão e exploração com parâmetros explícitos.
3. Registrar candidatos, componentes da prioridade, escolha, justificativa e versão da política.
4. Controlar repetição e concentração da prática em poucos itens.
5. Comparar o comportamento com seleção aleatória e uma referência simples de reforço.

**Critério de aceite:** cada recomendação tem um motivo compreensível e um registro que permite auditar a seleção; cobertura e exposição foram avaliadas nos cenários definidos.

## 6. Integrar tutor, layouts dinâmicos e curadoria assistida

Essas integrações podem ser liberadas de forma independente, conforme suas evidências de qualidade. A curadoria assistida pode ser antecipada se a revisão manual se tornar o gargalo do banco.

| Integração | Próximo trabalho | Critério de liberação |
| --- | --- | --- |
| Tutor com LLM | Preparar resoluções e pistas aprovadas; recuperar referências; definir níveis de ajuda, validação e ferramentas limitadas; registrar ajuda utilizada, versões, custo e latência. | Avaliação com casos revisados, respeito à etapa de ajuda e continuidade com conteúdo aprovado quando o provedor falhar. |
| Layouts dinâmicos | Consumir agrupamentos e relações espaciais aprovadas, preservando texto nativo, ordem de leitura e vínculos em desktop e celular. | Comparação visual com o original e ausência de cortes, inversões e relações perdidas nos layouts de avaliação. |
| Curadoria assistida | Detectar falhas de extração, recursos ausentes, duplicatas e inconsistências; propor correções com evidência e revisão humana. | Falsos positivos medidos, alterações rastreáveis e possibilidade de reversão; mudanças que afetem a resposta têm revisão reforçada. |

## 7. Expandir o produto e a pesquisa

Após estabilizar as integrações, preservar no backlog:

- Cobertura das quatro áreas e dos anos e aplicações definidos pelo projeto.
- Turmas, atividades e visão agregada para docentes, com regras próprias de acesso e tratamento de dados.
- Predição de acerto, knowledge tracing, dificuldade calibrada e políticas avançadas com referências e protocolos de avaliação.
- Multimodalidade, análise do raciocínio escrito e exercícios gerados com revisão.
- Treinamento ou ajuste de modelos quando houver dados e recursos suficientes, com artefato, documentação e avaliação; publicação no Hugging Face quando aplicável.
- Estudo educacional com pré e pós-teste, itens novos e comparáveis, condição de referência e acompanhamento de retenção.

**Critério de aceite por incremento:** comportamento executável, conteúdo revisado, decisões rastreáveis e resultados correspondentes às medições realizadas.

## 8. Publicar uma versão para o piloto

**Dependências: aceites externos da primeira entrega, listados no final deste documento, e validação dos incrementos priorizados nas etapas 2 a 7. Frente principal: Plataforma.**

1. Definir o ambiente de hospedagem e configurar domínio, HTTPS e origens autorizadas.
2. Provisionar PostgreSQL e armazenamento persistente para os recursos das questões.
3. Aplicar as migrações e importar o conjunto revisado; conferir os papéis de aluno e curadoria.
4. Validar a recuperação assistida de acesso e os registros de falhas e latência.
5. Fazer backup e ensaiar a restauração nesse ambiente, preservando banco, versões e arquivos associados.
6. Publicar uma identificação da versão e atualizar o README e o vídeo com o endereço da demonstração.

**Critério de aceite:** a aplicação publicada preserva uma tentativa após reinício dos serviços, permite recuperar os dados de um backup e mantém o acesso individual ao histórico.

## 9. Executar o piloto e ajustar a experiência

**Dependência: versão utilizável da etapa 8. Frente conjunta.**

1. Convidar aproximadamente 5–10 estudantes adultos, conforme a proposta exploratória do plano.
2. Observar entrada na conta, localização da prova, marcação e alteração de resposta, retomada e consulta do resultado.
3. Registrar conclusão das tarefas, falhas, dificuldades, abandono e clareza do painel.
4. Priorizar e corrigir os problemas observados, preservando as tentativas existentes.
5. Produzir um relato com a versão testada, quantidade de participantes, resultados e limitações.

**Critério de aceite:** os problemas encontrados têm encaminhamento registrado e existe um relato reproduzível do funcionamento e da usabilidade. A investigação de ganho de aprendizagem terá protocolo próprio em uma etapa posterior.

## Primeiro bloco de trabalho recomendado

Encaminhar a segunda anotação da referência e preparar o próximo lote a partir do acervo indexado, resolvendo os relatórios antes de publicar. Iniciar os protocolos exploratórios da etapa 3 com os 89 itens elegíveis, sem tratá-los como benchmark pedagógico independente. Encaminhar em paralelo a revisão pedagógica independente e os testes manuais de acessibilidade descritos no final. Publicação e piloto continuam sujeitos a esses aceites e às dependências das etapas 8 e 9.

## Referências locais

- [Estado atual e pendências](status-implementacao.md)
- [Plano original](enem_adaptativo_plano_do_projeto.md)
- [Critérios da primeira entrega](../primeira-entrega.md)
- [Arquitetura e contratos](../architecture.md)
- [Implantação, backup e recuperação](../operations.md)
- [Preparação e origem do banco](../../data/README.md)

## Pendências externas da primeira entrega

Estas atividades foram retiradas da etapa técnica porque exigem pessoas, tecnologias assistivas ou aparelhos indisponíveis para a execução automatizada. **Apesar de estarem no final do documento, são critérios de liberação anteriores à publicação e ao piloto.**

| Pendência | Por que não foi concluída aqui | Critério de conclusão |
| --- | --- | --- |
| Revisão pedagógica independente dos 90 itens | A conferência técnica feita durante a implementação não constitui uma segunda revisão independente por profissional de educação. | Revisor independente compara enunciados, fórmulas, tabelas, figuras, alternativas e gabaritos com a fonte; registra divergências e aprova as correções por novas versões. |
| Leitores de tela e descrições científicas | Axe, MathML, nomes acessíveis e testes de foco não verificam a experiência falada nem a interpretação de gráficos por uma pessoa usuária de tecnologia assistiva. | Conferir cadastro, resolução, química/matemática falada, tabelas, legendas, ampliação e resultado com leitor de tela real; corrigir e registrar os casos encontrados. |
| Aparelhos reais e zoom do navegador | Os testes de celular usam viewport emulado no Chrome; não há interação física com telefones, Safari/iOS ou recursos de ampliação do sistema. | Executar a jornada em Android e iPhone e conferir teclado/zoom do navegador no desktop; registrar aparelho, navegador, versão, tarefas e resultados. |

O roteiro de execução manual e as evidências automáticas estão em [primeira entrega](../primeira-entrega.md). Nenhuma dessas pendências foi marcada como revisão concluída, piloto realizado ou evidência de aprendizagem.

## Pendências da ampliação do banco e da classificação

| Pendência | Estado e critério para concluir |
| --- | --- |
| Curadoria integral do acervo histórico | Os originais foram preservados e o texto extraído está consultável. Preparar e conferir enunciados, fórmulas científicas, figuras, tabelas, alternativas e gabarito de cada lote antes de aprovar/publicar. As cores e versões acessíveis não devem inflar a quantidade de itens canônicos. |
| Dois links oficiais indisponíveis | Uma prova superampliada de 2024 e o gabarito braile/ledor de reaplicação de 2025 retornam 404. Retomar a coleta quando houver fonte oficial correta; nunca usar o gabarito de outra aplicação. URLs exatas estão no relatório de cobertura. |
| Dois casos de extração ainda sinalizados | Caderno azul do segundo dia de reaplicação/PPL de 2010 apresenta um número fora da faixa; caderno branco do primeiro dia de reaplicação/PPL de 2021 tem texto com codificação corrompida. Conferir visualmente/OCR, corrigir o adaptador e reproduzir os índices. |
| Deduplicação visual e semântica | Identidades de extrações com figuras são conservadoras. Comparar conteúdo e correspondência de alternativas antes de unir; avaliar duplicatas restantes antes de definir os splits dos experimentos. |
| Segunda anotação e adjudicação | Um revisor independente deve comparar os 135 itens e suas classificações; registrar divergências, decisões e evidências. As 90 habilidades candidatas permanecem propostas até esse aceite. |
| Gabaritos e áreas não explícitos em provas antigas | O acervo de 1998–2008 oferece o caderno amarelo sem gabarito separado nos links anuais. Localizar uma fonte oficial verificável e classificar itens interdisciplinares antes de preparar publicação; não preencher respostas ou áreas por suposição. |

As pendências de acessibilidade e revisão independente da primeira entrega também se aplicam aos novos itens. O catálogo não representa todo o acervo como revisado nem o conjunto de referência como avaliação independente concluída.
