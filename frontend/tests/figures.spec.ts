import { expect, test } from '@playwright/test';

test('legendas e química acompanham a figura; ampliação, zoom e teclado ficam no site', async ({ page, context }, info) => {
  test.setTimeout(60_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  expect((await page.request.post('/api/auth/register', { data: { name: 'Teste de Figuras', email: `e2e-figures-${info.project.name}-${Date.now()}@example.com`, password: 'senha-figuras-latex-2026' } })).status()).toBe(201);
  const created = await page.request.post('/api/exam-runs', { data: { exam_id: 'enem-2024-dia2-azul', idempotency_key: `figures-${Date.now()}` } });
  const run = await created.json();
  await page.goto(`/runs/${run.id}`);
  await expect(page.getByRole('heading', { name: 'Questão 91', exact: true })).toBeVisible();
  const figure = page.locator('.question-figure').first();
  await expect(figure.locator('figcaption')).toContainText('Momentum and Car safety. GCSE Physics Revision.');
  await expect(page.locator('.native-paragraph').filter({ hasText: 'Momentum and Car safety' })).toHaveCount(0);
  const descriptionId = await figure.locator('img').getAttribute('aria-describedby');
  expect(descriptionId).toBe(await figure.locator('figcaption').getAttribute('id'));
  const url = page.url(), tabs = context.pages().length;
  const enlarge = figure.getByRole('button', { name: 'Ampliar figura', exact: true });
  await enlarge.click();
  const dialog = page.getByRole('dialog', { name: 'Figura da questão 91', exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Fechar ampliação' })).toBeFocused();
  await expect(dialog.locator('figcaption')).toContainText('shalom-education.com');
  await dialog.getByRole('button', { name: 'Aumentar ampliação' }).click();
  await expect(dialog.locator('output')).toHaveText('125%');
  await dialog.getByRole('button', { name: 'Restaurar tamanho' }).click();
  await expect(dialog.locator('output')).toHaveText('100%');
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(enlarge).toBeFocused();
  expect(page.url()).toBe(url);
  expect(context.pages()).toHaveLength(tabs);
  await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden');

  await page.getByRole('button', { name: 'Próxima questão' }).click();
  await expect(page.getByRole('heading', { name: 'Questão 92', exact: true })).toBeVisible();
  await expect(figure.locator('.figure-equation .katex')).toHaveCount(2);
  await expect(figure.locator('.figure-credit')).toContainText('QUINTO, A. C.');
  await expect(page.locator('.alternatives .katex')).toHaveCount(5);
  await expect(page.locator('.katex-error')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  // The left edge of a long equation must remain reachable on narrow screens.
  const bounds = await figure.locator('.figure-equation').first().evaluate(el => {
    const math = el.querySelector('.katex-html')!;
    return { left: el.getBoundingClientRect().left, mathLeft: math.getBoundingClientRect().left };
  });
  expect(bounds.mathLeft).toBeGreaterThanOrEqual(bounds.left - 1);
  await page.screenshot({ path: `test-results/${info.project.name}-chemistry.png`, fullPage: true });
  await figure.getByRole('button', { name: 'Ampliar figura', exact: true }).click();
  const chemicalDialog = page.getByRole('dialog', { name: 'Figura da questão 92', exact: true });
  await expect(chemicalDialog.locator('.figure-equation .katex')).toHaveCount(2);
  await expect(chemicalDialog.locator('figcaption')).toContainText('QUINTO, A. C.');
  await page.getByRole('button', { name: 'Fechar ampliação' }).click();
  await page.getByRole('button', { name: 'Alternar tema' }).click();
  await figure.getByRole('button', { name: 'Ampliar figura', exact: true }).click();
  await expect(chemicalDialog).toBeVisible();
  expect(context.pages()).toHaveLength(tabs);
  await expect(page.locator('.katex-error')).toHaveCount(0);
  await page.screenshot({ path: `test-results/${info.project.name}-figure-dialog.png` });
  await page.keyboard.press('Escape');
  for (const number of [94, 97, 99, 100, 114, 116, 118, 123, 128, 132, 133, 135, 170]) {
    if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Abrir mapa de questões' }).click();
    await page.getByRole('button', { name: new RegExp(`^Questão ${number}(,|$)`) }).click();
    await expect(page.getByRole('heading', { name: `Questão ${number}`, exact: true })).toBeVisible();
    await expect(page.locator('.katex-error')).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    if ([94, 118, 135].includes(number)) await page.screenshot({ path: `test-results/${info.project.name}-q${number}-review.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});
