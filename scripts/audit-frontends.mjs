import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { randomBytes } from 'node:crypto';

const require = createRequire(process.env.AUDIT_TOOLS
  ? resolve(process.env.AUDIT_TOOLS, 'package.json') : import.meta.url);
const { default: lighthouse } = await import(pathToFileURL(require.resolve('lighthouse')));
const chromeLauncher = await import(pathToFileURL(require.resolve('chrome-launcher')));
const { chromium } = require('playwright');
const phase = process.argv[2];
assert(['before', 'after', 'blocked'].includes(phase), 'Usage: node scripts/audit-frontends.mjs before|after|blocked');
const runs = Number(process.env.AUDIT_RUNS || 3);
assert(Number.isInteger(runs) && runs > 0);
const origin = process.env.AUDIT_ORIGIN || 'http://127.0.0.1:8080';
const api = process.env.AUDIT_API || 'http://127.0.0.1:8000';
const directory = resolve('audit', phase);
await mkdir(directory, { recursive: true });
async function captureReports() {
  const stored = JSON.parse(await readFile(resolve(directory, 'summary.json'), 'utf8'));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1350, height: 1100 } });
    for (const target of stored.pages) {
      const sample = target.samples.find((candidate) => candidate.scores.performance === target.median.scores.performance) || target.samples[0];
      const filename = `${target.name}-${target.device}-${sample.run}.html`;
      await page.goto(`${origin}/audit/${phase}/${filename}`, { waitUntil: 'networkidle' });
      await page.waitForFunction(() => ['Performance', 'Accessibility', 'Best Practices', 'SEO']
        .every((label) => document.body.innerText.includes(label)));
      const evidence = `${target.name}-${target.device}-lighthouse.png`;
      await page.screenshot({ path: resolve(directory, evidence) });
      target.reportScreenshot = { file: evidence, source: filename, run: sample.run };
      console.log(`Captured ${phase}/${evidence} from run ${sample.run}`);
    }
    await writeFile(resolve(directory, 'summary.json'), JSON.stringify(stored, null, 2));
  } finally {
    await browser.close();
  }
}

if (process.argv.includes('--capture-reports')) {
  await captureReports();
  process.exit(0);
}

const identity = { email: 'lighthouse@example.test', password: randomBytes(24).toString('hex'), name: 'Lighthouse Audit' };
identity.email = `lighthouse-${randomBytes(6).toString('hex')}@example.test`;
async function apiJson(path, options = {}) {
  const response = await fetch(`${api}${path}`, options);
  assert(response.ok, `API ${path}: HTTP ${response.status}`);
  return response.json();
}
await apiJson('/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(identity) });
const session = await apiJson('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(identity) });
const pages = [
  { name: 'website-home', path: '/', protected: false },
  { name: 'website-registration', path: '/application.html', protected: false },
  { name: 'backoffice-dashboard', path: '/uis/backoffice/', protected: true },
];
const summaryPath = resolve(directory, 'summary.json');
const summary = process.env.AUDIT_PAGES && phase !== 'blocked'
  ? JSON.parse(await readFile(summaryPath, 'utf8'))
  : { phase, measuredAt: new Date().toISOString(), node: process.version, runs, server: 'Python http.server: static files, no dev compilation', pages: [] };
for (const target of pages) {
  if (process.env.AUDIT_PAGES && !process.env.AUDIT_PAGES.split(',').includes(target.name)) continue;
  for (const device of ['mobile', 'desktop']) {
    const viewport = device === 'mobile' ? { width: 412, height: 823 } : { width: 1350, height: 940 };
    const record = { name: target.name, device, url: `${origin}${target.path}`, samples: [] };
    for (let run = 1; run <= runs; run += 1) {
      const chrome = await chromeLauncher.launch({ chromePath: chromium.executablePath(), chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'] });
      const browser = await chromium.connectOverCDP(`http://127.0.0.1:${chrome.port}`);
      try {
        const context = browser.contexts()[0];
        const page = await context.newPage();
        await page.setViewportSize(viewport);
        await page.goto(`${origin}/application.html`, { waitUntil: 'networkidle' });
        await page.evaluate(({ token, apiBase }) => {
          localStorage.setItem('brasaland.jwt', token);
          localStorage.setItem('brasaland.apiBase', apiBase);
        }, { token: session.access_token, apiBase: api });
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        await page.goto(record.url, { waitUntil: 'networkidle' });
        if (target.protected && phase !== 'blocked') {
          await page.waitForSelector('#protectedApp:not(.hidden)');
          await page.waitForSelector('#suppliersTable tbody tr');
          record.supplierRows = await page.locator('#suppliersTable tbody tr').count();
          const resources = await page.evaluate(() => performance.getEntriesByType('resource')
            .filter((entry) => entry.name.includes(':8000/'))
            .map((entry) => ({ path: new URL(entry.name).pathname, start: entry.startTime, duration: entry.duration })));
          record.sessionRequests = resources;
          record.suppliersReadyMs = Math.max(...resources.map((entry) => entry.start + entry.duration));
        }
        record.browserErrors = errors;
        if (phase !== 'blocked') assert.deepEqual(errors, [], 'Uncaught browser errors');
        if (run === 1) {
          await page.screenshot({ path: resolve(directory, `${target.name}-${device}.png`), fullPage: true });
          record.horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
        }
        const protocol = await context.newCDPSession(page);
        await protocol.send('Network.clearBrowserCache');
        await protocol.detach();
        await page.close();
        const throttling = device === 'mobile'
          ? { rttMs: 150, throughputKbps: 1638.4, requestLatencyMs: 562.5, downloadThroughputKbps: 1474.56, uploadThroughputKbps: 675, cpuSlowdownMultiplier: 4 }
          : { rttMs: 40, throughputKbps: 10240, requestLatencyMs: 0, downloadThroughputKbps: 0, uploadThroughputKbps: 0, cpuSlowdownMultiplier: 1 };
        const result = await lighthouse(record.url, {
          port: chrome.port, output: ['json', 'html'], logLevel: 'error',
          onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
          disableStorageReset: true, formFactor: device, throttlingMethod: 'simulate', throttling,
          screenEmulation: { mobile: device === 'mobile', ...viewport, deviceScaleFactor: 1, disabled: false },
        });
        assert(!result.lhr.runtimeError, JSON.stringify(result.lhr.runtimeError));
        assert(new URL(result.lhr.finalDisplayedUrl).pathname === target.path, 'Unexpected redirect (login?)');
        const prefix = resolve(directory, `${target.name}-${device}-${run}`);
        const sanitizedJson = result.report[0].replaceAll(session.access_token, '[REDACTED]');
        const sanitizedHtml = result.report[1].replaceAll(session.access_token, '[REDACTED]');
        await writeFile(`${prefix}.json`, sanitizedJson);
        await writeFile(`${prefix}.html`, sanitizedHtml);
        const lhr = JSON.parse(sanitizedJson);
        summary.lighthouseVersion = lhr.lighthouseVersion;
        summary.browser = lhr.environment.hostUserAgent;
        const metric = (id) => lhr.audits[id]?.numericValue ?? null;
        record.samples.push({
          run, scores: Object.fromEntries(Object.entries(lhr.categories).map(([key, category]) => [key, Math.round(category.score * 100)])),
          lcpMs: metric('largest-contentful-paint'), cls: metric('cumulative-layout-shift'),
          fcpMs: metric('first-contentful-paint'), tbtMs: metric('total-blocking-time'),
          ttfbMs: metric('server-response-time'), bytes: metric('total-byte-weight'),
          failedAudits: Object.values(lhr.audits).filter((audit) => audit.score !== null && audit.score < 1)
            .map((audit) => ({ id: audit.id, title: audit.title, value: audit.displayValue })),
        });
        console.log(`${phase}: ${target.name} ${device} ${run}/${runs}`, record.samples.at(-1).scores);
      } finally {
        await browser.close();
        await chrome.kill();
      }
    }
    const median = (values) => [...values].sort((left, right) => left - right)[Math.floor(values.length / 2)];
    record.median = Object.fromEntries(['lcpMs', 'cls', 'fcpMs', 'tbtMs', 'ttfbMs', 'bytes'].map((key) => [key, median(record.samples.map((sample) => sample[key]))]));
    record.median.scores = Object.fromEntries(Object.keys(record.samples[0].scores).map((key) => [key, median(record.samples.map((sample) => sample.scores[key]))]));
    summary.pages = summary.pages.filter((existing) => existing.name !== record.name || existing.device !== device);
    summary.pages.push(record);
    await writeFile(resolve(directory, 'summary.json'), JSON.stringify(summary, null, 2));
  }
}
await apiJson(`/users/${session.user_id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${session.access_token}` } });
assert((await readFile(resolve(directory, 'summary.json'), 'utf8')).length > 0);
console.log(`Saved ${summary.pages.length * runs} reports and ${summary.pages.length} screenshots to audit/${phase}/`);