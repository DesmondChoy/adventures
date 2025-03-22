/**
 * React App Patch
 * 
 * This script patches the React app to use the state ID from the URL.
 * It should be included in the summary page after the React app's JavaScript.
 */

(function() {
    // Function to patch the React app's fetch function
    function patchReactFetch() {
        console.log('[DEBUG] Patching React app fetch function');
        
        // Get the state ID from localStorage (set by summary-state-handler.js)
        let stateId = localStorage.getItem('summary_state_id');
        console.log('[DEBUG] State ID from localStorage:', stateId);
        
        if (!stateId) {
            console.log('[DEBUG] No state ID found in localStorage, not patching fetch');
            return;
        }
        
        // Clean up the state ID in case it contains multiple values
        if (stateId.includes(',')) {
            console.log('[DEBUG] State ID contains multiple values:', stateId);
            stateId = stateId.split(',')[0].trim();
            console.log('[DEBUG] Using first value:', stateId);
            // Update localStorage with the clean value
            localStorage.setItem('summary_state_id', stateId);
        }
        
        console.log('[DEBUG] Found state ID in localStorage:', stateId);
        
        // Try to find the fetch function in the React app
        // This is a bit hacky, but it's the best we can do without modifying the React app directly
        const originalFetch = window.fetch;
        console.log('[DEBUG] Original fetch function:', originalFetch ? 'exists' : 'not found');
        
        // Override the fetch function
        window.fetch = function(url, options) {
            console.log('[DEBUG] Fetch called with URL:', url);
            
            // Check if this is a request to the adventure summary API
            if (url && typeof url === 'string' && url.includes('/adventure/api/adventure-summary')) {
                // Check if the URL already has a state_id parameter
                const urlObj = new URL(url, window.location.origin);
                const urlParams = new URLSearchParams(urlObj.search);
                
                // Remove any existing state_id parameters
                urlParams.delete('state_id');
                
                // Add our clean state_id
                urlParams.append('state_id', stateId);
                
                // Construct the new URL
                urlObj.search = urlParams.toString();
                const newUrl = urlObj.toString();
                console.log('[DEBUG] Patching fetch URL:', url, '->', newUrl);
                
                // Log the options
                console.log('[DEBUG] Fetch options:', options ? JSON.stringify(options) : 'none');
                
                return originalFetch(newUrl, options);
            }
            
            // Otherwise, use the original fetch function
            console.log('[DEBUG] Not patching URL:', url);
            return originalFetch(url, options);
        };
        
        console.log('[DEBUG] Fetch function patched successfully');
        
        // Test the patched fetch function
        console.log('[DEBUG] Testing patched fetch function with a dummy URL');
        fetch('/adventure/api/adventure-summary');
    }
    
    // Wait for the React app to load
    window.addEventListener('load', function() {
        console.log('[DEBUG] Window load event fired');
        // Give the React app a moment to initialize
        console.log('[DEBUG] Setting timeout for 500ms to patch fetch');
        setTimeout(patchReactFetch, 500);
    });
    
    // Also listen for the custom event from summary-state-handler.js
    document.addEventListener('summaryStateIdAvailable', function(e) {
        console.log('[DEBUG] summaryStateIdAvailable event received with state ID:', e.detail.stateId);
        // Patch the fetch function when the state ID is available
        patchReactFetch();
    });
    
    // Log that the patch script has loaded
    console.log('[DEBUG] React app patch script loaded');
})();
