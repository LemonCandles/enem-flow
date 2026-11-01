import { expect, test } from '@playwright/test';

test.use({ video: 'off' });

test('origem automática e pendências ficam visíveis no catálogo e na questão', async ({ page }, info) => {
  expect((await page.request.post('/api/auth/register', { data: {
    name: 'Teste de Acervo', email: `acervo-${info.project.name}-${Date.now()}@example.com`, password: 'senha-acervo-integracao',
  } })).status()).toBe(201);
  // Exercise the presentation contract without installing unreviewed content in the test catalog.
  const quality = { origin: 'automatic', review_status: 'pending', blocking_issues: 1 };
  await page.route('**/api/exams', async route => {
    const response = await route.fetch();
    const exams = await response.json();
    for (const exam of exams) if (exam.id === 'enem-2024-dia2-azul') exam.content_quality = quality;
    await route.fulfill({ response, json: exams });
  });
  await page.route('**/api/exam-runs/*', async route => {
    if (route.request().method() !== 'GET') return route.continue();
    const response = await route.fetch();
    const run = await response.json();
    run.exam.content_quality = quality;
    run.items[0].preparation_errors = 1;
    await route.fulfill({ response, json: run });
  });
  await page.goto('/exams');
  const card = page.locator('.exam-card').filter({ has: page.getByRole('heading', { name: 'ENEM 2024 · 2º dia', exact: true }) });
  await expect(card.getByText('Extração automática', { exact: true })).toBeVisible();
  await card.getByRole('button', { name: 'Iniciar prova', exact: true }).click();
  await expect(page.getByText(/Este caderno foi extraído automaticamente e aguarda conferência/)).toBeVisible();
  await expect(page.getByText(/Esta questão tem pendências de apresentação registradas/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'caderno oficial', exact: true })).toHaveAttribute('href', /#page=2$/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});
