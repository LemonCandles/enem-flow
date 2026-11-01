# Cobertura do acervo oficial

Coleta de **31/10/2026**, reproduzida a partir de `data/sources/catalogo/acervo.json` e `data/bank/coverage.json`. Escopo: todas as aplicações e formatos com arquivos vinculados no [acervo do Inep](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos).

- **28 anos:** 1998–2025.
- **886 referências**, correspondentes a **822 URLs** de arquivos.
- **884 referências obtidas**; **2 URLs indisponíveis**.
- **2.51 GB** de originais organizados, incluindo cópias de arquivos compartilhados por mais de um caderno/formato.
- **480 PDFs e 10 TXT de prova indexados**; **44311 ocorrências extraídas**.
- **43226 identidades conservadoras**; **1085 ocorrências agrupadas**. Essa contagem inclui identidades provisórias e não é a quantidade comprovada de questões semanticamente únicas de todo o ENEM.
- **21 fontes com observações de integridade da extração**. Todas as extrações históricas aguardam conferência de conteúdo, inclusive quando a numeração foi reconhecida.
- **135 questões publicadas**, em dois lotes conferidos: segundo dia azul de 2024 e Matemática azul de 2023. Anuladas 129/2024 e 164/2023; 133 itens válidos.
- **89 questões válidas de Matemática em oito temas** na referência exploratória. Habilidades candidatas aguardam segunda revisão e não foram publicadas como rótulos.

Arquivos originais, ocorrências e questões aprovadas são contagens diferentes. Cores, aplicações e versões acessíveis podem repetir itens. Somente texto exatamente normalizado é agrupado automaticamente; figuras são tratadas conservadoramente. Os índices se ligam às identidades do catálogo conferido por fonte e número.

## Cobertura por ano

| Ano | Referências | Obtidas | Aplicações do acervo | Fontes de questões indexadas | Ocorrências extraídas |
| --- | ---: | ---: | --- | ---: | ---: |
| 1998 | 1 | 1 | regular | 1 | 63 |
| 1999 | 1 | 1 | regular | 1 | 63 |
| 2000 | 1 | 1 | regular | 1 | 63 |
| 2001 | 1 | 1 | regular | 1 | 63 |
| 2002 | 1 | 1 | regular | 1 | 63 |
| 2003 | 1 | 1 | regular | 1 | 63 |
| 2004 | 1 | 1 | regular | 1 | 63 |
| 2005 | 1 | 1 | regular | 1 | 63 |
| 2006 | 1 | 1 | regular | 1 | 63 |
| 2007 | 1 | 1 | regular | 1 | 63 |
| 2008 | 1 | 1 | regular | 1 | 63 |
| 2009 | 18 | 18 | regular | 10 | 900 |
| 2010 | 24 | 24 | reaplicacao-ppl, regular | 16 | 1480 |
| 2011 | 20 | 20 | reaplicacao-ppl, regular | 12 | 1110 |
| 2012 | 22 | 22 | reaplicacao-ppl, regular | 12 | 1110 |
| 2013 | 22 | 22 | reaplicacao-ppl, regular | 12 | 1110 |
| 2014 | 24 | 24 | reaplicacao-ppl, regular, terceira-aplicacao | 12 | 1110 |
| 2015 | 34 | 34 | reaplicacao-ppl, regular | 18 | 1665 |
| 2016 | 50 | 50 | reaplicacao-ppl, regular, segunda-aplicacao | 26 | 2495 |
| 2017 | 56 | 56 | reaplicacao-ppl, regular | 32 | 2970 |
| 2018 | 48 | 48 | reaplicacao-ppl, regular | 24 | 2220 |
| 2019 | 60 | 60 | reaplicacao-ppl, regular | 30 | 2775 |
| 2020 | 84 | 84 | digital, reaplicacao-ppl, regular | 42 | 3855 |
| 2021 | 92 | 92 | digital, reaplicacao-ppl, regular | 46 | 4130 |
| 2022 | 92 | 92 | digital, reaplicacao-ppl, regular | 46 | 4226 |
| 2023 | 70 | 70 | reaplicacao-ppl, regular | 42 | 3515 |
| 2024 | 65 | 64 | reaplicacao-ppl, regular | 37 | 3425 |
| 2025 | 94 | 93 | belem-ananindeua-marituba, reaplicacao, regular | 62 | 5522 |

A coluna de fontes indexadas inclui TXT quando presentes; os nomes de aplicação normalizados preservam a distinção dos títulos oficiais, disponíveis no manifesto. Ausência de arquivo no índice não autoriza concluir que uma aplicação nunca existiu.

## URLs oficiais indisponíveis

| Ano e aplicação | Arquivo | Resultado |
| --- | --- | --- |
| 2024 · regular | [Prova (Superampliada) — 2º Dia – Caderno 12 – Roxo (Libras) – Aplicação Regular](https://download.inep.gov.br/enem/provas_e_gabaritos/2024_PV_impresso_D2_CD12_Superampliada.pdf) | HTTPError: HTTP Error 404: Not Found |
| 2025 · reaplicacao | [Gabarito — 2º Dia – Caderno 11 – Laranja (Braile e ledor) – Reaplicação](https://download.inep.gov.br/enem/provas_e_gabaritos/2025_GB_impresso_D6_CD11.pdf) | HTTPError: HTTP Error 404: Not Found |

Não foi usado gabarito de outra aplicação como substituto. Uma URL de nome parecido pode pertencer, por exemplo, à aplicação de Belém; o número do caderno sozinho não determina a prova.

## Fontes com observações de extração

| Fonte | Questões extraídas | Observação |
| --- | ---: | --- |
| `enem/2010/reaplicacao-ppl/impresso/dia-2/caderno-7-azul/prova.pdf` | 95 | Quantidade de números distintos diferente da referência 90; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-1/caderno-1-azul/ciencias-humanas/prova.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-1/caderno-2-amarelo/ciencias-humanas/prova.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-1/caderno-3-branco/ciencias-humanas/prova.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-1/caderno-4-rosa/ciencias-humanas/prova.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-2/caderno-5-amarelo/linguagens/prova.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-2/caderno-6-cinza/linguagens/prova.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-2/caderno-7-azul/linguagens/prova.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2016/segunda-aplicacao/impresso/dia-2/caderno-8-rosa/linguagens/prova.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2021/reaplicacao-ppl/impresso/dia-1/caderno-3-branco/prova.pdf` | 0 | Cabeçalhos não reconhecidos de forma completa; exige adaptação/OCR e conferência. |
| `enem/2024/regular/impresso/dia-1/caderno-9-laranja/linguagens/prova-nvda.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2024/regular/impresso/dia-2/caderno-11-laranja/ciencias-da-natureza/prova-nvda.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/belem-ananindeua-marituba/impresso/dia-1/caderno-9-laranja/linguagens/prova-nvda.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/belem-ananindeua-marituba/impresso/dia-2/caderno-11-laranja/ciencias-da-natureza/prova-nvda.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/reaplicacao/impresso/dia-1/caderno-9-laranja/prova-ampliada.pdf` | 80 | Quantidade de números distintos diferente da referência 90; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/reaplicacao/impresso/dia-1/caderno-9-laranja/prova-ledor.pdf` | 0 | Cabeçalhos não reconhecidos de forma completa; exige adaptação/OCR e conferência. |
| `enem/2025/reaplicacao/impresso/dia-1/caderno-9-laranja/prova-superampliada.pdf` | 88 | Quantidade de números distintos diferente da referência 90; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/reaplicacao/impresso/dia-2/caderno-11-laranja/prova-ledor.pdf` | 0 | Cabeçalhos não reconhecidos de forma completa; exige adaptação/OCR e conferência. |
| `enem/2025/reaplicacao/impresso/dia-2/caderno-11-laranja/prova-superampliada.pdf` | 84 | Quantidade de números distintos diferente da referência 90; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/regular/impresso/dia-1/caderno-9-laranja/linguagens/prova-nvda.pdf` | 95 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |
| `enem/2025/regular/impresso/dia-2/caderno-11-laranja/ciencias-da-natureza/prova-nvda.pdf` | 90 | Quantidade de números distintos diferente da referência 45; conferir faltas, anulação e atendimento especializado. |

Uma observação de contagem não resolve OCR, leitura de fórmulas, tabelas ou textos compartilhados. O texto bruto permanece consultável na curadoria e não é usado como questão aprovada sem preparação.

## Temas da referência de Matemática

| Tema | Questões válidas |
| --- | ---: |
| Estatística | 8 |
| Geometria espacial | 6 |
| Geometria plana | 12 |
| Grandezas e medidas | 7 |
| Gráficos e coordenadas | 8 |
| Números e proporcionalidade | 18 |
| Probabilidade e combinatória | 9 |
| Álgebra e funções | 21 |

## Reproduzir

```bash
python scripts/archive_enem.py inventory
python scripts/archive_enem.py sync --workers 4
python scripts/archive_enem.py audit
.venv/bin/python scripts/build_bank.py --workers 4
.venv/bin/python scripts/report_bank.py
```

Enquanto os dois links oficiais permanecerem quebrados, `sync` e `audit` retornam 2 e mantêm as demais fontes verificadas. O [guia das fontes](../data/sources/README.md) explica o intermediário TLS opcional, arquivos locais versus versionados e organização dos derivados. O [processo de classificação](banco-classificacao.md) registra a revisão e seus limites.
