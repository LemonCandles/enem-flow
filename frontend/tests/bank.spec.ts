import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.use({ video: 'off' });

test('seção de Matemática de 2023 mantém texto, tabelas, LaTeX, figuras e rótulos', async ({ page }, info) => {
  test.setTimeout(180_000);
  expect((await page.request.post('/api/auth/register', { data: { name: 'Referência Matemática', email: `math-${info.project.name}-${Date.now()}@example.com`, password: 'matematica-conteudo-nativo' } })).status()).toBe(201);
  await page.goto('/exams');
  await page.getByRole('combobox', { name: 'Todos os anos' }).selectOption('2023');
  const card = page.locator('.exam-card').filter({ hasText: 'ENEM 2023' });
  await expect(card).toContainText('Seção completa');
  await expect(card).toContainText('150 minutos');
  await card.getByRole('button', { name: 'Iniciar prova', exact: true }).click();
  for (let number = 136; number <= 180; number++) {
    await expect(page.getByRole('heading', { name: `Questão ${number}`, exact: true })).toBeVisible();
    await expect(page.locator('.katex-error')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await expect.poll(() => page.locator('.question-content img, .alternatives img').evaluateAll(images => images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))).toBeTruthy();
    if (number === 137) {
      await expect(page.getByRole('table')).toContainText('2 000,00');
      await expect(page.getByRole('table')).toContainText('7 000,00');
    }
    if (number === 141) await expect(page.locator('.alternatives .katex')).toHaveCount(5);
    if (number === 178) {
      await expect(page.locator('.question-content')).toContainText('torneira inteligente');
      await expect(page.locator('.alternatives img')).toHaveCount(5);
    }
    if ([136,137,145,161,169,172,178].includes(number)) await page.screenshot({ scale: 'css', path: `test-results/${info.project.name}-math2023-${number}.png`, fullPage: true });
    if (number < 180) await page.getByRole('button', { name: 'Próxima questão' }).click();
  }
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(axe.violations).toEqual([]);
  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Abrir mapa de questões' }).click();
  await page.getByRole('button', { name: 'Finalizar prova', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmar finalização' }).click();
  await expect(page.getByText('0 de 44 questões válidas')).toBeVisible();
  await page.goto('/progress');
  await page.getByRole('button', { name: 'Tema', exact: true }).click();
  await expect(page.getByText('44/44 tentativas · 100%')).toBeVisible();
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});

test('curadoria consulta acervo por ano e distingue extração de aprovação', async ({ page }, info) => {
  const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  const source = { id: 'fonte1998', year: 1998, application: 'regular', day: null, booklet: 'caderno-amarelo', variant: 'padrao', role: 'prova', status: 'downloaded', url: 'https://download.inep.gov.br/original.pdf', path: 'enem/1998/regular/impresso/dia-unico/caderno-amarelo/prova.pdf', sha256: 'a'.repeat(64) };
  const occurrence = { occurrence_id: 'fonte1998-q1-1', canonical_id: 'enem-referencia', year: 1998, application: 'regular', booklet: 'caderno-amarelo', number: 1, page: 1, has_visual: false };
  await page.route('**/api/me', route => route.fulfill(json({ id: 'curador', name: 'Curadoria', role: 'admin', preferences: {} })));
  await page.route('**/api/admin/exams', route => route.fulfill(json([])));
  await page.route('**/api/admin/audit', route => route.fulfill(json([])));
  await page.route('**/api/admin/archive', route => route.fulfill(json({ years: [1998], applications: ['regular'], references: 1, downloaded: 1, unavailable: [], coverage: { occurrences: 63 }, files: [source] })));
  await page.route('**/api/admin/archive/questions?*', route => route.fulfill(json({ total: 1, items: [occurrence] })));
  await page.route('**/api/admin/archive/questions/fonte1998-q1-1', route => route.fulfill(json({ ...occurrence, text: 'Enunciado selecionável da fonte original para conferência.', issues: ['Texto ainda não revisado.'], source_issues: [], source, occurrences: [occurrence] })));
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Acervo oficial para curadoria' })).toBeVisible();
  await page.getByLabel('Número da questão').fill('1');
  await page.getByRole('button', { name: /Questão 1 regular/ }).click();
  await expect(page.locator('.archive-transcript')).toHaveText('Enunciado selecionável da fonte original para conferência.');
  await expect(page.locator('.archive-detail')).toContainText('antes da publicação');
  await expect(page.locator('.archive-detail img')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  const axe = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(axe.violations).toEqual([]);
  await page.screenshot({ scale: 'css', path: `test-results/${info.project.name}-archive.png`, fullPage: true });
});
