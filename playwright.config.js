const { defineConfig } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
// Keep browser profiles in a writable, ignored location on Windows agent hosts.
if (process.platform === 'win32') {
  const temp = path.join(__dirname, 'playwright/.cache/tmp');
  fs.mkdirSync(temp, { recursive: true });
  process.env.TEMP = temp;
  process.env.TMP = temp;
}
module.exports = defineConfig({
  timeout: 90000,
  globalTimeout: 240000,
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:4173',
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run test:serve',
    url: 'http://127.0.0.1:4173/tests/fixtures/parent.html',
    reuseExistingServer: false,
  },
});
