import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { chromium } from 'playwright';

const origin = process.env.AUDIT_ORIGIN || 'http://127.0.0.1:8080';
const api = process.env.AUDIT_API || 'http://127.0.0.1:8000';
const identity = {
  email: `smoke-${randomBytes(6).toString('hex')}@example.test`,
  password: randomBytes(24).toString('hex'),
  name: 'Audit Smoke',
};
const created = await fetch(`${api}/users`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(identity),
});
assert.equal(created.status, 201);
const user = await created.json();
const browser = await chromium.launch();
let token;
try {
  for (const width of [412, 1350]) {
    const page = await browser.newPage({ viewport: { width, height: 940 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`${origin}/`, { waitUntil: 'networkidle' });
    assert(await page.locator('img').evaluate((image) => image.complete && image.naturalWidth > 0));
    assert.equal(await page.locator('script[src*=tailwind]').count(), 0);
    await page.goto(`${origin}/application.html`, { waitUntil: 'networkidle' });
    await page.selectOption('#country', 'Colombia');
    await page.selectOption('#city', 'Medellin');
    await page.selectOption('#location', 'El Poblado');
    await page.locator('button').click();
    assert.equal(await page.locator('#error-name').innerText(), 'Nombre y apellido');
    assert.equal(await page.locator('#error-city').innerText(), '');
    await page.evaluate((base) => localStorage.setItem('brasaland.apiBase', base), api);
    await page.goto(`${origin}/uis/backoffice/login/`, { waitUntil: 'networkidle' });
    await page.locator('input[name=email]').fill(identity.email);
    await page.locator('input[name=password]').fill(identity.password);
    await page.locator('button[type=submit]').click();
    await page.waitForURL((url) => ['/uis/backoffice/', '/uis/backoffice/index.html'].includes(url.pathname));
    await page.waitForSelector('main[aria-busy=false]');
    token = await page.evaluate(() => localStorage.getItem('brasaland.jwt'));
    assert.equal(await page.locator('#suppliersTable tbody tr').count(), 15);
    assert.equal(await page.locator('#profileForm input[name=name]').inputValue(), identity.name);
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    assert.equal(await page.evaluate(() => performance.getEntriesByType('resource').filter((entry) => entry.name.includes('/profiles/me')).length), 0);
    assert(await page.locator('.inline-rate input').first().getAttribute('aria-label'));
    await page.selectOption('#filterCountry', 'USA');
    await page.waitForFunction(() => [...document.querySelectorAll('#suppliersTable tbody tr')]
      .length > 0 && [...document.querySelectorAll('#suppliersTable tbody tr')].every((row) => row.cells[1].textContent === 'USA'));
    await page.selectOption('#filterCountry', '');
    await page.waitForFunction(() => document.querySelectorAll('#suppliersTable tbody tr').length === 15);
    const row = page.locator('#suppliersTable tbody tr').first();
    const originalRate = await row.locator('input[name=rate]').inputValue();
    await row.locator('input[name=rate]').fill('12345');
    await row.locator('button[type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#suppliersTable tbody tr').cells[3].textContent === '12345');
    await row.locator('input[name=rate]').fill(originalRate);
    await row.locator('button[type=submit]').click();
    await page.waitForFunction((rate) => document.querySelector('#suppliersTable tbody tr').cells[3].textContent === rate, originalRate);
    await page.locator('#fileInput').setInputFiles('incidents-brasaland.csv');
    await page.locator('#analyzeBtn').click();
    await page.waitForSelector('#results:not(.hidden)');
    assert.equal(await page.locator('#kpis .kpi').count(), 4);
    const download = page.waitForEvent('download');
    await page.locator('#downloadBtn').click();
    assert.equal((await download).suggestedFilename(), 'results.csv');
    await page.locator('#profileForm input[name=name]').fill('Audit Updated');
    await page.locator('#profileForm button').click();
    await page.waitForFunction(() => document.getElementById('profileMessage').textContent.includes('actualizado'));
    await page.locator('#profileForm input[name=name]').fill(identity.name);
    await page.locator('#profileForm button').click();
    await page.waitForFunction(() => document.getElementById('profileMessage').textContent.includes('actualizado'));
    await page.evaluate(() => {
      const parent = document.getElementById('statusMessage');
      let calls = 0;
      window.BrasalandStatusActions.render(parent, { label: 'Reintentar', onAction: () => { calls += 1; } });
      window.BrasalandStatusActions.render(parent, { label: 'Reintentar', onAction: () => { calls += 1; } });
      parent.querySelector('button').click();
      if (calls !== 1 || parent.querySelectorAll('.status-actions').length !== 1) throw new Error('Duplicate status actions');
    });
    await page.goto(`${origin}/uis/web/`, { waitUntil: 'networkidle' });
    await page.waitForSelector('#protectedApp:not(.hidden)');
    assert.equal(await page.evaluate(() => typeof window.BrasalandStatusActions.render), 'function');
    await page.goto(`${origin}/uis/backoffice/`, { waitUntil: 'networkidle' });
    await page.waitForSelector('main[aria-busy=false]');
    await page.locator('#logoutBtn').click();
    await page.waitForURL(`${origin}/uis/backoffice/login/`);
    assert.equal(await page.evaluate(() => localStorage.getItem('brasaland.jwt')), null);
    assert.deepEqual(errors, []);
    await page.close();
    console.log(`PASS ${width}px: public form, login/logout, filters, rates, CSV/export, profile and shared component`);
  }
} finally {
  await browser.close();
  if (token) {
    await fetch(`${api}/users/${user.id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
  }
}