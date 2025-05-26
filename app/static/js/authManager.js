/**
 * Authentication Manager
 * Handles Supabase authentication, session management, and user status UI updates
 */

export const authManager = {
    session: null,
    accessToken: null,
    user: null,

    async initialize() {
        if (!window.supabase) {
            console.error("Supabase client (window.supabase) not available. Auth cannot be initialized.");
            const { showError, hideLoader } = await import('./uiManager.js');
            showError("Authentication service is unavailable. Please try again later.");
            const storyCategoryScreen = document.getElementById('storyCategoryScreen');
            if (storyCategoryScreen) {
                 storyCategoryScreen.innerHTML = '<p class="text-red-500 text-center p-8 text-lg">Critical Error: Authentication service did not load. Please refresh or contact support.</p>';
            }
            const lessonTopicScreen = document.getElementById('lessonTopicScreen');
            if (lessonTopicScreen) lessonTopicScreen.classList.add('hidden');
            const storyContainer = document.getElementById('storyContainer');
            if (storyContainer) storyContainer.classList.add('hidden');
            hideLoader();
            return false; 
        }

        try {
            const { data, error } = await window.supabase.auth.getSession();
            if (error) {
                console.error("Error getting session:", error.message);
                window.location.href = '/'; 
                return false;
            }
            if (!data.session) {
                window.location.href = '/'; 
                return false;
            }
            
            this.session = data.session;
            this.accessToken = data.session.access_token;
            this.user = data.session.user;
            this.updateUserStatusUI();

            window.supabase.auth.onAuthStateChange((event, session) => {
                if (event === 'SIGNED_OUT') {
                    this.clearSessionAndRedirect();
                } else if (event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED') {
                    this.session = session;
                    this.accessToken = session ? session.access_token : null;
                    this.user = session ? session.user : null;
                    this.updateUserStatusUI();
                }
            });
            return true; 
        } catch (e) {
            console.error("Exception during auth initialization:", e);
            const { showError } = await import('./uiManager.js');
            showError("An error occurred during authentication setup.");
            window.location.href = '/'; 
            return false;
        }
    },

    updateUserStatusUI() {
        const userStatusEl = document.getElementById('user-status');
        const logoutButton = document.getElementById('logout-button');
        if (userStatusEl && logoutButton) {
            if (this.user) {
                let displayName = "Guest";
                if (this.user.is_anonymous === false && this.user.email) {
                    displayName = this.user.email;
                } else if (this.user.is_anonymous === true && this.user.id) {
                    displayName = `Guest (${this.user.id.substring(0,8)}...)`;
                }
                userStatusEl.textContent = `Logged in as: ${displayName}`;
                logoutButton.classList.remove('hidden');
            } else {
                userStatusEl.textContent = 'Not logged in.';
                logoutButton.classList.add('hidden');
            }
        }
    },

    async handleLogout() {
        if (!window.supabase) {
            console.error("Supabase client not available for logout.");
            return;
        }
        const { showLoader, hideLoader } = await import('./uiManager.js');
        showLoader();
        const { error } = await window.supabase.auth.signOut();
        if (error) {
            console.error('Error logging out:', error);
            alert('Error logging out: ' + error.message);
            hideLoader();
        }
        // onAuthStateChange (event === 'SIGNED_OUT') handles redirect.
    },
    
    clearSessionAndRedirect() {
        this.session = null;
        this.accessToken = null;
        this.user = null;
        window.location.href = '/';
    }
};
