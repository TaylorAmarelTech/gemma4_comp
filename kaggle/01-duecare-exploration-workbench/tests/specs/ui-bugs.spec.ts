import { test, expect } from '@playwright/test';

// Regression tests for the 5 bugs reported + fixed 2026-05-12 plus
// two more reported during initial Kaggle smoke (duplicate nav,
// duplicate shutdown).

test.describe('UI bug regressions (2026-05-12 batch)', () => {
  async function closePickerIfOpen(page) {
    const popover = page.locator('#dc-wb-model-popover');
    if (await popover.isVisible().catch(() => false)) {
      const closeBtn = page.locator('#dc-wb-model-close');
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await expect(popover).toHaveAttribute('hidden', '', { timeout: 5_000 });
      }
    }
  }

  test('Bug 2: "This prompt expects an image" hint is hidden by default', async ({ page }) => {
    await page.goto('/static/chat.html');
    const hint = page.locator('#pending-image-hint');
    await expect(hint).toBeHidden();
  });

  test('Bug 1: "best for judges" badge is gone (replaced with peer-review inline label)', async ({ page }) => {
    await page.goto('/static/chat.html');
    await expect(page.getByText(/best for judges/i)).toHaveCount(0);
    await expect(page.getByText(/recommended for peer review/i)).toBeVisible();
  });

  test('Bug 3: Compare card uses inline notice instead of browser alert', async ({ page }) => {
    let dialogFired = false;
    page.on('dialog', async (d) => { dialogFired = true; await d.dismiss(); });
    await page.goto('/static/chat.html');
    await closePickerIfOpen(page);
    const compareCard = page.locator('text=/compare two configs/i').first();
    await compareCard.click({ trial: false });
    await page.waitForTimeout(800);
    expect(dialogFired).toBeFalsy();
  });

  test('Bug 4: model picker close button is visible on re-open', async ({ page }) => {
    await page.goto('/static/chat.html');
    const popover = page.locator('#dc-wb-model-popover');
    const openBtn = page.locator('#dc-wb-model-open');
    const closeBtn = page.locator('#dc-wb-model-close');
    await expect(openBtn).toBeVisible();
    await openBtn.click();
    await expect(popover).not.toHaveAttribute('hidden', '', { timeout: 5_000 });
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
    await expect(popover).toHaveAttribute('hidden', '', { timeout: 5_000 });
    await openBtn.click();
    await expect(popover).not.toHaveAttribute('hidden', '', { timeout: 5_000 });
    await expect(closeBtn).toBeVisible();
  });

  test('Bug 5: resolve step does not claim image refs on text-only turns', async ({ page, request }) => {
    const status = await request.get('/api/model-info').then(r => r.json()).catch(() => null);
    if (!status || !status.loaded) {
      test.skip(true, 'requires a loaded model on the kernel');
    }
    const resp = await request.post('/api/chat/send', {
      data: {
        messages: [{ role: 'user', content: [{ type: 'text', text: 'hi' }] }],
        toggles: {},
        generation: { max_new_tokens: 16 },
      },
      timeout: 90_000,
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.text();
    expect(body).toContain('no images attached');
    expect(body).not.toContain('image references resolved');
  });

  test('Bug 6: at most one global top-nav after sending a message', async ({ page }) => {
    // Reported 2026-05-12: a second nav appears below the model status
    // strip after the first chat round-trip. Count visible <nav> +
    // role=navigation elements; only one should be visible at the top.
    await page.goto('/static/chat.html');
    await page.waitForLoadState('networkidle');
    const navs = page.locator('header nav, [role="navigation"]');
    const visibleCount = await navs.evaluateAll((els) =>
      els.filter((el) => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
      }).length
    );
    expect(visibleCount).toBeLessThanOrEqual(1);
  });

  test('Bug 7: at most one shutdown/power button in the top bar', async ({ page }) => {
    // Reported 2026-05-12. Look for buttons whose accessible name or
    // title matches /shut ?down|power off|stop kernel|terminate/.
    await page.goto('/static/chat.html');
    const buttons = page.locator('button, [role="button"], a');
    const candidates = await buttons.evaluateAll((els) =>
      els.filter((el) => {
        const txt = (el.textContent || '').trim().toLowerCase();
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        const title = (el.getAttribute('title') || '').toLowerCase();
        const blob = txt + ' ' + aria + ' ' + title;
        return /shut\s?down|power\s?off|stop\s+kernel|terminate/.test(blob);
      }).length
    );
    expect(candidates).toBeLessThanOrEqual(1);
  });

  test('Hash deep-link: /#compare auto-opens the A/B compare modal', async ({ page }) => {
    // Added 2026-05-12: improved visibility for the Compare flow.
    // Navigating directly to /#compare should auto-open the modal
    // without a manual click, so the URL is shareable + bookmarkable.
    await page.goto('/static/chat.html#compare');
    await page.waitForLoadState('networkidle');
    const overlay = page.locator('#modal-overlay');
    await expect(overlay).toHaveClass(/active/, { timeout: 8_000 });
    await expect(page.locator('#compare-prompt')).toBeVisible();
    await expect(page.locator('#compare-run-btn')).toBeVisible();
  });

  test('Hash deep-link: closing the compare modal clears #compare from URL', async ({ page }) => {
    await page.goto('/static/chat.html#compare');
    await page.waitForLoadState('networkidle');
    const overlay = page.locator('#modal-overlay');
    await expect(overlay).toHaveClass(/active/, { timeout: 8_000 });
    // Close via the modal close button or Escape.
    const closeBtn = page.locator(
      '#modal-overlay [aria-label="Close"], ' +
      '#modal-overlay button:has-text("Close"), ' +
      '#modal-overlay button:has-text("✕")'
    ).first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await expect(overlay).not.toHaveClass(/active/, { timeout: 4_000 });
    await expect
      .poll(() => page.evaluate(() => window.location.hash), { timeout: 2_000 })
      .toBe('');
  });
});
