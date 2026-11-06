import { expect, test } from '@playwright/test';

test('conteúdo automático conferido não exibe aviso e salva sem armazenamento do navegador', async ({ page }, info) => {
  await page.request.post('/api/auth/register', {
    data: {
      name: 'Teste',
      email: `consistency-${info.project.name}-${Date.now()}@example.com`,
      password: 'senha-segura-2026',
    },
  });
  const catalog = await (await page.request.get('/api/exams')).json();
  const exam = catalog.find((e: { content_quality?: { origin: string } }) => e.content_quality?.origin === 'automatic');
  expect(exam).toBeTruthy();
  const started = await page.request.post('/api/exam-runs', {
    data: { exam_id: exam.id, idempotency_key: `automatic-${Date.now()}` },
  });
  expect(started.status()).toBe(201);
  const run = await started.json();
  await page.addInitScript(() => {
    const getItem = Storage.prototype.getItem;
    const setItem = Storage.prototype.setItem;
    const removeItem = Storage.prototype.removeItem;
    Storage.prototype.getItem = function (key) {
      if (key.startsWith('exam-answer-pending:')) throw new Error('Storage unavailable');
      return getItem.call(this, key);
    };
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith('exam-answer-pending:')) throw new Error('Storage unavailable');
      return setItem.call(this, key, value);
    };
    Storage.prototype.removeItem = function (key) {
      if (key.startsWith('exam-answer-pending:')) throw new Error('Storage unavailable');
      return removeItem.call(this, key);
    };
  });
  await page.goto(`/runs/${run.id}`);
  await page.getByRole('radio').first().check();
  await expect(page.getByText('Resposta salva', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('radio', { checked: true })).toHaveCount(1);
  // The bundled automatic exams were verified: no question carries a presentation warning.
  // The warning itself is covered with simulated data in archive-quality.spec.ts.
  expect(exam.content_quality.review_status).toBe('reviewed');
  expect(run.items.every((item: { preparation_errors: number }) => item.preparation_errors === 0)).toBe(true);
  await expect(page.getByText(/Esta questão tem pendências de apresentação registradas/)).toHaveCount(0);
  await page.goto(`/runs/${run.id}/extra`);
  await expect(page.getByRole('heading', { name: 'Página não encontrada' })).toBeVisible();
  await page.request.delete('/api/me/history');
});
