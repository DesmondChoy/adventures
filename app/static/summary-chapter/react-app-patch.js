/**
 * React App Patch
 * 
 * This script patches the React app to use the state ID from the URL.
 * It should be included in the summary page after the React app's JavaScript.
 */

(function() {
    // Function to patch the React app's fetch function
    function patchReactFetch() {
        console.log('Patching React app fetch function');
        
        // Get the state ID from localStorage (set by summary-state-handler.js)
        const stateId = localStorage.getItem('summary_state_id');
        
        if (!stateId) {
            console.log('No state ID found in localStorage, not patching fetch');
            return;
        }
        
        console.log('Found state ID in localStorage:', stateId);
        
        // Try to find the fetch function in the React app
        // This is a bit hacky, but it's the best we can do without modifying the React app directly
        const originalFetch = window.fetch;
        
        // Override the fetch function
        window.fetch = function(url, options) {
            // Check if this is a request to the adventure summary API
            if (url && typeof url === 'string' && url.includes('/adventure/api/adventure-summary')) {
                // Add the state ID to the URL
                const separator = url.includes('?') ? '&' : '?';
                const newUrl = `${url}${separator}state_id=${stateId}`;
                console.log('Patching fetch URL:', url, '->', newUrl);
                return originalFetch(newUrl, options);
            }
            
            // Otherwise, use the original fetch function
            return originalFetch(url, options);
        };
        
        console.log('Fetch function patched successfully');
    }
    
    // Wait for the React app to load
    window.addEventListener('load', function() {
        // Give the React app a moment to initialize
        setTimeout(patchReactFetch, 500);
    });
    
    // Also listen for the custom event from summary-state-handler.js
    document.addEventListener('summaryStateIdAvailable', function(e) {
        // Patch the fetch function when the state ID is available
        patchReactFetch();
    });
})();
