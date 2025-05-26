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

// --- Loader Functions ---
export function showLoader() {
    console.log('Showing loader...');
    const overlay = document.getElementById('loaderOverlay');
    if (!overlay) {
        console.error('Loader overlay element not found!');
        return;
    }
    
    // Force display to ensure it's visible
    overlay.style.display = 'flex';
    overlay.classList.remove('hidden');
    
    // Use setTimeout to ensure the transition works
    setTimeout(() => {
        overlay.classList.add('active');
        console.log('Loader activated');
    }, 0);
}

export function hideLoader() {
    console.log('Hiding loader...');
    const overlay = document.getElementById('loaderOverlay');
    if (!overlay) {
        console.error('Loader overlay element not found!');
        return;
    }
    
    overlay.classList.remove('active');
    
    // Wait for transition to complete before hiding
    setTimeout(() => {
        overlay.classList.add('hidden');
        console.log('Loader hidden');
    }, 300);
}

// --- Progress Functions ---
export function updateProgress(currentChapter, totalChapters) {
    document.getElementById('current-chapter').textContent = currentChapter;
    document.getElementById('total-chapters').textContent = totalChapters;
    
    // Dispatch event for new chapter loaded (for font size manager)
    document.dispatchEvent(new CustomEvent('newChapterLoaded'));
}

// --- Navigation Functions ---
export function goToLessonTopicScreen() {
    if (!selectedCategory) {
        showError('Please select a story category to continue');
        return;
    }
    // Add hidden class to trigger transition
    document.getElementById('storyCategoryScreen').classList.add('hidden');
    // Remove hidden class to trigger transition
    document.getElementById('lessonTopicScreen').classList.remove('hidden');
    
    // Get total lesson topics from global config
    const totalLessonTopics = window.appConfig?.totalLessonTopics || 0;
    
    // Initialize the lesson carousel with our Carousel class
    window.lessonCarousel = new Carousel({
        elementId: 'lessonCarousel',
        itemCount: totalLessonTopics,
        dataAttribute: 'topic',
        inputId: 'lessonTopic',
        onSelect: (topic) => {
            selectedLessonTopic = topic;
        }
    });
    
    // Update the keyboard navigation to include the lesson carousel
    setupCarouselKeyboardNavigation([window.categoryCarousel, window.lessonCarousel]);
    
    // Fix mobile-specific active card scaling if needed
    if (window.innerWidth <= 768) {
        window.lessonCarousel.fixMobileActiveCardScaling();
    }
}

export async function startAdventure() {
    console.log('[FrontendWS Log 0] startAdventure called. Category:', selectedCategory, 'Topic:', selectedLessonTopic);
    // Validate both inputs
    if (!selectedCategory) {
        showError('Please select a story category to continue');
        return;
    }
    
    if (!selectedLessonTopic) {
        showError('Please select a lesson topic to begin');
        return;
    }
    
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
    console.log('[FrontendWS Log 1] Before calling initWebSocket() in startAdventure.');
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
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = text;
    const decodedText = tempDiv.textContent;

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
        console.log('Detected dialogue at paragraph start - ensuring proper formatting');
        // Ensure the quotation mark is preserved
        textToAdd = decodedText;
    }

    // Check if we're starting a new paragraph after a double newline
    if (streamBuffer.endsWith('\n\n') && decodedText.trim().startsWith('"')) {
        console.log('Detected dialogue at new paragraph - ensuring proper formatting');
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

    // Always scroll to bottom as text streams in
    storyContent.scrollTop = storyContent.scrollHeight;
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
    
    // Update chapter number to show we're in the summary
    updateProgress(state.current_chapter.chapter_number, state.stats.total_lessons);
    
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
        } else if (data.type === 'adventure_created' || data.type === 'adventure_loaded') {
            // Store the adventure_id for persistence
            if (data.adventure_id && window.appState?.wsManager) {
                window.appState.wsManager.setAdventureId(data.adventure_id);
                console.log(`Received adventure_id: ${data.adventure_id} from server`);
            }
             // If adventure_loaded, update selectedCategory and selectedLessonTopic from server state
            if (data.type === 'adventure_loaded' && data.state) {
                selectedCategory = data.state.story_category || selectedCategory;
                selectedLessonTopic = data.state.lesson_topic || selectedLessonTopic;
                console.log(`[FrontendWS] Adventure loaded. Category: ${selectedCategory}, Topic: ${selectedLessonTopic}`);
                
                // CRITICAL FIX: Update progress display with correct chapter information from server
                if (data.state.chapters && Array.isArray(data.state.chapters)) {
                    const currentChapterNumber = data.state.chapters.length + 1;
                    const totalChapters = data.state.story_length || 10;
                    console.log(`[CHAPTER DISPLAY FIX] Updating progress: Chapter ${currentChapterNumber} of ${totalChapters}`);
                    console.log(`[CHAPTER DISPLAY FIX] Server state chapters count: ${data.state.chapters.length}`);
                    console.log(`[CHAPTER DISPLAY FIX] Server state story_length: ${data.state.story_length}`);
                    updateProgress(currentChapterNumber, totalChapters);
                } else {
                    console.warn(`[CHAPTER DISPLAY FIX] No chapters array found in server state:`, data.state);
                }
                
                // Update hidden inputs if they exist (they might not on direct resume)
                const storyCatEl = document.getElementById('storyCategory');
                const lessonTopicEl = document.getElementById('lessonTopic');
                if (storyCatEl) storyCatEl.value = selectedCategory;
                if (lessonTopicEl) lessonTopicEl.value = selectedLessonTopic;
            }
            // Don't hide loader here - wait for hide_loader message
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
    
    // Re-initialize the category carousel with our Carousel class
    const totalCategories = window.appConfig?.totalCategories || 0;
    window.categoryCarousel = new Carousel({
        elementId: 'categoryCarousel',
        itemCount: totalCategories,
        dataAttribute: 'category',
        inputId: 'storyCategory',
        onSelect: (categoryId) => {
            selectedCategory = categoryId;
        }
    });
    
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
