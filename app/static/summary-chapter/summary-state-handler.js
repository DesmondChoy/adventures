/**
 * Summary State Handler
 * 
 * This script handles retrieving the state ID from the URL and passing it to the React app.
 * It should be included in the summary page before the React app's JavaScript.
 */

// Function to extract query parameters from URL
function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    // If there are multiple values for the same parameter, get only the first one
    const values = urlParams.getAll(name);
    const value = values.length > 0 ? values[0] : null;
    
    console.log(`[DEBUG] getQueryParam('${name}') = '${value}'`);
    console.log(`[DEBUG] Full URL: ${window.location.href}`);
    console.log(`[DEBUG] Search params: ${window.location.search}`);
    
    if (values.length > 1) {
        console.log(`[DEBUG] Multiple values found for '${name}': ${values.join(', ')}`);
        console.log(`[DEBUG] Using first value: ${value}`);
    }
    
    return value;
}

// When the window loads, check for state_id in the URL
window.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOMContentLoaded event fired');
    
    // Get state_id from URL if present
    const stateId = getQueryParam('state_id');
    
    if (stateId) {
        console.log('[DEBUG] Found state_id in URL:', stateId);
        
        // Store the state ID in localStorage so the React app can access it
        localStorage.setItem('summary_state_id', stateId);
        console.log('[DEBUG] Stored state_id in localStorage:', localStorage.getItem('summary_state_id'));
        
        // Create a custom event that the React app can listen for
        const event = new CustomEvent('summaryStateIdAvailable', { detail: { stateId } });
        document.dispatchEvent(event);
        console.log('[DEBUG] Dispatched summaryStateIdAvailable event');
    } else {
        console.log('[DEBUG] No state_id found in URL');
    }
    
    // Add event listener for React app's fetch requests
    document.addEventListener('fetchSummaryData', function(e) {
        console.log('[DEBUG] fetchSummaryData event received');
        
        // Ensure we're using a clean state ID (no duplicates)
        const cleanStateId = stateId ? stateId.split(',')[0].trim() : null;
        
        const apiUrl = cleanStateId 
            ? `/adventure/api/adventure-summary?state_id=${cleanStateId}`
            : '/adventure/api/adventure-summary';
            
        console.log('[DEBUG] API URL:', apiUrl);
            
        // Store the API URL for the React app to use
        localStorage.setItem('summary_api_url', apiUrl);
        console.log('[DEBUG] Stored API URL in localStorage:', localStorage.getItem('summary_api_url'));
        
        // Dispatch event with the API URL
        const urlEvent = new CustomEvent('summaryApiUrlAvailable', { 
            detail: { apiUrl } 
        });
        document.dispatchEvent(urlEvent);
        console.log('[DEBUG] Dispatched summaryApiUrlAvailable event');
    });
});
