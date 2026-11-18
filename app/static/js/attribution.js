/**
 * First-touch marketing attribution.
 *
 * Reads utm_* parameters and the external referrer host from the first page a
 * visitor lands on and keeps them in localStorage, so the adventure page can
 * attach them to the adventure it creates. A visit that carries UTM tags
 * replaces an earlier visit that only had a referrer; otherwise the first
 * touch wins.
 */
(function () {
    const STORAGE_KEY = 'learning_odyssey_attribution';
    const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'];
    const MAX_LENGTH = 200;

    function clean(value) {
        return typeof value === 'string' ? value.trim().slice(0, MAX_LENGTH) : '';
    }

    function readStored() {
        try {
            const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
            return parsed && typeof parsed === 'object' ? parsed : null;
        } catch (e) {
            return null;
        }
    }

    function hasUtm(attribution) {
        return !!attribution && UTM_KEYS.some((key) => attribution[key]);
    }

    function externalReferrerHost() {
        try {
            if (!document.referrer) return '';
            const host = new URL(document.referrer).hostname;
            return host && host !== window.location.hostname ? clean(host) : '';
        } catch (e) {
            return '';
        }
    }

    function capture() {
        const params = new URLSearchParams(window.location.search);
        const current = {};
        UTM_KEYS.forEach((key) => {
            const value = clean(params.get(key));
            if (value) current[key] = value;
        });
        const referrer = externalReferrerHost();
        if (referrer) current.referrer = referrer;
        if (Object.keys(current).length === 0) return;

        const stored = readStored();
        if (stored && (hasUtm(stored) || !hasUtm(current))) return;

        current.landing_path = clean(window.location.pathname);
        current.captured_at = new Date().toISOString();
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
        } catch (e) {
            // Storage can be unavailable (private mode); attribution is optional.
        }
    }

    capture();

    // Query-string fragment for the story WebSocket URL ('' when nothing stored).
    window.getAttributionQuery = function () {
        const stored = readStored();
        if (!stored) return '';
        return [...UTM_KEYS, 'referrer']
            .filter((key) => typeof stored[key] === 'string' && stored[key])
            .map((key) => `&${key}=${encodeURIComponent(stored[key])}`)
            .join('');
    };
})();
