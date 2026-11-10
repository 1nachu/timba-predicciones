import { test, expect } from '@playwright/test';

test.describe('History Page', () => {
  test('filters by league and days and shows warning on invalid league code', async ({
    page,
  }) => {
    await page.goto('/history?league_code=E0&days=7');
    await expect(
      page.getByRole('heading', { name: 'Auditoría de Predicciones' })
    ).toBeVisible();
    await expect(page.getByText('PRECISIÓN GLOBAL')).toBeVisible();

    await page.goto('/history?league_code=INVALID&days=14');
    await expect(page.getByText(/no soportada/i)).toBeVisible();
  });
});
