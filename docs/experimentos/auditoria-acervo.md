# Auditoria do acervo

Ferramentas genéricas para conferir fontes, versões, gabaritos, recursos e apresentação. Resultados pertencem a uma execução específica e ficam em `tmp/`; não equivalem a aprovação pedagógica.

## Reproduzir

Requer o banco local, o espelho e as provas geradas. Use uma pasta nova por execução. Faça backup e ensaie as correções em uma cópia antes de aplicá-las à base de uso.

```bash
.venv/bin/python scripts/backup_sqlite.py backups/antes-auditoria.db
.venv/bin/python scripts/backup_sqlite.py tmp/auditoria/ensaio.db

# Auditoria inicial; --render-sources guarda os recortes das questões.
.venv/bin/python scripts/audit_archive.py \
  --output tmp/auditoria/inicial --render-sources

# Plano de correções; ambiguidades permanecem propostas.
.venv/bin/python scripts/propose_archive_repairs.py \
  --audit tmp/auditoria/inicial --output tmp/auditoria/correcoes

.venv/bin/python scripts/apply_archive_audit.py \
  --plan tmp/auditoria/correcoes/corrections-plan.json \
  --database tmp/auditoria/ensaio.db --apply

# Confere fontes e simula a correção com as versões corrigidas.
.venv/bin/python scripts/audit_archive.py \
  --database tmp/auditoria/ensaio.db \
  --output tmp/auditoria/final --scoring --render-sources

# Compare modelos antes de aplicar o selecionado ao acervo.
.venv/bin/python scripts/run_experiments.py --output tmp/auditoria/modelos
.venv/bin/python scripts/experiment_archive_all.py \
  --database tmp/auditoria/ensaio.db --output tmp/auditoria/etapa3 \
  --model tmp/auditoria/modelos/classification-model.json

# Em outro terminal: npm --prefix frontend run start -- --port 3100
node scripts/audit_archive_browser.cjs \
  --input tmp/auditoria/final --url http://127.0.0.1:3100 \
  --workers 1 --capture-issues

.venv/bin/python scripts/report_archive_audit.py \
  --audit tmp/auditoria/final --experiments tmp/auditoria/etapa3 \
  --initial tmp/auditoria/inicial \
  --plan tmp/auditoria/correcoes/corrections-plan.json
```

`--resume` na auditoria revalida versões, fontes, recursos e recortes antes de reutilizar um relatório. O ensaio de resultados também associa o cache aos itens, gabaritos e código da correção. `--retry-failed` no gerador retoma provas sem relatório completo, validando as versões dos candidatos preservados. Uma falha por prova fica registrada; um relatório parcial não é apresentado como conclusão integral.

O navegador também reaproveita provas completas compatíveis com o build, a versão, o gabarito, o viewport e os recursos do manifesto. Para retomar após alterar somente a orquestração, `--compatible-harness caminho/do/auditor-anterior.cjs` exige que a função de inspeção seja textualmente idêntica; o relatório guarda os dois hashes. O tempo de execução corresponde à rodada registrada, incluindo seu cache, e não é tempo humano de revisão.

O consolidador aceita `--figure-review` para decisões sobre equivalência local de recortes e `--visual-review` para acrescentar achados assistidos. Ambos vinculam as decisões à versão, à fonte e aos bytes das evidências; uma decisão antiga não acompanha conteúdo ou arquivos alterados. A inspeção assistida não remove os demais diagnósticos nem aprova questões. No registro desta rodada, `pixel-review/decisions.json` contém 14 decisões sobre recortes e `conferencia-final/visual-review.json` contém os três casos visuais selecionados.

Sem `--apply`, o instalador valida e desfaz a transação. Depois de conferir o ensaio e o relatório visual, o mesmo plano pode ser aplicado à base de uso:

```bash
.venv/bin/python scripts/apply_archive_audit.py \
  --plan tmp/auditoria/correcoes/corrections-plan.json \
  --apply --sync-derived
```

`--sync-derived` atualiza apenas caches compatíveis com a versão anterior/atual, recalcula os relatórios e guarda um mapa das identidades estáveis. Edições próprias não são sobrescritas. A revisão independente de conteúdo, descrições científicas, rótulos e vínculos continua pendente.

## Arquivos de saída

| Arquivo | Conteúdo |
| --- | --- |
| `sources/<prova>.json` | Questões, versões, gabaritos oficiais, recursos, coordenadas e achados |
| `runs/<prova>.json` | Snapshots usados pelo navegador, sem usuários reais |
| `originals/` | Recortes das fontes |
| `browser/{desktop,mobile}/` | Resultado de cada questão nos dois temas |
| `screenshots/` | Capturas conforme a política escolhida |
| `scoring-report.json` | Resultados e idempotência dos cenários descartáveis |
| `all-proposals/<prova>.json` | Layout e classificação temática por versão |
| `historical-inventory.json` | Integridade e limites do banco histórico |
| `historical-recovery-queue.json` | Ocorrências encaminhadas para recuperação |
| `review.html`, `review-index.json` | Fila local com original, site e diagnósticos |
| `visual-review.json` | Achados assistidos selecionados, com hashes do conteúdo, das fontes e das evidências |
| `complete-report.json` | Cobertura, evidências, correções e pendências consolidadas |

O relatório completo preserva `manual_semantic_review_complete: false` e `independent_pedagogical_review: false`. Não registra tempo humano fictício nem transforma ausência de medição em aprovação.
