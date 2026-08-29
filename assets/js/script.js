const DISCORD_INVITE = 'qTjFD8zhyz';
let discordCache = null;

function showMainWindow() {
    hideAllWindows();
    document.getElementById('mainWindow').classList.remove('hidden');
}

function toggleAbout() {
    hideAllWindows();
    document.getElementById('aboutWindow').classList.remove('hidden');
}

function toggleDiscord() {
    hideAllWindows();
    document.getElementById('discordWindow').classList.remove('hidden');
    loadDiscordServerInfo();
}

function toggleProfiles() {
    hideAllWindows();
    document.getElementById('profilesWindow').classList.remove('hidden');
}

async function loadDiscordServerInfo() {
    if (discordCache) {
        applyDiscordServerInfo(discordCache);
        return;
    }

    const inviteCode = DISCORD_INVITE;

    try {
        const response = await fetch(`https://discord.com/api/v10/invites/${inviteCode}?with_counts=true`);
        const data = await response.json();
        
        if (data.guild) {
            discordCache = data;
            applyDiscordServerInfo(data);
        }
    } catch (error) {
        console.error('Failed to load Discord server info:', error);
        // Fallback values
        document.getElementById('discordServerName').textContent = 'Nenquen\'s Community';
        document.getElementById('discordMemberCount').textContent = 'Loading failed';
        document.getElementById('discordOnlineCount').textContent = 'Loading failed';
        document.getElementById('discordBoostCount').textContent = 'Loading failed';
    }
}

function hideAllWindows() {
    document.getElementById('mainWindow').classList.add('hidden');
    document.getElementById('aboutWindow').classList.add('hidden');
    document.getElementById('discordWindow').classList.add('hidden');
    document.getElementById('profilesWindow').classList.add('hidden');
    document.getElementById('warningWindow').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

let pendingUrl = null;
let previousWindow = null;

function playClickSound() {
    const clickSound = new Audio('assets/sounds/click.wav');
    clickSound.volume = 0.3;
    clickSound.play().catch(e => console.log('Audio play failed:', e));
}

function playWarningSound() {
    const warningSound = new Audio('assets/sounds/warning.wav');
    warningSound.volume = 0.5;
    warningSound.play().catch(e => console.log('Audio play failed:', e));
}

function showWarningWindow(url) {
    pendingUrl = url;
    previousWindow = getCurrentWindow();
    playWarningSound();
    hideAllWindows();
    document.getElementById('warningWindow').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function getCurrentWindow() {
    if (!document.getElementById('mainWindow').classList.contains('hidden')) return 'mainWindow';
    if (!document.getElementById('aboutWindow').classList.contains('hidden')) return 'aboutWindow';
    if (!document.getElementById('discordWindow').classList.contains('hidden')) return 'discordWindow';
    if (!document.getElementById('profilesWindow').classList.contains('hidden')) return 'profilesWindow';
    return 'mainWindow';
}

function openPendingUrl() {
    if (pendingUrl) {
        window.open(pendingUrl, '_blank');
        pendingUrl = null;
    }
    restorePreviousWindow();
}

function cancelWarning() {
    pendingUrl = null;
    restorePreviousWindow();
}

function restorePreviousWindow() {
    hideAllWindows();
    if (previousWindow === 'aboutWindow') {
        document.getElementById('aboutWindow').classList.remove('hidden');
    } else if (previousWindow === 'discordWindow') {
        document.getElementById('discordWindow').classList.remove('hidden');
    } else if (previousWindow === 'profilesWindow') {
        document.getElementById('profilesWindow').classList.remove('hidden');
    } else {
        document.getElementById('mainWindow').classList.remove('hidden');
    }
    previousWindow = null;
}

function setRandomWelcomeMessage() {
    const messages = [
        "Welcome! What's up :p",
        "Check out our discord server!",
        "Nenquen was here :3",
        "Giggity giggity giggity giggity!",
        "The source code of the site is available on my github!"
    ];
    
    const randomIndex = Math.floor(Math.random() * messages.length);
    document.getElementById('welcome-message').textContent = messages[randomIndex];
}

function applyDiscordServerInfo(data) {
    document.getElementById('discordServerName').textContent = data.guild.name;

    if (data.guild.icon) {
        const iconUrl = `https://cdn.discordapp.com/icons/${data.guild.id}/${data.guild.icon}.png`;
        document.getElementById('discordServerIcon').src = iconUrl;
    }

    if (data.approximate_member_count) {
        document.getElementById('discordMemberCount').textContent = `${data.approximate_member_count} Members`;
    }

    if (data.approximate_presence_count) {
        document.getElementById('discordOnlineCount').textContent = `${data.approximate_presence_count} Online`;
    }

    if (data.guild.premium_subscription_count !== undefined) {
        document.getElementById('discordBoostCount').textContent = `${data.guild.premium_subscription_count} Boosts`;
    } else {
        document.getElementById('discordBoostCount').textContent = '0 Boosts';
    }
}

function handleRoute() {
    const hash = window.location.hash;

    if (hash === '#discord') {
        toggleDiscord();
    } else if (hash === '#about') {
        toggleAbout();
    } else if (hash === '#profiles') {
        toggleProfiles();
    } else {
        showMainWindow();
    }
}

// Listen for hash changes
window.addEventListener('hashchange', handleRoute);

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Check URL hash for routing
    handleRoute();
    
    // Set random welcome message
    setRandomWelcomeMessage();
    
    // Add event listeners to navigation buttons
    document.getElementById('aboutButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = 'about';
    });
    document.getElementById('profilesButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = 'profiles';
    });
    document.getElementById('backButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('backDiscordButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('backProfilesButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    
    // Add event listeners to all external links
    document.querySelectorAll('.external-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            playClickSound();
            showWarningWindow(this.href);
        });
    });
    
    // Add event listeners to link buttons
    document.getElementById('githubButton').addEventListener('click', function() {
        playClickSound();
        showWarningWindow('https://github.com/nenquen');
    });
    document.getElementById('discordButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = 'discord';
    });
    document.getElementById('joinDiscordButton').addEventListener('click', function() {
        playClickSound();
        showWarningWindow(`https://discord.gg/${DISCORD_INVITE}`);
    });
    
    // Add event listeners to window control buttons
    document.getElementById('closeAboutButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('closeDiscordButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('closeProfilesButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('closeMainButton').addEventListener('click', function() {
        playClickSound();
        window.location.hash = '';
    });
    document.getElementById('closeWarningButton').addEventListener('click', function() {
        playClickSound();
        cancelWarning();
    });
    document.getElementById('cancelWarningButton').addEventListener('click', function() {
        playClickSound();
        cancelWarning();
    });
    document.getElementById('confirmWarningButton').addEventListener('click', function() {
        playClickSound();
        openPendingUrl();
    });
    document.getElementById('minimizeWarningButton').addEventListener('click', function() {
        playClickSound();
        cancelWarning();
    });
    document.getElementById('maximizeWarningButton').addEventListener('click', function() {
        playClickSound();
        document.getElementById('warningWindow').classList.toggle('maximized');
    });

    // Minimize / maximize for each window
    const windows = ['main', 'about', 'discord', 'profiles'];
    windows.forEach(function(prefix) {
        const winId = prefix + 'Window';
        document.getElementById('minimize' + capitalize(prefix) + 'Button').addEventListener('click', function() {
            playClickSound();
            showMainWindow();
        });
        document.getElementById('maximize' + capitalize(prefix) + 'Button').addEventListener('click', function() {
            playClickSound();
            document.getElementById(winId).classList.toggle('maximized');
        });
    });
});

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}