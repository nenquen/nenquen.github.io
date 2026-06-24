(function () {
    var bday = new Date(2007, 6, 31);
    var today = new Date();
    var now = Date.now();

    // --- Age ---
    var age = today.getFullYear() - bday.getFullYear();
    var m = today.getMonth() - bday.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < bday.getDate())) age--;
    var ageEl = document.getElementById('age');
    if (ageEl) ageEl.textContent = age;

    // --- Birthday check ---
    var isBirthday = today.getMonth() === 6 && today.getDate() === 31;
    if (!isBirthday) return;

    document.documentElement.classList.add('birthday');

    // --- Confetti with canvas-confetti library ---
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.4/dist/confetti.browser.min.js';
    s.onload = function () {
        var positions = [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9];
        positions.forEach(function (x, i) {
            setTimeout(function () {
                confetti({
                    particleCount: 30,
                    angle: 90,
                    spread: 35,
                    startVelocity: 55 + Math.random() * 25,
                    ticks: 400,
                    origin: { x: x, y: -0.1 },
                    colors: ['#FF6B6B','#FFD700','#6BCEFF','#6BFF96','#FF8C42','#C084FC','#FF69B4'],
                });
            }, i * 100);
        });
        setTimeout(function () {
            positions.forEach(function (x, i) {
                setTimeout(function () {
                    confetti({
                        particleCount: 25,
                        angle: 90,
                        spread: 25,
                        startVelocity: 50 + Math.random() * 20,
                        ticks: 400,
                        origin: { x: x + 0.05, y: -0.15 },
                        colors: ['#FF6B6B','#FFD700','#6BCEFF','#6BFF96','#FF8C42','#C084FC','#FF69B4'],
                    });
                }, i * 80);
            });
        }, 800);
    };
    document.head.appendChild(s);
})();
