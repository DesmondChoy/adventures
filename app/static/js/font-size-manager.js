/**
 * FontSizeManager - Manages font size adjustments for mobile users
 * 
 * Features:
 * - Increase/decrease font size with + and - buttons
 * - Display current font size as percentage
 * - Save preferences to localStorage
 * - Show/hide controls on scroll (matching chapter indicator behavior)
 */
class FontSizeManager {
    constructor() {
        // Configuration
        this.defaultSize = 1.2; // rem (matches --font-size-content in typography.css)
        this.minSize = 0.8; // rem
        this.maxSize = 2.0; // rem
        this.step = 0.1; // rem
        
        // State
        this.currentSize = this.loadSavedSize() || this.defaultSize;
        
        // DOM Elements
        this.contentElement = document.querySelector('.markdown-content');
        this.choicesContainer = document.getElementById('choicesContainer');
        this.decreaseButton = document.getElementById('decrease-font');
        this.increaseButton = document.getElementById('increase-font');
        this.percentageDisplay = document.getElementById('font-size-percentage');
        this.fontSizeControls = document.querySelector('.font-size-controls');
        this.storyContainer = document.getElementById('storyContainer');
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize the font size manager
     */
    init() {
        // Only initialize on mobile devices
        if (window.innerWidth > 768) return;
        
        // Set initial font size
        this.applyFontSize();
        this.updatePercentageDisplay();
        
        // Add event listeners
        this.decreaseButton.addEventListener('click', () => this.decreaseFontSize());
        this.increaseButton.addEventListener('click', () => this.increaseFontSize());
        
        // Add scroll behavior
        this.setupScrollBehavior();
        
        console.log('FontSizeManager initialized');
    }
    
    /**
     * Load saved font size from localStorage
     * @returns {number} The saved font size or defaultSize if not found
     */
    loadSavedSize() {
        const saved = localStorage.getItem('font_size_preference');
        return saved ? parseFloat(saved) : this.defaultSize;
    }
    
    /**
     * Save current font size to localStorage
     */
    saveFontSize() {
        localStorage.setItem('font_size_preference', this.currentSize.toString());
    }
    
    /**
     * Apply the current font size to content elements
     */
    applyFontSize() {
        if (!this.contentElement) return;
        
        // Apply to story content
        this.contentElement.style.fontSize = `${this.currentSize}rem`;
        
        // Apply to choice buttons (maintaining the same size as content)
        if (this.choicesContainer) {
            const choiceButtons = this.choicesContainer.querySelectorAll('button');
            choiceButtons.forEach(button => {
                button.style.fontSize = `${this.currentSize}rem`;
            });
        }
    }
    
    /**
     * Update the percentage display
     */
    updatePercentageDisplay() {
        if (!this.percentageDisplay) return;
        
        // Calculate percentage based on default size
        const percentage = Math.round((this.currentSize / this.defaultSize) * 100);
        this.percentageDisplay.textContent = `${percentage}%`;
        
        // Update button states
        this.decreaseButton.disabled = this.currentSize <= this.minSize;
        this.increaseButton.disabled = this.currentSize >= this.maxSize;
    }
    
    /**
     * Increase the font size
     */
    increaseFontSize() {
        if (this.currentSize < this.maxSize) {
            this.currentSize = Math.min(this.maxSize, this.currentSize + this.step);
            this.applyFontSize();
            this.updatePercentageDisplay();
            this.saveFontSize();
        }
    }
    
    /**
     * Decrease the font size
     */
    decreaseFontSize() {
        if (this.currentSize > this.minSize) {
            this.currentSize = Math.max(this.minSize, this.currentSize - this.step);
            this.applyFontSize();
            this.updatePercentageDisplay();
            this.saveFontSize();
        }
    }
    
    /**
     * Setup scroll behavior to show/hide controls
     */
    setupScrollBehavior() {
        if (!this.storyContainer || !this.fontSizeControls) return;
        
        let lastScrollTop = 0;
        let headerControlsVisible = true;
        const headerControls = document.querySelector('.header-controls');
        
        this.storyContainer.addEventListener('scroll', () => {
            const scrollTop = this.storyContainer.scrollTop;
            
            // Hide controls when scrolling down, show when scrolling up
            if (scrollTop > lastScrollTop && headerControlsVisible && scrollTop > 50) {
                // Scrolling down
                headerControls.classList.add('header-controls-hidden');
                headerControlsVisible = false;
            } else if (scrollTop < lastScrollTop && !headerControlsVisible) {
                // Scrolling up
                headerControls.classList.remove('header-controls-hidden');
                headerControlsVisible = true;
            }
            
            lastScrollTop = scrollTop;
        });
        
        // Show controls when making a choice (going to next page)
        document.addEventListener('newChapterLoaded', () => {
            headerControls.classList.remove('header-controls-hidden');
            headerControlsVisible = true;
        });
    }
}

// Initialize font size manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait for story container to be visible
    const checkStoryContainer = setInterval(() => {
        const storyContainer = document.getElementById('storyContainer');
        if (storyContainer && !storyContainer.classList.contains('hidden')) {
            clearInterval(checkStoryContainer);
            window.fontSizeManager = new FontSizeManager();
        }
    }, 500);
});
