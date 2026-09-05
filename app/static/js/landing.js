// These previews are local to the landing page. Adventure selections still
// belong to the existing authenticated/guest selection flow.
document.querySelectorAll('[data-preview-group]').forEach((group) => {
    const buttons = group.querySelectorAll('[data-preview-target]');
    const panels = group.querySelectorAll('[data-preview-panel]');

    buttons.forEach((button) => {
        button.addEventListener('click', () => {
            buttons.forEach((candidate) => {
                candidate.setAttribute('aria-pressed', String(candidate === button));
            });
            panels.forEach((panel) => {
                panel.hidden = panel.id !== button.dataset.previewTarget;
            });
        });
    });
});

// Native anchor navigation keeps history and keyboard focus useful. Move focus
// to the entry controls when an invitation brings someone back to the hero.
document.querySelectorAll('a[href="#begin"]').forEach((link) => {
    link.addEventListener('click', (event) => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        // Wait until the browser has followed the fragment; its default focus
        // handling would otherwise undo our focus change.
        requestAnimationFrame(() => {
            document.getElementById('continue-guest')?.focus({ preventScroll: true });
        });
    });
});

const topicTicker = document.querySelector('[data-topic-ticker]');
if (topicTicker) {
    const topics = [...topicTicker.querySelectorAll('li')].map((item) => item.textContent.trim());
    const layers = topicTicker.querySelectorAll('.topic-name');
    const control = topicTicker.querySelector('.topic-rotation-control');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let topicIndex = 0;
    let layerIndex = 0;
    let paused = false;
    let timer = null;

    function nextTopic() {
        topicIndex = (topicIndex + 1) % topics.length;
        const nextLayer = 1 - layerIndex;
        layers[nextLayer].textContent = topics[topicIndex];
        layers[layerIndex].classList.remove('is-current');
        layers[nextLayer].classList.add('is-current');
        layerIndex = nextLayer;
    }

    function updateRotation() {
        window.clearInterval(timer);
        timer = null;
        // With reduced motion, the same control advances topics on demand.
        control.textContent = reducedMotion.matches ? 'Next' : paused ? 'Play' : 'Pause';
        control.setAttribute('aria-label', reducedMotion.matches ? 'Next topic' : paused ? 'Resume topic rotation' : 'Pause topic rotation');
        if (!paused && !reducedMotion.matches && !document.hidden) {
            timer = window.setInterval(nextTopic, 4000);
        }
    }

    if (topics.length > 1) {
        control.hidden = false;
        control.addEventListener('click', () => {
            if (reducedMotion.matches) {
                nextTopic();
            } else {
                paused = !paused;
                updateRotation();
            }
        });
        reducedMotion.addEventListener('change', updateRotation);
        document.addEventListener('visibilitychange', updateRotation);
        updateRotation();
    }
}
