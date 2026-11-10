import { test, expect } from '@playwright/test';

test.describe('Predict Page', () => {
  test('simulates match prediction, sets dynamic OG title and warns on same team', async ({
    page,
    request,
  }) => {
    const ssrRes = await request.get(
      '/predict?liga_id=1&local=Arsenal&visitante=Chelsea'
    );
    expect(ssrRes.status()).toBe(200);
    const html = await ssrRes.text();
    expect(html).toContain('Arsenal vs Chelsea — Timba Predictor');

    await page.goto('/predict?liga_id=1&local=Arsenal&visitante=Chelsea');
    await expect(page.getByText('Goles Esperados (xG)')).toBeVisible();
    await expect(page.getByText('Telemetría de Córners')).toBeVisible();

    await page.selectOption('select[name="local"]', 'Arsenal');
    await page.selectOption('select[name="visitante"]', 'Arsenal');
    await page.getByRole('button', { name: /Simular Predicción/i }).click();
    await expect(
      page.getByText(/Debes seleccionar dos equipos diferentes/i)
    ).toBeVisible();
  });
});
