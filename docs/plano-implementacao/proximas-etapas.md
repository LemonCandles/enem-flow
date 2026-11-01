# Próximas etapas

Atualizado em **31/10/2026**. Este roteiro parte do [status da implementação](status-implementacao.md) e organiza a continuidade do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

As etapas abaixo são propostas de execução, com dependências e critérios de aceite. **Toda a curadoria fica concentrada na [etapa 8](#8-curadoria-do-conteúdo-e-dos-rótulos), no final do desenvolvimento.** Isso inclui revisão humana, aprovação e importação de conteúdo, segunda revisão dos rótulos, aprovação de propostas automáticas e curadoria assistida. As etapas 2 a 7 usam o conteúdo já publicado e os rótulos de curadoria técnica, sem esperar revisões. Publicação e piloto vêm depois da curadoria, porque dependem de conteúdo revisado. O marco de 15/11/2026 permanece como referência do PDF; a definição das datas operacionais depende da capacidade disponível e das evidências de cada entrega.

## 1. Consolidar a primeira entrega

**Consolidação técnica concluída em 31/10/2026.** A revisão pedagógica independente foi para a [curadoria](#8-curadoria-do-conteúdo-e-dos-rótulos), e os aceites que dependem de aparelhos ou tecnologias assistivas estão no final deste roteiro.

- [x] Conferir integridade dos 90 itens, gabarito oficial, anulação, hashes das fontes e recursos; compilar as 150 expressões LaTeX do caderno publicado.
- [x] Corrigir o lote de 15 questões com novas versões e justificativas; preservar respostas, resultados e snapshots anteriores.
- [x] Integrar preparação generalizada, curadoria, navegação, figuras e LaTeX na mesma regressão.
- [x] Executar 57 testes de API em SQLite e 57 em PostgreSQL, com migrações e alinhamento de esquema verificados.
- [x] Construir e iniciar uma instalação isolada com dependências instaladas do zero, Compose, PostgreSQL e volumes persistentes. Substituir os contêineres e conferir login, resposta, resultado, histórico, 90 snapshots e arquivos próprios.
- [x] Ensaiar backup/restauração de SQLite e PostgreSQL sem alterar o banco de uso da aplicação.
- [x] Conferir as 90 questões em desktop e viewport móvel; verificar teclado, foco, diálogos, ampliação de figuras e reflow em larguras reduzidas. Corrigir contraste, nomes acessíveis e hierarquia de títulos encontrados pela auditoria automatizada.
- [x] Revisar os arquivos, registrar commits por decisão lógica e incluir verificações de conteúdo, acessibilidade e persistência de contêineres no CI. As execuções da versão estão vinculadas nas [evidências](../primeira-entrega.md).

**Resultado:** a base técnica da primeira entrega está consolidada. Isso não equivale à revisão pedagógica independente, que está na [etapa 8](#8-curadoria-do-conteúdo-e-dos-rótulos), nem à validação de uso em aparelhos reais, que está nas [pendências externas](#pendências-externas-da-primeira-entrega).

O registro completo de procedimentos e limites está em [primeira entrega](../primeira-entrega.md) e [operação](../operations.md). A comparação do lote de apresentação com a fonte permanece em [origem do conteúdo](../../data/README.md#revisão-de-apresentação).

## 2. Ampliar o banco e a classificação

**Parte técnica concluída em 31/10/2026.** A implementação está descrita em [banco e classificação](../banco-classificacao.md) e no [ensaio da preparação](../preparacao-provas.md#ensaio-em-outros-layouts). As atividades de curadoria desta etapa foram para a [etapa 8](#8-curadoria-do-conteúdo-e-dos-rótulos).

- [x] **1. Definir os próximos cadernos, anos e aplicações**, mantendo explícita a cobertura disponível. O acervo oficial de 1998–2025 está inventariado, com [cobertura](../cobertura-acervo.md). A seção de Matemática azul de 2023 foi incorporada, e o ensaio deixou 7 cadernos legíveis de outros layouts preparados como candidatos. *Curadoria (etapa 8):* escolher e importar os próximos.
- [x] **2. Validar e ampliar a preparação generalizada** com novos cadernos. O [ensaio](../preparacao-provas.md#ensaio-em-outros-layouts) com `scripts/trial_preparation.py` preparou cadernos de 1º e 2º dia, PPL e anos de 2012 a 2024, todos com 90 questões. O adaptador passou a tratar:
  - a opção de língua pelo manifesto;
  - alternativas em grade;
  - marca d'água girada e faixas decorativas;
  - linhas duplicadas pela camada acessível;
  - cabeçalhos com letras e números espaçados, pela mesma regra usada no banco textual;
  - a ordem das áreas de 2009 e os metadados compartilhados entre ensaio e geração;
  - moedas como `US$`;
  - texto com codificação quebrada, que é bloqueado.

  Nos cadernos legíveis restam 1 a 8 pendências bloqueantes, em geral tabelas mescladas e relações espaciais. Os 34 PDFs com codificação quebrada (7% do acervo, sobretudo 2021) podem ser preparados por outra cor legível quando ela existe. Sem cor legível, é preciso reconstruir o mapeamento da fonte ou usar OCR. *Curadoria (etapa 8):* resolver as pendências e aprovar.
- [x] **3. Identificar questões repetidas entre cores** e preservar um identificador canônico com suas ocorrências. `canonical_questions` guarda a identidade. Os 135 itens conferidos estão vinculados às quatro cores da aplicação (540 ocorrências), com texto, pareamento único, gabarito oficial de cada cor e figuras conferidos. A importação de outra cor reaproveita a identidade e recusa gabarito divergente. No restante do acervo, só texto idêntico é agrupado automaticamente.
- [x] **4. Definir uma taxonomia versionada** de disciplinas e temas, separada das competências e habilidades oficiais: `enem-content-v1` e matriz oficial de Matemática.
- [x] **5. Anotar uma amostra de referência** com evidências dos vínculos com habilidades: 135 anotações técnicas e 90 habilidades candidatas. *Curadoria (etapa 8):* segunda anotação independente, discussão das divergências e adjudicação.
- [x] **6. Publicar os rótulos** para que o painel mostre recortes com cobertura útil: disciplina e tema publicados, com a cobertura real no painel. *Curadoria (etapa 8):* revisar e publicar as habilidades.
- [x] **Publicação automática do acervo (decisão de 31/10/2026).** As provas de 2009 a 2025 podem ser geradas e publicadas sem curadoria com `make acervo`. O ensaio inicial registrou 96 provas, 8.595 questões e 506 pendências; os arquivos ficam locais, fora do Git. Os detalhes estão em [publicação automática](../preparacao-provas.md#publicação-automática-do-acervo). O site identifica a origem automática e as pendências conhecidas; o fluxo manual mantém seus bloqueios. A melhoria da extração fica para a etapa 3 e a conferência para a etapa 8.
- [x] **7. Construir o conjunto inicial dos experimentos adaptativos:** `adaptive-math-reference-v1` tem 89 questões válidas de Matemática em oito temas, dentro da referência de 80–150 questões em 6–8 temas.

**Critério de aceite:** o novo conteúdo tem origem e versões rastreáveis, não duplica itens canônicos e apresenta a cobertura real dos rótulos no painel. Testes verificam esses pontos, inclusive a ausência de duplicação entre cores. A revisão humana do conteúdo e das habilidades é critério da etapa 8.

**Base disponível:**
- preparação: módulo `backend/app/preparation/`, CLI `scripts/prepare_exam.py`, adaptador `scripts/exam_pdf.py`, manifesto de exemplo e ensaio `scripts/trial_preparation.py`;
- acervo e banco textual: `scripts/archive_enem.py` e `scripts/build_bank.py`;
- vínculo entre cores: `scripts/link_booklets.py`.

A normalização usa regras e contexto, sem depender dos números das questões. Notação perdida e estruturas ambíguas continuam sinalizadas para a curadoria.

A integração das duas frentes preserva os vínculos entre cores e os relatórios de preparação ao acrescentar classificação. O índice reconstruído reúne 44.524 ocorrências e 43.439 identidades conservadoras, com duas fontes sinalizadas; dois links oficiais permanecem indisponíveis. A matriz oficial pode ser recuperada pelo manifesto e o banco local pode ser montado somente para leitura. Evidências e limites da integração estão em [banco e classificação](../banco-classificacao.md#validação-da-integração).

Em 01/11/2026, o acervo processado recebido foi incorporado: a instalação local tem 98 provas e 8.730 questões. As 96 provas automáticas passaram pela conferência de fontes, gabaritos, LaTeX e figuras e pelo ensaio integral de resolução em uma cópia isolada. Permanecem 506 pendências de apresentação em 489 questões, para as etapas 3 e 8. [Registro e limites](../banco-classificacao.md#incorporação-do-acervo-processado).

A [revisão de consistência](../revisoes/revisao-projeto-2026-11-01.md#fechamento-das-correções) encontrou e corrigiu cinco falhas em auditoria de preparo, identificação de clientes no Docker, deduplicação durante edição/publicação, publicação posterior do catálogo e recuperação de senha com sessão ativa. Foram aprovados 97 testes em cada banco e 28 testes de navegador, além do ensaio real de proxy e persistência. A próxima frente permanece a etapa 3; a curadoria permanece na etapa 8.

## 3. Iniciar os experimentos de Dados e IA

**Próxima frente de desenvolvimento. Dependências: contratos da etapa 2 e a referência técnica `adaptive-math-reference-v1`. A revisão humana das amostras fica na etapa 8. Duas frentes podem avançar em paralelo.**

### Classificação temática

- Estabelecer uma referência simples, como regras ou as anotações técnicas existentes.
- Comparar classificadores supervisionados, representações de texto e LLMs conforme os dados disponíveis.
- Separar desenvolvimento e teste depois da deduplicação; manter variantes do mesmo item no mesmo conjunto.
- Medir precisão, revocação, F1 por classe, consistência, latência, custo e tipos de erro.
- Definir, com base nas medições, quais propostas seguirão para a revisão da etapa 8, preservando a origem dos rótulos propostos.

### Análise de layout

O material principal são as provas publicadas automaticamente e seus relatórios de pendências. O agrupamento e a classificação dos blocos usam modelos clássicos.

- Anotar blocos, páginas, posições, agrupamentos, ordem de leitura e associação das imagens e alternativas.
- Comparar extração de coordenadas, regras de geometria, reconstrução de fontes com codificação quebrada, OCR e métodos visuais quando necessários.
- Reservar exemplos difíceis e padrões de layout para avaliação independente.
- Reduzir as pendências das provas publicadas: separar alternativas, estruturar tabelas mescladas e relações espaciais, reconstruir fontes com codificação quebrada e recuperar o gabarito marcado visualmente em 2010.
- Medir localização, ordem, vínculos, integridade e tempo de correção humana.

**Critério de aceite:** cada frente entrega dados no contrato acordado, comparação com uma referência, configuração versionada, métricas reproduzíveis e casos de erro. Propostas automáticas ficam como propostas até a curadoria da etapa 8.

## 4. Implementar diagnóstico e estado por habilidade

**Dependências: histórico consistente e os rótulos já publicados (disciplina e tema de curadoria técnica). As habilidades revisadas entram quando a etapa 8 as publicar; até lá, o estado é calculado por tema. Frente principal: Plataforma.**

1. Criar sessões de diagnóstico com objetivo, área e tempo disponível.
2. Distribuir os itens pelos temas disponíveis e registrar a quantidade de evidência por tema e, quando houver, por habilidade.
3. Manter tentativas recentes, acertos independentes, itens vistos e última prática.
4. Implementar e avaliar um estimador explicável. O plano sugere uma taxa suavizada ou Beta-Binomial; com prior Beta(1,1), a média seria `(1 + acertos) / (2 + tentativas)`.
5. Mostrar quando há poucas respostas para sustentar uma interpretação e separar desempenho independente de desempenho assistido.

**Critério de aceite:** o estado do aluno pode ser reconstruído a partir de eventos e versões, informa a quantidade de evidência e respeita o momento de finalização das provas.

## 5. Integrar uma política adaptativa inicial

**Dependência: etapa 4 e itens elegíveis com os rótulos disponíveis. A política funciona por tema e incorpora habilidades quando a etapa 8 as publicar. Frente conjunta.**

1. Definir os filtros de área, integridade, tema/habilidade, exposição e dificuldade provisória.
2. Combinar reforço, revisão e exploração com parâmetros explícitos.
3. Registrar candidatos, componentes da prioridade, escolha, justificativa e versão da política.
4. Controlar repetição e concentração da prática em poucos itens.
5. Comparar o comportamento com seleção aleatória e uma referência simples de reforço.

**Critério de aceite:** cada recomendação tem um motivo compreensível e um registro que permite auditar a seleção; cobertura e exposição foram avaliadas nos cenários definidos.

## 6. Integrar tutor e layouts dinâmicos

Essas integrações podem ser liberadas de forma independente, conforme suas evidências de qualidade. O conteúdo que elas produzem (resoluções, pistas e agrupamentos) é aprovado na etapa 8.

| Integração | Próximo trabalho | Critério de liberação |
| --- | --- | --- |
| Tutor com LLM | Preparar resoluções e pistas; recuperar referências; definir níveis de ajuda, validação e ferramentas limitadas; registrar ajuda utilizada, versões, custo e latência. | Avaliação com casos de teste, respeito à etapa de ajuda e continuidade com conteúdo publicado quando o provedor falhar. |
| Layouts dinâmicos | Consumir agrupamentos e relações espaciais extraídos, preservando texto nativo, ordem de leitura e vínculos em desktop e celular. | Comparação visual com o original e ausência de cortes, inversões e relações perdidas nos layouts de avaliação. |

## 7. Expandir o produto e a pesquisa

Após estabilizar as integrações, preservar no backlog:

- Cobertura das quatro áreas e dos anos e aplicações definidos pelo projeto, com a importação revisada na etapa 8.
- Turmas, atividades e visão agregada para docentes, com regras próprias de acesso e tratamento de dados.
- Predição de acerto, knowledge tracing, dificuldade calibrada e políticas avançadas com referências e protocolos de avaliação.
- Multimodalidade, análise do raciocínio escrito e exercícios gerados com revisão.
- Treinamento ou ajuste de modelos quando houver dados e recursos suficientes, com artefato, documentação e avaliação; publicação no Hugging Face quando aplicável.
- Estudo educacional com pré e pós-teste, itens novos e comparáveis, condição de referência e acompanhamento de retenção.

**Critério de aceite por incremento:** comportamento executável, decisões rastreáveis e resultados correspondentes às medições realizadas. O conteúdo novo é revisado na etapa 8.

## 8. Curadoria do conteúdo e dos rótulos

**Etapa final de desenvolvimento, que reúne toda a curadoria do projeto. Dependências: parte técnica das etapas 2 a 7 e revisores independentes. Frente conjunta.**

1. **Revisão pedagógica independente dos lotes publicados.** São os 90 itens de 2024 e os 45 de 2023. O revisor compara enunciados, fórmulas, tabelas, figuras, alternativas e gabaritos com a fonte, registra divergências e aprova as correções por novas versões.
2. **Revisão das provas publicadas automaticamente e de novos cadernos.** Escolher entre os cadernos preparados no ensaio e resolver as pendências bloqueantes (tabelas mescladas, relações espaciais, alternativas com várias figuras) e os avisos, como as descrições de figuras. Depois, importar, aprovar e publicar. Cadernos com codificação quebrada usam outra cor legível ou o mapeamento reconstruído.
3. **Segunda anotação independente** de disciplina, tema e habilidades, sem consultar a primeira decisão. Registrar `question_id`, hash da versão, rótulos, evidência, justificativa e revisor; medir concordância; discutir e adjudicar as divergências, como as 139/2023, 163/2023 e itens interdisciplinares de Natureza.
4. **Publicação das habilidades adjudicadas** por novas versões, atualizando a referência, a cobertura do painel e o protocolo experimental. As decisões anteriores ficam preservadas para auditoria.
5. **Aprovação das propostas automáticas** das etapas 3 a 7: rótulos sugeridos, agrupamentos de layout, resoluções e pistas do tutor.
6. **Curadoria assistida.** Detectar falhas de extração, recursos ausentes, duplicatas e inconsistências e propor correções com evidência para revisão humana. Os falsos positivos são medidos, as alterações são rastreáveis e reversíveis, e mudanças que afetam a resposta têm revisão reforçada.

**Critério de aceite:** o conteúdo publicado foi revisado por pessoa independente, as habilidades publicadas têm segunda anotação e adjudicação registradas, e nenhuma proposta automática entra no conteúdo sem aprovação rastreável.

## 9. Publicar uma versão para o piloto

**Dependências: curadoria da etapa 8, aceites externos listados no final deste documento e validação dos incrementos priorizados nas etapas 2 a 7. Frente principal: Plataforma.**

1. Definir o ambiente de hospedagem e configurar domínio, HTTPS e origens autorizadas.
2. Provisionar PostgreSQL e armazenamento persistente para os recursos das questões.
3. Aplicar as migrações e importar o conjunto revisado; conferir os papéis de aluno e curadoria.
4. Validar a recuperação assistida de acesso e os registros de falhas e latência.
5. Fazer backup e ensaiar a restauração nesse ambiente, preservando banco, versões e arquivos associados.
6. Publicar uma identificação da versão e atualizar o README e o vídeo com o endereço da demonstração.

**Critério de aceite:** a aplicação publicada preserva uma tentativa após reinício dos serviços, permite recuperar os dados de um backup e mantém o acesso individual ao histórico.

## 10. Executar o piloto e ajustar a experiência

**Dependência: versão utilizável da etapa 9. Frente conjunta.**

1. Convidar aproximadamente 5–10 estudantes adultos, conforme a proposta exploratória do plano.
2. Observar entrada na conta, localização da prova, marcação e alteração de resposta, retomada e consulta do resultado.
3. Registrar conclusão das tarefas, falhas, dificuldades, abandono e clareza do painel.
4. Priorizar e corrigir os problemas observados, preservando as tentativas existentes.
5. Produzir um relato com a versão testada, quantidade de participantes, resultados e limitações.

**Critério de aceite:** os problemas encontrados têm encaminhamento registrado e existe um relato reproduzível do funcionamento e da usabilidade. A investigação de ganho de aprendizagem terá protocolo próprio em uma etapa posterior.

## Primeiro bloco de trabalho recomendado

Iniciar a etapa 3 com a referência técnica de 89 questões de Matemática: uma linha de base de classificação temática e a anotação de layout dos cadernos já preparados no ensaio. Encaminhar em paralelo os testes manuais de acessibilidade descritos no final. A curadoria fica para a etapa 8; publicação e piloto, para as etapas 9 e 10.

## Pendências e melhorias

Itens fora das etapas, sem data, para retomar quando houver oportunidade.

| Item | O que fazer | Por quê |
| --- | --- | --- |
| Integrar a checagem das provas geradas ao fluxo | O ensaio integral foi executado em 01/11/2026 nas 96 provas, com respostas pelo gabarito e finalização idempotente, usando uma cópia isolada. Transformá-lo em comando versionado após `make acervo`, incluindo fontes, língua, figuras e texto ilegível; pular em clones sem o acervo. | A validação deste lote está registrada, mas a execução ainda precisa ser incorporada ao fluxo reutilizável. O teste verifica instalação/correção; a fidelidade visual e pedagógica continua na etapa 8. |

## Referências locais

- [Estado atual e pendências](status-implementacao.md)
- [Plano original](enem_adaptativo_plano_do_projeto.md)
- [Critérios da primeira entrega](../primeira-entrega.md)
- [Arquitetura e contratos](../architecture.md)
- [Implantação, backup e recuperação](../operations.md)
- [Preparação e origem do banco](../../data/README.md)

## Pendências externas da primeira entrega

Estas atividades foram retiradas da etapa técnica porque exigem tecnologias assistivas ou aparelhos indisponíveis para a execução automatizada. **Apesar de estarem no final do documento, são critérios de liberação anteriores à publicação e ao piloto.** A revisão pedagógica independente, antes listada aqui, faz parte da [curadoria](#8-curadoria-do-conteúdo-e-dos-rótulos).

| Pendência | Por que não foi concluída aqui | Critério de conclusão |
| --- | --- | --- |
| Leitores de tela e descrições científicas | Axe, MathML, nomes acessíveis e testes de foco não verificam a experiência falada nem a interpretação de gráficos por uma pessoa usuária de tecnologia assistiva. | Conferir cadastro, resolução, química/matemática falada, tabelas, legendas, ampliação e resultado com leitor de tela real; corrigir e registrar os casos encontrados. |
| Aparelhos reais e zoom do navegador | Os testes de celular usam viewport emulado no Chrome; não há interação física com telefones, Safari/iOS ou recursos de ampliação do sistema. | Executar a jornada em Android e iPhone e conferir teclado/zoom do navegador no desktop; registrar aparelho, navegador, versão, tarefas e resultados. |

O roteiro de execução manual e as evidências automáticas estão em [primeira entrega](../primeira-entrega.md). Nenhuma dessas pendências foi marcada como concluída, piloto realizado ou evidência de aprendizagem.
