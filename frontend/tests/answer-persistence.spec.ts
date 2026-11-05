import { expect, test } from '@playwright/test';

// A reload right after choosing must not lose the answer that is still being saved.
test('resposta marcada sobrevive a recarregar a página logo em seguida', async ({ page }, info) => {
  test.setTimeout(120_000);
  const email = `e2e-reload-${info.project.name}-${Date.now()}@example.com`;
  const registered = await page.request.post('/api/auth/register', {
    data: { name: 'Estudante de Teste', email, password: 'senha-teste-segura-2026' },
  });
  expect(registered.status()).toBe(201);
  const started = await page.request.post('/api/exam-runs', {
    data: { exam_id: 'enem-2024-dia2-azul', idempotency_key: `reload-${Date.now()}` },
  });
  expect(started.status()).toBe(201);
  const run = await started.json();
  await page.goto(`/runs/${run.id}`);
  for (const letter of ['B', 'C', 'D', 'E', 'A', 'C', 'B', 'D', 'A', 'E', 'B', 'C']) {
    const radio = page.locator(`input[type="radio"][value="${letter}"]`);
    await expect(radio).toBeEnabled();
    await radio.check();
    await page.reload();
    await expect(radio, `a alternativa ${letter} deve continuar marcada`).toBeChecked();
  }
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});

test('resposta que não chegou a ser enviada é reenviada ao voltar à página', async ({ page }, info) => {
  const email = `e2e-resend-${info.project.name}-${Date.now()}@example.com`;
  const registered = await page.request.post('/api/auth/register', {
    data: { name: 'Estudante de Teste', email, password: 'senha-teste-segura-2026' },
  });
  expect(registered.status()).toBe(201);
  const started = await page.request.post('/api/exam-runs', {
    data: { exam_id: 'enem-2024-dia2-azul', idempotency_key: `resend-${Date.now()}` },
  });
  const run = await started.json();
  await page.goto(`/runs/${run.id}`);
  // The first save never reaches the API, like a request cut off by a bad connection.
  await page.route('**/answers/**', () => {}, { times: 1 });
  const radio = page.locator('input[type="radio"][value="D"]');
  await radio.check();
  await page.reload();
  await expect(radio).toBeChecked();
  await expect(page.getByText('Resposta salva', { exact: true })).toBeVisible();
  const saved = await (await page.request.get(`/api/exam-runs/${run.id}`)).json();
  expect(Object.values(saved.answers)).toEqual(['D']);
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});
