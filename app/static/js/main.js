/**
 * Main Application Module
 * Entry point for the client-side application, handles initialization and coordination
 */

import { authManager } from './authManager.js';
import { AdventureStateManager } from './adventureStateManager.js';
import { WebSocketManager } from './webSocketManager.js';
import { stateManager, manageState } from './stateManager.js';
import { Carousel, setupCarouselKeyboardNavigation } from './carousel-manager.js';
import {
    showError,
    hideLoader,
    showLoader,
    updateProgress,
    resetApplicationState,
    setSelectedCategory,
    setSelectedLessonTopic,
    clearStreamBuffer,
    clearActiveParagraphs
} from './uiManager.js';

// Global application state
window.appState = {
    authManager: authManager,
    stateManager: stateManager,
    wsManager: null,
    storyWebSocket: null
};

// Global configuration (will be set from template data)
// Don't overwrite if it already exists
if (!window.appConfig) {
    window.appConfig = {
        totalCategories: 0,
        totalLessonTopics: 0
    };
}

// Initialize WebSocket connection
export function initWebSocket() {
    showLoader();
    if (!authManager || !authManager.accessToken) {
        // console.warn('[FrontendWS Log 2] In initWebSocket: AuthManager or AccessToken is missing initially.'); // Kept as warn
    }

    const websocketUrl = window.appState.wsManager.getWebSocketUrl();

    try {
        window.appState.storyWebSocket = new WebSocket(websocketUrl);
        window.appState.wsManager.connection = window.appState.storyWebSocket;
        window.appState.wsManager.setupConnectionHandlers(); // This will set onopen, onclose, onerror, onmessage
    } catch (e) {
        console.error("CRITICAL ERROR instantiating WebSocket:", e);
        hideLoader(); // Hide loader if WebSocket creation fails
    }

    // Initialize with a new state or restore existing
    const savedState = stateManager.loadState();
    if (savedState && !window.appState.wsManager.adventureIdToResume) {
        // Don't call updateProgress here - let the backend's adventure_loaded message handle it
    }
}

// Make a choice and send to server
export function makeChoice(choiceId, choiceText) {
    if (window.appState.storyWebSocket && window.appState.storyWebSocket.readyState === WebSocket.OPEN) {
        showLoader();
        // Clear the stream buffer when making a new choice
        clearStreamBuffer();

        // Reset active paragraphs for the new chapter
        clearActiveParagraphs();

        const existingState = stateManager.loadState() || {};
        const currentChapter = existingState.chapters || [];

        // Create new chapter data with complete structure
        const newChapter = {
            chapter_number: currentChapter.length + 1,
            content: document.getElementById('storyContent').textContent,
            // chapter_type will be set by the server based on adventure flow
            response: {
                chosen_path: choiceId,
                choice_text: choiceText
            },
            chapter_content: {
                content: document.getElementById('storyContent').textContent,
                choices: [] // Empty choices since this is a completed chapter
            }
        };

        const updatedState = manageState('update', {
            current_chapter_id: choiceId,
            chapters: [...currentChapter, newChapter]
        });

        // Don't call updateProgress here - let the backend handle chapter display updates

        // Send state and choice data to server
        window.appState.wsManager.sendMessage({
            state: updatedState,
            choice: {
                id: choiceId,
                text: choiceText,
                chapter_number: currentChapter.length + 1
            }
        });

        // Clear UI for next chapter
        document.getElementById('storyContent').textContent = '';
        document.getElementById('choicesContainer').innerHTML = '';

        // Hide the chapter image container for the new chapter
        // It will be shown again when the new image is ready
        document.getElementById('chapterImageContainer').classList.add('hidden');
    }
}

// Adventure summary function
export async function viewAdventureSummary() {
    // Show loading indicator
    showLoader();

    // Flag to track if we've already redirected
    let hasRedirected = false;
    let timeoutId = null;

    // Check if WebSocket is available and in correct state
    if (!window.appState.storyWebSocket || window.appState.storyWebSocket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not available for summary generation');
        showError('Unable to generate summary. WebSocket connection is not available.');
        hideLoader();
        return;
    }

    // Get the current state
    const currentState = stateManager.loadState();
    if (!currentState) {
        showError('No adventure state found. Please complete an adventure first.');
        hideLoader();
        return;
    }

    // Store the original onmessage handler
    const originalOnMessage = window.appState.storyWebSocket.onmessage;

    // Set up timeout for WebSocket response
    timeoutId = setTimeout(() => {
        console.error('WebSocket timeout: No summary_ready response received within 8 seconds');

        // Restore original handler
        if (originalOnMessage) {
            window.appState.storyWebSocket.onmessage = originalOnMessage;
        }

        if (!hasRedirected) {
            showError('Summary generation timed out. Please try again.');
            hideLoader();
        }
    }, 8000); // Increased to 8 seconds for reliability

    // Override ONLY the onmessage handler temporarily
    window.appState.storyWebSocket.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'summary_ready') {
                console.log('Summary ready received, state_id:', data.state_id);

                // Clear timeout and prevent duplicate actions
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }

                if (!hasRedirected) {
                    hasRedirected = true;

                    // Restore original handler
                    if (originalOnMessage) {
                        window.appState.storyWebSocket.onmessage = originalOnMessage;
                    }

                    // Use the state_id from the WebSocket response
                    const stateId = data.state_id;

                    // Navigate to the summary page with this state_id
                    window.location.href = `/adventure/summary?state_id=${stateId}`;
                }
            } else {
                // Pass other messages to the original handler
                if (originalOnMessage) {
                    originalOnMessage(event);
                }
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
            // If JSON parsing fails, pass to original handler
            if (originalOnMessage) {
                originalOnMessage(event);
            }
        }
    };

    // Send reveal_summary message via WebSocket
    try {
        window.appState.storyWebSocket.send(JSON.stringify({
            state: currentState,
            choice: "reveal_summary"
        }));
        console.log('Summary generation request sent via WebSocket');
    } catch (error) {
        console.error('Error sending WebSocket message:', error);

        // Clean up on send failure
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        if (originalOnMessage) {
            window.appState.storyWebSocket.onmessage = originalOnMessage;
        }

        showError('Failed to send summary generation request. Please try again.');
        hideLoader();
    }
}

// Initialize carousels
function initializeCarousels() {
    const carouselElement = document.getElementById('categoryCarousel');

    if (!carouselElement) {
        console.error('Category carousel element not found!');
        return;
    }

    if (!window.appConfig?.totalCategories || window.appConfig.totalCategories === 0) {
        console.error('totalCategories is 0 or undefined in initializeCarousels:', window.appConfig?.totalCategories);
        return;
    }

    // Create category carousel
    window.categoryCarousel = new Carousel({
        elementId: 'categoryCarousel',
        itemCount: window.appConfig.totalCategories,
        dataAttribute: 'category',
        inputId: 'storyCategory',
        onSelect: (categoryId) => {
            setSelectedCategory(categoryId);
        }
    });

    // Set up global keyboard navigation
    setupCarouselKeyboardNavigation([window.categoryCarousel]);
}

// Main initialization function
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

    // Initialize WebSocket manager
    window.appState.wsManager = new WebSocketManager(authManager);

    const authInitialized = await authManager.initialize();
    if (!authInitialized) {
        return;
    }

    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => authManager.handleLogout());
    } else {
        // console.warn("Logout button not found on the page. Ensure it's added to the HTML."); // Kept as warn
    }

    const urlParams = new URLSearchParams(window.location.search);
    const adventureIdToResumeFromQuery = urlParams.get('resume_adventure_id');

    if (adventureIdToResumeFromQuery) {
        window.appState.wsManager.adventureIdToResume = adventureIdToResumeFromQuery;
        stateManager.clearState(); // Clear any local state to ensure fresh load from server

        showLoader();
        // Setup UI for adventure in progress
        document.getElementById('storyCategoryScreen').classList.add('hidden');
        document.getElementById('lessonTopicScreen').classList.add('hidden');
        document.getElementById('introText').classList.add('hidden');
        document.getElementById('storyContainer').classList.remove('hidden');
        // Note: selectedCategory and selectedLessonTopic will be set by server state
        // and retrieved from sessionStorage in getWebSocketUrl
        initWebSocket();
    } else {
        const savedState = stateManager.loadState();
        if (savedState?.chapters?.length > 0 && savedState.storyCategory && savedState.lessonTopic) {
            showLoader();
            // Don't call updateProgress here - let the backend's adventure_loaded message handle it

            document.getElementById('storyCategoryScreen').classList.add('hidden');
            document.getElementById('lessonTopicScreen').classList.add('hidden');
            document.getElementById('introText').classList.add('hidden');
            document.getElementById('storyContainer').classList.remove('hidden');

            setSelectedCategory(savedState.storyCategory);
            setSelectedLessonTopic(savedState.lessonTopic);

            const storyCatEl = document.getElementById('storyCategory');
            const lessonTopicEl = document.getElementById('lessonTopic');
            if (storyCatEl) storyCatEl.value = savedState.storyCategory;
            if (lessonTopicEl) lessonTopicEl.value = savedState.lessonTopic;

            initWebSocket();
        } else {
            manageState('reset');
            hideLoader();

            // Initialize carousels since we have the imports
            if (document.getElementById('categoryCarousel') && window.appConfig.totalCategories > 0) {
                initializeCarousels();
            } else {
                // console.warn("Category carousel element or totalCategories not found. Carousel UI may not function."); // Kept as warn
            }
        }
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', initialize);

// Add click handler to banner for reset
document.addEventListener('DOMContentLoaded', () => {
    const bannerLink = document.querySelector('h1 a');
    if (bannerLink) {
        bannerLink.addEventListener('click', function (e) {
            e.preventDefault();
            resetApplicationState();
        });
    }
});

// Initialize carousels on page load (fallback)
window.addEventListener('load', () => {
    if (window.appConfig.totalCategories > 0 && document.getElementById('categoryCarousel')) {
        initializeCarousels();
    }
});

// Clean up WebSocket when leaving the page
window.addEventListener('beforeunload', function () {
    if (window.appState.storyWebSocket) {
        window.appState.storyWebSocket.close();
    }
});

// Expose functions to global scope for onclick handlers
window.resetApplicationState = resetApplicationState;
window.viewAdventureSummary = viewAdventureSummary;
