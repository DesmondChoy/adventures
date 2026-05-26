import { expect, type Page, test } from '@playwright/test';

import { ensureSelectionPage, installFakeSupabase, waitForCarousel } from './helpers';

const DESKTOP_VIEWPORT = { width: 1366, height: 900 };
const MOBILE_VIEWPORT = { width: 390, height: 844 };

async function disableMotion(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }
    `,
  });
}

async function expectCarouselScreenshot(
  page: Page,
  screenId: string,
  snapshotName: string,
): Promise<void> {
  const container = page.locator(`#${screenId} .carousel-container`);
  await expect(container).toBeVisible();
  await expect(container).toHaveScreenshot(snapshotName, {
    animations: 'disabled',
    caret: 'hide',
  });
}

test('category and lesson carousels render correctly on desktop and mobile', async ({ page }) => {
  await installFakeSupabase(page);
  await ensureSelectionPage(page);
  await waitForCarousel(page, 'categoryCarousel');
  await disableMotion(page);

  await page.setViewportSize(DESKTOP_VIEWPORT);
  await expectCarouselScreenshot(page, 'storyCategoryScreen', 'category-desktop.png');

  await page.setViewportSize(MOBILE_VIEWPORT);
  const categoryRadius = await page.evaluate(
    () => (window as any).carouselInstances?.categoryCarousel?.radius,
  );
  expect(categoryRadius).toBeGreaterThan(200);
  await expectCarouselScreenshot(page, 'storyCategoryScreen', 'category-mobile.png');

  await page.evaluate(() => (window as any).categoryCarousel?.rotate('next'));
  await page.evaluate(() => (window as any).categoryCarousel?.rotate('next'));
  await expectCarouselScreenshot(page, 'storyCategoryScreen', 'category-mobile-rotated.png');

  await page.evaluate(
    () => (window as any).categoryCarousel?.select('festival_of_lights_and_colors'),
  );
  const continueButton = page.locator('#category-continue-btn');
  await expect(continueButton).toBeEnabled();
  await continueButton.click();
  await waitForCarousel(page, 'lessonCarousel');

  await page.setViewportSize(DESKTOP_VIEWPORT);
  await expectCarouselScreenshot(page, 'lessonTopicScreen', 'lesson-desktop.png');

  await page.setViewportSize(MOBILE_VIEWPORT);
  const lessonRadius = await page.evaluate(
    () => (window as any).carouselInstances?.lessonCarousel?.radius,
  );
  expect(lessonRadius).toBeGreaterThan(200);
  await expectCarouselScreenshot(page, 'lessonTopicScreen', 'lesson-mobile.png');

  await page.evaluate(() => (window as any).lessonCarousel?.rotate('next'));
  await page.evaluate(() => (window as any).lessonCarousel?.rotate('next'));
  await expectCarouselScreenshot(page, 'lessonTopicScreen', 'lesson-mobile-rotated.png');
});
