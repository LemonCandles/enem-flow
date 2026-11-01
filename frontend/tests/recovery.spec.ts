import { expect, test } from '@playwright/test';

test.use({ video: 'off' });

for (const activeSession of [false, true]) {
  test(`recuperação abre e conclui com sessão ${activeSession ? 'ativa' : 'ausente'}`, async ({ page }) => {
    const token = 'token-sintetico-exclusivo-para-recuperacao';
    let completed = false;
    let profileCalls = 0;
    await page.route('**/api/me', route => {
      profileCalls++;
      return route.fulfill(activeSession && !completed ? { json: {
        id: 'recovery-user', name: 'Teste', email: 'recovery@example.com', role: 'student', preferences: {},
      } } : { status: 401, json: { detail: 'Entre na sua conta.' } });
    });
    await page.route('**/api/auth/reset-password', async route => {
      expect(route.request().postDataJSON()).toEqual({ token, password: 'nova-senha-de-recuperacao' });
      completed = true;
      await route.fulfill({ json: { message: 'Senha atualizada. Entre novamente.' } });
    });
    await page.goto(`/?recovery=${token}`);
    await expect(page.getByRole('heading', { name: 'Uma nova senha.' })).toBeVisible();
    expect(new URL(page.url()).search).toBe('');
    expect(profileCalls).toBe(0);
    await page.getByLabel('Nova senha', { exact: true }).fill('nova-senha-de-recuperacao');
    await page.getByRole('button', { name: 'Atualizar senha', exact: true }).click();
    await expect(page.getByText('Senha atualizada. Entre com sua nova senha.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Entrar na minha conta', exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('button', { name: 'Entrar na minha conta', exact: true })).toBeVisible();
    expect(completed).toBe(true);
  });
}
