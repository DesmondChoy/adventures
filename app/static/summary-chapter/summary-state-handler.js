/**
 * Summary State Handler
 *
 * This script handles retrieving the state ID from the URL and passing it to the React app.
 * It MUST be included in the summary page before the React app's JavaScript.
 *
 * CRITICAL: The fetch patching runs IMMEDIATELY (not on DOMContentLoaded) so that
 * window.fetch is already patched before the React module bundle makes its first API call.
 */

// Function to extract query parameters from URL
function getQueryParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    const values = urlParams.getAll(name);
    return values.length > 0 ? values[0].trim() : null;
}

// =============================================================================
// IMMEDIATE FETCH PATCH — runs before React module loads
// =============================================================================
(function() {
    // Read state_id from URL immediately
    let stateId = getQueryParam('state_id');
    if (stateId && stateId.includes(',')) {
        stateId = stateId.split(',')[0].trim();
    }

    // Fall back to localStorage if URL doesn't have it
    if (!stateId) {
        stateId = localStorage.getItem('summary_state_id');
    }

    if (!stateId) {
        console.log('[SummaryStateHandler] No state_id found, skipping fetch patch');
        return;
    }

    // Store in localStorage for consistency
    localStorage.setItem('summary_state_id', stateId);

    // Read auth token stored by main app before navigation
    const accessToken = localStorage.getItem('summary_access_token');

    console.log('[SummaryStateHandler] Patching fetch BEFORE React loads. state_id:', stateId, 'hasToken:', !!accessToken);

    const originalFetch = window.fetch;

    window.fetch = function(url, options) {
        // Only intercept adventure-summary API calls
        if (url && typeof url === 'string' && url.includes('/adventure/api/adventure-summary')) {
            const urlObj = new URL(url, window.location.origin);
            const urlParams = new URLSearchParams(urlObj.search);

            // Replace any existing state_id with our clean one
            urlParams.delete('state_id');
            urlParams.append('state_id', stateId);
            urlObj.search = urlParams.toString();
            const newUrl = urlObj.toString();

            console.log('[SummaryStateHandler] Intercepted fetch:', url, '->', newUrl);

            // Inject Authorization header if token is available
            if (accessToken) {
                options = options || {};
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', 'Bearer ' + accessToken);
                } else {
                    options.headers['Authorization'] = 'Bearer ' + accessToken;
                }
            }

            return originalFetch(newUrl, options);
        }

        return originalFetch(url, options);
    };

    console.log('[SummaryStateHandler] Fetch patched successfully');
})();

// =============================================================================
// DOMContentLoaded — dispatch events for any listeners
// =============================================================================
window.addEventListener('DOMContentLoaded', function() {
    const stateId = getQueryParam('state_id');

    if (stateId) {
        localStorage.setItem('summary_state_id', stateId);

        const event = new CustomEvent('summaryStateIdAvailable', { detail: { stateId } });
        document.dispatchEvent(event);
    }

    document.addEventListener('fetchSummaryData', function() {
        const cleanStateId = stateId ? stateId.split(',')[0].trim() : null;
        const apiUrl = cleanStateId
            ? '/adventure/api/adventure-summary?state_id=' + cleanStateId
            : '/adventure/api/adventure-summary';

        localStorage.setItem('summary_api_url', apiUrl);

        const urlEvent = new CustomEvent('summaryApiUrlAvailable', { detail: { apiUrl } });
        document.dispatchEvent(urlEvent);
    });
});
