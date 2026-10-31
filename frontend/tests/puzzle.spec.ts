import { expect, test } from '@playwright/test';
import { PUZZLE_JOIN_PATHS } from '../src/lib/puzzle-geometry';

test('peças do layout têm contornos complementares e não se sobrepõem', async ({ page }) => {
  // Read-only UI fixtures keep this geometric check independent of accounts/DB.
  const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  await page.route('**/api/me', route => route.fulfill(json({ id: 'design-fixture', name: 'Estudante', email: 'design@example.com', role: 'student', preferences: {} })));
  await page.route('**/api/exams', route => route.fulfill(json([])));
  await page.route('**/api/me/history', route => route.fulfill(json([])));
  await page.route('**/api/me/progress', route => route.fulfill(json({ completed_runs: 0, summary: { total: 0, answered: 0, correct: 0, incorrect: 0, unanswered: 0, annulled: 0, percentage: null } })));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Aprender, no seu tempo/ })).toBeVisible();
  const graphic = page.locator('.home-intro .learning-pieces');
  await expect(graphic.locator('[data-piece-outline]')).toHaveCount(3);

  const geometry = await graphic.evaluate((svg, joins) => {
    const ns = 'http://www.w3.org/2000/svg';
    const probe = document.createElementNS(ns, 'svg');
    probe.style.cssText = 'position:fixed;left:-10000px;width:400px;height:420px';
    document.body.appendChild(probe);
    const shapes = new Map<string, SVGPathElement>();
    const offsets = new Map<string, DOMMatrix>();
    for (const group of svg.querySelectorAll<SVGGElement>('[data-puzzle-piece]')) {
      const source = group.querySelector<SVGPathElement>('[data-piece-outline]')!;
      const clone = document.createElementNS(ns, 'path');
      clone.setAttribute('d', source.getAttribute('d')!);
      clone.setAttribute('fill', 'black');
      probe.appendChild(clone);
      shapes.set(group.dataset.puzzlePiece!, clone);
      offsets.set(group.dataset.puzzlePiece!, group.transform.baseVal.consolidate()!.matrix.inverse());
    }
    const inside = (id: string, p: DOMPoint) => shapes.get(id)!.isPointInFill(p);
    const mismatches: string[] = [];
    for (const [name, d, a, b] of [
      ['reading/practice', joins.readingPractice, 'reading', 'practice'],
      ['reasoning/practice', joins.reasoningPractice, 'reasoning', 'practice'],
    ]) {
      const seam = document.createElementNS(ns, 'path');
      seam.setAttribute('d', d);
      probe.appendChild(seam);
      const length = seam.getTotalLength();
      // Test both sides of every curved boundary against the actual closed pieces.
      for (let i = 1; i < 100; i++) {
        const at = length * i / 100;
        const p = seam.getPointAtLength(at);
        const before = seam.getPointAtLength(at - .05);
        const after = seam.getPointAtLength(at + .05);
        const dx = after.x - before.x, dy = after.y - before.y;
        const norm = Math.hypot(dx, dy);
        const plus = new DOMPoint(p.x - dy / norm * .2, p.y + dx / norm * .2);
        const minus = new DOMPoint(p.x + dy / norm * .2, p.y - dx / norm * .2);
        if (inside(a, plus) === inside(b, plus) || inside(a, minus) === inside(b, minus) || inside(a, plus) === inside(a, minus)) mismatches.push(`${name}:${i}`);
      }
    }
    let overlaps = 0;
    for (let y = -9; y < 400; y += 3) for (let x = -19; x < 380; x += 3) {
      const p = new DOMPoint(x, y);
      const count = [...shapes.keys()].filter(id => inside(id, p.matrixTransform(offsets.get(id)!))).length;
      if (count > 1) overlaps++;
    }
    probe.remove();
    return { mismatches, overlaps };
  }, PUZZLE_JOIN_PATHS);
  expect(geometry.mismatches).toEqual([]);
  expect(geometry.overlaps).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: 'Alternar tema' }).click();
  await expect(graphic).toBeVisible();
});
