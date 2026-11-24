import { authManager } from './authManager.js';
import { AdventureStateManager } from './adventureStateManager.js';
import { WebSocketManager } from './webSocketManager.js';
import { stateManager, manageState } from './stateManager.js';
import { Carousel, setupCarouselKeyboardNavigation } from './carousel-manager.js';
import {
    showError,
    hideLoader,
    showLoader,
    resetApplicationState,
    setSelectedCategory,
    setSelectedLessonTopic,
    clearStreamBuffer,
    clearActiveParagraphs,
    getCurrentChapterChoices,
    clearCurrentChapterChoices,
    advanceExpectedImageChapter,
    resetDisplayedImageChapter,
    hideChapterImage,
    cancelChapterImageSoftHold,
    goToLessonTopicScreen,
    goBackToCategoryScreen,
    startAdventure,
    initializeLoaderRetryButton,
    updateAdventureContextRibbon
} from './uiManager.js';

const SUMMARY_GENERATION_TIMEOUT_MS = 60_000;

if (!window.appState || !window.appState.wsManager) {
    window.appState = {
        authManager: authManager,
        stateManager: stateManager,
        wsManager: null,
        storyWebSocket: null
    };
}

if (!window.appConfig) {
    window.appConfig = {
        totalCategories: 0,
        totalLessonTopics: 0
    };
}

export function initWebSocket() {
    showLoader();
    if (!authManager) {
        console.error('initWebSocket: authManager missing');
    }

    if (!window.appState.wsManager) {
        try {
            window.appState.wsManager = new WebSocketManager(authManager);
        } catch (e) {
            console.error('initWebSocket: failed to instantiate WebSocketManager:', e);
            hideLoader();
            return;
        }
    }

    const websocketUrl = window.appState.wsManager.getWebSocketUrl();

    try {
        window.appState.storyWebSocket = new WebSocket(websocketUrl);
        window.appState.wsManager.connection = window.appState.storyWebSocket;
        window.appState.wsManager.setupConnectionHandlers();
    } catch (e) {
        console.error("CRITICAL ERROR instantiating WebSocket:", e);
        hideLoader();
    }
}

export function makeChoice(choiceId, choiceText) {
    if (window.appState.storyWebSocket && window.appState.storyWebSocket.readyState === WebSocket.OPEN) {
        showLoader();
        clearStreamBuffer();
        clearActiveParagraphs();

        const existingState = stateManager.loadState() || {};
        const currentChapters = existingState.chapters || [];
        const displayedChapter = Number.parseInt(
            document.getElementById('current-chapter')?.textContent || '',
            10
        );
        const chapterNumber = Number.isInteger(displayedChapter) && displayedChapter > 0
            ? displayedChapter
            : currentChapters.length + 1;

        const preservedChoices = getCurrentChapterChoices();
        const newChapter = {
            chapter_number: chapterNumber,
            content: document.getElementById('storyContent').textContent,
            response: {
                chosen_path: choiceId,
                choice_text: choiceText
            },
            chapter_content: {
                content: document.getElementById('storyContent').textContent,
                choices: preservedChoices
            }
        };

        const updatedState = manageState('update', {
            current_chapter_id: choiceId,
            chapters: [...currentChapters.slice(0, chapterNumber - 1), newChapter]
        });

        const nextChapter = chapterNumber + 1;
        advanceExpectedImageChapter(nextChapter);
        resetDisplayedImageChapter();
        cancelChapterImageSoftHold();
        hideChapterImage();

        window.appState.wsManager.sendMessage({
            state: updatedState,
            choice: {
                id: choiceId,
                text: choiceText,
                chapter_number: chapterNumber
            }
        });

        document.getElementById('storyContent').textContent = '';
        document.getElementById('choicesContainer').innerHTML = '';
        clearCurrentChapterChoices();
    }
}

export async function viewAdventureSummary() {
    showLoader();

    let hasRedirected = false;
    let timeoutId = null;

    if (!window.appState.storyWebSocket || window.appState.storyWebSocket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not available for summary generation');
        showError('Unable to generate summary. WebSocket connection is not available.');
        hideLoader();
        return;
    }

    const currentState = stateManager.loadState();
    if (!currentState) {
        showError('No adventure state found. Please complete an adventure first.');
        hideLoader();
        return;
    }

    const originalOnMessage = window.appState.storyWebSocket.onmessage;

    timeoutId = setTimeout(() => {
        console.error('WebSocket timeout: No summary_ready response received within 60 seconds');
        timeoutId = null;

        if (originalOnMessage) {
            window.appState.storyWebSocket.onmessage = originalOnMessage;
        }

        if (!hasRedirected) {
            showError('Summary generation is taking longer than usual. Still trying...');
        }
    }, SUMMARY_GENERATION_TIMEOUT_MS);

    window.appState.storyWebSocket.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'summary_ready') {
                console.log('Summary ready received, state_id:', data.state_id);

                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }

                if (!hasRedirected) {
                    hasRedirected = true;

                    if (originalOnMessage) {
                        window.appState.storyWebSocket.onmessage = originalOnMessage;
                    }

                    const stateId = data.state_id;
                    if (stateId) {
                        localStorage.setItem('summary_state_id', stateId);
                    }

                    if (authManager.accessToken) {
                        localStorage.setItem('summary_access_token', authManager.accessToken);
                    }

                    window.location.href = `/adventure/summary?state_id=${stateId}`;
                }
            } else if (data.type === 'error' || data.type === 'save_failed') {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }

                if (originalOnMessage) {
                    window.appState.storyWebSocket.onmessage = originalOnMessage;
                    originalOnMessage(event);
                } else {
                    const message = typeof data.message === 'string' && data.message.trim()
                        ? data.message
                        : 'Unable to generate summary. Please try again.';
                    showError(message);
                    hideLoader();
                }
            } else if (originalOnMessage) {
                originalOnMessage(event);
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
            if (originalOnMessage) {
                originalOnMessage(event);
            }
        }
    };

    try {
        window.appState.storyWebSocket.send(JSON.stringify({
            state: currentState,
            choice: "reveal_summary"
        }));
        console.log('Summary generation request sent via WebSocket');
    } catch (error) {
        console.error('Error sending WebSocket message:', error);

        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        if (originalOnMessage) {
            window.appState.storyWebSocket.onmessage = originalOnMessage;
        }

        showError('Failed to send summary generation request. Please try again.');
        hideLoader();
    }
}

function toTitleCase(str) {
    return (str || '')
        .replace(/[_-]+/g, ' ')
        .split(' ')
        .filter(Boolean)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

function initializeCarousels() {
    if (window.categoryCarousel && typeof window.categoryCarousel.reposition === 'function') {
        return;
    }

    const carouselElement = document.getElementById('categoryCarousel');

    if (!carouselElement) {
        console.error('Category carousel element not found!');
        return;
    }

    if (!window.appConfig?.totalCategories || window.appConfig.totalCategories === 0) {
        console.error('totalCategories is 0 or undefined in initializeCarousels:', window.appConfig?.totalCategories);
        return;
    }

    window.categoryCarousel = new Carousel({
        elementId: 'categoryCarousel',
        itemCount: window.appConfig.totalCategories,
        dataAttribute: 'category',
        inputId: 'storyCategory',
        onSelect: (categoryId) => {
            setSelectedCategory(categoryId);
            const btn = document.getElementById('category-continue-btn');
            if (btn) {
                if (categoryId) {
                    btn.disabled = false;
                    btn.classList.remove('cursor-not-allowed');
                    btn.textContent = `Continue with "${toTitleCase(categoryId)}"`;
                } else {
                    btn.disabled = true;
                    btn.classList.add('cursor-not-allowed');
                    btn.textContent = 'Continue';
                }
            }
        }
    });

    setupCarouselKeyboardNavigation([window.categoryCarousel]);
}

async function initialize() {
    if (!window.supabase) {
        console.error("CRITICAL: Supabase client (window.supabase) not found on DOMContentLoaded.");
        showError("Application cannot start: Auth service failed to load.");
        const storyCategoryScreen = document.getElementById('storyCategoryScreen');
        if (storyCategoryScreen) {
            storyCategoryScreen.innerHTML = '<p class="text-red-500 text-center p-8 text-lg">Application Error: Core authentication service failed. Please refresh or contact support.</p>';
        }
        hideLoader();
        return;
    }

    window.appState.wsManager = new WebSocketManager(authManager);
    initializeLoaderRetryButton();

    const authInitialized = await authManager.initialize();
    if (!authInitialized) {
        return;
    }

    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => authManager.handleLogout());
    }

    const urlParams = new URLSearchParams(window.location.search);
    const adventureIdToResumeFromQuery = urlParams.get('resume_adventure_id');

    if (adventureIdToResumeFromQuery) {
        window.appState.wsManager.adventureIdToResume = adventureIdToResumeFromQuery;
        stateManager.clearState();

        showLoader();
        document.getElementById('storyCategoryScreen').classList.add('hidden');
        document.getElementById('lessonTopicScreen').classList.add('hidden');
        document.getElementById('introText').classList.add('hidden');
        document.getElementById('storyContainer').classList.remove('hidden');
        initWebSocket();
    } else {
        const savedState = stateManager.loadState();
        if (savedState?.chapters?.length > 0 && savedState.storyCategory && savedState.lessonTopic) {
            showLoader();

            document.getElementById('storyCategoryScreen').classList.add('hidden');
            document.getElementById('lessonTopicScreen').classList.add('hidden');
            document.getElementById('introText').classList.add('hidden');
            document.getElementById('storyContainer').classList.remove('hidden');

            setSelectedCategory(savedState.storyCategory);
            setSelectedLessonTopic(savedState.lessonTopic);
            updateAdventureContextRibbon(savedState.storyCategory, savedState.lessonTopic);

            const storyCatEl = document.getElementById('storyCategory');
            const lessonTopicEl = document.getElementById('lessonTopic');
            if (storyCatEl) storyCatEl.value = savedState.storyCategory;
            if (lessonTopicEl) lessonTopicEl.value = savedState.lessonTopic;

            initWebSocket();
        } else {
            manageState('reset');
            hideLoader();

            if (document.getElementById('categoryCarousel') && window.appConfig.totalCategories > 0) {
                initializeCarousels();
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', initialize);

document.addEventListener('DOMContentLoaded', () => {
    const bannerLink = document.querySelector('h1 a');
    if (bannerLink) {
        bannerLink.addEventListener('click', function (e) {
            e.preventDefault();
            resetApplicationState();
        });
    }
});

window.addEventListener('load', () => {
    if (window.appConfig.totalCategories > 0 && document.getElementById('categoryCarousel')) {
        initializeCarousels();
    }
});

window.addEventListener('beforeunload', function () {
    if (window.appState.storyWebSocket) {
        window.appState.storyWebSocket.close();
    }
});

window.resetApplicationState = resetApplicationState;
window.viewAdventureSummary = viewAdventureSummary;
window.goToLessonTopicScreen = goToLessonTopicScreen;
window.goBackToCategoryScreen = goBackToCategoryScreen;
window.startAdventure = startAdventure;
window.makeChoice = makeChoice;
