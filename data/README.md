# Dados do projeto

## Conteúdo distribuído

O perfil local de `catalog/profiles.json` define seis provas regulares de 2024/2025 (540 posições). O Docker usa dois lotes conferidos. JSONs, figuras, fontes oficiais necessárias, anotações, taxonomia e referências experimentais estão versionados; o acervo histórico e o banco textual são opcionais.

`make setup` instala o perfil local; `make check-distribution` verifica contratos, hashes, recursos e LaTeX. O manifesto `catalog/distribution-hashes.json` identifica os arquivos conferidos. Mudanças intencionais exigem revisão e atualização explícita de seus hashes.

## Preparar novas provas

Use `scripts/prepare_exam.py` e o manifesto de exemplo em `examples/`. O fluxo de [preparação](../docs/preparacao-provas.md) extrai conteúdo e registra ambiguidades. Importe como rascunho; correções criam novas versões e mantêm snapshots. Não substitua JSON publicado por saída experimental.

## Compatibilidade

Os dois arquivos de `derived/baselines/` são entradas de compatibilidade para snapshots antigos de 2024. A aplicação compara fingerprints completos antes de adaptar apenas apresentação. Eles não são temporários; removê-los altera tentativas antigas. Geradores pontuais das transcrições iniciais foram retirados; seu histórico permanece no Git.

## Anotações e experimentos

`classification/annotations-v1.json` conserva decisões, evidências e vínculo ao hash do conteúdo/fonte. Alterar texto invalida a anotação anterior. Habilidades ficam propostas até segunda revisão. Datasets em `datasets/` permitem reproduzir avaliações; relatórios são gerados em `tmp/`, sem publicação automática.

## Fontes e direitos

Originais em `sources/` são imutáveis e mantêm URL e SHA-256; [fontes oficiais](sources/README.md) descreve recuperação e organização. Provas e figuras conservam os direitos de seus autores. O produto não tem vínculo com o Inep.
