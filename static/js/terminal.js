/*
 * RALPH_MODE - Terminal JavaScript
 * Handles terminal effects and interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Cursor blink effect is handled by CSS
    // Additional effects can be added here

    // Add random "glitch" characters to the screen
    const glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
    const glitchInterval = setInterval(() => {
        if (Math.random() > 0.95) { // 5% chance
            createGlitch();
        }
    }, 5000);

    function createGlitch() {
        const glitch = document.createElement('div');
        glitch.className = 'glitch';
        glitch.style.cssText = `
            position: fixed;
            top: ${Math.random() * 100}%;
            left: ${Math.random() * 100}%;
            color: #00ff00;
            font-family: monospace;
            font-size: 12px;
            pointer-events: none;
            z-index: 9999;
            opacity: 0.3;
        `;
        glitch.textContent = glitchChars[Math.floor(Math.random() * glitchChars.length)];
        document.body.appendChild(glitch);

        setTimeout(() => {
            glitch.remove();
        }, 100);
    }

    // Keyboard sound effect (optional - requires audio files)
    // document.addEventListener('keydown', () => {
    //     playTypingSound();
    // });

    // Boot sequence effect on page load
    runBootSequence();
});

function runBootSequence() {
    const bootMessages = [
        '> BIOS Version 1.0.0',
        '> Memory Test: 640K OK',
        '> Initializing Ralph_Mode...',
        '> Loading neural networks...',
        '> Connecting to recipe database...',
        '> System ready.'
    ];

    // Create boot overlay
    const bootOverlay = document.createElement('div');
    bootOverlay.id = 'boot-overlay';
    bootOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: #000;
        color: #00ff00;
        font-family: monospace;
        padding: 2rem;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    `;

    let messageIndex = 0;

    function showNextMessage() {
        if (messageIndex < bootMessages.length) {
            const line = document.createElement('div');
            line.textContent = bootMessages[messageIndex];
            line.style.cssText = `
                margin: 0.5rem 0;
                opacity: 0;
                animation: fadeIn 0.5s forwards;
            `;
            bootOverlay.appendChild(line);
            messageIndex++;
            setTimeout(showNextMessage, 200);
        } else {
            setTimeout(() => {
                bootOverlay.style.transition = 'opacity 1s';
                bootOverlay.style.opacity = '0';
                setTimeout(() => bootOverlay.remove(), 1000);
            }, 500);
        }
    }

    document.body.appendChild(bootOverlay);
    setTimeout(showNextMessage, 500);
}
