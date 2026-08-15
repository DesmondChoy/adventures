import { readFileSync } from 'node:fs';

import { expect, test } from '@playwright/test';

import {
  ensureSelectionPage,
  installFakeStorySocket,
  installFakeSupabase,
  waitForCarousel,
} from './helpers';

const SUMMARY_STATE_ID = '11111111-1111-4111-8111-111111111111';
const CHAPTER_IMAGE = readFileSync(
  'app/static/images/stories/clockwork_sky_city.jpg',
).toString('base64');

const SUMMARY_DATA = {
  chapterSummaries: Array.from({ length: 10 }, (_, index) => ({
    number: index + 1,
    title: `The Clockwork Discovery ${index + 1}`,
    summary: `The learner advances through the clockwork mystery in chapter ${index + 1}.`,
    chapterType: index === 9 ? 'conclusion' : 'story',
  })),
  educationalQuestions: Array.from({ length: 3 }, (_, index) => ({
    question: `What did the learner discover in lesson ${index + 1}?`,
    userAnswer: `Fixture answer ${index + 1}`,
    correctAnswer: `Fixture answer ${index + 1}`,
    isCorrect: true,
    explanation: `Fixture explanation ${index + 1}.`,
  })),
  statistics: {
    chaptersCompleted: 10,
    questionsAnswered: 3,
    timeSpent: '12 mins',
    correctAnswers: 3,
  },
};

test('completes the deterministic selection-to-Memory-Lane browser flow', async ({ page }) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  let summaryRequestUrl = '';
  let summaryAuthorization = '';

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await installFakeSupabase(page);
  await installFakeStorySocket(page);
  await page.route('**/api/loading-phrases', async (route) => {
    await route.fulfill({ json: { phrases: ['Testing the complete adventure...'] } });
  });
  await page.route('**/api/adventure/active_by_client_uuid/**', async (route) => {
    await route.fulfill({ json: { adventure: null } });
  });
  await page.route('**/api/feedback/check**', async (route) => {
    await route.fulfill({ json: { has_given_feedback: true } });
  });
  await page.route('**/adventure/api/adventure-summary**', async (route) => {
    summaryRequestUrl = route.request().url();
    summaryAuthorization = route.request().headers().authorization ?? '';
    await route.fulfill({ json: SUMMARY_DATA });
  });

  await ensureSelectionPage(page);
  await waitForCarousel(page, 'categoryCarousel');

  await page.evaluate(
    ({ chapterImage, summaryStateId }) => {
      const server = (window as any).__fakeStoryServer;
      const stats = {
        total_lessons: 3,
        correct_lesson_answers: 3,
        completion_percentage: 100,
      };

      server.currentChapter = 0;
      server.emitChapter = function (chapterNumber: number): void {
        this.currentChapter = chapterNumber;
        const state = {
          story_length: 10,
          current_chapter: {
            chapter_number: chapterNumber,
            chapter_type: chapterNumber === 10 ? 'conclusion' : 'story',
          },
          stats,
        };

        setTimeout(() => {
          this.emit({
            type: 'chapter_update',
            current_chapter: chapterNumber,
            total_chapters: 10,
            state,
          });
          this.emit({
            type: 'story',
            content: `CHAPTER_${chapterNumber}_FIXTURE: The clockwork journey advances.`,
          });
        }, 0);

        setTimeout(() => {
          if (chapterNumber < 10) {
            this.emit({
              type: 'choices',
              choices: [1, 2, 3].map((choiceNumber) => ({
                id: `chapter-${chapterNumber}-choice-${choiceNumber}`,
                text: `Choice ${choiceNumber} for chapter ${chapterNumber}`,
              })),
            });
          } else {
            this.emit({
              type: 'story_complete',
              state: { ...state, show_summary_button: true },
            });
          }
        }, 25);

        setTimeout(() => {
          this.emit({
            type: 'chapter_image_update',
            chapter_number: chapterNumber,
            image_data: chapterImage,
          });
        }, 700);
      };

      server.onSend = function (message: string): void {
        const payload = JSON.parse(message);
        if (payload.choice === 'start') {
          this.emit({
            type: 'adventure_created',
            adventure_id: summaryStateId,
            total_chapters: 10,
          });
          this.emitChapter(1);
          return;
        }

        if (payload.choice === 'reveal_summary') {
          setTimeout(() => {
            this.emit({ type: 'summary_ready', state_id: summaryStateId });
          }, 0);
          return;
        }

        this.emitChapter(this.currentChapter + 1);
      };
    },
    { chapterImage: CHAPTER_IMAGE, summaryStateId: SUMMARY_STATE_ID },
  );

  await page.locator('[data-category="clockwork_sky_city"]').click();
  await expect(page.locator('#category-continue-btn')).toBeEnabled();
  await page.locator('#category-continue-btn').click();
  await waitForCarousel(page, 'lessonCarousel');

  await page.locator('[data-topic="Astronomy"]').click();
  await expect(page.locator('#lesson-start-btn')).toBeEnabled();
  await page.locator('#lesson-start-btn').click();

  for (let chapterNumber = 1; chapterNumber <= 10; chapterNumber += 1) {
    await expect(page.locator('#current-chapter')).toHaveText(String(chapterNumber));
    await expect(page.locator('#total-chapters')).toHaveText('10');
    await expect(page.locator('#storyContent')).toContainText(
      `CHAPTER_${chapterNumber}_FIXTURE`,
    );
    if (chapterNumber > 1) {
      await expect(page.locator('#storyContent')).not.toContainText(
        `CHAPTER_${chapterNumber - 1}_FIXTURE`,
      );
    }

    await expect(page.locator('#chapterImage')).toHaveAttribute(
      'alt',
      `Illustration for Chapter ${chapterNumber}`,
    );
    await expect(page.locator('#chapterImageContainer')).toBeVisible();

    if (chapterNumber < 10) {
      const choices = page.locator('#choicesContainer button.choice-card');
      await expect(choices).toHaveCount(3);
      await choices.first().click();
      await expect(page.locator('#chapterImageContainer')).toBeHidden();
    }
  }

  const memoryLaneButton = page.getByRole('button', { name: /Take a Trip Down Memory Lane/ });
  await expect(memoryLaneButton).toBeVisible();
  await memoryLaneButton.click();

  await expect(page).toHaveURL(
    new RegExp(`/adventure/summary\\?state_id=${SUMMARY_STATE_ID}$`),
  );
  await expect(page.getByRole('heading', { name: 'Adventure Complete!' })).toBeVisible();
  await expect(page.getByText('Chapters Completed')).toBeVisible();
  await expect(page.getByText('Questions Answered')).toBeVisible();
  await expect(page.getByText('The Clockwork Discovery 10')).toBeVisible();
  await expect(page.getByText('Question 3')).toBeVisible();

  const summaryStorage = await page.evaluate(() => ({
    stateId: localStorage.getItem('summary_state_id'),
    accessToken: localStorage.getItem('summary_access_token'),
  }));
  expect(summaryStorage).toEqual({ stateId: SUMMARY_STATE_ID, accessToken: 'test-token' });
  expect(new URL(summaryRequestUrl).searchParams.getAll('state_id')).toEqual([
    SUMMARY_STATE_ID,
  ]);
  expect(summaryAuthorization).toBe('Bearer test-token');
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
