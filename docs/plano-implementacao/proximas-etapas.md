# Próximas etapas

Atualizado em **04/11/2026**. Este roteiro parte do [status da implementação](status-implementacao.md) e organiza a continuidade do [plano do projeto](enem_adaptativo_plano_do_projeto.md).

As etapas abaixo são propostas de execução, com dependências e critérios de aceite. **Curadoria, publicação e piloto não fazem parte deste roteiro.** As etapas 2 a 7 usam o conteúdo já publicado e os rótulos de curadoria técnica, sem esperar revisões. O marco de 15/11/2026 permanece como referência do PDF; a definição das datas operacionais depende da capacidade disponível e das evidências de cada entrega.

## 1. Consolidar a primeira entrega

**Consolidação técnica concluída em 31/10/2026.** A revisão pedagógica independente e os aceites que dependem de aparelhos ou tecnologias assistivas não foram realizados; os roteiros manuais estão em [primeira entrega](../primeira-entrega.md#aceites-manuais-ainda-necessários).

- [x] Conferir integridade dos 90 itens, gabarito oficial, anulação, hashes das fontes e recursos; compilar as 150 expressões LaTeX do caderno publicado.
- [x] Corrigir o lote de 15 questões com novas versões e justificativas; preservar respostas, resultados e snapshots anteriores.
- [x] Integrar preparação generalizada, curadoria, navegação, figuras e LaTeX na mesma regressão.
- [x] Executar 57 testes de API em SQLite e 57 em PostgreSQL, com migrações e alinhamento de esquema verificados.
- [x] Construir e iniciar uma instalação isolada com dependências instaladas do zero, Compose, PostgreSQL e volumes persistentes. Substituir os contêineres e conferir login, resposta, resultado, histórico, 90 snapshots e arquivos próprios.
- [x] Ensaiar backup/restauração de SQLite e PostgreSQL sem alterar o banco de uso da aplicação.
- [x] Conferir as 90 questões em desktop e viewport móvel; verificar teclado, foco, diálogos, ampliação de figuras e reflow em larguras reduzidas. Corrigir contraste, nomes acessíveis e hierarquia de títulos encontrados pela auditoria automatizada.
- [x] Revisar os arquivos, registrar commits por decisão lógica e incluir verificações de conteúdo, acessibilidade e persistência de contêineres no CI. As execuções da versão estão vinculadas nas [evidências](../primeira-entrega.md).

**Resultado:** a base técnica da primeira entrega está consolidada. Isso não equivale à revisão pedagógica independente nem à validação de uso em aparelhos reais.

O registro completo de procedimentos e limites está em [primeira entrega](../primeira-entrega.md) e [operação](../operations.md). A comparação do lote de apresentação com a fonte permanece em [origem do conteúdo](../../data/README.md#revisão-de-apresentação).

## 2. Ampliar o banco e a classificação

**Parte técnica concluída em 31/10/2026.** A implementação está descrita em [banco e classificação](../banco-classificacao.md) e no [ensaio da preparação](../preparacao-provas.md#ensaio-em-outros-layouts).

- [x] **1. Definir os próximos cadernos, anos e aplicações**, mantendo explícita a cobertura disponível. O acervo oficial de 1998–2025 está inventariado, com [cobertura](../cobertura-acervo.md). A seção de Matemática azul de 2023 foi incorporada, e o ensaio deixou 7 cadernos legíveis de outros layouts preparados como candidatos.
- [x] **2. Validar e ampliar a preparação generalizada** com novos cadernos. O [ensaio](../preparacao-provas.md#ensaio-em-outros-layouts) com `scripts/trial_preparation.py` preparou cadernos de 1º e 2º dia, PPL e anos de 2012 a 2024, todos com 90 questões. O adaptador passou a tratar:
  - a opção de língua pelo manifesto;
  - alternativas em grade;
  - marca d'água girada e faixas decorativas;
  - linhas duplicadas pela camada acessível;
  - cabeçalhos com letras e números espaçados, pela mesma regra usada no banco textual;
  - a ordem das áreas de 2009 e os metadados compartilhados entre ensaio e geração;
  - moedas como `US$`;
  - texto com codificação quebrada, que é bloqueado.

  Nos cadernos legíveis restam 1 a 8 pendências bloqueantes, em geral tabelas mescladas e relações espaciais. Os 34 PDFs com codificação quebrada (7% do acervo, sobretudo 2021) podem ser preparados por outra cor legível quando ela existe. Sem cor legível, é preciso reconstruir o mapeamento da fonte ou usar OCR.
- [x] **3. Identificar questões repetidas entre cores** e preservar um identificador canônico com suas ocorrências. `canonical_questions` guarda a identidade. Os 135 itens conferidos estão vinculados às quatro cores da aplicação (540 ocorrências), com texto, pareamento único, gabarito oficial de cada cor e figuras conferidos. A importação de outra cor reaproveita a identidade e recusa gabarito divergente. No restante do acervo, só texto idêntico é agrupado automaticamente.
- [x] **4. Definir uma taxonomia versionada** de disciplinas e temas, separada das competências e habilidades oficiais: `enem-content-v1` e matriz oficial de Matemática.
- [x] **5. Anotar uma amostra de referência** com evidências dos vínculos com habilidades: 135 anotações técnicas e 90 habilidades candidatas.
- [x] **6. Publicar os rótulos** para que o painel mostre recortes com cobertura útil: disciplina e tema publicados, com a cobertura real no painel.
- [x] **Publicação automática do acervo (decisão de 31/10/2026).** As provas de 2009 a 2025 podem ser geradas e publicadas sem curadoria com `make acervo`. O ensaio inicial registrou 96 provas, 8.595 questões e 506 pendências; os arquivos ficam locais, fora do Git. Os detalhes estão em [publicação automática](../preparacao-provas.md#publicação-automática-do-acervo). O site identifica a origem automática e as pendências conhecidas; o fluxo manual mantém seus bloqueios. A melhoria da extração fica para a etapa 3; a conferência não foi realizada.
- [x] **7. Construir o conjunto inicial dos experimentos adaptativos:** `adaptive-math-reference-v1` tem 89 questões válidas de Matemática em oito temas, dentro da referência de 80–150 questões em 6–8 temas.

**Critério de aceite:** o novo conteúdo tem origem e versões rastreáveis, não duplica itens canônicos e apresenta a cobertura real dos rótulos no painel. Testes verificam esses pontos, inclusive a ausência de duplicação entre cores.

**Base disponível:**
- preparação: módulo `backend/app/preparation/`, CLI `scripts/prepare_exam.py`, adaptador `scripts/exam_pdf.py`, manifesto de exemplo e ensaio `scripts/trial_preparation.py`;
- acervo e banco textual: `scripts/archive_enem.py` e `scripts/build_bank.py`;
- vínculo entre cores: `scripts/link_booklets.py`.

A normalização usa regras e contexto, sem depender dos números das questões. Notação perdida e estruturas ambíguas continuam sinalizadas.

A integração das duas frentes preserva os vínculos entre cores e os relatórios de preparação ao acrescentar classificação. O índice reconstruído reúne 44.524 ocorrências e 43.439 identidades conservadoras, com duas fontes sinalizadas; dois links oficiais permanecem indisponíveis. A matriz oficial pode ser recuperada pelo manifesto e o banco local pode ser montado somente para leitura. Evidências e limites da integração estão em [banco e classificação](../banco-classificacao.md#validação-da-integração).

Em 01/11/2026, o acervo processado recebido foi incorporado: a instalação local tem 98 provas e 8.730 questões. As 96 provas automáticas passaram pela conferência de fontes, gabaritos, LaTeX e figuras e pelo ensaio integral de resolução em uma cópia isolada. Permanecem 506 pendências de apresentação em 489 questões. [Registro e limites](../banco-classificacao.md#incorporação-do-acervo-processado).

A [revisão de consistência](../revisoes/revisao-projeto-2026-11-01.md#fechamento-das-correções) encontrou e corrigiu cinco falhas em auditoria de preparo, identificação de clientes no Docker, deduplicação durante edição/publicação, publicação posterior do catálogo e recuperação de senha com sessão ativa. Foram aprovados 97 testes em cada banco e 28 testes de navegador, além do ensaio real de proxy e persistência.

## 3. Iniciar os experimentos de Dados e IA

**Primeiro ciclo técnico implementado e executado em 03/11/2026.** As duas frentes têm configuração, dados, contratos, métricas e casos de erro reproduzíveis. O [guia dos experimentos](../experimentos/README.md) reúne comandos e limites; os [resultados medidos](../experimentos/resultados-2026-11-03.json) registram a execução. A revisão independente e a aprovação das propostas não foram realizadas.

A [extensão de auditoria integral](../experimentos/auditoria-acervo.md) percorreu as 98 provas/8.730 posições publicadas, com duas leituras independentes de gabarito, comparação de recursos, ensaio de correção e validação no navegador. Passaram 294 cenários de resultado e os gabaritos coincidiram integralmente. A aplicação dos métodos produziu 99.187 blocos e 2.017 propostas temáticas de Matemática. Foram instaladas 993 novas versões, preservando as sete tabelas de dados protegidos e a revisão independente pendente. A inspeção automatizada concluiu as 17.460 apresentações em desktop/celular e nos dois temas, com 1.070 capturas e nenhuma falha detectada pelos verificadores de renderização. Permanecem 928 diagnósticos de preparação em 441 posições, além dos achados de triagem e identidade, sem adjudicação.

`make experiments` compara cinco métodos temáticos nos 89 itens de Matemática e três métodos de layout numa amostra técnica de 13 questões/145 blocos. `make experiments-archive` acrescenta as propostas de recuperação dos cadernos locais, fontes e gabarito visual; não publica conteúdo nem altera o banco de uso. As saídas incluem modelos em JSON, partições, previsões, matrizes de confusão, métricas por classe, latências, custos declarados e uma revisão visual com registro explícito de tempo humano.

O ciclo local escolheu palavras-chave pelo desenvolvimento (macro-F1 0,649; teste 0,501) e geometria para layout. A varredura dos 96 cadernos produziu candidatos para 84 pendências de alternativas e 68 de tabelas mescladas; as 506 pendências originais permanecem registradas. A amostra do gabarito visual coincidiu em 11/11 respostas conferidas. OCR e hipóteses de fontes permanecem propostas, com erros residuais medidos. O comparador de LLM aceita previsões externas com proveniência; nenhuma chamada a provedor foi executada. Esses resultados não constituem benchmark independente ou liberação automática.

### Classificação temática

- [x] Estabelecer uma referência simples com as anotações técnicas existentes: 89 itens válidos de Matemática, em oito temas.
- [x] Comparar cinco métodos locais: maioria, palavras-chave, Naive Bayes e centróides TF-IDF de palavras e caracteres.
- [x] Separar treino, desenvolvimento e teste depois do agrupamento por identidade; manter variantes do mesmo item no mesmo conjunto.
- [x] Medir precisão, revocação, F1 por classe, consistência, latência, custo externo e tipos de erro, registrando custos locais não medidos.
- [x] Selecionar o método pelo desenvolvimento e gerar propostas rastreáveis para revisão, preservando a origem dos rótulos e sem promovê-los ao conteúdo publicado.
- [x] Disponibilizar contrato, exportação de entradas e comparador para previsões externas de LLM com proveniência.

### Análise de layout

O material principal são as provas publicadas automaticamente e seus relatórios de pendências. O agrupamento e a classificação dos blocos usam modelos clássicos.

- [x] Anotar uma referência técnica assistida com 13 questões e 145 blocos, incluindo páginas, posições, agrupamentos, ordem de leitura e associação das imagens e alternativas.
- [x] Comparar extração de coordenadas, regras de geometria e CART; experimentar mapeamento de fontes, OCR local e leitura visual de gabarito, com os erros e limites registrados.
- [x] Reservar exemplos difíceis em uma partição de teste separada, com seis questões; a referência continua assistida, sem adjudicação independente.
- [x] Implementar propostas de recuperação de alternativas, tabelas mescladas, relações espaciais, fontes e gabaritos visuais, preservando as ambiguidades.
- [x] Aplicar os métodos selecionados às 8.730 posições publicadas e registrar propostas por versão e fonte.
- [x] Instalar 993 correções técnicas verificadas, incluindo 63 gabaritos, preservando versões, tentativas e resultados anteriores.
- [x] Medir localização, ordem, vínculos, integridade e latência; disponibilizar revisão visual e contrato para registrar correção humana.

**Critério de aceite:** cada frente entrega dados no contrato acordado, comparação com uma referência, configuração versionada, métricas reproduzíveis e casos de erro. Propostas automáticas continuam como propostas, sem entrar no conteúdo publicado.

## 4. Implementar diagnóstico e estado por habilidade

**Implementação técnica concluída em 04/11/2026.** Contratos, parâmetros, avaliação sintética e verificações em [diagnóstico e estado](../diagnostico-estado.md).

**Dependências: histórico consistente e os rótulos já publicados (disciplina e tema de curadoria técnica). As habilidades entram quando forem publicadas; até lá, o estado é calculado por tema. Frente principal: Plataforma.**

- [x] **1.** Criar sessões de diagnóstico com objetivo, área e tempo disponível.
- [x] **2.** Distribuir os itens pelos temas disponíveis e registrar a quantidade de evidência por tema e, quando houver, por habilidade.
- [x] **3.** Manter tentativas recentes, acertos independentes, itens vistos e última prática.
- [x] **4.** Implementar e avaliar um estimador explicável. O plano sugere uma taxa suavizada ou Beta-Binomial; com prior Beta(1,1), a média seria `(1 + acertos) / (2 + tentativas)`.
- [x] **5.** Mostrar quando há poucas respostas para sustentar uma interpretação e separar desempenho independente de desempenho assistido.

**Critério de aceite:** o estado do aluno pode ser reconstruído a partir de eventos e versões, informa a quantidade de evidência e respeita o momento de finalização das provas.

## 5. Integrar uma política adaptativa inicial

**Dependência: etapa 4 e itens elegíveis com os rótulos disponíveis. A política funciona por tema e incorpora habilidades quando forem publicadas. Frente conjunta.**

1. Definir os filtros de área, integridade, tema/habilidade, exposição e dificuldade provisória.
2. Combinar reforço, revisão e exploração com parâmetros explícitos.
3. Registrar candidatos, componentes da prioridade, escolha, justificativa e versão da política.
4. Controlar repetição e concentração da prática em poucos itens.
5. Comparar o comportamento com seleção aleatória e uma referência simples de reforço.

**Critério de aceite:** cada recomendação tem um motivo compreensível e um registro que permite auditar a seleção; cobertura e exposição foram avaliadas nos cenários definidos.

## 6. Integrar tutor e layouts dinâmicos

Essas integrações podem ser liberadas de forma independente, conforme suas evidências de qualidade. O conteúdo que elas produzem (resoluções, pistas e agrupamentos) continua como proposta até ser aprovado por uma pessoa.

| Integração | Próximo trabalho | Critério de liberação |
| --- | --- | --- |
| Tutor com LLM | Preparar resoluções e pistas; recuperar referências; definir níveis de ajuda, validação e ferramentas limitadas; registrar ajuda utilizada, versões, custo e latência. | Avaliação com casos de teste, respeito à etapa de ajuda e continuidade com conteúdo publicado quando o provedor falhar. |
| Layouts dinâmicos | Consumir agrupamentos e relações espaciais extraídos, preservando texto nativo, ordem de leitura e vínculos em desktop e celular. | Comparação visual com o original e ausência de cortes, inversões e relações perdidas nos layouts de avaliação. |

## 7. Expandir o produto e a pesquisa

Após estabilizar as integrações, preservar no backlog:

- Cobertura das quatro áreas e dos anos e aplicações definidos pelo projeto.
- Turmas, atividades e visão agregada para docentes, com regras próprias de acesso e tratamento de dados.
- Predição de acerto, knowledge tracing, dificuldade calibrada e políticas avançadas com referências e protocolos de avaliação.
- Multimodalidade, análise do raciocínio escrito e exercícios gerados com revisão.
- Treinamento ou ajuste de modelos quando houver dados e recursos suficientes, com artefato, documentação e avaliação; publicação no Hugging Face quando aplicável.
- Estudo educacional com pré e pós-teste, itens novos e comparáveis, condição de referência e acompanhamento de retenção.

**Critério de aceite por incremento:** comportamento executável, decisões rastreáveis e resultados correspondentes às medições realizadas. O conteúdo novo continua sujeito a revisão.

## Pendências e melhorias

Itens fora das etapas, sem data, para retomar quando houver oportunidade.

| Item | O que fazer | Por quê |
| --- | --- | --- |
| Regras de domínio sem dependência de HTTP | Trocar o `HTTPException` lançado por `services/` e `installers/` (conteúdo, identidade canônica e lotes conferidos) por exceções de domínio, como conflito e não encontrado. Um tratador em `main.py` as converte nos mesmos códigos e mensagens de hoje. Verificar com os testes de 401, 404, 409, 422 e 429 e com uma comparação das respostas de erro antes e depois. | Esses módulos também são usados pela CLI e pelos scripts, onde não há requisição HTTP. É a fase 2 da reorganização do backend, cuja fase 1 dividiu o código em `core/`, `models/`, `schemas/`, `services/` e `installers/`. |
| Rotas reais do App Router | Trocar a escolha de página em `app.tsx`, sobre a rota `[[...path]]`, por rotas próprias do Next.js. | Fica fora da refatoração porque muda a estrutura de navegação e carregamento das páginas. |

## Referências locais

- [Estado atual e pendências](status-implementacao.md)
- [Plano original](enem_adaptativo_plano_do_projeto.md)
- [Critérios da primeira entrega](../primeira-entrega.md)
- [Arquitetura e contratos](../architecture.md)
- [Implantação, backup e recuperação](../operations.md)
- [Preparação e origem do banco](../../data/README.md)

