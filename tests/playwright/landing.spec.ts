import { expect, test, type Page } from '@playwright/test';

// Keep landing-page checks signed out and independent of a real auth service.
async function installLandingAuth(page: Page, resume = false): Promise<void> {
  await page.route('**/@supabase/supabase-js@2', async (route) => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `
        window.__landingAuthCalls = [];
        window.supabase = {
          createClient() {
            const session = ${resume ? "{ access_token: 'test-token', user: { id: 'test-user', is_anonymous: false } }" : 'null'};
            return { auth: {
              async getSession() { return { data: { session }, error: null }; },
              onAuthStateChange() {},
              async signInAnonymously() {
                window.__landingAuthCalls.push('guest');
                return { data: {}, error: null };
              },
              async signInWithOAuth(options) {
                window.__landingAuthCalls.push(options.provider);
                return { data: {}, error: null };
              }
            }};
          }
        };
      `,
    });
  });
}

test('world and walkthrough previews work independently with the keyboard', async ({ page }) => {
  await installLandingAuth(page);
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');

  const underwater = page.getByRole('button', { name: 'Underwater', exact: true });
  await underwater.focus();
  await page.keyboard.press('Enter');
  await expect(underwater).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#portal-sea')).toBeVisible();
  await expect(page.locator('#portal-sky')).toBeHidden();
  await expect(page.locator('#example-world')).toBeVisible();

  await page.getByRole('button', { name: /Shape the story/ }).click();
  await expect(page.locator('#example-story')).toBeVisible();
  await expect(page.locator('#example-story img')).toHaveAttribute('src', /monster-encounter/);
  await expect(page.locator('#example-world')).toBeHidden();
  await expect(page.locator('#portal-sea')).toBeVisible();

  await page.getByRole('button', { name: /Discover as you go/ }).click();
  await expect(page.locator('#example-lesson')).toBeVisible();
  await expect(page.locator('#example-lesson img')).toHaveAttribute('src', /red-green-portal/);
  await expect(page.locator('#example-story')).toBeHidden();
  expect(errors).toEqual([]);
});

test('entry controls retain guest and Google authentication and closing invitation focus', async ({ page }) => {
  await installLandingAuth(page);
  await page.goto('/');
  await page.getByRole('link', { name: 'Begin your free adventure', exact: true }).click();
  await expect(page.locator('#continue-guest')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#guest-warning')).toBeVisible();
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click();
  await expect(page.locator('#guest-warning')).toBeHidden();
  expect(await page.evaluate(() => (window as any).__landingAuthCalls)).toEqual(['guest', 'google']);
});

test('returning users can still resume an existing adventure', async ({ page }) => {
  await installLandingAuth(page, true);
  await page.route('**/api/user/current-adventure', (route) => route.fulfill({
    json: { adventure: {
      adventure_id: '11111111-1111-4111-8111-111111111111',
      story_category: 'Clockwork Sky City',
      lesson_topic: 'Astronomy',
      current_chapter: 4,
      total_chapters: 10,
      last_updated: new Date().toISOString(),
    } },
  }));
  await page.route('**/select?resume_adventure_id=*', (route) => route.fulfill({
    contentType: 'text/html', body: '<h1>Resume destination</h1>',
  }));
  await page.goto('/');
  await expect(page.locator('#resumeModal')).toBeVisible();
  await expect(page.locator('#modalProgress')).toHaveText('Chapter 4 out of 10');
  await page.getByRole('button', { name: 'Continue Adventure', exact: true }).click();
  await expect(page).toHaveURL(/\/select\?resume_adventure_id=11111111-1111-4111-8111-111111111111$/);
});

test('mobile has no horizontal overflow and brings artwork into the first screen', async ({ page }) => {
  await installLandingAuth(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);
    for (const name of ['Sky city', 'Underwater', 'Drawing world']) {
      await page.getByRole('button', { name, exact: true }).click();
      const layout = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        artworkTop: document.querySelector('.portal-frame')!.getBoundingClientRect().top + window.scrollY,
        animation: getComputedStyle(document.querySelector('.portal-scene:not([hidden])')!).animationName,
      }));
      expect(layout.overflow, `overflow at ${width}px for ${name}`).toBe(false);
      expect(layout.artworkTop, `artwork placement at ${width}px`).toBeLessThan(700);
      expect(layout.animation).toBe('none');
    }
  }
});

test('topic names dissolve in sequence and rotation can be paused and resumed', async ({ page }) => {
  await installLandingAuth(page);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.clock.install();
  await page.goto('/');
  const ticker = page.locator('[data-topic-ticker]');
  await ticker.scrollIntoViewIfNeeded();
  const current = ticker.locator('.topic-name.is-current');
  await expect(current).toHaveText('Astronomy');
  await page.clock.runFor(4100);
  await expect(current).toHaveText('Dinosaurs');
  expect(await current.evaluate((element) => getComputedStyle(element).transitionProperty)).toBe('opacity');
  await page.getByRole('button', { name: 'Pause topic rotation', exact: true }).click();
  await page.clock.runFor(12000);
  await expect(current).toHaveText('Dinosaurs');
  await page.getByRole('button', { name: 'Resume topic rotation', exact: true }).click();
  await page.clock.runFor(4100);
  await expect(current).toHaveText('Oceans');
});

test('reduced-motion topic display advances manually and fits on a narrow screen', async ({ page }) => {
  await installLandingAuth(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 844 });
  await page.clock.install();
  await page.goto('/');
  const ticker = page.locator('[data-topic-ticker]');
  await ticker.scrollIntoViewIfNeeded();
  const current = ticker.locator('.topic-name.is-current');
  await page.clock.runFor(12000);
  await expect(current).toHaveText('Astronomy');
  for (const topic of ['Dinosaurs', 'Oceans', 'Ancient civilisations', 'Music & sound', 'Astronomy']) {
    await page.getByRole('button', { name: 'Next topic', exact: true }).click();
    await expect(current).toHaveText(topic);
    expect(await current.evaluate((element) => getComputedStyle(element).transitionDuration)).toBe('0s');
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  }
});
