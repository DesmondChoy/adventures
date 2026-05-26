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
