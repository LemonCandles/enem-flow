import { expect, test } from '@playwright/test';

test('curadoria exibe transformações e bloqueia aprovação de conteúdo pendente', async ({ page }, info) => {
  const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  const exam = { id: 'generic-fixture', title: 'Nova prova preparada', year: 2025, booklet: 'Azul', status: 'draft', expected_items: 1, item_count: 1, approved_items: 0, source: { url: 'https://example.org/prova.pdf' } };
  const item = { id: 'unseen-q37:1', question_id: 'unseen-q37', version: 1, status: 'draft', content: { number: 37, page: 2, images: [], statement: 'Considere a reação química.', layout: { preparation: { version: 'generic-v1', changes: [{ operation: 'latex' }], issues: [{ code: 'unlocated_images', severity: 'error', message: 'Informe a posição da figura conforme o original.', location: 'images' }] } } } };
  await page.route('**/api/me', route => route.fulfill(json({ id: 'curator', name: 'Curadoria', email: 'curator@example.org', role: 'admin', preferences: {} })));
  await page.route('**/api/admin/exams', route => route.fulfill(json([exam])));
  await page.route('**/api/admin/audit', route => route.fulfill(json([])));
  await page.route('**/api/admin/exams/generic-fixture', route => route.fulfill(json({ ...exam, items: [item] })));
  await page.route('**/api/admin/archive', route => route.fulfill(json({ years: [], files: [], coverage: {} })));
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Revisar', exact: true }).click();
  const notice = page.getByRole('complementary', { name: 'Preparação automática' });
  await expect(notice).toContainText('1 transformações registradas');
  await expect(notice).toContainText('Informe a posição da figura');
  await expect(page.getByRole('button', { name: 'Aprovar questão', exact: true })).toBeDisabled();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: `test-results/${info.project.name}-preparation-review.png`, fullPage: true });
});
