# Preparação de novas provas

O preparador comum não tem regras por ano ou número de questão. O caderno já publicado mantém sua transcrição conferida; este incremento não o substitui por uma extração automática.

## Importar JSON pela curadoria

**Importar JSON** executa automaticamente o preparador antes de criar o rascunho. Salvar uma correção também prepara a nova versão:

1. Valida o contrato e preserva numeração, área, rótulos, gabarito, anulação e letras das alternativas.
2. Preserva LaTeX explícito e converte notação reconhecível: índices, cargas em sobrescrito, espécies químicas, reações, unidades, porcentagens, notação científica e alternativas com frações simples.
3. Associa equações, legendas e referências adjacentes às figuras. Parágrafos com `role: body` são respeitados. Vínculos inferidos ficam sinalizados para conferência.
4. Registra transformações, hashes e pendências em `layout.preparation`. A curadoria mostra o relatório da versão selecionada; esses metadados não são enviados ao aluno.
5. Mantém o conteúdo em rascunho. Pendências bloqueantes impedem aprovação e publicação; avisos exigem a conferência humana que já faz parte da curadoria.

Corrija o conteúdo e salve uma nova versão para resolver pendências. Tentativas e versões anteriores permanecem preservadas. Uma prévia sem gravação está disponível para a curadoria em `POST /admin/imports/prepare`, com o mesmo corpo de `POST /admin/imports`; retorna `exam` e `report`.

## Preparar por comando

Instale `backend/requirements-dev.lock` e execute `npm ci` em `frontend/`. O comando usa o mesmo KaTeX/mhchem do site para compilar o LaTeX do JSON inteiro.

Para o JSON de qualquer prova, com blocos ou texto e alternativas:

```bash
.venv/bin/python scripts/prepare_exam.py \
  --input caminho/nova-prova.json \
  --output tmp/nova-prova-preparada.json
```

Gera também `tmp/nova-prova-preparada.report.json`. O comando não importa nem publica no banco. Depois de conferir a saída e disponibilizar os recursos em `data/assets/`, use **Importar JSON** na curadoria.

Se o JSON tiver regiões `content.layout.blocks[].page/bbox`, passe também `--pdf caminho/prova.pdf`. O hash deve coincidir com `source.sha256`. A extração reconstrói texto nativo e tabelas reconhecidas; recorta somente figuras, sem usar a imagem integral da questão como enunciado.

## Partir de um novo PDF

Copie [o manifesto de exemplo](../data/examples/manifesto-prova.json) e altere metadados, fontes, total esperado, áreas e layout. O exemplo usa os arquivos já incluídos:

```bash
.venv/bin/python scripts/prepare_exam.py \
  --manifest data/examples/manifesto-prova.json \
  --pdf data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/prova.pdf \
  --answer-key data/sources/enem/2024/regular/impresso/dia-2/caderno-7-azul/gabarito.pdf \
  --output tmp/exemplo-preparado.json
```

Este é um ensaio: o identificador do exemplo já existe no catálogo e a importação não substitui a prova publicada. Uma nova prova precisa de identificador e fontes próprios.

O manifesto declara:

- Metadados no contrato: `id`, `title`, `year`, `application`, `booklet`, `day`, `kind`, `expected_items`, `duration_minutes` e `source`.
- `areas`: intervalos `first`/`last`, uma `area` válida e `discipline` opcional. Temas e habilidades não são inventados.
- `layout`: páginas, limites em pontos PDF e `columns: "auto"` ou intervalos de coordenadas. `page_overrides` permite ajustar uma página sem editar código.
- Gabarito textual em `--answer-key` ou objeto `answers` com números e valores A–E/`null`. Com `answers`, forneça também `source.answer_key_sha256`.
- `language`: obrigatório quando o caderno tem opções de língua estrangeira, como as questões 1–5 do 1º dia desde 2017 ou 91–95 do 2º dia até 2016. Use `ingles` ou `espanhol`. Só a opção declarada é preparada, e os itens guardam a língua em `layout.language`.

Exemplo de configuração de layout:

```json
{
  "pages": [2, 31],
  "top": 64,
  "bottom": 746,
  "columns": "auto",
  "page_overrides": { "15": { "columns": [[31, 538]] } }
}
```

O adaptador identifica cabeçalhos textuais `QUESTÃO`/`QUESTAO`, mantém a ordem de colunas/páginas, recupera índices/cargas numéricos por posição e recorta componentes rasterizados/vetoriais. Tabelas com grade reconhecível viram dados HTML. Células mescladas e relações espaciais não resolvidas geram pendências.

Alternativas gráficas são separadas pelos marcadores A–E, inclusive em grade (A D / B E / C):

- Letras soltas, sem tabulação, valem como marcadores quando uma mesma fonte imprime exatamente A–E uma vez. Rótulos de pontos nas figuras usam a fonte do texto e nunca completam o conjunto.
- Uma figura ao lado de um único marcador fica inteira com ele. Só desenhos que abrangem várias letras são recortados por célula.

Também são descartados:

- textos girados que repetem uma unidade curta, como a marca d'água vertical com o nome do exame entre as colunas;
- faixas finas que ocupam mais da metade da altura da página, que são decoração de abertura de seção;
- linhas duplicadas na mesma posição pela camada acessível.

Siglas de moeda antes de `$` (`R$`, `US$`, `A$`) são texto, e não delimitadores de LaTeX.

Questões e gabarito devem coincidir exatamente com o total declarado. Cabeçalhos duplicados, áreas sobrepostas, hash divergente e gabaritos conflitantes interrompem a preparação. Opções de língua são reconhecidas pelos títulos "Questões de 01 a 05 (opção inglês)" e "(opção espanhol)". Sem `language`, ou com uma língua que o caderno não oferece, a preparação para e indica as opções encontradas. Quando faltam questões, a mensagem aponta os cabeçalhos que ficaram fora de `layout.top`/`layout.bottom`.

## Relatório e limites

O relatório lista operações e pendências por questão, com trecho, localização e gravidade. Não atribui aprovação nem uma confiança numérica artificial.

| Caso | Tratamento |
| --- | --- |
| `H₂O`, `Mg²⁺`, reações legíveis, índices e unidades | LaTeX preservando valores, coeficientes e sinais. |
| `Mg2+` ou carga genérica sem posição preservada | Preserva a escrita e sinaliza ambiguidade. |
| Estado `(I)` extraído | Preserva `I`, inclusive no rodapé LaTeX, e pede conferir se é `l`. |
| Expoente achatado, como `4,0 × 105` | Sinaliza; não inventa a potência `10^5`. |
| Fração/expressão espacial sem estrutura recuperável | Pede transcrição e comparação com a fonte. |
| Vínculo inferido de legenda/crédito | Associa e pede conferência. |
| Descrição automática com página/número | Pede descrição real do conteúdo; não inventa interpretação visual. |
| Imagem sem posição, recorte integral, alternativas não separadas ou tabela incompatível | Bloqueia aprovação até correção em nova versão. |
| Delimitadores/agrupamentos LaTeX incompletos | Bloqueia aprovação. O comando também compila o LaTeX com KaTeX. |
| Linha com codificação de texto quebrada (`garbled_text`) | Bloqueia aprovação; prepare por outra cor legível da mesma aplicação. |

Alternativas incorretas não são balanceadas nem corrigidas conceitualmente. Aprovar continua exigindo comparação com o original.

Entradas não são substituídas. Saídas existentes exigem `--force`, que também não permite escrever sobre uma entrada. Recursos têm nomes derivados do hash da fonte e do recorte. `--assets-root` permite preparar em diretório temporário; depois copie os recursos correspondentes para `data/assets/` antes da importação.

Código de saída `0`: preparação técnica concluída. Código `2`: erro ou pendência bloqueante; com `--strict`, avisos também retornam `2`. Quando possível, rascunho e relatório são gravados mesmo com pendências. Recursos ausentes são informados no relatório. LaTeX que não compila interrompe a saída e identifica a questão.

O adaptador lê a camada de texto do PDF: as letras e suas posições, que viram o JSON nativo exibido com o layout do site. Ele não usa OCR.

Os 480 PDFs de prova do acervo têm camada de texto; nenhum é digitalizado. Em 34 deles (7%), porém, a fonte não informa quais letras os glifos representam, e o texto extraído sai embaralhado, como `fÜ éîèÜèê`. Isso ocorre sobretudo em 2021, regular e PPL, e também em 2010, 2014, 2017 e 2018.

- O adaptador detecta essas linhas e bloqueia a questão com `garbled_text`.
- Como as cores da mesma aplicação trazem os mesmos itens, prepare por uma cor legível quando ela existir; o vínculo entre cores liga as ocorrências.
- Sem cor legível (2021, 2º dia regular e PPL; 2014, 3ª aplicação e PPL), é preciso reconstruir o mapeamento da fonte ou usar OCR. Em 2014, por exemplo, cada letra está deslocada de um valor fixo.

A interface continua recebendo JSON; não há upload de PDF nem interpretação visual por IA. O adaptador geométrico tem limites, apresentados no relatório.

## Ensaio em outros layouts

O ensaio executa a preparação em cadernos de anos, dias e aplicações diferentes, a partir do espelho local do acervo. Não importa nem publica nada: rascunhos, relatórios e figuras ficam em `tmp/ensaio-preparacao/`, junto de `resumo.json`.

```bash
.venv/bin/python scripts/trial_preparation.py
.venv/bin/python scripts/trial_preparation.py --years 2022 2024
```

Resultado em 31/10/2026, com margem superior de 64 pontos (45 em 2012) e páginas até o último cabeçalho de questão:

| Caderno | Questões | Bloqueantes | Alternativas gráficas | Bloqueantes por tipo |
| --- | ---: | ---: | ---: | --- |
| 2024, 1º dia azul, inglês | 90 | 1 | 0 | alternativa com duas figuras 1 |
| 2024, 1º dia azul, espanhol | 90 | 1 | 0 | alternativa com duas figuras 1 |
| 2024 PPL, 2º dia azul | 90 | 4 | 4 | células mescladas 3, layout espacial 1 |
| 2022, 2º dia azul | 90 | 8 | 4 | células mescladas 6, layout espacial 2 |
| 2021, 2º dia azul | 90 | 123 | 4 | codificação quebrada 95, LaTeX inválido 13, células mescladas 8, alternativas 4, layout espacial 3 |
| 2019, 2º dia azul | 90 | 7 | 2 | layout espacial 4, células mescladas 3 |
| 2017, 2º dia azul | 90 | 8 | 4 | layout espacial 5, células mescladas 3 |
| 2015, 2º dia azul, inglês | 90 | 3 | 2 | layout espacial 2, células mescladas 1 |
| 2012, 1º dia azul | 90 | 5 | 4 | layout espacial 4, alternativa com duas figuras 1 |

O caderno de 2021 tem codificação quebrada e serve para mostrar o bloqueio: sem ele, 2021 seria preparado em silêncio com enunciados ilegíveis. Nenhuma das 720 questões dos cadernos legíveis acusou codificação quebrada.

Antes das extensões deste ensaio, os cadernos com opção de língua (2024, 1º dia, e 2015) e o de 2012 nem chegavam ao relatório. 2022, 2019 e 2017 tinham 15, 14 e 10 pendências bloqueantes, por causa de alternativas em grade, letras duplicadas pela camada acessível e moedas como `US$` lidas como LaTeX. As 100 alternativas gráficas segmentadas foram conferidas contra a posição dos marcadores no PDF, sem divergências.

As pendências restantes são casos que exigem revisão humana: tabelas com células mescladas, relações espaciais e alternativas com mais de uma figura. Os avisos (descrições de figuras, vínculos inferidos e notação ambígua) também exigem conferência. Nenhum desses rascunhos foi importado ou revisado. A incorporação de um novo caderno ao catálogo depende da curadoria, prevista na [etapa 8 do roteiro](plano-implementacao/proximas-etapas.md#8-curadoria-do-conteúdo-e-dos-rótulos).

## Publicação automática do acervo

**Decisão de 31/10/2026:** as provas do acervo vão para o site sem curadoria. O tratamento de layout fica para a etapa 3, e a curadoria para a etapa 8 do [roteiro](plano-implementacao/proximas-etapas.md).

```bash
.venv/bin/python scripts/build_archive_exams.py          # gera JSON e figuras
.venv/bin/python -m backend.app.cli archive              # publica no banco
make acervo                                              # os dois passos
```

**Geração** (`scripts/build_archive_exams.py`):

- Uma prova por ano, aplicação, dia e língua, de 2009 em diante, no formato padrão.
- O caderno azul é preferido. Cadernos com codificação de texto quebrada são pulados. Se o gabarito do Inep não corresponder à prova (links trocados no site oficial), o gerador tenta a cor seguinte.
- O manifesto é montado automaticamente:
  - áreas da época: até 2016, Humanas e Natureza no 1º dia; desde 2017, Linguagens e Humanas;
  - duração da época;
  - margem superior a partir dos cabeçalhos;
  - páginas até a última questão;
  - uma prova para cada opção de língua.
- O gabarito é lido na coluna da língua escolhida, e respostas retificadas ("*A") são aceitas.
- Questões já conferidas não são geradas de novo: o 2º dia de 2024 fica de fora, e do 2º dia de 2023 sai só Ciências da Natureza.
- As saídas ficam em `data/derived/exams/<id>.json`, `<id>.report.json` e `resumo.json`, com as figuras em `data/assets/<id>/`, todas fora do Git.

**Publicação** (`backend.app.cli archive`):

- Importa, aprova e publica cada prova com a identidade de serviço, registrando o motivo "publicação automática sem curadoria".
- As pendências bloqueantes ficam nos relatórios das versões, mas não impedem a publicação. Só esse comando pode publicar com pendências; a API e a curadoria continuam bloqueando.
- Cada prova é publicada ou recusada sozinha, inclusive quando um JSON é inválido. Conteúdo e versões já existentes não são substituídos. Instalações automáticas antigas recebem apenas o registro de origem e revisão pendente quando ausente.
- O catálogo informa **Extração automática**, a resolução sinaliza que o caderno aguarda conferência e questões com erros conhecidos mostram vínculo à página original. A API expõe `content_quality` na prova e `preparation_errors` na questão; os gabaritos continuam privados até finalizar. A publicação manual válida encerra o estado pendente.

**Resultado do ensaio inicial da frente integrada, em 31/10/2026:**

- **96 provas geradas, com 8.595 questões.** Uma instalação desses arquivos, somada aos dois lotes conferidos, oferece 98 provas e 8.730 questões, de 2009 a 2025. Os arquivos não acompanham o clone; a quantidade instalada depende da geração e da publicação no banco escolhido. A integração posterior revalidou uma amostra, sem repetir o ensaio integral.
- **Pendências registradas:** 506, sendo 222 de layout espacial, 154 alternativas não separadas e 130 tabelas com células mescladas.
- **Alternativas não separadas:** essas questões mostram "Alternativa não extraída; conferir original." e continuam corrigidas pela letra do gabarito.
- **Fora do site:**
  - 2010 regular: o Inep publica a prova "com gabarito" marcado no próprio caderno, sem gabarito em texto;
  - 2010 e 2011 PPL: sem gabarito no acervo;
  - 3ª aplicação de 2014, 1º dia do PPL 2014 e 2021 impresso (regular e PPL): nenhuma cor tem texto legível;
  - 1998–2008: sem gabarito no acervo, e o formato de 63 questões não tem áreas.

## Implementação e validação

- Preparador compartilhado: `backend/app/preparation/`.
- Adaptador e comando: `scripts/exam_pdf.py` e `scripts/prepare_exam.py`.
- Validador: `node frontend/scripts/validate-latex.cjs caminho/prova.json` ou `--stdin`.
- Testes cobrem notação, palavras comuns, idempotência, dados de avaliação, prévia/importação, bloqueios, CLI e PDF. Testes gráficos trocam a numeração para confirmar que ela não seleciona regras especiais.
- `backend/tests/test_pdf_layouts.py` reproduz em PDFs sintéticos os layouts encontrados no ensaio: opção de língua, marca d'água girada, alternativas em grade, figuras em coluna, faixa decorativa, cabeçalhos fora das margens e codificação quebrada. Esses testes não dependem do acervo local.
- `scripts/pdf_headings.py` compartilha o reconhecimento de cabeçalhos espaçados entre o banco textual e o adaptador nativo; `test_archive_layouts.py` verifica ambos com o mesmo PDF. Geração e ensaio compartilham áreas e duração, incluindo Natureza antes de Humanas em 2009.
- O ensaio completo usa os 90 itens em arquivos temporários e mantém pendências visíveis. O resultado não substitui o JSON revisado nem é publicado automaticamente.

Validação local em 31/10/2026: 55 testes de API em SQLite e 14 testes Playwright aprovados no build de produção, com TypeScript aprovado. No ensaio genérico dos 90 itens, 176 expressões compilaram e o relatório apontou cinco bloqueios: células mescladas na 139 e relações espaciais nas 148, 169, 170 e 180. Também há avisos de descrições, vínculos inferidos e notação ambígua. Esses números identificam os casos encontrados no ensaio; não selecionam regras do preparador. Nenhum desses rascunhos foi importado no banco local.

[Painel de revisão no desktop](screenshots/curadoria-preparacao.png) e [no celular](screenshots/curadoria-preparacao-mobile.png), com dados simulados de curadoria. Este incremento passou a integrar a [regressão consolidada](primeira-entrega.md), incluindo PostgreSQL e CI. Outros cadernos e leitores de tela continuam exigindo validação própria.
