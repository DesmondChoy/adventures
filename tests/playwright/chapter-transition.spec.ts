import { expect, type Page, test } from '@playwright/test';

import { ensureSelectionPage, installFakeSupabase, waitForCarousel } from './helpers';

const CHAPTER_ONE_MARKER = 'CHAPTER_ONE_MARKER: Diego finds the first glowing orb.';
const CHAPTER_TWO_MARKER = 'CHAPTER_TWO_MARKER: Diego steps into the next light-cloud.';

async function installFakeStorySocket(page: Page): Promise<void> {
  await page.addInitScript(() => {
    class FakeStoryWebSocket extends EventTarget {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      readonly url: string;
      readonly sentMessages: string[] = [];
      readyState = FakeStoryWebSocket.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;

      constructor(url: string | URL) {
        super();
        this.url = String(url);

        const fakeServer = (window as any).__fakeStoryServer;
        fakeServer.sockets.push(this);

        setTimeout(() => {
          this.readyState = FakeStoryWebSocket.OPEN;
          const event = new Event('open');
          this.onopen?.(event);
          this.dispatchEvent(event);
        }, 0);
      }

      send(message: string): void {
        this.sentMessages.push(message);
        (window as any).__fakeStoryServer.sentMessages.push(message);
      }

      close(): void {
        if (this.readyState === FakeStoryWebSocket.CLOSED) {
          return;
        }

        this.readyState = FakeStoryWebSocket.CLOSED;
        const event = new CloseEvent('close', { wasClean: true });
        this.onclose?.(event);
        this.dispatchEvent(event);
      }

      emit(payload: unknown): void {
        const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
        const event = new MessageEvent('message', { data });
        this.onmessage?.(event);
        this.dispatchEvent(event);
      }
    }

    (window as any).__fakeStoryServer = {
      sockets: [] as FakeStoryWebSocket[],
      sentMessages: [] as string[],
      emit(payload: unknown): void {
        const socket = this.sockets[this.sockets.length - 1];
        if (!socket) {
          throw new Error('No fake story WebSocket is connected');
        }
        socket.emit(payload);
      },
      streamChapter(chapterNumber: number, content: string): void {
        this.emit({
          type: 'chapter_update',
          current_chapter: chapterNumber,
          total_chapters: 10,
        });
        this.emit({ type: 'story', content });
      },
    };

    (window as any).WebSocket = FakeStoryWebSocket;
  });
}

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
  await expect(page.locator('#storyContent')).toContainText(CHAPTER_ONE_MARKER);

  await page.evaluate((content) => {
    (window as any).__fakeStoryServer.streamChapter(2, content);
  }, CHAPTER_TWO_MARKER);

  await expect(page.locator('#current-chapter')).toHaveText('2');
  await expect(page.locator('#storyContent')).toContainText(CHAPTER_TWO_MARKER);
  await expect(page.locator('#storyContent')).not.toContainText(CHAPTER_ONE_MARKER);

  const streamedText = await page.locator('#storyContent').innerText();
  expect(streamedText.trim().startsWith(CHAPTER_TWO_MARKER)).toBe(true);
});
