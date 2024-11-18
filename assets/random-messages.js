document.addEventListener("DOMContentLoaded", () => {
    const messages = [
        "Welcome! What's up :p",
        "Check out our discord server!",
        "Oreo was here :3",
        "giggity giggity giggity giggity!",
        "The source code of the site is available on my github!"
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
            updateElement.textContent = currentMessage.substring(0, charIndex);
        } else {
            charIndex++;
            updateElement.textContent = currentMessage.substring(0, charIndex);
        }

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
