import { test, expect } from '@playwright/test';
import path from 'path';

const repoRoot = path.resolve(__dirname, '..', '..', '..', '..');
const samplesRoot = path.join(
  repoRoot,
  'packages',
  'duecare-llm-chat',
  'src',
  'duecare',
  'chat',
  'static',
  'samples',
);

function activityLog(page) {
  return page.locator('#wb-log, #page-activity-log, #cmp-log, #search-log, [aria-label="Activity log"]').first();
}

async function sharedModelPopoverOpen(page) {
  const popover = page.locator('#dc-wb-model-popover');
  return await popover.evaluate((el) => !el.hasAttribute('hidden')).catch(() => false);
}

test.describe('cross-page workflow clicks', () => {
  test('primary workbench pages load and expose activity logs', async ({ page }) => {
    for (const route of [
      '/static/chat.html',
      '/static/compare.html',
      '/static/process.html',
      '/static/knowledge.html',
      '/static/search.html',
      '/static/share.html',
    ]) {
      const response = await page.goto(route);
      expect(response?.status(), route).toBe(200);
      await expect(page.locator('body')).toContainText(/DueCare|Harness|Knowledge|Search|Sharing|Review/i);
      await expect(activityLog(page), route).toBeVisible({ timeout: 10_000 });
    }
  });

  test('model selector opens from the shared top bar on process page', async ({ page }) => {
    await page.goto('/static/process.html');
    if (!(await sharedModelPopoverOpen(page))) {
      await page.locator('#dc-wb-model-open').click();
    }
    await expect(page.locator('#dc-wb-model-popover')).not.toHaveAttribute('hidden', '', { timeout: 5_000 });
    await expect(page.locator('#dc-wb-model-select')).toBeVisible();
    await expect(page.locator('#dc-wb-model-load')).toBeVisible();
    // The deterministic local fixture starts loaded, so it also proves the
    // shared selector exposes the current-model unload control.
    await expect(page.locator('#dc-wb-model-unload')).toBeVisible();
  });

  test('process page can upload the media-rich source bundle and reach results', async ({ page }) => {
    await page.goto('/static/process.html');
    const sample = path.join(samplesRoot, 'case_files_media_rich_sample.zip');
    await page.locator('#wb-file-input').setInputFiles(sample);
    await expect(page.locator('#wb-process-btn')).toBeEnabled({ timeout: 5_000 });
    await page.locator('#wb-process-btn').click();
    await expect(page.locator('#wb-process-progress-label')).toContainText(/100%/i, { timeout: 60_000 });
    await expect(page.getByRole('heading', { name: 'Extracted intelligence', exact: true })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText('Evidence edges', { exact: true })).toBeVisible();
    await expect(activityLog(page)).toContainText('/api/process/batch/start');
  });

  test('knowledge page can use source text and draft suggestions', async ({ page }) => {
    await page.goto('/static/knowledge.html');
    const gemmaToggle = page.locator('#kx-use-gemma');
    await expect(gemmaToggle).toBeChecked();
    await gemmaToggle.uncheck();
    await expect(gemmaToggle).not.toBeChecked();
    await page.locator('#kx-raw').fill(
      'Recruiter message: worker agrees to a PHP 45,000 processing loan, deducted from salary in Hong Kong. Agency: Pearl Bridge Manpower. Corridor: PH-HK.',
    );
    await page.getByRole('button', { name: /continue to draft/i }).click();
    await page.locator('#kx-extract-btn').click();
    await expect(page.locator('#kx-extract-status')).toContainText(/draft suggestions ready|review/i, {
      timeout: 20_000,
    });
    await expect(page.locator('#kx-extract-result')).toContainText(/knowledge_object_type|schema_version|draft/i);
    await expect(activityLog(page)).toBeVisible();
  });

  test('search page sanitizes and drafts from deterministic result cards', async ({ page }) => {
    await page.goto('/static/search.html');
    await page.locator('#q').fill('Hong Kong Employment Agency Fined');
    await page.locator('#go-btn').click();
    await expect(activityLog(page)).toContainText('/api/search/sanitize', { timeout: 10_000 });
    await expect(page.locator('#status')).toContainText(/results=/i, { timeout: 20_000 });
    await page.locator('#draft-btn').click();
    await expect(page.locator('#draft-status')).toContainText(/drafting|draft/i, { timeout: 10_000 });
    await expect(activityLog(page)).toContainText('/api/search/client');
  });

  test('share page accepts knowledge files wording and sample links', async ({ page }) => {
    await page.goto('/static/share.html');
    await expect(page.getByText(/knowledge files/i).first()).toBeVisible();
    await expect(page.locator('a[href="/static/samples/knowledge_files_sample.zip"]')).toBeVisible();
    await expect(page.locator('a[href="/static/samples/case_files_media_rich_sample.zip"]')).toBeVisible();
  });

  test('compare page defaults import layer off and opens examples', async ({ page }) => {
    await page.goto('/static/compare.html');
    await expect(page.locator('#A-import_corpus')).not.toBeChecked();
    await expect(page.locator('#B-import_corpus')).not.toBeChecked();
    await page.getByRole('button', { name: /unified ph-hk demo/i }).click();
    await expect(page.locator('#cmp-prompt')).toHaveValue(/Philippine|Hong Kong|salary deduction|placement fee/i);
  });
});
