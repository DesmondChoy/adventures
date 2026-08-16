import { expect, type Page } from '@playwright/test';

export async function installFakeSupabase(page: Page): Promise<void> {
  await page.route('**/@supabase/supabase-js@2', async (route) => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `
        const testSession = {
          access_token: 'test-token',
          user: { id: 'test-user-id', is_anonymous: true, email: '' }
        };
        window.supabase = {
          createClient() {
            return {
              auth: {
                async getSession() {
                  return { data: { session: testSession }, error: null };
                },
                onAuthStateChange() {
                  return { data: { subscription: { unsubscribe() {} } } };
                },
                async signInAnonymously() {
                  window.location.href = '/select';
                  return { data: { session: testSession, user: testSession.user }, error: null };
                },
                async signInWithOAuth() {
                  return { data: {}, error: null };
                },
                async signOut() {
                  return { error: null };
                }
              }
            };
          }
        };
      `,
    });
  });
}

export async function installFakeStorySocket(page: Page): Promise<void> {
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
        const fakeServer = (window as any).__fakeStoryServer;
        fakeServer.sentMessages.push(message);
        fakeServer.onSend?.(message, this);
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
      onSend: null as null | ((message: string, socket: FakeStoryWebSocket) => void),
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

export async function ensureSelectionPage(page: Page): Promise<void> {
  await page.goto('/select');

  const guestButton = page.getByRole('button', { name: 'Continue as Guest' });
  if (await guestButton.count()) {
    await guestButton.first().click();
  }

  await expect(page).toHaveURL(/\/select$/);
}

export async function waitForCarousel(page: Page, carouselId: string): Promise<void> {
  await page.waitForFunction((id) => {
    const fallback =
      id === 'categoryCarousel'
        ? (window as any).categoryCarousel
        : (window as any).lessonCarousel;
    const instance = (window as any).carouselInstances?.[id] ?? fallback;
    const element = document.getElementById(id);
    const cardCount = element?.querySelectorAll('.carousel-card').length ?? 0;
    const firstCard = element?.querySelector('.carousel-card') as HTMLElement | null;
    const has3dTransform = !!firstCard && firstCard.style.transform.includes('translateZ(');
    return !!instance && !!element && cardCount > 0 && has3dTransform;
  }, carouselId);
}

export async function selectCarouselCard(
  page: Page,
  screenId: string,
  cardSelector: string,
): Promise<void> {
  const screen = page.locator(`#${screenId}`);
  const cards = screen.locator('.carousel-card');
  const targetCard = screen.locator(cardSelector);
  const nextButton = screen.getByRole('button', { name: 'Next', exact: true });

  await expect(targetCard).toHaveCount(1);
  const cardCount = await cards.count();

  for (let step = 0; step < cardCount; step += 1) {
    if (await targetCard.evaluate((card) => card.classList.contains('active'))) {
      await targetCard.click();
      await expect(targetCard).toHaveAttribute('aria-selected', 'true');
      return;
    }

    await nextButton.click();
  }

  throw new Error(`Carousel card never became active: ${cardSelector}`);
}
