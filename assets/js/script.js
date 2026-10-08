const DISCORD_INVITE = 'qTjFD8zhyz';
const WINDOW_IDS = ['mainWindow', 'aboutWindow', 'discordWindow', 'warningWindow'];
const ROUTE_TO_WINDOW = { '': 'mainWindow', about: 'aboutWindow', discord: 'discordWindow' };
const DISCORD_CACHE_MS = 60_000;
const DISCORD_TIMEOUT_MS = 8000;

let discordCache = null;
let discordCachedAt = 0;
let discordRequest = null;
let pendingUrl = null;
let previousWindow = null;
let lastFocused = null;
let restoreFocusAfterClose = false;

/* ---------- sound (lazy, but warmed up on first user gesture) ---------- */

const sounds = {};

function loadSound(key, src, volume) {
    const audio = new Audio();
    audio.preload = 'auto';
    audio.volume = volume;
    audio.src = src;
    sounds[key] = audio;
}

function playSound(key) {
    const audio = sounds[key];
    if (!audio) return;
    try {
        const clone = audio.cloneNode();
        clone.volume = audio.volume;
        const result = clone.play();
        if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch {}
}

function warmSounds() {
    try {
        if (!sounds.click) loadSound('click', 'assets/sounds/click.wav', 0.3);
        if (!sounds.warning) loadSound('warning', 'assets/sounds/warning.wav', 0.5);
    } catch {}
}

/* ---------- window switching ---------- */

function isWarningOpen() {
    const el = document.getElementById('warningWindow');
    return !!el && !el.classList.contains('hidden');
}

function routeFromHash() {
    const hash = window.location.hash;
    if (hash === '#about') return 'about';
    if (hash === '#discord') return 'discord';
    return '';
}

function currentRoute() {
    if (!document.getElementById('aboutWindow').classList.contains('hidden')) return 'about';
    if (!document.getElementById('discordWindow').classList.contains('hidden')) return 'discord';
    return '';
}

function showWindow(id) {
    for (const windowId of WINDOW_IDS) {
        document.getElementById(windowId).classList.add('hidden');
    }
    document.getElementById(id).classList.remove('hidden');
    if (id !== 'warningWindow') {
        document.getElementById('overlay').classList.add('hidden');
    }
}

function showRoute(route) {
    const id = ROUTE_TO_WINDOW[route] || 'mainWindow';
    showWindow(id);
    if (id === 'discordWindow') loadDiscordServerInfo();
}

/* ---------- discord server info ---------- */

function applyDiscordServerInfo(data) {
    document.getElementById('discordServerName').textContent = data.guild.name;

    if (data.guild.icon) {
        document.getElementById('discordServerIcon').src =
            `https://cdn.discordapp.com/icons/${data.guild.id}/${data.guild.icon}.png`;
    }

    document.getElementById('discordMemberCount').textContent =
        data.approximate_member_count != null ? `${data.approximate_member_count} Members` : 'Unknown members';
    document.getElementById('discordOnlineCount').textContent =
        data.approximate_presence_count != null ? `${data.approximate_presence_count} Online` : 'Unknown online';
    document.getElementById('discordBoostCount').textContent =
        data.guild.premium_subscription_count != null ? `${data.guild.premium_subscription_count} Boosts` : '0 Boosts';
}

function setDiscordError() {
    document.getElementById('discordServerName').textContent = "Nenquen's Community";
    document.getElementById('discordMemberCount').textContent = 'Loading failed';
    document.getElementById('discordOnlineCount').textContent = 'Loading failed';
    document.getElementById('discordBoostCount').textContent = 'Loading failed';
}

async function fetchDiscordInvite() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), DISCORD_TIMEOUT_MS);
    try {
        const response = await fetch(
            `https://discord.com/api/v10/invites/${DISCORD_INVITE}?with_counts=true`,
            { signal: controller.signal }
        );
        if (!response.ok) throw new Error(`Discord API: ${response.status}`);
        const data = await response.json();
        if (!data.guild) throw new Error('No guild in invite response');
        return data;
    } finally {
        clearTimeout(timer);
    }
}

async function loadDiscordServerInfo() {
    if (discordCache && Date.now() - discordCachedAt < DISCORD_CACHE_MS) {
        applyDiscordServerInfo(discordCache);
        return;
    }
    if (discordRequest) return; // already in flight

    discordRequest = fetchDiscordInvite()
        .then((data) => {
            discordCache = data;
            discordCachedAt = Date.now();
            applyDiscordServerInfo(data);
        })
        .catch((error) => {
            console.error('Failed to load Discord server info:', error);
            setDiscordError();
        })
        .finally(() => {
            discordRequest = null;
        });
}

/* ---------- SmartScreen-style warning dialog ---------- */

function fileNameFromUrl(url) {
    try {
        const parsed = new URL(url);
        const segment = parsed.pathname.split('/').filter(Boolean).pop();
        if (segment) return decodeURIComponent(segment);
        return parsed.hostname;
    } catch {
        return url;
    }
}

function setDetailsOpen(open) {
    const details = document.getElementById('warningDetails');
    details.open = open;
    document.getElementById('warningDetailsPanel').hidden = !open;
    details.querySelector('summary').textContent =
        open ? 'Hide details' : 'Show details';
}

function showWarningWindow(url) {
    if (!url) return;
    pendingUrl = url;
    previousWindow = ROUTE_TO_WINDOW[currentRoute()] || 'mainWindow';

    // Only take the focus back if the user arrived here by keyboard.
    // Restoring it after a mouse click leaves the trigger looking
    // permanently lit.
    const trigger = document.activeElement;
    restoreFocusAfterClose =
        !!trigger && trigger !== document.body && trigger.matches(':focus-visible');
    lastFocused = restoreFocusAfterClose ? trigger : null;

    document.getElementById('warningFileName').textContent = fileNameFromUrl(url);
    document.getElementById('warningFullPath').textContent = url;
    setDetailsOpen(false);

    showWindow('warningWindow');
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('cancelWarningButton').focus();
    playSound('warning');
}

function closeWarning() {
    const restoreFocus = lastFocused;
    pendingUrl = null;
    lastFocused = null;
    restoreFocusAfterClose = false;

    showWindow(previousWindow || 'mainWindow');
    previousWindow = null;

    if (restoreFocus && document.contains(restoreFocus)) {
        restoreFocus.focus();
    } else if (document.activeElement && document.activeElement !== document.body) {
        // Mouse flow: the hidden trigger must not keep focus, otherwise
        // it renders as if it were still hovered/active.
        document.activeElement.blur();
    }
}

function openPendingUrl() {
    const url = pendingUrl;
    const backTo = previousWindow || 'mainWindow';
    closeWarning();
    if (url) window.open(url, '_blank', 'noopener');
    showWindow(backTo);
}

/* ---------- routing ---------- */

function handleRoute() {
    const route = routeFromHash();

    // Dialog stays open across hash changes (browser Back/Forward),
    // but we remember where the user wanted to go.
    if (isWarningOpen()) {
        previousWindow = ROUTE_TO_WINDOW[route] || 'mainWindow';
        return;
    }

    showRoute(route);
}

function setHash(route) {
    const target = route ? `#${route}` : '';
    if (window.location.hash === target) return false;

    if (route) {
        window.location.hash = target;
        return true;
    }

    // Clearing the hash with `location.hash = ''` throws an
    // "Unsafe attempt" error on file://, so use history instead.
    const clean = window.location.pathname + window.location.search;
    try {
        history.pushState(null, '', clean);
    } catch {
        try {
            history.replaceState(null, '', clean);
        } catch {}
    }
    return true;
}

function go(route) {
    playSound('click');
    setHash(route);
    // Show right away: hashchange can be blocked on file://.
    showRoute(route);
}

function setRandomWelcomeMessage() {
    const messages = [
        "Welcome! What's up :p",
        'Check out our discord server!',
        'Nenquen was here :3',
        'Giggity giggity giggity giggity!',
        'The source code of the site is available on my github!'
    ];
    document.getElementById('welcome-message').textContent =
        messages[Math.floor(Math.random() * messages.length)];
}

window.addEventListener('hashchange', handleRoute);

document.addEventListener('DOMContentLoaded', () => {
    handleRoute();
    setRandomWelcomeMessage();
    warmSounds();

    // Browsers only allow audio after a user gesture.
    document.addEventListener('pointerdown', warmSounds, { once: true });
    document.addEventListener('keydown', warmSounds, { once: true });

    // Title-bar buttons are decorative: swallow any activation attempt.
    document.querySelectorAll('.title-bar-controls .title-btn-dead').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, true);
    });

    const on = (id, handler) => {
        document.getElementById(id).addEventListener('click', handler);
    };

    on('aboutButton', () => go('about'));
    on('discordButton', () => go('discord'));
    on('backButton', () => go(''));
    on('backDiscordButton', () => go(''));

    document.querySelectorAll('.external-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            playSound('click');
            showWarningWindow(link.href);
        });
    });

    on('githubButton', () => {
        playSound('click');
        showWarningWindow('https://github.com/nenquen');
    });
    on('joinDiscordButton', () => {
        playSound('click');
        showWarningWindow(`https://discord.gg/${DISCORD_INVITE}`);
    });

    // Native <details> drives the toggle; we mirror it onto the panel and
    // keep the label in sync.
    const details = document.getElementById('warningDetails');
    details.querySelector('summary').addEventListener('click', () => playSound('click'));
    details.addEventListener('toggle', () => setDetailsOpen(details.open));

    on('cancelWarningButton', () => {
        playSound('click');
        closeWarning();
    });
    on('confirmWarningButton', () => {
        playSound('click');
        openPendingUrl();
    });

    on('overlay', () => {
        if (isWarningOpen()) closeWarning();
    });

    document.addEventListener('keydown', (e) => {
        if (!isWarningOpen()) return;
        // SmartScreen behaviour: Escape / Enter cancel, Enter also works
        // when focus is not already on a button.
        if (e.key === 'Escape') {
            closeWarning();
        } else if (e.key === 'Enter' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A') {
            e.preventDefault();
            closeWarning();
        }
    });
});