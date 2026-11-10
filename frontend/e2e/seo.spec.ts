import { test, expect } from '@playwright/test';

test.describe('SEO & API Proxy', () => {
  test('serves robots.txt, sitemap.xml, OG tags and proxies /api/v1/health', async ({
    request,
  }) => {
    const robots = await request.get('/robots.txt');
    expect(robots.status()).toBe(200);
    expect(await robots.text()).toContain('Sitemap:');

    const sitemap = await request.get('/sitemap.xml');
    expect(sitemap.status()).toBe(200);
    expect(await sitemap.text()).toContain('/predict');

    const health = await request.get('/api/v1/health');
    expect(health.status()).toBe(200);
    const json = await health.json();
    expect(json.status).toBe('ok');
  });
});
