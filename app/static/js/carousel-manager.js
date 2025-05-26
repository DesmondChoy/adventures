/**
 * Carousel - Manages 3D carousel functionality
 * 
 * Features:
 * - Rotation with keyboard, button, and touch controls
 * - Card selection with visual feedback
 * - Responsive design for mobile and desktop
 */
class Carousel {
  /**
   * Create a new carousel instance
   * @param {Object} options - Configuration options
   * @param {string} options.elementId - ID of the carousel element
   * @param {number} options.itemCount - Number of items in the carousel
   * @param {string} options.dataAttribute - Data attribute for selection (e.g., 'category', 'topic')
   * @param {string} options.inputId - ID of the input element to update on selection
   * @param {Function} options.onSelect - Callback function when an item is selected
   */
  constructor(options) {
    // Configuration
    this.elementId = options.elementId;
    this.itemCount = options.itemCount;
    this.dataAttribute = options.dataAttribute;
    this.inputId = options.inputId;
    this.onSelect = options.onSelect || function() {};
    
    // State
    this.currentRotation = 0;
    this.currentIndex = 0;
    this.rotationAngle = 360 / this.itemCount;
    this.selectedValue = '';
    
    // DOM Elements
    this.element = document.getElementById(this.elementId);
    this.inputElement = document.getElementById(this.inputId);
    
    // Initialize
    this.init();
  }
  
  /**
   * Initialize the carousel
   */
  init() {
    if (!this.element) {
      console.error(`Carousel element with ID "${this.elementId}" not found!`);
      return;
    }
    
    // Position cards in 3D space
    const cards = this.element.getElementsByClassName('carousel-card');
    const radius = 400;
    
    try {
      for (let i = 0; i < cards.length; i++) {
        const angle = (i * this.rotationAngle);
        cards[i].style.transform = `rotateY(${angle}deg) translateZ(${radius}px)`;
        cards[i].style.visibility = 'visible';
      }
      
      // Set initial active card
      this.updateActiveCard();
      
      // Add event listeners
      this.setupEventListeners();
    } catch (error) {
      console.error(`Error during carousel initialization:`, error);
    }
  }
  
  /**
   * Set up event listeners for the carousel
   */
  setupEventListeners() {
    // Add touch event handling
    let touchStartX = 0;
    let touchEndX = 0;
    
    this.element.addEventListener('touchstart', (event) => {
      touchStartX = event.touches[0].clientX;
      // Hide swipe tip on first touch
      const swipeTip = document.querySelector('.swipe-tip');
      if (swipeTip) swipeTip.style.display = 'none';
    }, false);
    
    this.element.addEventListener('touchmove', (event) => {
      event.preventDefault(); // Prevent scrolling while swiping
    }, false);
    
    this.element.addEventListener('touchend', (event) => {
      touchEndX = event.changedTouches[0].clientX;
      this.handleSwipe(touchStartX, touchEndX);
    }, false);
    
    // Add click handlers to cards
    const cards = this.element.getElementsByClassName('carousel-card');
    Array.from(cards).forEach(card => {
      card.addEventListener('click', () => {
        const value = card.dataset[this.dataAttribute];
        if (value) {
          this.select(value);
        }
      });
    });
  }
  
  /**
   * Handle swipe gestures
   * @param {number} startX - Starting X position
   * @param {number} endX - Ending X position
   */
  handleSwipe(startX, endX) {
    const swipeThreshold = 50; // Minimum distance for a swipe
    const swipeDistance = endX - startX;
    
    if (Math.abs(swipeDistance) > swipeThreshold) {
      if (swipeDistance > 0) {
        // Swipe right
        this.rotate('prev');
      } else {
        // Swipe left
        this.rotate('next');
      }
    }
  }
  
  /**
   * Rotate the carousel
   * @param {string} direction - Direction to rotate ('next' or 'prev')
   */
  rotate(direction) {
    if (direction === 'next') {
      this.currentRotation -= this.rotationAngle;
      this.currentIndex = (this.currentIndex + 1) % this.itemCount;
    } else {
      this.currentRotation += this.rotationAngle;
      this.currentIndex = (this.currentIndex - 1 + this.itemCount) % this.itemCount;
    }
    
    this.element.style.transform = `translate(-50%, -50%) rotateY(${this.currentRotation}deg)`;
    
    // Update active state
    this.updateActiveCard();
  }
  
  /**
   * Update the active card
   */
  updateActiveCard() {
    const cards = this.element.getElementsByClassName('carousel-card');
    Array.from(cards).forEach((card, index) => {
      card.classList.remove('active');
      if (index === this.currentIndex) {
        card.classList.add('active');
      }
    });
  }
  
  /**
   * Select a card by its data attribute value
   * @param {string} value - The value to select
   */
  select(value) {
    this.selectedValue = value;
    
    if (this.inputElement) {
      this.inputElement.value = value;
    }
    
    // Remove selected class from all cards and add to the chosen one
    const cards = this.element.getElementsByClassName('carousel-card');
    Array.from(cards).forEach(card => {
      card.classList.remove('selected', 'selecting');
      if (card.dataset[this.dataAttribute] === value) {
        card.classList.add('selected', 'selecting');
        setTimeout(() => card.classList.remove('selecting'), 300);
      }
    });
    
    // Call the onSelect callback
    this.onSelect(value);
  }
  
  /**
   * Handle keyboard navigation
   * @param {KeyboardEvent} event - The keyboard event
   */
  handleKeyPress(event) {
    if (event.key === 'ArrowLeft') {
      this.rotate('prev');
    } else if (event.key === 'ArrowRight') {
      this.rotate('next');
    } else if (event.key === 'Enter') {
      const cards = this.element.getElementsByClassName('carousel-card');
      const activeCard = cards[this.currentIndex];
      if (activeCard) {
        const value = activeCard.dataset[this.dataAttribute];
        if (value) {
          this.select(value);
        }
      }
    }
  }
  
  /**
   * Fix mobile-specific active card scaling
   */
  fixMobileActiveCardScaling() {
    // This function only runs on mobile devices
    if (window.innerWidth > 768) return;
    
    // Ensure the active card has the correct scaling
    const cards = this.element.getElementsByClassName('carousel-card');
    const activeCard = cards[this.currentIndex];
    
    if (activeCard) {
      // Remove active class from all cards
      Array.from(cards).forEach(card => card.classList.remove('active'));
      
      // Add active class to the current card
      activeCard.classList.add('active');
    }
  }
}

/**
 * Set up global keyboard navigation for carousels
 * @param {Array<Carousel>} carousels - Array of carousel instances
 */
function setupCarouselKeyboardNavigation(carousels) {
  document.addEventListener('keydown', (event) => {
    // Find the visible carousel
    const visibleCarousel = carousels.find(carousel => {
      const container = document.getElementById(carousel.elementId).closest('.carousel-container');
      return container && !container.closest('.hidden');
    });
    
    if (visibleCarousel) {
      visibleCarousel.handleKeyPress(event);
    }
  });
}

// Export for ES6 modules
export { Carousel, setupCarouselKeyboardNavigation };

// Also make available globally for onclick handlers
window.Carousel = Carousel;
window.setupCarouselKeyboardNavigation = setupCarouselKeyboardNavigation;
