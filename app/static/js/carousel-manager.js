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
    // Use at least 5 slots for geometry so carousels with 2-4 items don't look flat
    this.effectiveCount = Math.max(this.itemCount, 5);
    this.dataAttribute = options.dataAttribute;
    this.inputId = options.inputId;
    this.onSelect = options.onSelect || function() {};
    
    // State
    this.currentRotation = 0;
    this.currentIndex = 0;
    this.rotationAngle = 360 / this.effectiveCount;
    this.selectedValue = '';
    
    // DOM Elements
    this.element = document.getElementById(this.elementId);
    this.inputElement = document.getElementById(this.inputId);
    
    // Register this instance for global tracking
    if (!window.carouselInstances) {
      window.carouselInstances = {};
    }
    window.carouselInstances[this.elementId] = this;
    
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
    
    // Calculate dynamic radius based on card count to prevent overlap
    const cardWidth = cards.length > 0 ? cards[0].offsetWidth : 300;
    const radius = (cardWidth / 2) / Math.tan(Math.PI / this.effectiveCount);
    
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
      if (index === this.currentIndex) {
        card.classList.add('active');
        card.style.willChange = 'transform';
      } else {
        card.classList.remove('active');
        card.style.willChange = 'auto';
      }
    });
  }
  
  /**
   * Select a card by its data attribute value
   * @param {string} value - The value to select
   */
  select(value) {
    const cards = this.element.getElementsByClassName('carousel-card');
    const targetCard = Array.from(cards).find(card => card.dataset[this.dataAttribute] === value);
    
    if (targetCard) {
      // Check if the card is already selected - if so, toggle it off
      if (targetCard.classList.contains('selected')) {
        targetCard.classList.remove('selected', 'selecting');
        this.selectedValue = '';
        if (this.inputElement) {
          this.inputElement.value = '';
        }
      } else {
        // Remove selected class from all cards and add to the chosen one
        Array.from(cards).forEach(card => {
          card.classList.remove('selected', 'selecting');
        });
        
        targetCard.classList.add('selected', 'selecting');
        setTimeout(() => targetCard.classList.remove('selecting'), 300);
        
        this.selectedValue = value;
        if (this.inputElement) {
          this.inputElement.value = value;
        }
        
        // Call the onSelect callback
        this.onSelect(value);
      }
    }
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
  
  /**
   * Reposition the carousel - recalculates radius and card positions
   * This serves as a fallback mechanism to fix 3D positioning if initial calculation fails
   * Can be called manually from console to force re-calculation of card transforms
   */
  reposition() {
    if (!this.element) {
      console.error(`Carousel element with ID "${this.elementId}" not found!`);
      return false;
    }
    
    const cards = this.element.getElementsByClassName('carousel-card');
    if (cards.length === 0) {
      console.warn('No carousel cards found to reposition');
      return false;
    }
    
    console.log(`Repositioning carousel "${this.elementId}" with ${cards.length} cards...`);
    
    try {
      // Force layout recalculation by temporarily showing element if hidden
      const wasHidden = this.element.offsetParent === null;
      let originalDisplay = null;
      
      if (wasHidden) {
        originalDisplay = this.element.style.display;
        this.element.style.display = 'block';
        this.element.style.visibility = 'hidden';
      }
      
      // Get current card dimensions (force recalculation)
      const firstCard = cards[0];
      firstCard.style.transform = 'none'; // Temporarily remove transform
      const cardWidth = firstCard.offsetWidth;
      firstCard.style.transform = ''; // Restore transform
      
      console.log(`Card width: ${cardWidth}px, Item count: ${this.itemCount}`);
      
      // Recalculate radius using the same logic as init()
      const calculatedRadius = (cardWidth / 2) / Math.tan(Math.PI / this.effectiveCount);
      const radius = calculatedRadius;
      
      console.log(`Calculated radius: ${calculatedRadius.toFixed(2)}px, Final radius: ${radius}px`);
      
      // Apply new transforms to all cards
      for (let i = 0; i < cards.length; i++) {
        const angle = (i * this.rotationAngle);
        const newTransform = `rotateY(${angle}deg) translateZ(${radius}px)`;
        cards[i].style.transform = newTransform;
        cards[i].style.visibility = 'visible';
        console.log(`Card ${i}: angle=${angle}deg, transform=${newTransform}`);
      }
      
      // Restore original display state if we modified it
      if (wasHidden && originalDisplay !== null) {
        this.element.style.display = originalDisplay;
        this.element.style.visibility = '';
      }
      
      // Reapply current rotation
      this.element.style.transform = `translate(-50%, -50%) rotateY(${this.currentRotation}deg)`;
      
      // Update active card
      this.updateActiveCard();
      
      console.log(`Carousel "${this.elementId}" repositioned successfully`);
      return true;
      
    } catch (error) {
      console.error(`Error during carousel reposition:`, error);
      return false;
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

/**
 * Global convenience functions for debugging and testing
 */

/**
 * Reposition all carousels on the page
 * Useful for fixing flat carousels after layout changes
 * @returns {Object} Results of repositioning attempts
 */
function repositionAllCarousels() {
  console.log('🔄 Repositioning all carousels...');
  const results = {
    attempted: 0,
    successful: 0,
    failed: 0,
    details: []
  };
  
  // Find all carousel elements
  const carouselElements = document.querySelectorAll('[class*="carousel-container"] .carousel, .carousel');
  
  carouselElements.forEach((element, index) => {
    const carouselId = element.id || `carousel-${index}`;
    results.attempted++;
    
    // Try to find the carousel instance
    if (window.carouselInstances && window.carouselInstances[carouselId]) {
      const carousel = window.carouselInstances[carouselId];
      const success = carousel.reposition();
      if (success) {
        results.successful++;
        results.details.push(`✅ ${carouselId}: repositioned successfully`);
      } else {
        results.failed++;
        results.details.push(`❌ ${carouselId}: reposition failed`);
      }
    } else {
      results.failed++;
      results.details.push(`❌ ${carouselId}: no carousel instance found`);
    }
  });
  
  console.log(`📊 Results: ${results.successful}/${results.attempted} carousels repositioned successfully`);
  results.details.forEach(detail => console.log(detail));
  
  return results;
}

/**
 * Reposition a specific carousel by ID
 * @param {string} carouselId - The ID of the carousel to reposition
 * @returns {boolean} Success status
 */
function repositionCarousel(carouselId) {
  console.log(`🔄 Repositioning carousel "${carouselId}"...`);
  
  if (window.carouselInstances && window.carouselInstances[carouselId]) {
    const carousel = window.carouselInstances[carouselId];
    const success = carousel.reposition();
    if (success) {
      console.log(`✅ Carousel "${carouselId}" repositioned successfully`);
    } else {
      console.log(`❌ Carousel "${carouselId}" reposition failed`);
    }
    return success;
  } else {
    console.error(`❌ Carousel instance "${carouselId}" not found`);
    console.log('Available carousels:', Object.keys(window.carouselInstances || {}));
    return false;
  }
}

/**
 * Debug carousel positioning by logging current state
 * @param {string} carouselId - The ID of the carousel to debug
 */
function debugCarousel(carouselId) {
  console.log(`🔍 Debugging carousel "${carouselId}"...`);
  
  const element = document.getElementById(carouselId);
  if (!element) {
    console.error(`❌ Carousel element "${carouselId}" not found`);
    return;
  }
  
  const cards = element.getElementsByClassName('carousel-card');
  console.log(`📋 Carousel "${carouselId}" debug info:`);
  console.log(`  - Element:`, element);
  console.log(`  - Card count: ${cards.length}`);
  console.log(`  - Element dimensions: ${element.offsetWidth}x${element.offsetHeight}`);
  console.log(`  - Element transform:`, element.style.transform || 'none');
  console.log(`  - Element visibility:`, window.getComputedStyle(element).visibility);
  console.log(`  - Element display:`, window.getComputedStyle(element).display);
  
  if (cards.length > 0) {
    console.log(`  - Card dimensions: ${cards[0].offsetWidth}x${cards[0].offsetHeight}`);
    Array.from(cards).forEach((card, i) => {
      console.log(`  - Card ${i} transform:`, card.style.transform || 'none');
    });
  }
  
  if (window.carouselInstances && window.carouselInstances[carouselId]) {
    const carousel = window.carouselInstances[carouselId];
    console.log(`  - Current rotation: ${carousel.currentRotation}deg`);
    console.log(`  - Current index: ${carousel.currentIndex}`);
    console.log(`  - Rotation angle: ${carousel.rotationAngle}deg`);
  }
}

// Export for ES6 modules
export { Carousel, setupCarouselKeyboardNavigation, repositionAllCarousels, repositionCarousel, debugCarousel };

// Also make available globally for onclick handlers and console testing
window.Carousel = Carousel;
window.setupCarouselKeyboardNavigation = setupCarouselKeyboardNavigation;
window.repositionAllCarousels = repositionAllCarousels;
window.repositionCarousel = repositionCarousel;
window.debugCarousel = debugCarousel;
