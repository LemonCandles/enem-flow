import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

test('acessibilidade automática, teclado, temas e reflow da jornada', async ({ page }, info) => {
  test.setTimeout(180_000);
  const violations: unknown[] = [];
  async function audit(label: string) {
    const result = await new AxeBuilder({ page }).analyze();
    const report = info.outputPath(`axe-${label}.json`);
    await writeFile(report, JSON.stringify(result, null, 2));
    await info.attach(`axe-${label}`, { path: report, contentType: 'application/json' });
    violations.push(...result.violations.map(v => ({ view: label, id: v.id, impact: v.impact, targets: v.nodes.map(n => n.target) })));
  }
  await page.goto('/');
  await expect(page.getByLabel('E-mail', { exact: true })).toBeVisible();
  await audit('login');
  expect((await page.request.post('/api/auth/register', { data: { name: 'Teste de Acessibilidade', email: `a11y-${info.project.name}-${Date.now()}@example.com`, password: 'senha-a11y-consolidacao-2026' } })).status()).toBe(201);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Aprender, no seu tempo/ })).toBeVisible();
  await audit('inicio-claro');
  await page.getByRole('button', { name: 'Alternar tema' }).click();
  await audit('inicio-escuro');
  for (const [url, title] of [['/exams','Banco de provas'],['/history','Histórico'],['/progress','Meu desempenho'],['/settings','Configurações']]) {
    await page.goto(url);
    await expect(page.locator('main h1')).toBeVisible();
    await audit(url.slice(1));
  }
  const response = await page.request.post('/api/exam-runs', { data: { exam_id: 'enem-2024-dia2-azul', idempotency_key: `a11y-${Date.now()}` } });
  const run = await response.json();
  await page.goto(`/runs/${run.id}`);
  await expect(page.getByRole('heading', { name: 'Questão 91', exact: true })).toBeVisible();
  await page.getByRole('radio', { name: /^B absorve/ }).check();
  await expect(page.getByText('Resposta salva', { exact: true })).toBeVisible();
  await audit('questao-com-resposta');
  const enlarge = page.getByRole('button', { name: 'Ampliar figura', exact: true }).first();
  await enlarge.focus(); await page.keyboard.press('Enter');
  const figure = page.getByRole('dialog', { name: 'Figura da questão 91' });
  await expect(figure).toBeVisible();
  await audit('figura-dialogo');
  await page.bringToFront();
  await figure.getByRole('button', { name: 'Fechar ampliação' }).focus();
  // Focus stays inside the native dialog throughout keyboard navigation.
  for (let i=0;i<8;i++) {
    await page.keyboard.press('Tab');
    expect(await figure.evaluate(el => el.contains(document.activeElement))).toBeTruthy();
  }
  await page.keyboard.press('Escape');
  await expect(enlarge).toBeFocused();
  if (info.project.name === 'mobile') await page.getByRole('button', { name: 'Abrir mapa de questões' }).click();
  await page.getByRole('button', { name: 'Finalizar prova', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Pronto para finalizar?' })).toBeVisible();
  await audit('confirmacao');
  await page.getByRole('button', { name: 'Confirmar finalização' }).click();
  await expect(page.getByText('Resultado definitivo', { exact: true })).toBeVisible();
  await audit('resultado');
  // 640 CSS pixels reproduce the layout width of a 1280px viewport at 200%.
  await page.setViewportSize({ width: 640, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.goto('/progress');
  await expect(page.locator('main h1')).toBeVisible();
  await audit('desempenho-com-resultado');
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
  expect(violations).toEqual([]);
});

test('caderno completo mantém texto, fórmulas e recursos legíveis', async ({ page }, info) => {
  test.setTimeout(180_000);
  expect((await page.request.post('/api/auth/register', { data: { name: 'Teste do Caderno', email: `booklet-${info.project.name}-${Date.now()}@example.com`, password: 'senha-caderno-consolidacao' } })).status()).toBe(201);
  const response = await page.request.post('/api/exam-runs', { data: { exam_id: 'enem-2024-dia2-azul', idempotency_key: `booklet-${Date.now()}` } });
  const run = await response.json();
  expect(run.items).toHaveLength(90);
  await page.goto(`/runs/${run.id}`);
  for (let number=91;number<=180;number++) {
    await expect(page.getByRole('heading', { name: `Questão ${number}`, exact: true })).toBeVisible();
    await expect(page.locator('.katex-error')).toHaveCount(0);
    await expect(page.locator('.native-question')).not.toBeEmpty();
    const broken = await page.locator('.question-content img, .alternatives img').evaluateAll(images => images.filter(el => !(el as HTMLImageElement).complete || !(el as HTMLImageElement).naturalWidth).map(el => el.getAttribute('src')));
    // Poll for images instead of accepting a cached/late-loading blank figure.
    if (broken.length) await expect.poll(async () => page.locator('.question-content img, .alternatives img').evaluateAll(images => images.every(el => (el as HTMLImageElement).complete && (el as HTMLImageElement).naturalWidth > 0))).toBeTruthy();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Questão ${number}`).toBeTruthy();
    if (number<180) await page.getByRole('button', { name: 'Próxima questão' }).click();
  }
  expect((await page.request.delete('/api/me/history')).status()).toBe(204);
});
