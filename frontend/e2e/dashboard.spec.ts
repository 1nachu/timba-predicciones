import { test, expect } from '@playwright/test';

test.describe('Dashboard Page (SSR)', () => {
  test('renders matches of the day and includes SSR content in raw HTML', async ({
    page,
    request,
  }) => {
    const rawRes = await request.get('/');
    expect(rawRes.status()).toBe(200);
    const html = await rawRes.text();
    expect(html).toContain('PARTIDOS DE HOY');
    expect(html).toContain('Arsenal');

    await page.goto('/');
    await expect(
      page.getByText('PARTIDOS DE HOY', { exact: true })
    ).toBeVisible();
    await expect(page.getByText('Arsenal').first()).toBeVisible();
    await expect(page.getByText('Chelsea').first()).toBeVisible();
  });
});
