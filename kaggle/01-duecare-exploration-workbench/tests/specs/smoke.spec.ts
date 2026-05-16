import { test, expect } from '@playwright/test';

async function openAnyModelSelector(page) {
  const sharedPopover = page.locator('#dc-wb-model-popover');
  if (await sharedPopover.evaluate((el) => !el.hasAttribute('hidden')).catch(() => false)) {
    return sharedPopover;
  }
  const sharedButton = page.locator('#dc-wb-model-open').first();
  if (await sharedButton.isVisible().catch(() => false)) {
    await sharedButton.click();
    await expect(sharedPopover).not.toHaveAttribute('hidden', '', { timeout: 5_000 });
    return sharedPopover;
  }

  const legacyOverlay = page.locator('#picker-overlay');
  if (await legacyOverlay.isVisible().catch(() => false)) {
    return legacyOverlay;
  }
  const legacyButton = page.getByRole('button', { name: /open model selector|pick a model/i }).first();
  await legacyButton.click();
  await expect(legacyOverlay).toBeVisible({ timeout: 5_000 });
  return legacyOverlay;
}

test.describe('smoke', () => {
  test('homepage returns 200 with title', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/duecare|exploration|chat/i);
  });

  test('safety harness panel is present', async ({ page }) => {
    await page.goto('/static/chat.html');
    const harnessSection = page.locator('#harness-tiles, [class*=harness]').first();
    await expect(harnessSection).toBeVisible({ timeout: 15_000 });
  });

  test('model picker overlay can open', async ({ page }) => {
    await page.goto('/static/chat.html');
    const selector = await openAnyModelSelector(page);
    await expect(selector).toBeVisible();
    await expect(page.locator('#dc-wb-model-select, #model-select').first()).toBeVisible();
  });

  test('input composer + send button render', async ({ page }) => {
    await page.goto('/static/chat.html');
    await expect(page.locator('#input')).toBeVisible();
    await expect(page.locator('#send')).toBeVisible();
  });

  test('GET /api/brand returns expected counts', async ({ request }) => {
    const resp = await request.get('/api/brand');
    expect(resp.ok()).toBeTruthy();
    const j = await resp.json();
    expect(j.counts).toHaveProperty('n_grep_rules');
    expect(j.counts).toHaveProperty('n_rag_docs');
    expect(j.counts).toHaveProperty('n_dimensions');
    expect(Number(j.counts.n_grep_rules)).toBeGreaterThan(0);
  });
});
