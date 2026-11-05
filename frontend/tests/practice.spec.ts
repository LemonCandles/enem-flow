import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('prática mostra o motivo de cada questão, usa a evidência e entra no histórico', async ({ page }, info) => {
  test.setTimeout(120_000);
  const email = `e2e-practice-${info.project.name}-${Date.now()}@example.com`;
  const registered = await page.request.post('/api/auth/register', {
    data: { name: 'Estudante de Teste', email, password: 'senha-teste-segura-2026' },
  });
  expect(registered.status()).toBe(201);
  await page.goto('/practice');
  await expect(page.getByRole('heading', { name: 'Iniciar prática', exact: true })).toBeVisible();
  await expect(page.getByText('Suas recomendações aparecerão aqui')).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByLabel('Objetivo', { exact: true }).fill('Praticar por pouco tempo');
  await page.getByLabel('Área', { exact: true }).selectOption('Matemática');
  await page.getByLabel('Tempo disponível em minutos').fill('6');
  await page.getByRole('button', { name: 'Começar prática' }).click();
  await expect(page.getByRole('heading', { name: 'Questão 01', exact: true })).toBeVisible();
  await expect(page.locator('.notice-box', { hasText: 'Por que esta questão?' })).toContainText('Exploração do tema');
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  const id = page.url().split('/').at(-1);
  const audit = await (await page.request.get(`/api/practice-sessions/${id}/recommendations`)).json();
  expect(audit.selection.version).toBe('adaptive-v1');
  expect(audit.recommendations).toHaveLength(2);
  expect(JSON.stringify(audit)).not.toContain('correct_answer');
  await page.getByRole('radio').first().check();
  await expect(page.getByText('Resposta salva', { exact: true })).toBeVisible();
  await page.goto('/history');
  await page.getByRole('link', { name: 'Continuar prática' }).click();
  await expect(page.getByRole('radio', { checked: true })).toHaveCount(1);
  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Abrir mapa de questões' }).click();
  await page.getByRole('button', { name: 'Finalizar prática', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('1 de 2 questões');
  await page.getByRole('button', { name: 'Confirmar finalização' }).click();
  await expect(page.getByText('Resultado definitivo', { exact: true })).toBeVisible();
  await expect(page.getByText('PRÁTICA CONCLUÍDA', { exact: true })).toBeVisible();
  const state = await (await page.request.get('/api/me/knowledge-state')).json();
  expect(state.themes.some((g: { independent_attempts: number }) => g.independent_attempts === 1)).toBeTruthy();
  await page.goto('/practice');
  await expect(page.getByRole('heading', { name: 'Exploração', exact: true }).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.goto('/history');
  await expect(page.getByRole('link', { name: 'Ver prática' })).toHaveCount(1);
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
  expect(await (await page.request.get('/api/me/recommendations')).json()).toEqual([]);
});
