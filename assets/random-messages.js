document.addEventListener("DOMContentLoaded", () => {
    const messages = [
        "welcome! What's up :p",
        "check out our discord server!",
        "nenquen was here :3",
        "giggity giggity giggity giggity!",
        "the source code of the site is available on my github!"
    ];

    const updateElement = document.getElementById("updates");
    let currentIndex = 0;
    let isDeleting = false;
    let charIndex = 0;
    const typingSpeed = 20;
    const deletingSpeed = 20;
    const pauseTime = 2000;
    const deletePauseTime = 1000;

    function updateMessage() {
        const currentMessage = messages[currentIndex];

        if (isDeleting) {
            charIndex--;
        } else {
            charIndex++;
        }

        let displayText = currentMessage.substring(0, charIndex);
        const prompt = `<span style="color: #3465A4;">~</span> <span style="color: #4E9A06;">$</span> `;

        // Render current state
        updateElement.innerHTML = `${prompt}${displayText}`;

        // Handle overflow with | indicator
        if (updateElement.scrollWidth > updateElement.clientWidth) {
            let slicedText = displayText;
            while (updateElement.scrollWidth > updateElement.clientWidth && slicedText.length > 0) {
                slicedText = slicedText.substring(1);
                updateElement.innerHTML = `${prompt}<span style="color: #bbb;">| </span>${slicedText}`;
            }
        }

        // Logic for pausing/switching
        if (!isDeleting && charIndex === currentMessage.length) {
            isDeleting = true;
            setTimeout(updateMessage, pauseTime);
            return;
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            currentIndex = (currentIndex + 1) % messages.length;
            setTimeout(updateMessage, deletePauseTime);
            return;
        }

        const speed = isDeleting ? deletingSpeed : typingSpeed;
        setTimeout(updateMessage, speed);
    }

    updateMessage();
});
