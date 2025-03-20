/**
 * Summary Chapter Manager
 * 
 * Handles the typewriter animation and navigation for chapter summaries
 */
class SummaryChapterManager {
  constructor() {
    // DOM Elements - with defensive null checks
    this.congratsView = document.getElementById('congratsView');
    this.summaryView = document.getElementById('summaryView');
    this.summaryContent = document.getElementById('summaryContent');
    
    if (this.summaryContent) {
      this.chapterHeader = this.summaryContent.querySelector('.chapter-header');
      this.chapterNumber = this.chapterHeader ? this.chapterHeader.querySelector('.chapter-number') : null;
      this.chapterTitle = this.chapterHeader ? this.chapterHeader.querySelector('.chapter-title') : null;
      this.chapterSummary = this.summaryContent.querySelector('.chapter-summary');
      this.yourChoices = this.summaryContent.querySelector('.your-choices ul');
      this.keyLearnings = this.summaryContent.querySelector('.key-learnings ul');
      this.chapterTypeIndicator = this.summaryContent.querySelector('.chapter-type');
    }
    
    this.currentSummary = document.getElementById('current-summary');
    this.totalSummaries = document.getElementById('total-summaries');
    this.prevButton = document.getElementById('prevSummary');
    this.nextButton = document.getElementById('nextSummary');
    this.viewSummariesButton = document.getElementById('viewSummaries');
    this.seeProgressButton = document.getElementById('seeProgress');
    this.chapterTabs = document.querySelector('.chapter-tabs');
    
    // State
    this.summaries = [];
    this.currentIndex = 0;
    this.isTyping = false;
    
    // Bind event handlers - with defensive null checks
    if (this.prevButton) {
      this.prevButton.addEventListener('click', this.showPreviousSummary.bind(this));
    }
    
    if (this.nextButton) {
      this.nextButton.addEventListener('click', this.showNextSummary.bind(this));
    }
    
    if (this.seeProgressButton) {
      this.seeProgressButton.addEventListener('click', this.showLearningProgress.bind(this));
    }
    
    // Add keyboard navigation
    document.addEventListener('keydown', this.handleKeyNavigation.bind(this));
    
    // Log initialization for debugging
    console.log('SummaryChapterManager initialized');
    this.logElementStatus();
  }
  
  /**
   * Log the status of DOM elements for debugging
   */
  logElementStatus() {
    console.log('DOM Element Status:');
    console.log('- congratsView:', this.congratsView ? 'Found' : 'Missing');
    console.log('- summaryView:', this.summaryView ? 'Found' : 'Missing');
    console.log('- summaryContent:', this.summaryContent ? 'Found' : 'Missing');
    console.log('- chapterHeader:', this.chapterHeader ? 'Found' : 'Missing');
    console.log('- chapterNumber:', this.chapterNumber ? 'Found' : 'Missing');
    console.log('- chapterTitle:', this.chapterTitle ? 'Found' : 'Missing');
    console.log('- chapterSummary:', this.chapterSummary ? 'Found' : 'Missing');
    console.log('- yourChoices:', this.yourChoices ? 'Found' : 'Missing');
    console.log('- keyLearnings:', this.keyLearnings ? 'Found' : 'Missing');
    console.log('- chapterTypeIndicator:', this.chapterTypeIndicator ? 'Found' : 'Missing');
    console.log('- currentSummary:', this.currentSummary ? 'Found' : 'Missing');
    console.log('- totalSummaries:', this.totalSummaries ? 'Found' : 'Missing');
    console.log('- prevButton:', this.prevButton ? 'Found' : 'Missing');
    console.log('- nextButton:', this.nextButton ? 'Found' : 'Missing');
    console.log('- viewSummariesButton:', this.viewSummariesButton ? 'Found' : 'Missing');
    console.log('- seeProgressButton:', this.seeProgressButton ? 'Found' : 'Missing');
    console.log('- chapterTabs:', this.chapterTabs ? 'Found' : 'Missing');
  }
  
  /**
   * Initialize the summary chapter with data
   * @param {Array} summaries - Array of chapter summaries from generate_chapter_summaries.py
   */
  initialize(summaries) {
    if (!summaries || !Array.isArray(summaries) || summaries.length === 0) {
      console.error('Invalid summaries data:', summaries);
      return;
    }
    
    console.log('Initializing with summaries:', summaries);
    this.summaries = summaries;
    this.currentIndex = 0;
    
    // Update total count
    if (this.totalSummaries) {
      this.totalSummaries.textContent = this.summaries.length;
    }
    
    // Create chapter tabs
    this.createChapterTabs();
    
    // Show congratulatory view first
    this.showCongratsView();
    
    // After animation completes, show the "Let's Recap Your Adventure" button
    if (this.viewSummariesButton) {
      setTimeout(() => {
        this.viewSummariesButton.classList.remove('opacity-0');
        this.viewSummariesButton.classList.add('show');
      }, 2500); // Slightly faster to match the new animation timing
      
      // Add event listener to the button
      this.viewSummariesButton.addEventListener('click', () => {
        this.transitionToSummaryView();
      });
    }
  }
  
  /**
   * Create vertical tabs for chapter navigation
   */
  createChapterTabs() {
    if (!this.chapterTabs || !this.summaries || this.summaries.length === 0) {
      console.warn('Cannot create chapter tabs: Missing elements or data');
      return;
    }
    
    // Clear any existing tabs
    this.chapterTabs.innerHTML = '';
    
    // Create a tab for each chapter
    this.summaries.forEach((summary, index) => {
      const tab = document.createElement('div');
      tab.className = 'chapter-tab';
      tab.textContent = index + 1;
      tab.dataset.index = index;
      
      // Add click event listener
      tab.addEventListener('click', () => {
        this.showSummary(index);
      });
      
      this.chapterTabs.appendChild(tab);
    });
    
    console.log(`Created ${this.summaries.length} chapter tabs`);
  }
  
  /**
   * Show the congratulatory view with stars animation
   */
  showCongratsView() {
    if (!this.congratsView) {
      console.warn('Cannot show congratulatory view: Missing element');
      return;
    }
    
    // Create stars animation
    this.createCongratsAnimation();
    
    // Show the congratulatory view
    this.congratsView.classList.remove('hidden');
    console.log('Showing congratulatory view');
  }
  
  /**
   * Transition from congratulatory view to summary view
   */
  transitionToSummaryView() {
    if (!this.congratsView || !this.summaryView) {
      console.warn('Cannot transition to summary view: Missing elements');
      return;
    }
    
    // Hide congratulatory view with fade-out animation
    this.congratsView.classList.add('animate-fadeOut');
    console.log('Transitioning to summary view');
    
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
    if (!this.congratsView) {
      console.warn('Cannot create congratulatory animation: Missing element');
      return;
    }
    
    const starsContainer = this.congratsView.querySelector('.congratulation-stars');
    if (!starsContainer) {
      console.warn('Cannot create stars: Missing container');
      return;
    }
    
    // Clear any existing stars
    starsContainer.innerHTML = '';
    
    // Create exactly 4 evenly spaced stars
    for (let i = 0; i < 4; i++) {
      const star = document.createElement('div');
      star.className = 'star';
      
      // Animation delay - staggered for each star
      const delay = 0.5 + (i * 0.2);
      
      // Set animation
      star.style.animation = `starPop 0.5s ease-out ${delay}s forwards`;
      
      starsContainer.appendChild(star);
    }
    
    console.log('Created congratulatory stars animation');
  }
  
  /**
   * Extract choices from a chapter summary
   * @param {string} summary - The chapter summary text
   * @returns {Array} - Array of choices
   */
  extractChoices(summary, chapterType) {
    if (!summary) {
      console.warn('Cannot extract choices: Missing summary text');
      return ['No choices available'];
    }
    
    // Default placeholder choices
    return ['Made a choice during the adventure', 'Explored the environment'];
  }
  
  /**
   * Extract key learnings from a chapter summary
   * @param {string} summary - The chapter summary text
   * @returns {Array} - Array of key learnings
   */
  extractLearnings(summary, chapterType) {
    if (!summary) {
      console.warn('Cannot extract learnings: Missing summary text');
      return ['No learnings available'];
    }
    
    // Default placeholder learnings
    return ['Gained knowledge through the adventure', 'Developed problem-solving skills'];
  }
  
  /**
   * Show a specific summary with all its components
   * @param {number} index - Index of the summary to show
   */
  showSummary(index) {
    // Validate index and data
    if (index < 0 || !this.summaries || index >= this.summaries.length) {
      console.warn(`Cannot show summary: Invalid index ${index} or missing data`);
      return;
    }
    
    // Check for required DOM elements
    if (!this.chapterNumber || !this.chapterTitle || !this.chapterSummary || 
        !this.yourChoices || !this.keyLearnings || !this.chapterTypeIndicator) {
      console.warn('Cannot show summary: Missing required DOM elements');
      console.log('DOM Element Status for showSummary:');
      console.log('- chapterNumber:', this.chapterNumber ? 'Found' : 'Missing');
      console.log('- chapterTitle:', this.chapterTitle ? 'Found' : 'Missing');
      console.log('- chapterSummary:', this.chapterSummary ? 'Found' : 'Missing');
      console.log('- yourChoices:', this.yourChoices ? 'Found' : 'Missing');
      console.log('- keyLearnings:', this.keyLearnings ? 'Found' : 'Missing');
      console.log('- chapterTypeIndicator:', this.chapterTypeIndicator ? 'Found' : 'Missing');
      return;
    }
    
    // Update current index
    this.currentIndex = index;
    console.log(`Showing summary for chapter ${index + 1}`);
    
    // Get the summary data
    const summaryData = this.summaries[index];
    const chapterNum = summaryData.chapter_number;
    const chapterType = summaryData.chapter_type;
    const summaryText = summaryData.summary;
    
    // Update chapter tabs
    this.updateChapterTabs();
    
    // Update navigation buttons
    this.updateNavigationButtons();
    
    // Update current summary number
    if (this.currentSummary) {
      this.currentSummary.textContent = chapterNum;
    }
    
    // Update chapter header with generic title
    this.chapterNumber.textContent = chapterNum;
    this.chapterTitle.textContent = "Recap";
    
    // Update chapter summary
    if (this.chapterSummary) {
      // Find or create the paragraph element
      let summaryParagraph = this.chapterSummary.querySelector('p');
      if (!summaryParagraph) {
        summaryParagraph = document.createElement('p');
        this.chapterSummary.appendChild(summaryParagraph);
      }
      summaryParagraph.textContent = summaryText;
    }
    
    // Extract and update choices
    const choices = this.extractChoices(summaryText, chapterType);
    this.yourChoices.innerHTML = '';
    choices.forEach(choice => {
      const li = document.createElement('li');
      li.textContent = choice;
      this.yourChoices.appendChild(li);
    });
    
    // Extract and update key learnings
    const learnings = this.extractLearnings(summaryText, chapterType);
    this.keyLearnings.innerHTML = '';
    learnings.forEach(learning => {
      const li = document.createElement('li');
      li.textContent = learning;
      this.keyLearnings.appendChild(li);
    });
    
    // Update chapter type indicator
    this.chapterTypeIndicator.textContent = `${chapterType.charAt(0).toUpperCase() + chapterType.slice(1)} Chapter`;
    this.chapterTypeIndicator.className = `chapter-type ${chapterType.toLowerCase()}`;
  }
  
  /**
   * Update the active chapter tab
   */
  updateChapterTabs() {
    if (!this.chapterTabs) {
      console.warn('Cannot update chapter tabs: Missing element');
      return;
    }
    
    // Remove active class from all tabs
    const tabs = this.chapterTabs.querySelectorAll('.chapter-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Add active class to current tab
    const currentTab = this.chapterTabs.querySelector(`.chapter-tab[data-index="${this.currentIndex}"]`);
    if (currentTab) {
      currentTab.classList.add('active');
    }
  }
  
  /**
   * Show the previous summary
   */
  showPreviousSummary() {
    if (this.currentIndex > 0) {
      this.showSummary(this.currentIndex - 1);
    }
  }
  
  /**
   * Show the next summary
   */
  showNextSummary() {
    if (this.currentIndex < this.summaries.length - 1) {
      this.showSummary(this.currentIndex + 1);
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
    if (!this.prevButton || !this.nextButton) {
      console.warn('Cannot update navigation buttons: Missing elements');
      return;
    }
    
    // Disable/enable previous button
    this.prevButton.disabled = this.currentIndex === 0;
    
    // Disable/enable next button
    this.nextButton.disabled = this.currentIndex === this.summaries.length - 1;
    
    // Add micro-interaction to buttons
    this.prevButton.classList.toggle('opacity-50', this.currentIndex === 0);
    this.nextButton.classList.toggle('opacity-50', this.currentIndex === this.summaries.length - 1);
  }
  
  /**
   * Show learning progress
   * This would typically navigate to a learning progress page
   * For now, we'll just show an alert
   */
  showLearningProgress() {
    alert('Learning Progress: This feature will be implemented in a future update.');
  }
  
  /**
   * Reset journey and return to start
   */
  resetJourney() {
    if (!this.summaryView) {
      console.warn('Cannot reset journey: Missing element');
      return;
    }
    
    // Add exit animation to summary view
    this.summaryView.classList.add('animate-fadeOut');
    
    // In a real implementation, this would navigate back to the start
    // For our test implementation, we'll just reload the page
    setTimeout(() => {
      window.location.reload();
    }, 500);
  }
}

// Ensure the script runs after the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM fully loaded, initializing SummaryChapterManager');
});
