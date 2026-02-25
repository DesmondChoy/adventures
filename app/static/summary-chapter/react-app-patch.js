/**
 * React App Patch — Button Fixes
 *
 * This script patches the React app's buttons:
 * 1. Remove the "Return Home" button
 * 2. Fix the "Start New Adventure" button to redirect to the main app
 *
 * NOTE: Fetch patching (state_id injection + auth token) is handled by
 * summary-state-handler.js which loads BEFORE the React bundle in <head>.
 */

(function() {
    function patchButtons() {
        const allButtons = document.querySelectorAll('button, a, [role="button"]');

        allButtons.forEach(button => {
            const text = button.textContent?.trim();

            // Remove "Return Home" button entirely
            if (text === 'Return Home') {
                button.remove();
                return;
            }

            // Fix "Start New Adventure" to redirect to carousel
            if (text === 'Start New Adventure') {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();

                    // Clear adventure state
                    localStorage.removeItem('adventure_state');
                    localStorage.removeItem('summary_state_id');
                    localStorage.removeItem('summary_api_url');
                    localStorage.removeItem('summary_access_token');

                    window.location.href = '/select';
                });
            }
        });
    }

    // Patch buttons after React renders
    window.addEventListener('load', function() {
        setTimeout(patchButtons, 1000);
        setTimeout(patchButtons, 2000);
        setTimeout(patchButtons, 3000);
    });

    // Also patch when React adds new content
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const buttons = node.querySelectorAll ? node.querySelectorAll('button, a') : [];
                        if (buttons.length > 0 || node.tagName === 'BUTTON' || node.tagName === 'A') {
                            setTimeout(patchButtons, 100);
                        }
                    }
                });
            }
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Continuous monitoring to remove Return Home buttons
    setInterval(() => {
        document.querySelectorAll('button, a, [role="button"]').forEach(button => {
            if (button.textContent?.trim() === 'Return Home') {
                button.remove();
            }
        });
    }, 500);
})();
