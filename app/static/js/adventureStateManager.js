/**
 * Adventure State Manager
 * Handles localStorage operations for adventure state persistence
 */

export class AdventureStateManager {
    constructor() {
        this.STORAGE_KEY = 'adventure_state';
        this.CLIENT_UUID_KEY = 'learning_odyssey_user_uuid';
        this.ensureClientUuid();
    }

    saveState(state) {
        // Ensure client_uuid is stored in state metadata
        if (!state.metadata) {
            state.metadata = {};
        }
        state.metadata.client_uuid = this.getClientUuid();
        
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
    }

    loadState() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        return saved ? JSON.parse(saved) : null;
    }

    clearState() {
        localStorage.removeItem(this.STORAGE_KEY);
        localStorage.removeItem(this.CLIENT_UUID_KEY);
        this.ensureClientUuid();
    }
    
    ensureClientUuid() {
        // Generate a UUID if one doesn't exist
        if (!localStorage.getItem(this.CLIENT_UUID_KEY)) {
            const cryptoApi = globalThis.crypto;
            if (!cryptoApi) {
                throw new Error('Secure UUID generation is unavailable in this browser.');
            }

            const uuid = typeof cryptoApi.randomUUID === 'function'
                ? cryptoApi.randomUUID()
                : this.generateFallbackUuid(cryptoApi);
                
            localStorage.setItem(this.CLIENT_UUID_KEY, uuid);
        }
    }
    
    getClientUuid() {
        return localStorage.getItem(this.CLIENT_UUID_KEY);
    }
    
    // Fallback UUID generator for older browsers
    generateFallbackUuid(cryptoApi = globalThis.crypto) {
        if (typeof cryptoApi?.getRandomValues !== 'function') {
            throw new Error('Secure UUID generation is unavailable in this browser.');
        }

        const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
        bytes[6] = (bytes[6] & 0x0f) | 0x40;
        bytes[8] = (bytes[8] & 0x3f) | 0x80;

        const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0'));
        return [
            hex.slice(0, 4).join(''),
            hex.slice(4, 6).join(''),
            hex.slice(6, 8).join(''),
            hex.slice(8, 10).join(''),
            hex.slice(10, 16).join('')
        ].join('-');
    }
}
