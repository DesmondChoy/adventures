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
        // Note: We don't clear the client UUID as it's used for persistence
    }
    
    ensureClientUuid() {
        // Generate a UUID if one doesn't exist
        if (!localStorage.getItem(this.CLIENT_UUID_KEY)) {
            // Use crypto.randomUUID() if available (modern browsers)
            const uuid = crypto.randomUUID ? 
                crypto.randomUUID() : 
                this.generateFallbackUuid();
                
            localStorage.setItem(this.CLIENT_UUID_KEY, uuid);
            console.log('Generated new client UUID for persistence');
        }
    }
    
    getClientUuid() {
        return localStorage.getItem(this.CLIENT_UUID_KEY);
    }
    
    // Fallback UUID generator for older browsers
    generateFallbackUuid() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
}
