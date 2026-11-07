import { expect, test } from '@playwright/test';

test.use({ video: 'off' });

test('provas do acervo aparecem disponíveis e mantêm as pendências específicas da questão', async ({ page }, info) => {
  // Read published content and mock the session/run so this presentation test never writes to the database.
  const response = await page.request.get('/api/exams');
  expect(response.status()).toBe(200);
  const exams = await response.json();
  const detail = await page.request.get('/api/exams/enem-2024-dia2-azul');
  expect(detail.status()).toBe(200);
  const { items, ...exam } = await detail.json();
  const quality = { origin: 'automatic', review_status: 'pending', blocking_issues: 1 };
  const run = {
    id: 'acervo-apresentacao',
    exam: { ...exam, content_quality: quality },
    items: items.map((item: object, index: number) => ({ ...item, preparation_errors: index === 0 ? 1 : 0 })),
    answers: {},
    started_at: Date.now() / 1000,
    finished_at: null,
    result: null,
  };
  await page.route('**/api/me', route =>
    route.fulfill({
      json: {
        id: 'acervo-teste',
        name: 'Teste de Acervo',
        email: 'acervo@example.com',
        role: 'student',
        preferences: {},
      },
    }),
  );
  await page.route('**/api/me/history', route => route.fulfill({ json: [] }));
  await page.route('**/api/exams', route =>
    route.fulfill({
      json: exams.map((exam: object) => ({ ...exam, content_quality: quality })),
    }),
  );
  await page.route('**/api/exam-runs', route => route.fulfill({ status: 201, json: run }));
  await page.route('**/api/exam-runs/*', route => route.fulfill({ json: run }));
  await page.goto('/exams');
  await expect(page.locator('.exam-card')).toHaveCount(exams.length);
  await expect(page.locator('.exam-card .badge.green')).toHaveText(exams.map(() => 'Disponível'));
  await expect(page.getByText('Extração automática', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: `test-results/${info.project.name}-catalogo-disponivel.png`, fullPage: true });
  const card = page
    .locator('.exam-card')
    .filter({ has: page.getByRole('heading', { name: 'ENEM 2024 · 2º dia', exact: true }) });
  await expect(card.getByText('Disponível', { exact: true })).toBeVisible();
  await card.getByRole('button', { name: 'Iniciar prova', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Questão 91', exact: true })).toBeVisible();
  await expect(page.getByText(/Este caderno foi extraído automaticamente e aguarda conferência/)).toHaveCount(0);
  await expect(page.getByText(/Esta questão tem pendências de apresentação registradas/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'caderno oficial', exact: true })).toHaveAttribute('href', /#page=2$/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
