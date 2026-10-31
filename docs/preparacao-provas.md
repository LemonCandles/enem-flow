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

O adaptador identifica cabeçalhos textuais `QUESTÃO`/`QUESTAO`, mantém a ordem de colunas/páginas, recupera índices/cargas numéricos por posição e recorta componentes rasterizados/vetoriais. Alternativas gráficas podem ser separadas pelos marcadores A–E, inclusive em duas colunas. Tabelas com grade reconhecível viram dados HTML. Células mescladas e relações espaciais não resolvidas geram pendências.

Questões e gabarito devem coincidir exatamente com o total declarado. Cabeçalhos duplicados, áreas sobrepostas, hash divergente e gabaritos conflitantes interrompem a preparação. Versões de língua do primeiro dia com numeração sobreposta precisam de um manifesto/recorte sem duplicatas; a escolha de língua ainda não é automática.

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

Alternativas incorretas não são balanceadas nem corrigidas conceitualmente. Aprovar continua exigindo comparação com o original.

Entradas não são substituídas. Saídas existentes exigem `--force`, que também não permite escrever sobre uma entrada. Recursos têm nomes derivados do hash da fonte e do recorte. `--assets-root` permite preparar em diretório temporário; depois copie os recursos correspondentes para `data/assets/` antes da importação.

Código de saída `0`: preparação técnica concluída. Código `2`: erro ou pendência bloqueante; com `--strict`, avisos também retornam `2`. Quando possível, rascunho e relatório são gravados mesmo com pendências. Recursos ausentes são informados no relatório. LaTeX que não compila interrompe a saída e identifica a questão.

PDFs digitalizados sem texto exigem OCR e conferência antes deste fluxo. A interface continua recebendo JSON; não há upload de PDF, OCR automático ou interpretação visual por IA. O adaptador geométrico tem limites, apresentados no relatório.

## Implementação e validação

- Preparador compartilhado: `backend/app/preparation/`.
- Adaptador e comando: `scripts/exam_pdf.py` e `scripts/prepare_exam.py`.
- Validador: `node frontend/scripts/validate-latex.cjs caminho/prova.json` ou `--stdin`.
- Testes cobrem notação, palavras comuns, idempotência, dados de avaliação, prévia/importação, bloqueios, CLI e PDF. Testes gráficos trocam a numeração para confirmar que ela não seleciona regras especiais.
- O ensaio completo usa os 90 itens em arquivos temporários e mantém pendências visíveis. O resultado não substitui o JSON revisado nem é publicado automaticamente.

Validação local em 31/10/2026: 55 testes de API em SQLite e 14 testes Playwright aprovados no build de produção, com TypeScript aprovado. No ensaio genérico dos 90 itens, 176 expressões compilaram e o relatório apontou cinco bloqueios: células mescladas na 139 e relações espaciais nas 148, 169, 170 e 180. Também há avisos de descrições, vínculos inferidos e notação ambígua. Esses números identificam os casos encontrados no ensaio; não selecionam regras do preparador. Nenhum desses rascunhos foi importado no banco local.

[Painel de revisão no desktop](screenshots/curadoria-preparacao.png) e [no celular](screenshots/curadoria-preparacao-mobile.png), com dados simulados de curadoria. Este incremento passou a integrar a [regressão consolidada](primeira-entrega.md), incluindo PostgreSQL e CI. Outros cadernos e leitores de tela continuam exigindo validação própria.
