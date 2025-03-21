// Placeholder JavaScript file for the Adventure Summary React application

// This is a simple placeholder script that will be replaced when the React app is built
console.log('Adventure Summary placeholder script loaded');

// Add a simple function to show a message when the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Adventure Summary page loaded');
    
    // Add a message to the page if it's the placeholder version
    const container = document.querySelector('.container');
    if (container) {
        const statusElement = document.createElement('div');
        statusElement.style.marginTop = '20px';
        statusElement.style.padding = '10px';
        statusElement.style.backgroundColor = '#e3f2fd';
        statusElement.style.borderRadius = '4px';
        statusElement.textContent = 'This is the placeholder version of the Adventure Summary page. The React app has not been built yet.';
        container.appendChild(statusElement);
    }
});

// Add a simple function to handle the return button click
function handleReturnClick() {
    console.log('Return button clicked');
    window.location.href = '/adventure';
    return false;
}

// Export a dummy function for testing
function getSummaryData() {
    return {
        chapterSummaries: [
            {
                number: 1,
                title: 'Placeholder Chapter 1',
                summary: 'This is a placeholder summary for chapter 1.',
                chapterType: 'STORY'
            },
            {
                number: 2,
                title: 'Placeholder Chapter 2',
                summary: 'This is a placeholder summary for chapter 2.',
                chapterType: 'LESSON'
            }
        ],
        educationalQuestions: [
            {
                question: 'Placeholder question 1?',
                userAnswer: 'Placeholder answer',
                isCorrect: true,
                explanation: 'This is a placeholder explanation.'
            }
        ],
        statistics: {
            chaptersCompleted: 10,
            questionsAnswered: 5,
            timeSpent: '45 mins',
            correctAnswers: 4
        }
    };
}
