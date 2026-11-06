import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const json = (body: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(body) });

const question = {
  id: 'tutor-q1:1',
  question_id: 'tutor-q1',
  canonical_id: 'tutor-q1',
  version: 1,
  number: 140,
  area: 'Matemática',
  statement: 'Uma loja vende 3 cadernos por $R\\$ 12{,}00$. Quanto custam 5 cadernos?',
  blocks: [{ type: 'paragraph', text: 'Uma loja vende 3 cadernos por R$ 12,00. Quanto custam 5 cadernos?' }],
  images: [],
  alternatives: ['R$ 15,00', 'R$ 20,00', 'R$ 24,00', 'R$ 30,00', 'R$ 36,00'].map((text, i) => ({
    letter: 'ABCDE'[i],
    text,
  })),
  labels: { discipline: 'Matemática', themes: ['Proporcionalidade'], skills: [] },
  page: 20,
  original_layout: false,
  preparation_errors: 0,
  source_url: 'https://example.org/prova.pdf',
  recommendation: {
    function: 'exploracao',
    reason: 'Exploração do tema Proporcionalidade.',
    policy_version: 'adaptive-v1',
  },
};

function session(help: unknown) {
  return {
    id: 'pratica-tutor',
    kind: 'practice',
    objective: 'Praticar',
    area: 'Matemática',
    available_minutes: 10,
    selection: {
      version: 'adaptive-v1',
      requested_items: 1,
      selected_items: 1,
      eligible_items: 1,
      themes: {},
      repeated_items: [],
    },
    answers: {},
    answered: 0,
    started_at: Date.now() / 1000,
    finished_at: null,
    result: null,
    items: [{ ...question, help }],
  };
}

async function asStudent(page: Page) {
  await page.route('**/api/me', route =>
    route.fulfill(json({ id: 'aluno', name: 'Aluno', email: 'aluno@example.org', role: 'student', preferences: {} })),
  );
}

test('prática pede ajuda por níveis e continua quando o tutor falha', async ({ page }) => {
  await asStudent(page);
  await page.route('**/api/practice-sessions/pratica-tutor', route =>
    route.fulfill(json(session({ available: true, next_level: 'orientation', delivered: [] }))),
  );
  const requests: { level: string; idempotency_key: string }[] = [];
  await page.route('**/api/practice-sessions/pratica-tutor/items/*/help', route => {
    const body = route.request().postDataJSON();
    requests.push(body);
    if (body.level === 'hint') return route.fulfill(json({ detail: 'O tutor não respondeu a tempo.' }, 503));
    return route.fulfill(
      json({
        id: 'ajuda-1',
        level: body.level,
        message: 'Descubra o preço de **um** caderno antes de calcular os cinco.',
        mode: 'tutor',
        outcome: 'delivered',
        delivered_at: Date.now() / 1000,
      }),
    );
  });
  await page.goto('/practice/pratica-tutor');
  const help = page.getByRole('region', { name: 'Ajuda do tutor' });
  await expect(help).toContainText('não contam como evidência independente');
  await help.getByRole('button', { name: 'Pedir orientação' }).click();
  await expect(help).toContainText('Descubra o preço de');
  await expect(help.getByText('Orientação', { exact: true })).toBeVisible();
  await help.getByRole('button', { name: 'Pedir uma pista' }).click();
  await expect(help.getByRole('alert')).toContainText('Você pode continuar a prática normalmente.');
  // Retrying after a failure reuses the same key, so the server never duplicates the help.
  await help.getByRole('button', { name: 'Pedir uma pista' }).click();
  await expect.poll(() => requests.filter(r => r.level === 'hint').length).toBe(2);
  const hints = requests.filter(r => r.level === 'hint');
  expect(hints[0].idempotency_key).toBe(hints[1].idempotency_key);
  await expect(page.getByRole('radio').first()).toBeEnabled();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});

test('sem material aprovado a prática não mostra ajuda', async ({ page }) => {
  await asStudent(page);
  await page.route('**/api/practice-sessions/pratica-tutor', route =>
    route.fulfill(json(session({ available: false, next_level: null, delivered: [] }))),
  );
  await page.goto('/practice/pratica-tutor');
  await expect(page.getByRole('heading', { name: 'Questão 01', exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Ajuda do tutor' })).toHaveCount(0);
});

test('curadoria aprova material do tutor com justificativa', async ({ page }) => {
  await page.route('**/api/me', route =>
    route.fulfill(json({ id: 'curador', name: 'Curadoria', email: 'c@example.org', role: 'admin', preferences: {} })),
  );
  const exam = {
    id: 'prova-tutor',
    title: 'Prova com tutor',
    year: 2025,
    booklet: 'Azul',
    status: 'published',
    expected_items: 1,
    item_count: 1,
    approved_items: 1,
    source: { url: 'https://example.org/prova.pdf' },
  };
  const material = {
    id: 'material-1',
    question_id: 'tutor-q1',
    version: 1,
    status: 'proposal',
    origin: 'llm',
    levels: {
      orientation: 'Pense no preço de cada caderno.',
      hint: 'Divida o valor total pela quantidade.',
      solution: 'Cada caderno custa R$ 4,00; cinco custam R$ 20,00, alternativa B.',
    },
    provenance: { model: 'llama-teste' },
    created_at: 1,
    reviewed_at: null,
    review_reason: null,
    current: true,
  };
  let approved = false;
  await page.route('**/api/admin/exams', route => route.fulfill(json([exam])));
  await page.route('**/api/admin/audit', route => route.fulfill(json([])));
  await page.route('**/api/admin/archive', route => route.fulfill(json({ years: [], files: [], coverage: {} })));
  await page.route('**/api/admin/tutor/status', route =>
    route.fulfill(json({ enabled: false, missing: ['GROQ_API_KEY'], model: null, daily_limit: 40 })),
  );
  await page.route('**/api/admin/tutor/exams/prova-tutor', route =>
    route.fulfill(
      json({
        exam: { id: 'prova-tutor', title: 'Prova com tutor' },
        items: [{ id: 'tutor-q1:1', number: 140, material: 'proposal' }],
      }),
    ),
  );
  await page.route('**/api/admin/tutor/questions/tutor-q1%3A1', route =>
    route.fulfill(
      json({
        question: { ...question, correct_answer: 'B', annulled: false },
        materials: [{ ...material, status: approved ? 'approved' : 'proposal' }],
      }),
    ),
  );
  await page.route('**/api/admin/tutor/materials/material-1/review', route => {
    approved = true;
    return route.fulfill(json({ ...material, status: 'approved' }));
  });
  await page.goto('/admin');
  const section = page.getByRole('region', { name: 'Material do tutor' });
  await expect(section).toContainText('Provedor desligado · falta GROQ_API_KEY');
  await expect(section.getByRole('button', { name: 'Gerar e aprovar com IA' })).toBeDisabled();
  await section.getByRole('button', { name: 'Aprovar', exact: true }).click();
  await expect(section).toContainText('Registre o que foi conferido');
  await section.getByLabel('Justificativa da decisão').fill('Conferido com o gabarito e sem resposta antecipada.');
  await section.getByRole('button', { name: 'Aprovar', exact: true }).click();
  await expect(section.getByRole('status')).toContainText('Material aprovado');
  await expect(section.locator('.badge.green', { hasText: 'Aprovado' })).toBeVisible();
});
