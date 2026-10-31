# Fontes oficiais

Este diretório contém **originais**, sem recortar, editar ou substituir seu conteúdo. O escopo solicitado é todo o acervo oficial disponível, de **1998 a 2025**, incluindo aplicações regular, segunda/terceira aplicação, reaplicação/PPL, digital, Belém/Ananindeua/Marituba e formatos acessíveis vinculados pelo Inep. A cobertura descreve o que o acervo oferece; não presume que uma aplicação sem link nunca existiu.

```text
sources/
├── catalogo/
│   ├── acervo.json                   # cada referência, URL, destino, estado e SHA-256
│   ├── paginas/{ano}.html            # páginas oficiais preservadas
│   ├── paginas/indice.html
│   └── certificados/                 # intermediário TLS público, com origem
├── enem/{ano}/{aplicacao}/{modalidade}/
│   └── dia-{1|2}/caderno-{numero}-{cor}[-idioma]/
│       ├── prova.pdf
│       ├── gabarito.pdf
│       ├── prova-{formato}.pdf
│       ├── gabarito-{formato}.pdf
│       └── {area}/prova-{formato}.{pdf|txt}
└── referencias/
    ├── matriz-referencia-enem.pdf    # local; recuperável pelo manifesto
    └── manifesto.json
```

Provas anteriores a 2009 usam `dia-unico/caderno-amarelo`. Arquivos sem dia informado usam `sem-dia-informado`; propostas de redação têm identificação própria. Versões digitais separadas por língua mantêm `-ingles`/`-espanhol`. Arquivos acessíveis separados por área usam, por exemplo, `ciencias-humanas/` e `matematica/`. Braile/ledor, ampliada, superampliada, Libras, NVDA e DOSVOX permanecem distintos. Se dois links ainda ocuparem o mesmo destino, um sufixo do identificador impede sobrescrita; os títulos originais continuam no manifesto.

## Aquisição, retomada e integridade

Na raiz do projeto:

```bash
python scripts/archive_enem.py inventory
python scripts/archive_enem.py sync --workers 4
python scripts/archive_enem.py audit
```

`inventory --refresh` consulta novamente o índice e as páginas anuais. Sem `--refresh`, reproduz o inventário a partir das páginas preservadas. `sync --years 2023 2024` limita uma retomada a anos determinados. O comando baixa apenas URLs encontradas nas páginas, valida o tipo dos arquivos e grava SHA-256 e tamanho. Um hash divergente é recusado e o original existente é preservado. As reorganizações de caminho também verificam o hash antes de mover.

Nesta coleta, o servidor do Inep omitiu um intermediário da cadeia TLS. Foi obtido da GlobalSign e validado contra as autoridades do sistema. Se o ambiente apresentar o mesmo problema, use:

```bash
python scripts/archive_enem.py sync --workers 4 \
  --ca-file data/sources/catalogo/certificados/rnp-icpedu-gr46-ov-tls-ca-2025.pem
```

Isso mantém a validação HTTPS. Origem e hash do certificado estão em `catalogo/certificados/origem.json`.

Falhas de rede e links oficiais quebrados ficam com `status: error`, sem arquivo falso ou gabarito de outra aplicação. `sync` e `audit` retornam código 2 enquanto houver pendências no recorte. O [relatório de cobertura](../../docs/cobertura-acervo.md) distingue esses casos de divergências de integridade.

## O que fica no Git e na imagem da aplicação

O espelho completo ocupa cerca de **2,5 GB** e é recuperável pelo manifesto. Os originais históricos baixados, a matriz de referência, o banco textual e os caches de `data/derived/` ficam locais e são ignorados pelo Git. Ficam versionados para conferência offline: as páginas oficiais, o catálogo, os certificados, o manifesto da matriz, os dois lotes conferidos (`data/enem-2024-dia2-azul.json` e `data/catalog/`), suas figuras, seus PDFs de prova e gabarito de 2023 e 2024, as bases de revisão em `data/derived/baselines/`, as anotações e o dataset de referência.

O banco textual comprimido em `data/bank/raw/{ano}.json.gz` é reconstruído com `scripts/build_bank.py` depois do `sync`; seu conteúdo é JSON, legível com `gzip` e `json` do Python.

O contexto Docker exclui o espelho histórico e as páginas HTML. A imagem inclui o inventário do acervo, a taxonomia, o catálogo conferido, as anotações e as figuras; não inclui o banco textual, então o acervo da curadoria lista as fontes sem as extrações. Uma instalação por clone não tem os PDFs históricos nem o banco até executar `sync` e `build_bank.py`; os links oficiais continuam registrados na curadoria.

## Separação dos derivados

- `data/derived/baselines/`: transcrições históricas imutáveis usadas para reproduzir as revisões.
- `data/derived/archive/`: cache retomável dos JSONs extraídos, por ano e identificador de fonte.
- `data/derived/assets/`: figuras de extrações automáticas que ainda não foram aprovadas.
- `data/catalog/`: conteúdo nativo conferido para instalação e publicação.
- `data/assets/`: somente recursos das versões servidas pelo site.

As antigas transcrições `enem-2024-dia2-azul-extraction.json` e `enem-2024-dia2-azul-native-v1.json` foram movidas para `derived/baselines/`, preservando seus bytes. Os dois PDFs iniciais foram movidos para a hierarquia do acervo. Identificadores, gabaritos e snapshots dos alunos foram preservados.
