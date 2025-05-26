/**
 * WebSocket Manager
 * Handles WebSocket connections, reconnection logic, and message handling
 */

import { AdventureStateManager } from './adventureStateManager.js';

export class WebSocketManager {
    constructor(authManager) {
        this.authManager = authManager;
        this.stateManager = new AdventureStateManager();
        this.connection = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.baseDelay = 1000; // 1 second
        this.maxDelay = 30000; // 30 seconds
        this.adventureId = null; // Store adventure_id for persistence
        this.adventureIdToResume = null; // For resuming specific adventure from modal
    }

    getWebSocketUrl() {
        console.log('[FrontendWS Log 1.2] getWebSocketUrl called.');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        let storyCategory = 'unknown';
        let lessonTopic = 'unknown';

        if (this.adventureIdToResume) {
            storyCategory = sessionStorage.getItem('resume_story_category') || 'unknown';
            lessonTopic = sessionStorage.getItem('resume_lesson_topic') || 'unknown';
            console.log(`[FrontendWS Log 1.3] Resuming: Story Category from sessionStorage: ${storyCategory}, Lesson Topic from sessionStorage: ${lessonTopic}`);
            // Optionally clear them if they are single-use, or keep for reconnects
            // sessionStorage.removeItem('resume_story_category');
            // sessionStorage.removeItem('resume_lesson_topic');
        } else {
            const storyCategoryEl = document.getElementById('storyCategory');
            const lessonTopicEl = document.getElementById('lessonTopic');
            storyCategory = storyCategoryEl ? storyCategoryEl.value : 'unknown';
            lessonTopic = lessonTopicEl ? lessonTopicEl.value : 'unknown';
            console.log(`[FrontendWS Log 1.4] New adventure: Story Category from input: ${storyCategory}, Lesson Topic from input: ${lessonTopic}`);
        }
        
        const clientUuid = this.stateManager.getClientUuid(); 
        
        const encodedStoryCategory = encodeURIComponent(storyCategory);
        const encodedLessonTopic = encodeURIComponent(lessonTopic);
        const encodedClientUuid = encodeURIComponent(clientUuid);

        let url = `${protocol}//${window.location.host}/ws/story/${encodedStoryCategory}/${encodedLessonTopic}?client_uuid=${encodedClientUuid}`;
        
        if (this.authManager.accessToken) {
            console.log('[FrontendWS Log 4] Token will be appended to URL.');
            url += `&token=${encodeURIComponent(this.authManager.accessToken)}`;
        } else {
            console.warn('[FrontendWS Log 5] No token found, proceeding without token for WebSocket.');
        }

        if (this.adventureIdToResume) {
            url += `&resume_adventure_id=${encodeURIComponent(this.adventureIdToResume)}`;
            console.log(`[FrontendWS Log 5.1] Appending resume_adventure_id: ${this.adventureIdToResume}`);
        }

        console.log('[FrontendWS Log 6] Final WebSocket URL:', url);
        return url;
    }
    
    setAdventureId(id) {
        this.adventureId = id;
        console.log(`Set adventure_id: ${id} for persistence`);
    }
    
    getAdventureId() {
        return this.adventureId;
    }

    async handleDisconnect() {
        if (this.connection?.readyState === WebSocket.CLOSED) {
            await this.reconnect();
        }
    }

    calculateBackoff() {
        return Math.min(
            this.baseDelay * Math.pow(2, this.reconnectAttempts),
            this.maxDelay
        );
    }

    async reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            const { appendStoryText } = await import('./uiManager.js');
            appendStoryText('\n\nUnable to reconnect after multiple attempts. Please refresh the page.');
            return;
        }

        const savedState = this.stateManager.loadState();
        if (!savedState && !this.adventureIdToResume) { // Also check adventureIdToResume
            const { appendStoryText } = await import('./uiManager.js');
            appendStoryText('\n\nUnable to recover story state. Please refresh the page.');
            return;
        }

        const delay = this.calculateBackoff();
        await new Promise(resolve => setTimeout(resolve, delay));

        const websocketUrl = this.getWebSocketUrl(); // This will now use sessionStorage if resuming
        console.log("[WebSocketManager.reconnect] Attempting to connect to WebSocket URL:", websocketUrl); 
        try {
            this.connection = new WebSocket(websocketUrl);
            console.log("[WebSocketManager.reconnect] WebSocket object created:", this.connection); 
            this.setupConnectionHandlers();
            this.reconnectAttempts++;
        } catch (e) {
            console.error("[WebSocketManager.reconnect] Error creating WebSocket:", e); 
            const { hideLoader } = await import('./uiManager.js');
            hideLoader();
        }
    }

    async setupConnectionHandlers() {
        const savedState = this.stateManager.loadState();
        const { hideLoader, updateProgress, handleMessage } = await import('./uiManager.js');
        const { manageState } = await import('./stateManager.js');

        this.connection.onopen = () => {
            console.log('[FrontendWS Log 9] WebSocket connection opened.');
            this.reconnectAttempts = 0;

            if (this.adventureIdToResume) {
                console.log(`[FrontendWS] Resuming specific adventure ID: ${this.adventureIdToResume}. Sending resume request.`);
                this.connection.send(JSON.stringify({
                    choice: 'resume_specific_adventure', 
                    adventure_id_to_resume: this.adventureIdToResume 
                }));
            } else if (savedState) {
                const currentChapter = savedState.chapters.length;
                updateProgress(currentChapter + 1, savedState.story_length);
                this.connection.send(JSON.stringify({
                    state: savedState,
                    choice: 'start'
                }));
            } else {
                const storyCategoryEl = document.getElementById('storyCategory');
                const lessonTopicEl = document.getElementById('lessonTopic');
                const initialState = manageState('initialize', {
                    storyCategory: storyCategoryEl ? storyCategoryEl.value : (sessionStorage.getItem('resume_story_category') || ''),
                    lessonTopic: lessonTopicEl ? lessonTopicEl.value : (sessionStorage.getItem('resume_lesson_topic') || '')
                });
                this.connection.send(JSON.stringify({
                    state: initialState,
                    choice: 'start'
                }));
            }
        };

        this.connection.onclose = (event) => {
            console.log(`[FrontendWS Log 11] WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`);
            hideLoader();
            if (!event.wasClean) {
                console.error('WebSocket connection died');
                this.handleDisconnect();
            }
        };

        this.connection.onerror = (error) => {
            console.error('[FrontendWS Log 10] WebSocket Error: ', error);
            hideLoader();
        };

        this.connection.onmessage = handleMessage;
    }

    sendMessage(message) {
        if (this.connection && this.connection.readyState === WebSocket.OPEN) {
            this.connection.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not open. Message not sent:', message);
        }
    }
}
