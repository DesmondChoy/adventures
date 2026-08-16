import { readFileSync } from 'node:fs';

import { expect, test } from '@playwright/test';

import {
  ensureSelectionPage,
  installFakeStorySocket,
  installFakeSupabase,
  waitForCarousel,
} from './helpers';

const CHAPTER_ONE_MARKER = 'CHAPTER_ONE_MARKER: Diego finds the first glowing orb.';
const CHAPTER_TWO_MARKER = 'CHAPTER_TWO_MARKER: Diego steps into the next light-cloud.';
const RESUMED_CHAPTER_MARKER = 'RESUMED_CHAPTER_MARKER: The saved journey continues.';
const RESUME_IMAGE = readFileSync(
  'app/static/images/stories/clockwork_sky_city.jpg',
).toString('base64');

test('chapter transition clears previous story content before new streaming chunks', async ({
  page,
}) => {
  await installFakeSupabase(page);
  await installFakeStorySocket(page);
  await page.route('**/api/loading-phrases', async (route) => {
    await route.fulfill({ json: { phrases: ['Testing the story stream...'] } });
  });
  await page.route('**/api/adventure/active_by_client_uuid/**', async (route) => {
    await route.fulfill({ json: { adventure: null } });
  });

  await ensureSelectionPage(page);
  await waitForCarousel(page, 'categoryCarousel');

  await page.evaluate(() =>
    (window as any).categoryCarousel.select('festival_of_lights_and_colors'),
  );
  await page.locator('#category-continue-btn').click();
  await waitForCarousel(page, 'lessonCarousel');

  await page.evaluate(() => (window as any).lessonCarousel.select('Astronomy'));
  await page.locator('#lesson-start-btn').click();

  await page.waitForFunction(() => (window as any).__fakeStoryServer.sockets.length === 1);
  await page.evaluate((content) => {
    (window as any).__fakeStoryServer.streamChapter(1, content);
  }, CHAPTER_ONE_MARKER);

  await expect(page.locator('#current-chapter')).toHaveText('1');
  await expect(page.locator('#total-chapters')).toHaveText('10');
  await expect(page.locator('#contextWorldName')).toHaveText('Festival Of Lights And Colors');
  await expect(page.locator('#contextLessonTopic')).toHaveText('Astronomy');
  await expect(page.locator('#chapterProgress')).toHaveAttribute('aria-valuenow', '1');
  await expect(page.locator('#chapterProgressFill')).toHaveAttribute('style', /width: 10%/);
  await expect(page.locator('#storyContent')).toContainText(CHAPTER_ONE_MARKER);

  await page.locator('#storyContainer').evaluate((element) => {
    element.style.maxWidth = '34rem';
  });
  await expect(page.locator('#adventureContextRibbon')).toHaveClass(/is-overflowing/);
  await expect(page.locator('#contextMarqueeTrack')).toHaveCSS('animation-name', 'context-ticker');
  await expect(page.locator('.context-copy-duplicate')).toBeVisible();

  await page.locator('#storyContent').evaluate((element) => {
    element.style.minHeight = '1500px';
  });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect.poll(async () => page.locator('#readerHeader').evaluate(
    (element) => Math.round(element.getBoundingClientRect().top),
  )).toBe(0);

  await page.evaluate((content) => {
    (window as any).__fakeStoryServer.streamChapter(2, content);
  }, CHAPTER_TWO_MARKER);

  await expect(page.locator('#current-chapter')).toHaveText('2');
  await expect(page.locator('#chapterProgress')).toHaveAttribute('aria-valuenow', '2');
  await expect(page.locator('#storyContent')).toContainText(CHAPTER_TWO_MARKER);
  await expect(page.locator('#storyContent')).not.toContainText(CHAPTER_ONE_MARKER);

  const chapterPosition = await page.evaluate(() => {
    const storyContainer = document.getElementById('storyContainer')!;
    const readerHeader = document.getElementById('readerHeader')!;
    return {
      scrollY: window.scrollY,
      readerTop: storyContainer.getBoundingClientRect().top
        + window.scrollY
        + readerHeader.offsetTop,
    };
  });
  expect(Math.abs(chapterPosition.scrollY - chapterPosition.readerTop)).toBeLessThan(2);

  const streamedText = await page.locator('#storyContent').innerText();
  expect(streamedText.trim().startsWith(CHAPTER_TWO_MARKER)).toBe(true);
});

test('resumed chapter replaces stale local progress and keeps an early image update', async ({
  page,
}) => {
  const staleState = {
    storyCategory: 'festival_of_lights_and_colors',
    lessonTopic: 'Music and Sound',
    story_length: 10,
    chapters: Array.from({ length: 10 }, (_, index) => ({
      chapter_number: index + 1,
      content: `Stale chapter ${index + 1}`,
    })),
    metadata: {},
  };

  await installFakeSupabase(page);
  await installFakeStorySocket(page);
  await page.addInitScript((state) => {
    window.localStorage.setItem('adventure_state', JSON.stringify(state));
  }, staleState);
  await page.route('**/api/loading-phrases', async (route) => {
    await route.fulfill({ json: { phrases: ['Restoring the adventure...'] } });
  });
  await page.route('**/api/feedback/check**', async (route) => {
    await route.fulfill({ json: { has_given_feedback: true } });
  });

  await ensureSelectionPage(page);
  await page.waitForFunction(() => (window as any).__fakeStoryServer.sockets.length === 1);

  await page.evaluate(
    ({ image, marker }) => {
      const server = (window as any).__fakeStoryServer;
      const state = {
        current_chapter: {
          chapter_number: 2,
          chapter_type: 'story',
        },
        story_length: 10,
        stats: {
          total_lessons: 0,
          correct_lesson_answers: 0,
          completion_percentage: 0,
        },
      };

      server.emit({
        type: 'adventure_loaded',
        adventure_id: 'resumed-adventure',
        story_category: 'festival_of_lights_and_colors',
        lesson_topic: 'Music and Sound',
        current_chapter: 2,
        total_chapters: 10,
        state,
      });
      server.emit({ type: 'story', content: marker });
      server.emit({
        type: 'choices',
        choices: [1, 2, 3].map((number) => ({
          id: `resumed-choice-${number}`,
          text: `Resumed choice ${number}`,
        })),
      });

      server.onSend = function (message: string): void {
        const payload = JSON.parse(message);
        if (!payload.choice || payload.choice === 'start') {
          return;
        }

        this.emit({
          type: 'chapter_update',
          current_chapter: 3,
          total_chapters: 10,
          state: {
            ...state,
            current_chapter: { chapter_number: 3, chapter_type: 'story' },
          },
        });
        setTimeout(() => {
          // Real image generation can beat the loader fade-out. This update must
          // survive underneath the loader and be visible once story text arrives.
          this.emit({
            type: 'chapter_image_update',
            chapter_number: 3,
            image_data: image,
          });
          this.emit({ type: 'story', content: 'CHAPTER_THREE_AFTER_RESUME' });
          this.emit({
            type: 'choices',
            choices: [1, 2, 3].map((number) => ({
              id: `chapter-3-choice-${number}`,
              text: `Chapter 3 choice ${number}`,
            })),
          });
        }, 50);
      };
    },
    { image: RESUME_IMAGE, marker: RESUMED_CHAPTER_MARKER },
  );

  await expect(page.locator('#current-chapter')).toHaveText('2');
  await expect(page.locator('#storyContent')).toContainText(RESUMED_CHAPTER_MARKER);
  await page.locator('#choicesContainer button.choice-card').first().click();

  await expect(page.locator('#current-chapter')).toHaveText('3');
  await expect(page.locator('#storyContent')).toContainText('CHAPTER_THREE_AFTER_RESUME');
  await expect(page.locator('#chapterImage')).toHaveAttribute(
    'alt',
    'Illustration for Chapter 3',
  );
  await expect(page.locator('#chapterImageContainer')).toBeVisible();

  const sentChoice = await page.evaluate(() => {
    const messages = (window as any).__fakeStoryServer.sentMessages
      .map((message: string) => JSON.parse(message))
      .filter((message: any) => message.choice && message.choice !== 'start');
    return messages.at(-1);
  });
  expect(sentChoice.choice.chapter_number).toBe(2);
  expect(sentChoice.state.chapters).toHaveLength(2);
  expect(sentChoice.state.chapters.at(-1).chapter_number).toBe(2);
});
