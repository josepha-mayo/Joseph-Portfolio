import { expect, test } from '@playwright/test';

test.use({ baseURL: 'http://127.0.0.1:3010', browserName: 'firefox' });

test('portfolio entry opens the Fun project in the same tab', async ({ page }) => {
  await page.goto('/');
  const project = page.locator('article').filter({ hasText: 'DOOMFLY' });
  await expect(project.getByText('Fun project', { exact: true })).toBeVisible();
  await project.getByRole('link', { name: 'explore the experiment' }).click();
  await expect(page).toHaveURL(/\/doomfly$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('DOOM.');
  await page.screenshot({ path: '.next/doomfly-desktop.png' });
});

test('recorded board supports stepping, scrubbing, playback, and the final result', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/doomfly#chess');
  await expect(page.getByText('Ply 0 of 186', { exact: true })).toBeVisible();
  const board = page.getByRole('img', { name: /Recorded chess position/ });
  await expect(board.locator(':scope > div')).toHaveCount(64);
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.getByText('Ply 1 of 186', { exact: true })).toBeVisible();
  await expect(board).toHaveAttribute('aria-label', /connectome played b3/);
  await page.getByRole('button', { name: 'Final position' }).click();
  await expect(page.getByText('Ply 186 of 186 / checkmate', { exact: true })).toBeVisible();
  await expect(board).toHaveAttribute('aria-label', /random played Rg1#/);
  await page.screenshot({ path: '.next/doomfly-chess.png' });
  const slider = page.getByRole('slider', { name: 'Recorded move position' });
  await slider.focus();
  await slider.press('Home');
  await expect(page.getByText('Ply 0 of 186', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Play replay' }).click();
  await expect(page.getByText('Ply 1 of 186', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  const paused = await slider.inputValue();
  await page.waitForTimeout(1000);
  expect(await slider.inputValue()).toBe(paused);
  expect(errors).toEqual([]);
});

test('setup clips and neural replay load without autoplay', async ({ page, request }) => {
  await page.goto('/doomfly#setup');
  const videos = page.locator('video');
  await expect(videos).toHaveCount(4);
  for (const video of await videos.all()) {
    await expect(video).not.toHaveAttribute('autoplay');
    await video.evaluate((element: HTMLVideoElement) => { element.preload = 'metadata'; element.load(); });
    await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.duration)).toBeGreaterThan(10);
    await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.videoWidth)).toBeGreaterThan(0);
  }
  const ranged = await request.get('/doomfly/setup-1.mp4', { headers: { Range: 'bytes=0-1023' } });
  expect(ranged.status()).toBe(206);
  expect((await ranged.body()).length).toBe(1024);
  for (const photo of ['/doomfly/setup-photo-1.jpg', '/doomfly/setup-photo-2.jpg']) {
    expect((await request.get(photo)).ok()).toBe(true);
  }
});

test('mobile layout fits and evidence downloads are available', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/doomfly');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '.next/doomfly-mobile.png' });
  await page.getByRole('button', { name: 'Final position' }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: '.next/doomfly-mobile-chess.png' });
  const pgn = await request.get('/doomfly/match.pgn');
  expect(pgn.ok()).toBe(true);
  expect(await pgn.text()).toContain('[Result "0-1"]');
  const summary = await (await request.get('/doomfly/summary.json')).json();
  expect(summary.real_fly_points).toBeNull();
  expect(summary.plies).toBe(186);
});
