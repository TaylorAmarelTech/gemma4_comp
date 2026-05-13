import { test, expect } from '@playwright/test';

test.describe('smoke', () => {
  test('homepage returns 200 with title', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/duecare|exploration|chat/i);
  });

  test('safety harness panel is present', async ({ page }) => {
    await page.goto('/');
    const harnessSection = page.locator('#harness-tiles, [class*=harness]').first();
    await expect(harnessSection).toBeVisible({ timeout: 15_000 });
  });

  test('model picker overlay can open', async ({ page }) => {
    await page.goto('/');
    const overlay = page.locator('#picker-overlay');
    const overlayVisible = await overlay.isVisible().catch(() => false);
    if (!overlayVisible) {
      const pickBtn = page.getByRole('button', { name: /pick a model/i }).first();
      await pickBtn.click();
    }
    await expect(overlay).toHaveClass(/show/);
  });

  test('input composer + send button render', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#input')).toBeVisible();
    await expect(page.locator('#send')).toBeVisible();
  });

  test('GET /api/brand returns expected counts', async ({ request }) => {
    const resp = await request.get('/api/brand');
    expect(resp.ok()).toBeTruthy();
    const j = await resp.json();
    expect(j).toHaveProperty('grep_rules');
    expect(j).toHaveProperty('rag_docs');
    expect(j).toHaveProperty('tools');
    expect(Number(j.grep_rules)).toBeGreaterThan(0);
  });
});
