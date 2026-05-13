import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('accessibility', () => {

  test('homepage has no critical axe violations', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const critical = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    if (critical.length) {
      console.log('CRITICAL/SERIOUS a11y violations:',
        critical.map(v => ({ id: v.id, nodes: v.nodes.length, help: v.helpUrl })));
    }
    expect(critical, JSON.stringify(critical, null, 2)).toEqual([]);
  });

  test('all images have alt text', async ({ page }) => {
    await page.goto('/');
    const imgs = await page.locator('img').all();
    for (const img of imgs) {
      const alt = await img.getAttribute('alt');
      const ariaHidden = await img.getAttribute('aria-hidden');
      const role = await img.getAttribute('role');
      expect(
        alt !== null || ariaHidden === 'true' || role === 'presentation',
        `<img> without alt or aria-hidden`,
      ).toBeTruthy();
    }
  });

  test('all buttons have accessible names', async ({ page }) => {
    await page.goto('/');
    const buttons = await page.locator('button').all();
    let missing = 0;
    for (const btn of buttons) {
      const visible = await btn.isVisible().catch(() => false);
      if (!visible) continue;
      const name = (await btn.textContent())?.trim()
        || await btn.getAttribute('aria-label')
        || await btn.getAttribute('title');
      if (!name) missing++;
    }
    expect(missing).toBe(0);
  });
});
