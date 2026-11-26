const { test, expect } = require('@playwright/test');
const path = require('node:path');
const segmentId = 'NL-1';
const payload = {
  type: 'CP_REGISTRATION', firstName: 'Test', lastName: 'Participant',
  city: 'Test City', email: 'picker-test@example.invalid',
  participation: 'Virtual', selectionMethod: 'manual', waiverAccepted: true, waiverVersion: '2026-11-24-24eb6e5bb870', waiverName: 'Test Participant', comments: 'Synthetic browser test', segmentIds: [segmentId],
};
let errors = [];
test.beforeEach(async ({ page }) => {
  errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Use the same real Leaflet version as production, without relying on a CDN.
  await page.route('https://unpkg.com/leaflet@1.9.4/dist/**', route => {
    const file = new URL(route.request().url()).pathname.split('/dist/')[1];
    return route.fulfill({ path: path.join(__dirname, '../node_modules/leaflet/dist', file) });
  });
  // Tests exercise real map behavior but do not depend on tile providers.
  await page.route(/https:\/\/.*cartocdn\.com\//, route => route.fulfill({
    contentType: 'image/png',
    body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1sAAAAASUVORK5CYII=', 'base64'),
  }));
  await page.clock.install();
  await page.goto('/tests/fixtures/parent.html');
  // Complete the production load handler's 250ms and 1000ms overview resets.
  await page.clock.runFor(1100);
});
test.afterEach(() => expect(errors, 'uncaught browser errors').toEqual([]));
function picker(page) { return page.frameLocator('iframe'); }
function row(page) { return picker(page).locator('.segment').filter({ has: picker(page).locator(`[data-select="${segmentId}"]`) }); }
async function openRegion(page) {
  await picker(page).getByRole('button', { name: 'Choose my own segment' }).click();
  await picker(page).locator('[data-key="NL"]').click();
  await expect(row(page).locator('.status-pill')).toHaveText('Confirmed');
}
async function fillRegistration(page) {
  await openRegion(page);
  await row(page).getByRole('button', { name: 'Select', exact: true }).click();
  await picker(page).getByRole('button', { name: 'Check Out / Register' }).click();
  await picker(page).getByLabel('First name *', { exact: true }).fill(payload.firstName);
  await picker(page).getByLabel('Last name *', { exact: true }).fill(payload.lastName);
  await picker(page).getByLabel('City of residence *', { exact: true }).fill(payload.city);
  await picker(page).getByLabel('Email address *', { exact: true }).fill(payload.email);
  await picker(page).getByRole('radio', { name: /Virtually/ }).check();
  await picker(page).getByLabel('Comments or message (optional)').fill(payload.comments);
  await picker(page).getByLabel('Type your full name as your signature *').fill(payload.waiverName);
  await picker(page).getByRole('checkbox').check();
}
async function submissions(page) {
  return page.evaluate(() => window.messages.filter(m => m.type === 'CP_REGISTRATION'));
}
test('shared status survives selection and deselection', async ({ page }) => {
  await openRegion(page);
  await row(page).getByRole('button', { name: 'Select', exact: true }).click();
  await expect(row(page).locator('.status-pill')).toHaveText('Confirmed');
  await expect(picker(page).locator('#selectedCount')).toHaveText('1');
  await row(page).getByRole('button', { name: 'Selected ✓', exact: true }).click();
  await expect(row(page).locator('.status-pill')).toHaveText('Confirmed');
  await expect(picker(page).locator('#selectedCount')).toHaveText('0');
});
test('registration success resets the form and refreshes statuses', async ({ page }) => {
  await fillRegistration(page);
  await picker(page).getByRole('button', { name: 'Submit registration request' }).click();
  await expect.poll(() => submissions(page)).toEqual([payload]);
  await page.evaluate(() => {
    window.statuses = { 'NL-1': 'Tentative' };
    window.reply({ type: 'CP_REGISTRATION_SUCCESS', registrationId: 'CP-TEST-001', status: 'Pending' });
  });
  await expect(picker(page).locator('#pendingBanner')).toContainText('CP-TEST-001');
  await expect(picker(page).getByRole('dialog')).toBeHidden();
  await expect(picker(page).locator('#selectedCount')).toHaveText('0');
  await expect(picker(page).locator('#regFirst')).toHaveValue('');
  await expect(picker(page).locator('#regEmail')).toHaveValue('');
  await expect.poll(() => page.evaluate(() => window.messages.filter(m => m.type === 'CP_GET_SEGMENT_STATUSES').length)).toBe(1);
  await expect(row(page).locator('.status-pill')).toHaveText('Tentative');
  expect(await submissions(page)).toEqual([payload]);
});
test('registration error preserves details and allows retry', async ({ page }) => {
  await fillRegistration(page);
  await picker(page).getByRole('button', { name: 'Submit registration request' }).click();
  await expect.poll(() => submissions(page)).toEqual([payload]);
  const dialog = page.waitForEvent('dialog');
  await page.evaluate(() => window.reply({ type: 'CP_REGISTRATION_ERROR', message: 'Test registration unavailable' }));
  const alert = await dialog;
  expect(alert.message()).toBe('Test registration unavailable');
  await alert.accept();
  await expect(picker(page).getByRole('dialog')).toBeVisible();
  await expect(picker(page).locator('#regEmail')).toHaveValue(payload.email);
  await expect(picker(page).locator('#selectedCount')).toHaveText('1');
  const submit = picker(page).getByRole('button', { name: 'Submit registration request' });
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect.poll(() => submissions(page)).toEqual([payload, payload]);
});

test('random choice uses an available approved segment and locks participation', async ({page})=>{
 await page.evaluate(()=>window.statuses={'NL-6':'Available','NL-1':'Available'});
 await picker(page).getByRole('button',{name:'Choose a random segment — virtual'}).click();
 await expect(picker(page).locator('#randomResult')).toContainText('NL-6');
 await expect(picker(page).getByRole('region',{name:'Map for segment NL-6',exact:true})).toBeVisible();
 await expect(picker(page).locator('#randomMapHost canvas')).toBeVisible();
 await picker(page).getByRole('button',{name:'Continue to registration'}).click();
 await expect(picker(page).getByRole('radio',{name:/On location/})).toBeDisabled();
 await expect(picker(page).getByRole('radio',{name:/Virtually/})).toBeChecked();
 await picker(page).getByRole('button',{name:'Cancel',exact:true}).click();
 await picker(page).getByRole('button',{name:'Change how I choose'}).click();
 await picker(page).getByRole('button',{name:'Choose my own segment'}).click();
 await expect(picker(page).locator('#selectedCount')).toHaveText('0');
 await expect(picker(page).getByLabel('Max distance (km)')).toHaveCount(0);
});
test('random choice reports no available countryside segments',async({page})=>{
 await picker(page).getByRole('button',{name:'Choose a random segment — virtual'}).click();
 await expect(picker(page).locator('#randomMessage')).toContainText('No countryside segments');
 await expect(picker(page).getByRole('button',{name:'Continue to registration'})).toBeDisabled();
});
test('waiver acceptance is required before sending registration',async({page})=>{
 await fillRegistration(page);
 await picker(page).getByRole('checkbox').uncheck();
 await picker(page).getByRole('button',{name:'Submit registration request'}).click();
 expect(await submissions(page)).toEqual([]);
 await picker(page).getByRole('checkbox').check();
 await picker(page).getByLabel('Type your full name as your signature *').fill('');
 await picker(page).getByRole('button',{name:'Submit registration request'}).click();
 expect(await submissions(page)).toEqual([]);
});

test('review preview samples across the full approved countryside list',async({page})=>{
 const eligible=require('../data/random-eligible.json').segmentIds;
 await page.goto('/tests/fixtures/parent.html?review=1');
 const frame=page.frames().find(f=>f.url().endsWith('/index.html'));
 await frame.evaluate(()=>{Math.random=()=>0;});
 await picker(page).getByRole('button',{name:'Choose a random segment — virtual'}).click();
 await expect(picker(page).locator('#randomResult')).toContainText('Segment '+eligible[0]+' ·');
 await expect.poll(()=>page.evaluate(()=>Object.values(window.statuses).filter(s=>s==='Available').length)).toBe(eligible.length);
 await frame.evaluate(()=>{Math.random=()=>0.999999;});
 await picker(page).getByRole('button',{name:'Choose another random segment'}).click();
 await expect(picker(page).locator('#randomResult')).toContainText('Segment '+eligible[eligible.length-1]+' ·');
 await expect(picker(page).getByRole('region',{name:'Map for segment '+eligible[eligible.length-1],exact:true})).toBeVisible();
});

test('phone view bounds routes and list while retaining cross-province checkout', async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await fillRegistration(page);
  await picker(page).getByRole('button',{name:'Cancel',exact:true}).click();
  await picker(page).locator('[data-key="ON"]').click();
  await expect(picker(page).locator('.segment')).toHaveCount(20);
  const frame=page.frames().find(f=>f.url().endsWith('/index.html'));
  await expect.poll(()=>frame.evaluate(()=>segmentLayers.getLayers().length)).toBe(20);
  await expect.poll(()=>frame.evaluate(()=>Object.keys(window.CP_REGION_DATA))).toEqual(['ON']);
  expect(await frame.evaluate(()=>[...selected.values()].every(s=>!('geometry' in s)))).toBe(true);
  const first=await picker(page).locator('[data-select]').first().getAttribute('data-select');
  await picker(page).getByRole('button',{name:'Next segments',exact:true}).click();
  await expect(picker(page).locator('.segment')).toHaveCount(20);
  await expect(picker(page).locator('[data-select]').first()).not.toHaveAttribute('data-select',first);
  await picker(page).getByRole('button',{name:'Previous segments',exact:true}).click();
  await picker(page).locator('[data-select]').first().click();
  await picker(page).locator('[data-key="NL"]').click();
  await expect(row(page).getByRole('button',{name:'Selected ✓'})).toBeVisible();
  await expect(picker(page).locator('#selectedCount')).toHaveText('2');
  await expect.poll(()=>frame.evaluate(()=>Object.keys(window.CP_REGION_DATA))).toEqual(['NL']);
  await picker(page).getByRole('button',{name:'Check Out / Register'}).click();
  await picker(page).getByRole('button',{name:'Submit registration request'}).click();
  await expect.poll(async()=> (await submissions(page))[0]?.segmentIds.slice().sort()).toEqual(['NL-1',first].sort());
});

test('phone filters bound map contents and checkout works without background tiles', async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.route(/https:\/\/.*cartocdn\.com\//, route=>route.abort());
  await fillRegistration(page);
  await picker(page).getByRole('button',{name:'Cancel',exact:true}).click();
  const frame=page.frames().find(f=>f.url().endsWith('/index.html'));
  await frame.evaluate(()=>basemap.redraw());
  await expect(picker(page).getByText('Background map is temporarily unavailable. Canadian Pursuit route data can still be used.')).toBeVisible();
  await picker(page).locator('#textFilter').fill('no-such-segment-xyz');
  await expect(picker(page).locator('.segment')).toHaveCount(0);
  expect(await frame.evaluate(()=>segmentLayers.getLayers().length)).toBe(0);
  await picker(page).locator('#textFilter').fill('');
  await expect(picker(page).locator('.segment')).toHaveCount(20);
  await picker(page).getByRole('button',{name:'Check Out / Register'}).click();
  await picker(page).getByRole('button',{name:'Submit registration request'}).click();
  await expect.poll(()=>submissions(page)).toEqual([payload]);
});
