import { test, expect } from '@playwright/test';

test.describe('visual capture', () => {

  test('homepage screenshot', async ({ page }, info) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: `test-results/screenshots/${info.project.name}-homepage.png`,
      fullPage: true,
    });
  });

  test('model picker open', async ({ page }, info) => {
    await page.goto('/static/chat.html');
    const overlay = page.locator('#picker-overlay');
    if (!(await overlay.isVisible().catch(() => false))) {
      const btn = page.getByRole('button', { name: /pick a model/i }).first();
      if (await btn.isVisible().catch(() => false)) await btn.click();
    }
    await page.waitForTimeout(500);
    await page.screenshot({
      path: `test-results/screenshots/${info.project.name}-model-picker.png`,
      fullPage: false,
    });
  });

  test('harness toggle panel', async ({ page }, info) => {
    await page.goto('/static/chat.html');
    const harness = page.locator('#harness-tiles').first();
    await harness.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await harness.screenshot({
      path: `test-results/screenshots/${info.project.name}-harness-tiles.png`,
    });
  });

  test('empty-state Step 04 Compare card (no overlap)', async ({ page }, info) => {
    await page.goto('/static/chat.html');
    const card = page.locator('text=/compare two configs/i').first().locator('..');
    if (await card.isVisible().catch(() => false)) {
      await card.scrollIntoViewIfNeeded();
      await card.screenshot({
        path: `test-results/screenshots/${info.project.name}-step04-compare-card.png`,
      });
    }
  });
});
