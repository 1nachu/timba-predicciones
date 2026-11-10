import { test, expect } from '@playwright/test';

test.describe('Base Layout & Navigation', () => {
  test('renders navbar, footer, main content and opens Bitcoin modal', async ({
    page,
    isMobile,
  }) => {
    await page.goto('/');
    await expect(page.locator('nav.navbar-promiedos')).toBeVisible();
    await expect(page.locator('main.main-content')).toBeVisible();
    await expect(page.locator('footer')).toContainText('Timba Team');

    if (isMobile) {
      await expect(page.locator('.mobile-nav')).toBeVisible();
      await page.getByRole('link', { name: 'Donar' }).click();
      await expect(page.locator('#mobiledonateModal')).toBeVisible();
      await page.getByRole('button', { name: /Bitcoin/i }).click();
      await expect(page.locator('#bitcoinModal')).toBeVisible();
    } else {
      await expect(page.locator('aside.sidebar')).toBeVisible();
      await page.locator('#donateDropdown').click();
      await page.getByRole('button', { name: /Bitcoin/i }).click();
      await expect(page.locator('#bitcoinModal')).toBeVisible();
    }
  });
});
