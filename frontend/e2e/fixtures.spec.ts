import { test, expect } from '@playwright/test';

test.describe('Fixtures Page', () => {
  test('loads fixtures for supported leagues and updates sidebar active item', async ({
    page,
    isMobile,
  }) => {
    for (const ligaId of [1, 2, 8, 10]) {
      await page.goto(`/fixtures?liga_id=${ligaId}`);
      await expect(
        page.getByRole('heading', { name: 'Próximos Partidos' })
      ).toBeVisible();

      if (!isMobile) {
        const activeLink = page.locator(
          `aside.sidebar a[href="/fixtures?liga_id=${ligaId}"]`
        );
        await expect(activeLink).toHaveClass(/active/);
      }
    }
  });
});
