/**
 * UI Manager
 * Handles DOM manipulation, UI updates, and user interface functions
 */

import { stateManager, manageState } from './stateManager.js';
import { Carousel, setupCarouselKeyboardNavigation } from './carousel-manager.js';

// Global variables for UI state
let streamBuffer = '';  // Buffer for accumulating streamed text
let renderTimeout = null;  // Timeout for debounced rendering
let activeParagraphs = new Set(); // Store active paragraph indices
let selectedCategory = '';
let selectedLessonTopic = '';

// Utility: convert string to Title Case (handles spaces, underscores, hyphens)
function toTitleCase(str) {
    return (str || '')
        .replace(/[_-]+/g, ' ')
        .split(' ')
        .filter(Boolean)
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
}

// Initialize marked.js with custom options
marked.setOptions({
    breaks: true,  // Enable line breaks
    gfm: true,    // Enable GitHub Flavored Markdown
    sanitize: false // Allow HTML in the markdown
});

// --- Error and Notification Functions ---
export function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

export function showCategoryWarning(message) {
    const warningContainer = document.getElementById('category-warning-container');
    const carouselContainer = document.querySelector('.carousel-container');
    
    if (warningContainer) {
        warningContainer.textContent = message;
        warningContainer.style.display = 'block';
        
        // Add class to carousel container to push it down
        if (carouselContainer) {
            carouselContainer.classList.add('warning-active');
        }
        
        // Remove after 3 seconds
        setTimeout(() => {
            warningContainer.style.display = 'none';
            if (carouselContainer) {
                carouselContainer.classList.remove('warning-active');
            }
        }, 3000);
    }
}

export function showLessonWarning(message) {
    const warningContainer = document.getElementById('lesson-warning-container');
    const carouselContainer = document.querySelector('#lessonTopicScreen .carousel-container');
    
    if (warningContainer) {
        warningContainer.textContent = message;
        warningContainer.style.display = 'block';
        
        // Add class to carousel container to push it down
        if (carouselContainer) {
            carouselContainer.classList.add('warning-active');
        }
        
        // Remove after 3 seconds
        setTimeout(() => {
            warningContainer.style.display = 'none';
            if (carouselContainer) {
                carouselContainer.classList.remove('warning-active');
            }
        }, 3000);
    }
}

// --- Loader Functions ---
// Loading phrase management
let loadingPhrases = [];
let currentPhraseIndex = -1;
let previousPhrase = '';
let phraseInterval = null;
let typewriterTimeout = null;

// Fetch loading phrases from API
async function fetchLoadingPhrases() {
    try {
        const response = await fetch('/api/loading-phrases');
        const data = await response.json();
        loadingPhrases = data.phrases || [];
    } catch (error) {
        console.error('Error fetching loading phrases:', error);
        // Fallback phrases
        loadingPhrases = [
            "Thickening the plot...",
            "Sprinkling magical dust...",
            "Loading narrative momentum..."
        ];
    }
}

// Get random phrase excluding the previous one
function getRandomPhrase() {
    if (loadingPhrases.length === 0) return "Loading...";
    if (loadingPhrases.length === 1) return loadingPhrases[0];
    
    let phrase;
    do {
        phrase = loadingPhrases[Math.floor(Math.random() * loadingPhrases.length)];
    } while (phrase === previousPhrase);
    
    previousPhrase = phrase;
    return phrase;
}

// Instant phrase display with immediate green gradient
function displayPhrase(element, text, callback) {
    element.textContent = text;
    element.classList.remove('green-gradient', 'fade-out');
    element.classList.add('fade-in', 'green-gradient');
    
    if (callback) callback();
}

// Phrase display with fade transition effect
function displayPhraseWithTransition(element, text, callback) {
    // Fade out current phrase
    element.classList.remove('green-gradient', 'fade-in');
    element.classList.add('fade-out');
    
    // After fade out completes, change text and fade in
    setTimeout(() => {
        element.textContent = text;
        element.classList.remove('fade-out');
        element.classList.add('fade-in', 'green-gradient');
        
        if (callback) callback();
    }, 500); // Wait for fade-out to complete
}

// Start phrase rotation
function startPhraseRotation() {
    const phraseElement = document.getElementById('loadingPhrase');
    if (!phraseElement) return;
    
    // Clear any existing intervals/timeouts
    clearInterval(phraseInterval);
    clearTimeout(typewriterTimeout);
    
    // Show first phrase immediately
    const firstPhrase = getRandomPhrase();
    displayPhrase(phraseElement, firstPhrase);
    
    // Set up 5-second rotation
    phraseInterval = setInterval(() => {
        const newPhrase = getRandomPhrase();
        displayPhraseWithTransition(phraseElement, newPhrase);
    }, 5000);
}

// Stop phrase rotation
function stopPhraseRotation() {
    clearInterval(phraseInterval);
    clearTimeout(typewriterTimeout);
    phraseInterval = null;
    typewriterTimeout = null;
    
    const phraseElement = document.getElementById('loadingPhrase');
    if (phraseElement) {
        phraseElement.textContent = '';
        phraseElement.classList.remove('green-gradient');
    }
}

export function showLoader() {
    const overlay = document.getElementById('loaderOverlay');
    if (!overlay) {
        console.error('Loader overlay element not found!');
        return;
    }
    
    // Force display to ensure it's visible
    overlay.style.display = 'flex';
    overlay.classList.remove('hidden');
    
    // Fetch phrases if not already loaded
    if (loadingPhrases.length === 0) {
        fetchLoadingPhrases().then(() => {
            startPhraseRotation();
        });
    } else {
        startPhraseRotation();
    }
    
    // Use setTimeout to ensure the transition works
    setTimeout(() => {
        overlay.classList.add('active');
    }, 0);
}

export function hideLoader() {
    const overlay = document.getElementById('loaderOverlay');
    if (!overlay) {
        console.error('Loader overlay element not found!');
        return;
    }
    
    // Stop phrase rotation
    stopPhraseRotation();
    
    overlay.classList.remove('active');
    
    // Wait for transition to complete before hiding
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 300);
}

// --- Progress Functions ---
export function updateProgress(currentChapter, totalChapters) {
    // Validate inputs
    if (!Number.isInteger(currentChapter) || !Number.isInteger(totalChapters) || 
        currentChapter < 1 || totalChapters < 1 || currentChapter > totalChapters) {
        console.warn('Invalid chapter progress:', { currentChapter, totalChapters });
        return;
    }
    
    document.getElementById('current-chapter').textContent = currentChapter;
    document.getElementById('total-chapters').textContent = totalChapters;
    
    // Dispatch event for new chapter loaded (for font size manager)
    document.dispatchEvent(new CustomEvent('newChapterLoaded'));
}

// Single function to handle all chapter updates
function handleChapterProgress(data) {
    const currentChapter = data.current_chapter || 
                          (data.state?.current_chapter?.chapter_number) || 1;
    const totalChapters = data.total_chapters || 
                         data.state?.total_chapters || 
                         window.appConfig?.defaultStoryLength || 10;
    
    if (currentChapter && totalChapters) {
        updateProgress(currentChapter, totalChapters);
    }
}

// --- Navigation Functions ---
export function goToLessonTopicScreen() {
    if (!selectedCategory) {
        showCategoryWarning('Click on a card below to choose your adventure');
        return;
    }
    // Add hidden class to trigger transition
    document.getElementById('storyCategoryScreen').classList.add('hidden');
    // Remove hidden class to trigger transition
    document.getElementById('lessonTopicScreen').classList.remove('hidden');

    // Announce step change for screen readers
    const stepRegion = document.getElementById('step-aria');
    if (stepRegion) {
        stepRegion.textContent = 'Step 2 of 2: Choose Topic';
    }
    
    // Wait for layout to settle after removing hidden class
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            // Get total lesson topics from global config
            const totalLessonTopics = window.appConfig?.totalLessonTopics || 0;
            
            console.log('[LESSON CAROUSEL] Initializing with', totalLessonTopics, 'topics');
            console.log('[LESSON CAROUSEL] Current window.lessonCarousel:', window.lessonCarousel);
            
            // Only initialize if not already initialized or if current instance is invalid
            if (!window.lessonCarousel || typeof window.lessonCarousel.reposition !== 'function') {
                try {
                    // Initialize the lesson carousel with our Carousel class
                    window.lessonCarousel = new Carousel({
                        elementId: 'lessonCarousel',
                        itemCount: totalLessonTopics,
                        dataAttribute: 'topic',
                        inputId: 'lessonTopic',
                        onSelect: (topic) => {
                            selectedLessonTopic = topic;
                            const btn = document.getElementById('lesson-start-btn');
                            if (btn) {
                                if (topic) {
                                btn.disabled = false;
                                btn.classList.remove('cursor-not-allowed');
                                btn.textContent = `Start adventure with "${toTitleCase(topic)}"`;
                                } else {
                                    btn.disabled = true;
                                    btn.classList.add('cursor-not-allowed');
                                    btn.textContent = 'Start adventure';
                                }
                            }
                        }
                    });
                    console.log('[LESSON CAROUSEL] Successfully created Carousel instance:', window.lessonCarousel);
                } catch (error) {
                    console.error('[LESSON CAROUSEL] Error creating Carousel instance:', error);
                    showError('Failed to initialize lesson carousel. Please refresh the page.');
                    return;
                }
            } else {
                console.log('[LESSON CAROUSEL] Using existing instance');
            }
            
            // Force reposition for lesson carousel if dimensions were wrong during init
            setTimeout(() => {
                if (window.lessonCarousel && typeof window.lessonCarousel.reposition === 'function') {
                    window.lessonCarousel.reposition();
                }
            }, 100);
            
            // Update the keyboard navigation to include the lesson carousel
            setupCarouselKeyboardNavigation([window.categoryCarousel, window.lessonCarousel]);
            
            // Fix mobile-specific active card scaling if needed
            if (window.innerWidth <= 768 && window.lessonCarousel && typeof window.lessonCarousel.fixMobileActiveCardScaling === 'function') {
                window.lessonCarousel.fixMobileActiveCardScaling();
            }
        });
    });
}

export async function startAdventure() {
    // Validate both inputs
    if (!selectedCategory) {
        showError('Please select a story category to continue');
        return;
    }
    
    if (!selectedLessonTopic) {
        showLessonWarning('Click on a card below to choose your lesson topic');
        return;
    }

    showLoader(); // Show loader early as API calls are made

    const authManager = window.appState?.authManager;
    const isAnonymous = authManager?.user?.is_anonymous === true;
    let currentActiveAdventureForConflictCheck = null;
    let fetchErrorOccurred = false;

    // Step 1: Determine if there's a current active adventure for the logged-in user/guest
    console.log('[CONFLICT DEBUG] Starting conflict detection...');
    console.log('[CONFLICT DEBUG] authManager state:', {
        hasAuthManager: !!authManager,
        hasAccessToken: !!authManager?.accessToken,
        isAnonymous: isAnonymous,
        userEmail: authManager?.user?.email,
        userId: authManager?.user?.id?.substring(0, 8) + '...'
    });

    if (authManager && (authManager.accessToken || isAnonymous)) {
        let endpoint;
        let headers = { 'Content-Type': 'application/json' };

        if (isAnonymous) {
            const clientUUID = localStorage.getItem('learning_odyssey_user_uuid');
            console.log('[CONFLICT DEBUG] Guest user - clientUUID:', clientUUID?.substring(0, 8) + '...');
            if (clientUUID) {
                endpoint = `/api/adventure/active_by_client_uuid/${clientUUID}`;
            }
        } else { // Google authenticated user
            endpoint = '/api/user/current-adventure';
            headers['Authorization'] = `Bearer ${authManager.accessToken}`;
            console.log('[CONFLICT DEBUG] Google user - endpoint:', endpoint);
            console.log('[CONFLICT DEBUG] Google user - token length:', authManager.accessToken?.length);
            console.log('[CONFLICT DEBUG] Google user - token preview:', authManager.accessToken?.substring(0, 20) + '...');
        }

        console.log('[CONFLICT DEBUG] Final endpoint:', endpoint);
        console.log('[CONFLICT DEBUG] Headers:', { ...headers, Authorization: headers.Authorization ? 'Bearer [REDACTED]' : undefined });

        if (endpoint) {
            try {
                console.log('[CONFLICT DEBUG] Making fetch request...');
                const response = await fetch(endpoint, { method: 'GET', headers: headers });
                
                console.log('[CONFLICT DEBUG] Response status:', response.status);
                console.log('[CONFLICT DEBUG] Response ok:', response.ok);
                console.log('[CONFLICT DEBUG] Response headers:', Object.fromEntries(response.headers.entries()));
                
                if (response.ok) {
                    const adventureData = await response.json();
                    console.log('[CONFLICT DEBUG] Response data:', adventureData);
                    
                    if (adventureData && adventureData.adventure) {
                        currentActiveAdventureForConflictCheck = adventureData.adventure;
                        console.log('[CONFLICT DEBUG] Found active adventure:', {
                            adventure_id: currentActiveAdventureForConflictCheck.adventure_id,
                            story_category: currentActiveAdventureForConflictCheck.story_category,
                            lesson_topic: currentActiveAdventureForConflictCheck.lesson_topic,
                            current_chapter: currentActiveAdventureForConflictCheck.current_chapter
                        });
                    } else {
                        console.log('[CONFLICT DEBUG] No adventure found in response or missing adventure property');
                    }
                } else {
                    const errorText = await response.text();
                    console.error('[CONFLICT DEBUG] API call failed:', response.status, errorText);
                    fetchErrorOccurred = true;
                }
            } catch (error) {
                console.error('[CONFLICT DEBUG] Exception during fetch:', error);
                fetchErrorOccurred = true;
            }
        } else {
            console.log('[CONFLICT DEBUG] No endpoint determined - skipping API call');
        }
    } else {
        console.log('[CONFLICT DEBUG] No authManager or access conditions not met');
    }

    if (fetchErrorOccurred) {
        showError('Could not check for existing adventures. Please try again.');
        hideLoader();
        return;
    }

    // Step 2: Perform conflict check if an active adventure was found
    console.log('[CONFLICT DEBUG] Checking for conflicts...');
    console.log('[CONFLICT DEBUG] Current active adventure:', currentActiveAdventureForConflictCheck);
    console.log('[CONFLICT DEBUG] Selected category:', selectedCategory);
    console.log('[CONFLICT DEBUG] Selected lesson:', selectedLessonTopic);

    if (currentActiveAdventureForConflictCheck) {
        const activeStory = currentActiveAdventureForConflictCheck.story_category;
        const activeLesson = currentActiveAdventureForConflictCheck.lesson_topic;

        console.log('[CONFLICT DEBUG] Active adventure details:', { activeStory, activeLesson });
        console.log('[CONFLICT DEBUG] Will have conflict?', activeStory !== selectedCategory || activeLesson !== selectedLessonTopic);

        if (activeStory !== selectedCategory || activeLesson !== selectedLessonTopic) {
            console.log('[CONFLICT DEBUG] Conflict detected! Showing conflict modal...');
            // Hide loader before showing modal so user can interact with it
            hideLoader();
            
            try {
                const userConfirmedAbandonment = await showConflictConfirmationModal(
                    currentActiveAdventureForConflictCheck,
                    { story_category: selectedCategory, lesson_topic: selectedLessonTopic }
                );
                
                console.log('[CONFLICT DEBUG] User confirmed abandonment:', userConfirmedAbandonment);
                
                if (userConfirmedAbandonment) {
                    showLoader(); // Show loader again for API calls
                    
                    cleanUrlResumeParam(); 
                    if (window.appState?.wsManager) {
                        window.appState.wsManager.adventureIdToResume = null;
                    }

                    if (!isAnonymous && authManager && authManager.accessToken) { // Google User
                        console.log('[CONFLICT DEBUG] Abandoning adventure for Google user...');
                        try {
                            const abandonResponse = await fetch(`/api/adventure/${currentActiveAdventureForConflictCheck.adventure_id}/abandon`, {
                                method: 'POST',
                                headers: { 'Authorization': `Bearer ${authManager.accessToken}` }
                            });
                            if (!abandonResponse.ok) {
                                 console.error('Failed to abandon active adventure via API.');
                                 showError('Could not abandon previous adventure. Please try again.');
                                 hideLoader(); return;
                            }
                            console.log('[CONFLICT DEBUG] Adventure abandoned successfully');
                        } catch (error) {
                            console.error('Error abandoning adventure via API:', error);
                            showError('Error abandoning previous adventure.');
                            hideLoader(); return;
                        }
                    } else if (isAnonymous) { // Guest User
                        console.log('[CONFLICT DEBUG] Guest user - no explicit abandonment API call needed');
                        // No explicit API call for guest abandonment here.
                    }
                } else { // User cancelled conflict modal
                    console.log('[CONFLICT DEBUG] User cancelled conflict modal');
                    hideLoader(); 
                    return; 
                }
            } catch (error) {
                console.error('[CONFLICT DEBUG] Error with conflict modal:', error);
                showError('Error processing conflict resolution.');
                hideLoader();
                return;
            }
        } else { // No conflict, selections match the active adventure
            console.log('[CONFLICT DEBUG] No conflict - resuming existing adventure');
            if (window.appState?.wsManager) {
                 window.appState.wsManager.adventureIdToResume = currentActiveAdventureForConflictCheck.adventure_id;
            }
            const url = new URL(window.location.href);
            if (url.searchParams.get('resume_adventure_id') !== String(currentActiveAdventureForConflictCheck.adventure_id)) {
                url.searchParams.set('resume_adventure_id', currentActiveAdventureForConflictCheck.adventure_id);
                window.history.replaceState({}, document.title, url.toString());
            }
        }
    } else {
        console.log('[CONFLICT DEBUG] No current active adventure found - proceeding to start fresh');
        // No current active adventure found. Proceed to start fresh.
        cleanUrlResumeParam(); 
        if (window.appState?.wsManager) {
            window.appState.wsManager.adventureIdToResume = null;
        }
    }
    // --- End New Adventure Conflict Logic ---

    // Initialize state with selected options
    manageState('initialize', {
        storyCategory: selectedCategory,
        lessonTopic: selectedLessonTopic
    });

    // Update UI - add hidden class to trigger transitions
    document.getElementById('lessonTopicScreen').classList.add('hidden');
    document.getElementById('introText').classList.add('hidden');
    // Remove hidden class to trigger transition
    document.getElementById('storyContainer').classList.remove('hidden');

    // Start the adventure
    showLoader();
    const { initWebSocket } = await import('./main.js');
    initWebSocket();
}

// --- Story Content Functions ---
export function addParagraphListeners() {
    const storyContent = document.getElementById('storyContent');
    const paragraphs = storyContent.querySelectorAll('p');
    
    paragraphs.forEach((paragraph, index) => {
        // Restore active state if this paragraph was previously active
        if (activeParagraphs.has(index)) {
            paragraph.classList.add('active');
        }
        
        // Add click listener if not already added
        if (!paragraph.hasAttribute('data-listener-added')) {
            paragraph.setAttribute('data-listener-added', 'true');
            paragraph.addEventListener('click', function() {
                // First, remove active class from all paragraphs
                paragraphs.forEach(p => p.classList.remove('active'));
                
                // Clear the active paragraphs set
                activeParagraphs.clear();
                
                // Add active class to the clicked paragraph
                this.classList.add('active');
                
                // Update active paragraphs set with only this paragraph
                activeParagraphs.add(index);
            });
        }
    });
}

export function appendStoryText(text) {
    const storyContent = document.getElementById('storyContent');
    
    // Decode HTML entities without using innerHTML/textContent which can strip quotes
    const decodedText = text
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>');

    // Check if this is the first chunk of text and it starts with a dialogue verb
    // This indicates we might have lost a character name and opening quote
    if (streamBuffer === '' && /^(chirped|said|whispered|shouted|called|murmured|exclaimed|replied|asked|answered|responded)/.test(decodedText.trim())) {
        console.warn('Detected text starting with dialogue verb - possible missing character name');
        // If we're starting with a dialogue verb, it's likely we lost the character name
        // We'll log this but continue processing normally
    }

    // Special handling for dialogue text at the beginning of paragraphs
    let textToAdd = decodedText;

    // If this is the first chunk of a paragraph and it starts with a quotation mark
    // make sure we preserve it properly
    if (streamBuffer === '' && decodedText.trim().startsWith('"')) {
        // Ensure the quotation mark is preserved
        textToAdd = decodedText;
    }

    // Check if we're starting a new paragraph after a double newline
    if (streamBuffer.endsWith('\n\n') && decodedText.trim().startsWith('"')) {
        // Ensure the quotation mark is preserved for new paragraphs
        textToAdd = decodedText;
    }

    // Normalize special characters while preserving opening quotes and character names
    const normalizedText = textToAdd
        .replace(/[\u2018\u2019]/g, "'")
        .replace(/[\u201C\u201D]/g, '"')
        .replace(/\u2014/g, '--')
        .replace(/\u2013/g, '-')
        .replace(/\u2026/g, '...');

    // Add text to buffer and immediately display
    streamBuffer += normalizedText;

    try {
        // Convert the entire buffer to HTML while preserving line breaks
        const htmlContent = marked.parse(streamBuffer, {
            breaks: true,
            gfm: true
        });

        // Apply the HTML content to the story container
        storyContent.innerHTML = htmlContent;

        // Add drop cap to the first paragraph
        const firstParagraph = storyContent.querySelector('p:first-child');
        if (firstParagraph && firstParagraph.textContent.trim()) {
            firstParagraph.classList.add('drop-cap');
        }

        // Add click listeners to paragraphs
        addParagraphListeners();

        // Additional check for dialogue formatting issues
        if (streamBuffer.trim().startsWith('chirped') ||
            streamBuffer.trim().startsWith('said') ||
            streamBuffer.trim().startsWith('whispered') ||
            streamBuffer.trim().startsWith('shouted') ||
            streamBuffer.trim().startsWith('called') ||
            streamBuffer.trim().startsWith('murmured') ||
            streamBuffer.trim().startsWith('exclaimed') ||
            streamBuffer.trim().startsWith('replied') ||
            streamBuffer.trim().startsWith('asked') ||
            streamBuffer.trim().startsWith('answered') ||
            streamBuffer.trim().startsWith('responded')) {

            console.warn('Story content starts with dialogue verb - possible formatting issue');

            // We could potentially add a visual indicator here for the user
            // For example, adding a small warning icon or changing the text color
            // But for now, we'll just log the warning
        }
    } catch (error) {
        console.error('Error parsing markdown:', error);
        // Fallback to plain text if markdown parsing fails
        storyContent.textContent = streamBuffer;
    }

    // Auto-scroll disabled - window stays in place during streaming
    // window.scrollTo(0, document.body.scrollHeight);
}

export function replaceStoryContent(content) {
    // Replace the entire stream buffer with the cleaned content
    streamBuffer = content;
    
    const storyContent = document.getElementById('storyContent');
    
    try {
        // Convert the content to HTML while preserving line breaks
        const htmlContent = marked.parse(streamBuffer, {
            breaks: true,
            gfm: true
        });

        // Apply the HTML content to the story container
        storyContent.innerHTML = htmlContent;

        // Add drop cap to the first paragraph
        const firstParagraph = storyContent.querySelector('p:first-child');
        if (firstParagraph && firstParagraph.textContent.trim()) {
            firstParagraph.classList.add('drop-cap');
        }

        // Add click listeners to paragraphs
        addParagraphListeners();
        
    } catch (error) {
        console.error('Error parsing markdown:', error);
        // Fallback to plain text if markdown parsing fails
        storyContent.textContent = streamBuffer;
    }
}

// --- Choice and Image Functions ---
export function updateChoiceWithImage(choiceIndex, imageData) {
    const choicesContainer = document.getElementById('choicesContainer');
    const choiceButtons = choicesContainer.querySelectorAll('button.choice-card');
    
    if (choiceIndex >= 0 && choiceIndex < choiceButtons.length) {
        const choiceButton = choiceButtons[choiceIndex];
        
        // Create image element if it doesn't exist
        let imageContainer = choiceButton.querySelector('.choice-image-container');
        if (!imageContainer) {
            const contentDiv = choiceButton.querySelector('.choice-content');
            
            if (!contentDiv) {
                // If we don't have the new structure, create it
                const oldContent = choiceButton.innerHTML;
                choiceButton.innerHTML = '';
                
                const newContentDiv = document.createElement('div');
                newContentDiv.className = 'choice-content';
                
                const textDiv = document.createElement('div');
                textDiv.className = 'choice-text';
                textDiv.innerHTML = oldContent;
                
                imageContainer = document.createElement('div');
                imageContainer.className = 'choice-image-container';
                
                newContentDiv.appendChild(textDiv);
                newContentDiv.appendChild(imageContainer);
                choiceButton.appendChild(newContentDiv);
            } else {
                // If we have the content div but no image container
                imageContainer = document.createElement('div');
                imageContainer.className = 'choice-image-container';
                contentDiv.appendChild(imageContainer);
            }
        }
        
        // Add or update image
        imageContainer.innerHTML = `<img src="data:image/jpeg;base64,${imageData}" alt="Illustration of choice" class="w-full h-auto rounded-lg">`;
        imageContainer.style.display = 'block';
        
        // Add fade-in animation
        const img = imageContainer.querySelector('img');
        img.classList.add('fade-in');
        setTimeout(() => {
            img.classList.add('show');
        }, 50);
    }
}

export function updateChapterImage(chapterNumber, imageData) {
    const imageContainer = document.getElementById('chapterImageContainer');
    const image = document.getElementById('chapterImage');
    
    // Set the image source
    image.src = `data:image/jpeg;base64,${imageData}`;
    image.alt = `Illustration for Chapter ${chapterNumber}`;
    
    // Show the container
    imageContainer.classList.remove('hidden');
    
    // Add fade-in animation
    image.classList.add('fade-in');
    setTimeout(() => {
        image.classList.add('show');
    }, 50);
}

export async function displayChoices(choices) {
    const choicesContainer = document.getElementById('choicesContainer');
    choicesContainer.innerHTML = ''; // Clear existing choices

    if (Array.isArray(choices) && choices.length === 0) {
        const button = document.createElement('button');
        button.className = 'w-full p-6 mb-3 text-center bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-all duration-300 transform hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 shadow-lg hover:shadow-xl backdrop-blur-sm';
        button.textContent = 'Return to Landing Page';
        button.onclick = resetApplicationState;
        choicesContainer.appendChild(button);
        return;
    }

    const shadowIntensities = [
        'shadow-lg',
        'shadow-xl',
        'shadow-2xl'
    ];

    choices.forEach((choice, index) => {
        const button = document.createElement('button');
        // Base classes for the card-like button
        const baseClasses = [
            'w-full',
            'p-6',
            'mb-4',
            'text-left',
            'rounded-xl',
            'transition-all',
            'duration-300',
            'transform',
            'hover:scale-[1.02]',
            'focus:outline-none',
            'focus:ring-2',
            'focus:ring-offset-2',
            shadowIntensities[index],
            'hover:shadow-2xl',
            'backdrop-blur-sm',
            'choice-card',
            'group'
        ];
        
        button.className = baseClasses.join(' ');
        
        // Create content wrapper with text and image areas
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'choice-content';
        
        // Create text container
        const textContainer = document.createElement('div');
        textContainer.className = 'choice-text';
        
        // Add main choice text with same font styling as narrative content
        const textElement = document.createElement('p');
        textElement.className = 'narrative-font group-hover:text-gray-900 transition-colors duration-300';
        textElement.textContent = choice.text;
        
        textContainer.appendChild(textElement);
        contentWrapper.appendChild(textContainer);
        
        // Create image container (initially empty)
        const imageContainer = document.createElement('div');
        imageContainer.className = 'choice-image-container';
        imageContainer.style.display = 'none'; // Hide until image is loaded
        contentWrapper.appendChild(imageContainer);
        
        button.appendChild(contentWrapper);

        button.onclick = async (e) => {
            const { makeChoice } = await import('./main.js');
            const storyWebSocket = window.appState?.storyWebSocket;
            
            if (storyWebSocket?.readyState !== WebSocket.OPEN) {
                showError('Connection lost. Please refresh the page.');
                return;
            }

            const allButtons = choicesContainer.querySelectorAll('button');
            allButtons.forEach(btn => {
                btn.disabled = true;
                btn.classList.add('choice-card', 'disabled');
            });

            // Add selection effect to clicked button
            const selectedButton = e.target.closest('button');
            selectedButton.classList.add('selected');

            makeChoice(choice.id, choice.text);
        };
        
        choicesContainer.appendChild(button);
    });
}

// --- Stats Display Functions ---
export function displayStats(state) {
    const statsHtml = `
        <div class="text-center p-4">
            <h3 class="text-lg font-semibold text-green-800 mb-2">Journey Complete!</h3>
            <div class="text-sm text-green-700">
                <p>Total Lessons: ${state.stats.total_lessons}</p>
                <p>Correct Answers: ${state.stats.correct_lesson_answers}</p>
                <p>Success Rate: ${state.stats.completion_percentage}%</p>
            </div>
            <button onclick="window.resetApplicationState()" 
                    class="mt-4 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition btn-hover">
                Start New Journey
            </button>
        </div>`;
    document.getElementById('choicesContainer').innerHTML = statsHtml;
}

export function displayStatsWithSummaryButton(state) {
    const statsHtml = `
        <div class="text-center p-4">
            <h3 class="text-lg font-semibold text-green-800 mb-2">Journey Complete!</h3>
            <div class="text-sm text-green-700">
                <p>Total Lessons: ${state.stats.total_lessons}</p>
                <p>Correct Answers: ${state.stats.correct_lesson_answers}</p>
                <p>Success Rate: ${state.stats.completion_percentage}%</p>
            </div>
            <div class="flex flex-col gap-3 mt-4">
                <button onclick="window.viewAdventureSummary()" 
                       class="px-6 py-3 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition btn-hover inline-block text-center">
                    <span class="text-lg text-center">🔮 Take a Trip Down 🔮<br>Memory Lane</span>
                    <p class="text-sm opacity-80 mt-1">Relive your adventure and learning highlights</p>
                </button>
                <button onclick="window.resetApplicationState()" 
                        class="mt-2 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition btn-hover text-center">
                    🚀 Start New Journey
                </button>
            </div>
        </div>`;
    document.getElementById('choicesContainer').innerHTML = statsHtml;
}

export function displaySummaryComplete(state) {
    hideLoader();
    
    // Update progress to show completed adventure (exclude SUMMARY chapter from display)
    // If current chapter is SUMMARY type, show the story length instead of chapter number
    const displayChapterNumber = state.current_chapter.chapter_type === 'summary' 
        ? state.story_length || window.appConfig?.defaultStoryLength || 10 
        : state.current_chapter.chapter_number;
    updateProgress(displayChapterNumber, state.stats.total_lessons);
    
    // Add buttons at the bottom
    const buttonsHtml = `
        <div class="text-center p-4">
            <div class="flex flex-col gap-3 mt-4">
                <button onclick="window.viewAdventureSummary()" 
                       class="px-6 py-3 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition btn-hover inline-block text-center">
                    <span class="text-lg text-center">🔮 Take a Trip Down 🔮<br>Memory Lane</span>
                    <p class="text-sm opacity-80 mt-1">Relive your adventure and learning highlights</p>
                </button>
                <button onclick="window.resetApplicationState()" 
                        class="mt-2 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition btn-hover text-center">
                    🚀 Start New Journey
                </button>
            </div>
        </div>`;
    document.getElementById('choicesContainer').innerHTML = buttonsHtml;
}

// --- WebSocket Message Handler ---
export async function handleMessage(event) {
    try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'hide_loader') {
            hideLoader();
        } else if (data.type === 'choices') {
            displayChoices(data.choices);
        } else if (data.type === 'story') {
            appendStoryText(data.content);
        } else if (data.type === 'replace_content') {
            replaceStoryContent(data.content);
        } else if (data.type === 'story_complete') {
            // Check if we should show the summary button
            if (data.state && data.state.show_summary_button) {
                displayStatsWithSummaryButton(data.state);
            } else {
                displayStats(data.state);
            }
        } else if (data.type === 'choice_image_update') {
            // Handle image updates for choices
            updateChoiceWithImage(data.choice_index, data.image_data);
        } else if (data.type === 'chapter_image_update') {
            // Handle image updates for chapters
            updateChapterImage(data.chapter_number, data.image_data);
        } else if (data.type === 'summary_start') {
            // Clear content for summary
            document.getElementById('storyContent').innerHTML = '';
            document.getElementById('choicesContainer').innerHTML = '';
            showLoader();
        } else if (data.type === 'summary_ready') {
            // Use the state_id from the WebSocket response
            const stateId = data.state_id;
            
            // Navigate to the summary page with this state_id
            window.location.href = `/adventure/summary?state_id=${stateId}`;
        } else if (data.type === 'summary_complete') {
            // Display the complete summary
            displaySummaryComplete(data.state);
        } else if (['adventure_created', 'adventure_loaded', 'adventure_status', 'chapter_update'].includes(data.type)) {
            // Store the adventure_id for persistence
            if (data.adventure_id && window.appState?.wsManager) {
                window.appState.wsManager.setAdventureId(data.adventure_id);
            }
            
            // Use consolidated function for all chapter progress messages
            if (['adventure_loaded', 'adventure_status', 'chapter_update'].includes(data.type)) {
                handleChapterProgress(data);
            }
        } else {
            // For any other message types, hide the loader as a fallback
            hideLoader();
        }
    } catch (e) {
        // Assume it's plain text if JSON parsing fails
        hideLoader();
        appendStoryText(event.data);
    }
}

// --- Reset Function ---
export async function resetApplicationState() {
    // Clear state
    manageState('reset');
    
    // Clear markdown buffer and timeout
    streamBuffer = '';
    if (renderTimeout) {
        clearTimeout(renderTimeout);
    }
    
    // Reset adventure_id
    if (window.appState?.wsManager) {
        window.appState.wsManager.setAdventureId(null);
    }
    
    // Reset active paragraphs
    activeParagraphs.clear();
    
    // Reset UI to initial state - add/remove hidden classes to trigger transitions
    document.getElementById('lessonTopicScreen').classList.add('hidden');
    document.getElementById('storyContainer').classList.add('hidden');
    document.getElementById('storyCategoryScreen').classList.remove('hidden');
    document.getElementById('introText').classList.remove('hidden');
    
    // Hide loaders
    document.getElementById('loaderOverlay').classList.remove('active');
    document.getElementById('loaderOverlay').classList.add('hidden');
    
    // Clear content
    document.getElementById('storyContent').textContent = '';
    document.getElementById('choicesContainer').innerHTML = '';
    
    // Reset progress
    updateProgress(1, '-');
    
    // Close WebSocket if it exists
    if (window.appState?.storyWebSocket) {
        window.appState.storyWebSocket.close();
        window.appState.storyWebSocket = null;
    }
    
    // Reset selections
    document.getElementById('storyCategory').value = '';
    document.getElementById('lessonTopic').value = '';
    selectedCategory = '';
    selectedLessonTopic = '';
    
    // Reset carousel selections and re-initialize the category carousel
    const cards = document.getElementsByClassName('carousel-card');
    Array.from(cards).forEach(card => {
        card.classList.remove('selected', 'selecting', 'active');
    });
    
    // Clear lesson carousel instance
    window.lessonCarousel = null;
    
    // Re-initialize the category carousel with our Carousel class
    const totalCategories = window.appConfig?.totalCategories || 0;
    
    // Only initialize if not already initialized or if current instance is invalid
    if (!window.categoryCarousel || typeof window.categoryCarousel.reposition !== 'function') {
        window.categoryCarousel = new Carousel({
            elementId: 'categoryCarousel',
            itemCount: totalCategories,
            dataAttribute: 'category',
            inputId: 'storyCategory',
            onSelect: (categoryId) => {
                selectedCategory = categoryId;
                const btn = document.getElementById('category-continue-btn');
                if (btn) {
                    if (categoryId) {
                        btn.disabled = false;
                        btn.classList.remove('cursor-not-allowed');
                        btn.textContent = `Continue with \"${toTitleCase(categoryId)}\"`;
                    } else {
                        btn.disabled = true;
                        btn.classList.add('cursor-not-allowed');
                        btn.textContent = 'Continue';
                    }
                }
            }
        });
    }
    
    // Set up global keyboard navigation
    setupCarouselKeyboardNavigation([window.categoryCarousel]);
}

// Export selected category and topic getters/setters
export function getSelectedCategory() {
    return selectedCategory;
}

export function setSelectedCategory(category) {
    selectedCategory = category;
}

export function getSelectedLessonTopic() {
    return selectedLessonTopic;
}

export function setSelectedLessonTopic(topic) {
    selectedLessonTopic = topic;
}

// Export stream buffer functions
export function clearStreamBuffer() {
    streamBuffer = '';
    if (renderTimeout) {
        clearTimeout(renderTimeout);
    }
}

export function clearActiveParagraphs() {
    activeParagraphs.clear();
}

// Helper function to remove resume_adventure_id from URL without reload
function cleanUrlResumeParam() {
    const url = new URL(window.location.href);
    if (url.searchParams.has('resume_adventure_id')) {
        url.searchParams.delete('resume_adventure_id');
        window.history.replaceState({}, document.title, url.toString());
    }
}

// --- Conflict Confirmation Modal Functions ---
function showConflictConfirmationModal(currentAdventure, newSelection) {
    return new Promise((resolve) => {
        const modal = document.getElementById('conflictModal');
        if (!modal) {
            console.error('Conflict modal element not found!');
            resolve(false); // Fallback to prevent blocking
            return;
        }

        // Check for all required elements
        const currentAdventureNameEl = document.getElementById('conflictModalCurrentAdventureName');
        const currentLessonTopicEl = document.getElementById('conflictModalCurrentLessonTopic');
        const currentProgressEl = document.getElementById('conflictModalCurrentProgress');
        const newAdventureNameEl = document.getElementById('conflictModalNewAdventureName');
        const newLessonTopicEl = document.getElementById('conflictModalNewLessonTopic');
        const abandonBtn = document.getElementById('abandonAndStartBtn');
        const cancelBtn = document.getElementById('cancelConflictBtn');

        if (!abandonBtn || !cancelBtn) {
            console.error('Required modal button elements not found!');
            resolve(false);
            return;
        }

        // Populate modal with data
        if (currentAdventureNameEl) currentAdventureNameEl.textContent = currentAdventure.story_category;
        if (currentLessonTopicEl) currentLessonTopicEl.textContent = currentAdventure.lesson_topic;
        if (currentProgressEl) currentProgressEl.textContent = `Chapter ${currentAdventure.current_chapter}`;
        if (newAdventureNameEl) newAdventureNameEl.textContent = newSelection.story_category;
        if (newLessonTopicEl) newLessonTopicEl.textContent = newSelection.lesson_topic;

        modal.style.display = 'flex';

        // Store handlers to remove them later
        const handleAbandon = () => {
            cleanup();
            resolve(true);
        };

        const handleCancel = () => {
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            modal.style.display = 'none';
            // Remove event listeners to prevent multiple bindings if modal is reused
            abandonBtn.removeEventListener('click', handleAbandon);
            cancelBtn.removeEventListener('click', handleCancel);
        };

        // Add event listeners, ensuring they are only added once or are removable
        abandonBtn.addEventListener('click', handleAbandon, { once: true });
        cancelBtn.addEventListener('click', handleCancel, { once: true });
    });
}
