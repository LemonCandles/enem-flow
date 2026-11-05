# Política adaptativa inicial

Implementação técnica da etapa 5 em 04/11/2026. A prática adaptativa escolhe questões a partir das respostas já finalizadas do aluno e explica cada escolha. Os pesos são parâmetros de experimento: não há combinação ótima presumida nem evidência de ganho de aprendizagem.

## Jornada

A entrada **Prática** pede objetivo, área e tempo disponível, como o diagnóstico. A quantidade é `min(20, floor(minutos / 3))`, limitada ao que restar depois dos filtros. O conjunto fica fixo ao iniciar: a correção e os eventos só aparecem na finalização, então a seleção não muda durante a sessão. Cada questão mostra **Por que esta questão?**, e a página lista as recomendações recentes.

## Seleção `adaptive-v1`

A política é uma função pura em `backend/app/services/adaptive.py`, usada pela API e pela comparação offline.

**Filtros**

| Filtro | Regra |
| --- | --- |
| Área | A escolhida pelo aluno. |
| Integridade e rótulos | Os de `eligible_items`: versão aprovada em prova publicada, com gabarito e tema, sem anulação nem pendência bloqueante, deduplicada por identidade. |
| Exposição | Fora os itens já apresentados 2 vezes ao aluno, em qualquer prova ou sessão, concluída ou não. |
| Dificuldade provisória | Taxa de acerto suavizada do item entre todos os alunos, em respostas sem ajuda, a partir de 5 respostas. Abaixo de 15%, o item sai, se a sessão mantiver o tamanho. Sem respostas suficientes, ela é desconhecida e neutra. |

Não há dificuldade calibrada. Enquanto houver poucos alunos, quase todos os itens têm dificuldade desconhecida.

**Função de cada tema ou habilidade**, com o estado de `beta-first-independent-v1`:

| Função | Critério | Urgência (0 a 1) |
| --- | --- | --- |
| Exploração | Menos de 5 respostas independentes, mesmo que todas erradas. | `1 - respostas / 5` |
| Reforço | 5 ou mais respostas e estimativa abaixo de 0,6. | `(0,6 - estimativa) / 0,6` |
| Revisão | 5 ou mais respostas e estimativa a partir de 0,6. | `dias desde a última prática / 14`, até 1 |

**Prioridade do item:** o maior valor de `peso × urgência` entre seus temas e habilidades publicadas, com pesos 1,0 (reforço), 0,6 (revisão) e 0,8 (exploração). O grupo que dá esse valor define a função e o motivo. Depois entram exposição (`-0,5 × exposições / 2`), concentração (`-0,5 × escolhas no grupo / limite`) e dificuldade (`+0,1 × proximidade de 60% de acerto`, 0,5 quando desconhecida).

**Controle de concentração:** um tema recebe no máximo metade das questões da sessão. O limite só cede quando não há alternativa, como em uma área com um só tema, e a quantidade fica em `relaxed_theme_cap`. As escolhas são gulosas, recalculadas a cada questão, e empates seguem a ordem embaralhada pela semente registrada.

## Contratos

Todas as rotas exigem autenticação e só acessam a própria conta.

| Rota | Contrato |
| --- | --- |
| `POST /practice-sessions` | `objective`, `area`, `available_minutes`, `idempotency_key`. Chave repetida devolve a mesma sessão; parâmetros diferentes ou chave usada em um diagnóstico retornam 409. Sem itens disponíveis, 422. |
| `GET /practice-sessions/{id}` | Sessão, com `recommendation` em cada item. Gabarito só depois de finalizar. |
| `PUT /practice-sessions/{id}/answers/{item_id}` | Como no diagnóstico. |
| `POST /practice-sessions/{id}/finish` | Finalização idempotente e transacional. |
| `GET /practice-sessions/{id}/recommendations` | Auditoria completa: parâmetros, semente, evidência e, por escolha, função, motivo, componentes e candidatos. |
| `GET /me/recommendations` | Escolhas da conta, sem os candidatos. Entra na exportação JSON. |

As sessões de prática usam a tabela `diagnostic_sessions`, com `kind = 'practice'`, e o ciclo comum de `services/attempts.py`. Um diagnóstico não abre pela rota de prática, nem o contrário. `GET /me/sessions` lista as duas, com `kind`, e `DELETE /me/history` remove também as recomendações.

## Auditoria

A migração `e5a1c7d30b12` cria `recommendation_events`, com uma linha por escolha: versão da política, função, motivo, componentes da prioridade, total de candidatos e os 25 candidatos de maior prioridade naquele passo, sempre com o escolhido. `selection` guarda a semente, os parâmetros, o instante, a evidência usada, os filtros aplicados e as funções. Os eventos de aprendizagem registram `policy_version` e a função. Nenhum desses registros contém gabarito.

O limite de 25 candidatos evita registros grandes quando o catálogo crescer; o total fica registrado, mas os demais candidatos daquele passo não. O downgrade da migração apaga as sessões de prática, seus eventos e o registro; faça backup antes de usá-lo.

## Comparação com as referências

`make experiments` compara `adaptive-v1` com `random-v1` (qualquer item, sem usar evidência) e `reinforcement-simple-v1` (menor estimativa primeiro, sem outro controle), usando os 89 itens de `adaptive-math-reference-v1`. Cada cenário tem 30 alunos simulados, com probabilidade de acerto fixa por tema. [Resultado completo](experimentos/politica-adaptativa-2026-11-04.json).

Valores médios. **Cobertura:** temas praticados entre os disponíveis. **Tema máximo:** maior fatia de um tema por sessão. **Repetição:** escolhas de item já apresentado. **Gini:** desigualdade de uso dos itens. **Tema fraco:** fatia dos temas fracos depois de haver evidência neles.

| Cenário | Política | Cobertura | Tema máximo | Repetição | Itens distintos | Gini | Tema fraco | Questões |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aluno-novo | Adaptativa | 100% | 20% | 0% | 40.0 | 0.55 | — | 40 |
| aluno-novo | Aleatória | 99% | 32% | 16% | 33.6 | 0.67 | — | 40 |
| aluno-novo | Reforço simples | 68% | 69% | 31% | 27.5 | 0.75 | — | 40 |
| tema-fraco | Adaptativa | 100% | 26% | 2% | 58.9 | 0.35 | 36% | 60 |
| tema-fraco | Aleatória | 100% | 33% | 25% | 45.0 | 0.59 | 11% | 60 |
| tema-fraco | Reforço simples | 71% | 84% | 61% | 23.6 | 0.82 | 100% | 60 |
| dois-temas-fracos | Adaptativa | 100% | 26% | 4% | 57.7 | 0.38 | 60% | 60 |
| dois-temas-fracos | Aleatória | 100% | 33% | 24% | 45.8 | 0.58 | 19% | 60 |
| dois-temas-fracos | Reforço simples | 70% | 82% | 60% | 23.9 | 0.82 | 100% | 60 |
| revisao-antiga | Adaptativa | 100% | 20% | 0% | 20.0 | 0.78 | — | 20 |
| revisao-antiga | Aleatória | 91% | 32% | 6% | 18.8 | 0.80 | — | 20 |
| revisao-antiga | Reforço simples | 82% | 56% | 5% | 18.9 | 0.80 | — | 20 |
| pratica-longa | Adaptativa | 100% | 26% | 26% | 88.8 | 0.17 | — | 120 |
| pratica-longa | Aleatória | 100% | 32% | 44% | 67.6 | 0.44 | — | 120 |
| pratica-longa | Reforço simples | 69% | 81% | 72% | 33.1 | 0.78 | — | 120 |
| acervo-pequeno | Adaptativa | 100% | 47% | 50% | 12.0 | 0.00 | — | 24 |
| acervo-pequeno | Aleatória | 100% | 33% | 70% | 12.0 | 0.11 | — | 40 |
| acervo-pequeno | Reforço simples | 87% | 36% | 73% | 10.9 | 0.15 | — | 40 |
| tema-unico | Adaptativa | 100% | 100% | 50% | 6.0 | 0.00 | — | 12 |
| tema-unico | Aleatória | 100% | 100% | 50% | 6.0 | 0.00 | — | 12 |
| tema-unico | Reforço simples | 100% | 100% | 50% | 6.0 | 0.00 | — | 12 |

**O que os números mostram**

- A adaptativa cobre todos os temas e repete menos itens que as duas referências nos cenários com acervo suficiente.
- O reforço simples concentra mais nos temas fracos, com perda de cobertura e muita repetição. A adaptativa fica no meio, de propósito: dedica menos questões ao tema fraco e continua explorando e revisando o restante.
- Em `revisao-antiga`, todas as escolhas da adaptativa são revisão, como esperado para esse cenário.
- **Custo do controle de exposição:** em `acervo-pequeno`, a adaptativa entrega 24 questões em vez de 40, porque nenhum item passa de 2 exposições. Em `tema-unico`, as três políticas empatam, por falta de alternativa.

## Limites

Os alunos são simulados, não aprendem entre as sessões e foram definidos pela mesma frente técnica que escolheu os pesos. A comparação descreve o comportamento da seleção; não mede aprendizagem nem indica os melhores pesos. Não houve estudo com estudantes, e os motivos ainda precisam ser avaliados por pessoas quanto à clareza.

Há pré-requisitos no plano que ainda não entram no reforço, porque o catálogo não os registra. As habilidades entram na decisão assim que forem publicadas em `labels.skills`; hoje a política funciona por tema. Só as questões com tema publicado são elegíveis, e o motivo descreve as respostas do aluno sem identificar a causa de um erro.

## Verificação

```bash
.venv/bin/pytest -q backend/tests/test_adaptive.py backend/tests/test_diagnostic_migration.py
make experiments
npm --prefix frontend run test:e2e -- --workers=1 tests/practice.spec.ts
```

Em 04/11/2026, passaram 185 testes em SQLite, 185 em PostgreSQL e 36 de navegador, em três rodadas seguidas, em desktop e celular. A migração foi conferida nos dois bancos, incluindo o downgrade.

A implantação requer `alembic upgrade head` antes de iniciar a aplicação.
