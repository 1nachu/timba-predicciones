import { test, expect } from '@playwright/test';

test.describe('Live Page & SWR Polling', () => {
  test('renders live scores and updates via client revalidation without reload', async ({
    page,
  }) => {
    await page.goto('/live');
    await expect(
      page.getByRole('heading', { name: 'PARTIDOS EN VIVO' })
    ).toBeVisible();
    await expect(page.getByText('Arsenal').first()).toBeVisible();

    await page.route('**/api/v1/live', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total: 1,
          es_demo: false,
          partidos: [
            {
              status: 'IN_PLAY',
              seccion: 'live',
              minute: 75,
              competition: { name: 'Premier League', area: { name: 'England' } },
              homeTeam: { name: 'Arsenal' },
              awayTeam: { name: 'Chelsea' },
              score: { fullTime: { home: 3, away: 1 } },
            },
          ],
        }),
      });
    });

    await page.locator('button[title="Recargar ahora"]').click();
    await expect(page.getByText("75'")).toBeVisible();
  });
});
