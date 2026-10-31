# Conjunto inicial

Inclui o caderno completo do segundo dia do ENEM 2024, aplicação regular, caderno 7 azul, com as 90 questões de 91 a 180. Não representa os dois dias nem todos os anos do ENEM. São 45 questões de Ciências da Natureza e 45 de Matemática.

Fontes primárias:

- [Caderno oficial do Inep](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D2_CD7.pdf)
- [Gabarito oficial correspondente](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D2_CD7.pdf)
- [Catálogo do Inep para 2024](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/2024)

Os PDFs ficam em `sources/`. O arquivo JSON guarda URLs, hashes SHA-256, página, numeração, gabarito, identificador canônico, rótulos e os retângulos em pontos PDF (origem no canto superior esquerdo). As imagens ficam em `assets/`. O gabarito e o JSON não são servidos como arquivos públicos pela aplicação.

## Apresentação e conferência

A fonte dos enunciados e das alternativas é o próprio JSON. Cada questão contém blocos tipados de parágrafo, imagem, tabela ou fórmula. O site renderiza os textos como HTML selecionável, as tabelas como tabelas reais e as expressões matemáticas com KaTeX e MathML. Imagens ficam restritas a fotografias, quadrinhos, gráficos, esquemas e diagramas das alternativas. O caderno não é exibido como uma imagem de texto.

Foram conferidos os 90 números únicos, a sequência, a correspondência de cada resposta com o gabarito oficial e a presença dos recursos. A transcrição inicial foi separada em enunciados e cinco alternativas reais. As tabelas foram estruturadas a partir dos dados do JSON; frações, raízes, potências e expressões cuja extração perdeu a disposição espacial foram conferidas com o original e normalizadas. Gráficos das alternativas continuam vinculados às opções A–E. A extração anterior e os 92 recortes integrais ficam preservados para rastreabilidade de versões antigas, mas não são usados como apresentação do enunciado.

A questão **129 é anulada**. Seu gabarito é `null` e `annulled=true`; ela não entra no denominador, nos acertos, nos erros nem na cobertura dos rótulos. Não se calcula nota TRI.

A área vem do caderno oficial; as questões 136–180 recebem a disciplina Matemática. Natureza não recebe subdivisão automática em Física, Química ou Biologia. Temas e habilidades oficiais estão vazios, explicitamente aguardando anotação e revisão. Não houve validação pedagógica independente, experimento de classificação ou estudo de ganho de aprendizagem.

## Estruturar o JSON

```bash
.venv/bin/python scripts/structure_questions.py
```

O comando lê `data/sources/enem-2024-dia2-azul-extraction.json`, a cópia preservada da transcrição inicial. Todo o texto vem desse JSON. O PDF associado é consultado apenas para isolar fotografias e diagramas; os enunciados não são rasterizados. O resultado estruturado fica em `data/enem-2024-dia2-azul.json` e as figuras isoladas em `assets/enem-2024-dia2-azul/native/`.

Para reconstruir a transcrição bruta a partir da fonte oficial, existe também o comando inicial:

```bash
.venv/bin/python scripts/import_official.py
```

É necessário instalar `backend/requirements-dev.lock`. A preparação ocorre fora das requisições do aluno. Os scripts são específicos desse caderno; outros anos exigem conferir suas particularidades de layout. A extração bruta falha se não encontrar exatamente os 90 itens e os 90 registros de gabarito. Após executá-la, aplique a estruturação do JSON para recuperar a apresentação nativa.

```bash
.venv/bin/python -m backend.app.cli seed
```

Importa o conjunto como rascunho. `seed --publish-reviewed` publica exclusivamente o conjunto incluído após registrar as decisões de conferência com uma identidade técnica sem senha conhecida. Para atualizar uma instalação com os recortes antigos, use `seed --publish-reviewed --refresh-bundled`: ele confere a assinatura da transcrição e cria novas versões sem modificar respostas, snapshots ou resultados. Edições próprias são recusadas e exigem revisão manual. Repetir o comando com o mesmo JSON não cria versões adicionais.

Tentativas antigas cuja transcrição coincide exatamente com a incluída também recebem a apresentação nativa na leitura, mantendo os mesmos identificadores, conteúdo de avaliação, gabarito e resultados. Essa adaptação de apresentação não grava alterações no histórico. Uma transcrição com edição própria não é substituída.

Novos arquivos podem ser importados pela interface de curadoria conforme `docs/content-schema.json`. Recursos de imagem referenciados precisam estar em `data/assets/` antes da importação; o MVP não faz download de URLs arbitrárias nem recebe upload de imagens. A URL do PDF de origem continua disponível para comparação. Novos cadernos podem reutilizar o mesmo identificador canônico quando o conteúdo é idêntico; a conferência de duplicatas semânticas é manual nesta entrega.

## Origem e direitos

Preservam-se as referências e os créditos contidos nas questões oficiais. A licença MIT do código não se estende automaticamente aos textos e às imagens desses documentos. Não foi atribuída uma licença aberta nova ao conteúdo de terceiros. Os PDFs originais permitem conferir os avisos e a procedência; alterações e futuras erratas devem criar versões, sem substituir tentativas antigas. A plataforma não é um produto oficial do Inep.
