import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const json = (body: unknown, status = 200) => ({ status, contentType: 'application/json', body: JSON.stringify(body) });

test('curadoria compara a proposta de layout com o original antes de aprovar', async ({ page }) => {
  const content = {
    number: 12,
    area: 'Matemática',
    statement: 'Observe o gráfico e responda.',
    blocks: [{ type: 'paragraph', text: 'Observe o gráfico e responda. Figura 1 Fonte: Inep.' }],
    images: [],
    alternatives: 'ABCDE'.split('').map(letter => ({ letter, text: `Opção ${letter}` })),
    correct_answer: 'C',
    annulled: false,
    page: 4,
    labels: { discipline: 'Matemática', themes: [], skills: [] },
    original_layout: false,
  };
  const converted = {
    ...content,
    blocks: [
      { type: 'paragraph', text: 'Observe o gráfico e responda.' },
      { type: 'math', tex: 'y = 2x + 1' },
    ],
  };
  const exam = {
    id: 'prova-layout',
    title: 'Prova com layout',
    year: 2025,
    booklet: 'Azul',
    status: 'published',
    expected_items: 1,
    item_count: 1,
    approved_items: 1,
    source: { url: 'https://example.org/prova.pdf' },
  };
  const item = { id: 'layout-q12:1', question_id: 'layout-q12', version: 1, status: 'approved', content };
  let reviewed: { action: string; compared_with_source: boolean } | undefined;
  await page.route('**/api/me', route =>
    route.fulfill(json({ id: 'curador', name: 'Curadoria', email: 'c@example.org', role: 'admin', preferences: {} })),
  );
  await page.route('**/api/admin/exams', route => route.fulfill(json([exam])));
  await page.route('**/api/admin/audit', route => route.fulfill(json([])));
  await page.route('**/api/admin/archive', route => route.fulfill(json({ years: [], files: [], coverage: {} })));
  await page.route('**/api/admin/tutor/status', route =>
    route.fulfill(json({ enabled: false, missing: ['GROQ_API_KEY'], model: null, daily_limit: 40 })),
  );
  await page.route('**/api/admin/tutor/exams/*', route =>
    route.fulfill(json({ exam: { id: 'prova-layout', title: exam.title }, items: [] })),
  );
  await page.route('**/api/admin/exams/prova-layout', route => route.fulfill(json({ ...exam, items: [item] })));
  await page.route('**/api/admin/layout/questions/*', route =>
    route.fulfill(
      json({
        published: content,
        source_url: 'https://example.org/prova.pdf',
        page: 4,
        proposals: [
          {
            id: 'proposta-1',
            question_version_id: 'layout-q12:1',
            adapter_version: 'layout-adapter-v1',
            status: reviewed ? 'approved' : 'proposal',
            errors: [],
            comparison: {
              preserved_ratio: 0.8,
              missing_words: 3,
              extra_words: 4,
              missing_sample: ['figura', 'fonte', 'inep'],
              blocks_before: 1,
              blocks_after: 2,
              figures_before: 0,
              figures_after: 0,
            },
            converted,
            result_version_id: null,
          },
        ],
      }),
    ),
  );
  await page.route('**/api/admin/layout/proposals/proposta-1/review', route => {
    reviewed = route.request().postDataJSON();
    return route.fulfill(json({ id: 'proposta-1', status: 'approved', result_version_id: 'layout-q12:2' }));
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Revisar', exact: true }).click();
  const section = page.getByRole('region', { name: 'Layout proposto' });
  await expect(section).toContainText('Texto preservado: 80%');
  await expect(section).toContainText('ausentes: figura, fonte, inep');
  await expect(section.getByText('PROPOSTO · layout-adapter-v1')).toBeVisible();
  await expect(section.getByRole('link', { name: /página 4 do caderno original/ })).toHaveAttribute(
    'href',
    'https://example.org/prova.pdf#page=4',
  );
  const approve = section.getByRole('button', { name: 'Aprovar e criar rascunho' });
  await expect(approve).toBeDisabled();
  await section.getByLabel(/Comparei a proposta com o caderno original/).check();
  await section.getByLabel('Justificativa').fill('Ordem e fórmula conferidas na página 4.');
  await approve.click();
  // Approval reloads the exam, which now carries the draft created from the proposal.
  await expect(page.getByText('Rascunho com o novo layout carregado.')).toBeVisible();
  expect(reviewed).toMatchObject({ action: 'approve', compared_with_source: true });
  await expect(section).toBeVisible();
  expect((await new AxeBuilder({ page }).include('.layout-review').analyze()).violations).toEqual([]);
});
