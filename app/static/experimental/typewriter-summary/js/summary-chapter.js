/**
 * Summary Chapter Manager
 * 
 * Handles the typewriter animation and navigation for chapter summaries
 */
class SummaryChapterManager {
  constructor() {
    // DOM Elements
    this.congratsView = document.getElementById('congratsView');
    this.summaryView = document.getElementById('summaryView');
    this.summaryContent = document.getElementById('summaryContent');
    this.chapterHeader = this.summaryContent.querySelector('.chapter-header');
    this.chapterSummaryText = this.summaryContent.querySelector('.chapter-summary-text');
    this.typewriterCursor = this.summaryContent.querySelector('.typewriter-cursor');
    this.chapterNumber = this.chapterHeader.querySelector('.chapter-number');
    this.currentSummary = document.getElementById('current-summary');
    this.totalSummaries = document.getElementById('total-summaries');
    this.prevButton = document.getElementById('prevSummary');
    this.nextButton = document.getElementById('nextSummary');
    this.viewSummariesButton = document.getElementById('viewSummaries');
    
    // State
    this.summaries = [];
    this.currentIndex = 0;
    this.isTyping = false;
    this.typewriterSpeed = 15; // ms per character (increased speed)
    
    // Bind event handlers
    this.prevButton.addEventListener('click', this.showPreviousSummary.bind(this));
    this.nextButton.addEventListener('click', this.showNextSummary.bind(this));
    
    // Add keyboard navigation
    document.addEventListener('keydown', this.handleKeyNavigation.bind(this));
  }
  
  /**
   * Initialize the summary chapter with data
   * @param {Array} summaries - Array of chapter summaries from generate_chapter_summaries.py
   */
  initialize(summaries) {
    this.summaries = summaries;
    this.currentIndex = 0;
    
    // Update total count
    this.totalSummaries.textContent = this.summaries.length;
    
    // Show congratulatory view first
    this.showCongratsView();
    
    // After animation completes, show the "View Summaries" button
    setTimeout(() => {
      this.viewSummariesButton.classList.remove('opacity-0');
      this.viewSummariesButton.classList.add('show');
    }, 3000);
    
    // Add event listener to the button
    this.viewSummariesButton.addEventListener('click', () => {
      this.transitionToSummaryView();
    });
  }
  
  /**
   * Show the congratulatory view with stars animation
   */
  showCongratsView() {
    // Create stars animation
    this.createCongratsAnimation();
    
    // Show the congratulatory view
    this.congratsView.classList.remove('hidden');
  }
  
  /**
   * Transition from congratulatory view to summary view
   */
  transitionToSummaryView() {
    // Hide congratulatory view with fade-out animation
    this.congratsView.classList.add('animate-fadeOut');
    
    // After animation completes, hide congrats view and show summary view
    setTimeout(() => {
      this.congratsView.classList.add('hidden');
      this.summaryView.classList.remove('hidden');
      this.summaryView.classList.add('animate-fadeIn');
      
      // Show first summary
      this.showSummary(0);
    }, 500);
  }
  
  /**
   * Create the congratulatory animation with stars
   */
  createCongratsAnimation() {
    const starsContainer = this.congratsView.querySelector('.congratulation-stars');
    
    // Clear any existing stars
    starsContainer.innerHTML = '';
    
    // Create 15 stars with random positions
    for (let i = 0; i < 15; i++) {
      const star = document.createElement('div');
      star.className = 'star';
      
      // Random position
      const left = Math.random() * 100;
      const top = Math.random() * 100;
      
      // Random size
      const size = 10 + Math.random() * 20;
      
      // Random animation delay
      const delay = Math.random() * 1.5;
      
      // Set styles
      star.style.left = `${left}%`;
      star.style.top = `${top}%`;
      star.style.width = `${size}px`;
      star.style.height = `${size}px`;
      star.style.animation = `starPop 0.5s ease-out ${delay}s forwards`;
      
      starsContainer.appendChild(star);
    }
  }
  
  /**
   * Show a specific summary with typewriter effect
   * @param {number} index - Index of the summary to show
   */
  showSummary(index) {
    // Validate index
    if (index < 0 || index >= this.summaries.length) {
      return;
    }
    
    // Update current index
    this.currentIndex = index;
    
    // Update navigation buttons
    this.updateNavigationButtons();
    
    // Update current summary number
    this.currentSummary.textContent = index + 1;
    
    // Update chapter header
    this.chapterNumber.textContent = this.summaries[index].chapter_number;
    
    // Clear previous text
    this.chapterSummaryText.textContent = '';
    
    // Reset header animation by removing and re-adding the element
    const oldHeader = this.chapterHeader;
    const newHeader = oldHeader.cloneNode(true);
    oldHeader.parentNode.replaceChild(newHeader, oldHeader);
    this.chapterHeader = newHeader;
    this.chapterNumber = this.chapterHeader.querySelector('.chapter-number');
    
    // Start typewriter effect
    this.typeText(this.summaries[index].summary);
  }
  
  /**
   * Type text with a handwriting animation effect
   * @param {string} text - Text to type
   */
  typeText(text) {
    // If already typing, stop
    if (this.isTyping) {
      this.isTyping = false;
      clearTimeout(this.typewriterTimeout);
    }
    
    // Reset
    this.chapterSummaryText.innerHTML = '';
    this.typewriterCursor.style.display = 'none';
    
    // Start typing with handwriting animation
    this.isTyping = true;
    
    // Create span for each character with randomized properties
    [...text].forEach((char, index) => {
      const span = document.createElement('span');
      span.textContent = char;
      span.className = 'handwriting-char';
      
      // Add randomized properties
      const rotation = (Math.random() * 6 - 3) + 'deg';
      span.style.setProperty('--rotation', rotation);
      span.style.setProperty('--index', index);
      
      // Special styling for certain characters
      if (['!', '.', '?'].includes(char)) {
        span.style.setProperty('--char-color', '#000');
        span.style.fontWeight = 'bold';
      }
      
      this.chapterSummaryText.appendChild(span);
    });
    
    // Set a timeout to mark typing as complete
    const totalDuration = text.length * 8 + 500; // Total animation time (adjusted for faster speed)
    this.typewriterTimeout = setTimeout(() => {
      this.isTyping = false;
    }, totalDuration);
    
    // Scroll to keep up with typing
    const scrollInterval = setInterval(() => {
      this.chapterSummaryText.scrollTop = this.chapterSummaryText.scrollHeight;
      if (!this.isTyping) clearInterval(scrollInterval);
    }, 100);
  }
  
  /**
   * Show the previous summary
   */
  showPreviousSummary() {
    if (this.currentIndex > 0) {
      // Add exit animation
      this.chapterSummaryText.style.animation = 'fadeOut 0.3s forwards';
      
      setTimeout(() => {
        this.chapterSummaryText.style.animation = '';
        this.showSummary(this.currentIndex - 1);
      }, 300);
    }
  }
  
  /**
   * Show the next summary
   */
  showNextSummary() {
    if (this.currentIndex < this.summaries.length - 1) {
      // Add exit animation
      this.chapterSummaryText.style.animation = 'fadeOut 0.3s forwards';
      
      setTimeout(() => {
        this.chapterSummaryText.style.animation = '';
        this.showSummary(this.currentIndex + 1);
      }, 300);
    }
  }
  
  /**
   * Handle keyboard navigation
   * @param {KeyboardEvent} event - Keyboard event
   */
  handleKeyNavigation(event) {
    if (event.key === 'ArrowLeft') {
      this.showPreviousSummary();
    } else if (event.key === 'ArrowRight') {
      this.showNextSummary();
    }
  }
  
  /**
   * Update navigation buttons based on current index
   */
  updateNavigationButtons() {
    // Disable/enable previous button
    this.prevButton.disabled = this.currentIndex === 0;
    
    // Disable/enable next button
    this.nextButton.disabled = this.currentIndex === this.summaries.length - 1;
    
    // Add micro-interaction to buttons
    this.prevButton.classList.toggle('opacity-50', this.currentIndex === 0);
    this.nextButton.classList.toggle('opacity-50', this.currentIndex === this.summaries.length - 1);
  }
  
  /**
   * Reset journey and return to start
   */
  resetJourney() {
    // Add exit animation to summary view
    this.summaryView.classList.add('animate-fadeOut');
    
    // In a real implementation, this would navigate back to the start
    // For our test implementation, we'll just reload the page
    setTimeout(() => {
      window.location.reload();
    }, 500);
  }
}
