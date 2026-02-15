// ===== AskBob.Ai — Electron Overlay App =====

const chat = document.getElementById('chat');
const input = document.getElementById('question');
const sendBtn = document.getElementById('send');
const clearBtn = document.getElementById('clearBtn');
const scrollBtn = document.getElementById('scrollBtn');
const copyBtn = document.getElementById('copyBtn');
const themeBtn = document.getElementById('themeBtn');
const soundBtn = document.getElementById('soundBtn');
const shortcutsOverlay = document.getElementById('shortcutsOverlay');
const shortcutsClose = document.getElementById('shortcutsClose');
const connectionBar = document.getElementById('connectionBar');
const playerBanner = document.getElementById('playerBanner');
const playerNameEl = document.getElementById('playerName');
const playerTypeEl = document.getElementById('playerType');
const playerStatsEl = document.getElementById('playerStats');

// Settings panel elements
const settingsOverlay = document.getElementById('settingsOverlay');
const settingsBtn = document.getElementById('settingsBtn');
const settingsSave = document.getElementById('settingsSave');
const settingsCancel = document.getElementById('settingsCancel');
const settingRsn = document.getElementById('settingRsn');
const settingGameMode = document.getElementById('settingGameMode');
const settingBackendUrl = document.getElementById('settingBackendUrl');
const settingOpacity = document.getElementById('settingOpacity');
const opacityValue = document.getElementById('opacityValue');
const settingTheme = document.getElementById('settingTheme');
const settingBoot = document.getElementById('settingBoot');

// Window controls
document.getElementById('minimizeBtn').addEventListener('click', () => window.askbob.minimize());
document.getElementById('closeBtn').addEventListener('click', () => window.askbob.close());

// ===== State =====
let conversationHistory = [];
let activeAbort = null;
let lastQuestion = '';
let backendUrl = 'https://askbob-backend-production.up.railway.app';
let currentRsn = '';
let currentGameMode = 'main';
let playerContext = null;
let soundEnabled = true;
let isConnected = false;

const AVATAR_SRC = '../assets/icon.png';

// ===== Init from electron-store =====
async function initSettings() {
    try {
        const settings = await window.askbob.getSettings();
        backendUrl = settings.backendUrl || 'http://127.0.0.1:8001';
        currentRsn = settings.rsn || '';
        currentGameMode = settings.gameMode || 'main';
        soundEnabled = true;

        applyTheme(settings.theme || 'dark');

        // Load player context if RSN is set
        if (currentRsn) {
            refreshPlayerContext();
        }

        // Restore chat from localStorage
        loadState();

        // Start health checks
        checkHealth();
        setInterval(checkHealth, 30000);

        // Focus input
        input.focus();
    } catch (e) {
        console.error('Failed to load settings:', e);
        loadState();
        input.focus();
    }
}

// ===== Theme =====
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    themeBtn.textContent = theme === 'light' ? 'Dark' : 'Light';
}

themeBtn.addEventListener('click', async () => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try { await window.askbob.saveSettings({ theme: next }); } catch (e) {}
});

// ===== Sound =====
function updateSoundBtn() {
    soundBtn.textContent = soundEnabled ? 'Mute' : 'Unmute';
}
updateSoundBtn();
soundBtn.addEventListener('click', () => {
    soundEnabled = !soundEnabled;
    updateSoundBtn();
});

function playChime() {
    if (!soundEnabled || !document.hidden) return;
    try {
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.setValueAtTime(1318.5, ctx.currentTime + 0.2);
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.4);
    } catch (e) {}
}

// ===== Chat State Persistence (localStorage) =====
const STORAGE_KEY = 'askbob_chat_state';

function saveState() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            history: conversationHistory,
            gameMode: currentGameMode,
        }));
    } catch (e) {}
}

function loadState() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const state = JSON.parse(raw);
        if (state.history && state.history.length > 0) {
            conversationHistory = state.history;
            hideStarters();
            state.history.forEach(msg => {
                if (msg.role === 'user') {
                    const userMsg = document.createElement('div');
                    userMsg.className = 'message user';
                    userMsg.textContent = msg.content;
                    chat.appendChild(userMsg);
                } else {
                    const botRow = document.createElement('div');
                    botRow.className = 'bot-row';
                    botRow.innerHTML = `<div class="bot-avatar"><img src="${AVATAR_SRC}" alt="Bob"></div>`;
                    const botMsg = document.createElement('div');
                    botMsg.className = 'message bot';
                    botMsg.innerHTML = '<div class="answer">' + renderMarkdown(msg.content) + '</div>';
                    botRow.appendChild(botMsg);
                    chat.appendChild(botRow);
                }
            });
            chat.scrollTop = chat.scrollHeight;
        }
    } catch (e) {}
}

// ===== Starter Questions =====
function hideStarters() {
    const el = document.getElementById('starterQuestions');
    if (el) el.style.display = 'none';
}
function showStarters() {
    const el = document.getElementById('starterQuestions');
    if (el) el.style.display = '';
}

chat.addEventListener('click', (e) => {
    const pill = e.target.closest('.starter-pill');
    if (!pill) return;
    input.value = pill.dataset.q;
    askQuestion();
});

// ===== Scroll-to-bottom =====
let userScrolledUp = false;
chat.addEventListener('scroll', () => {
    const atBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 60;
    userScrolledUp = !atBottom;
    scrollBtn.classList.toggle('visible', userScrolledUp);
});
scrollBtn.addEventListener('click', () => {
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
});

// ===== Auto-resize textarea =====
input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 80) + 'px';
});

// ===== Markdown Renderer =====
function renderMarkdown(text) {
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code>${code.trim()}</code></pre>`
    );
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^[-\u2022] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, (match) => {
        if (!match.startsWith('<ul>')) return '<ul>' + match + '</ul>';
        return match;
    });
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = html.replace(/(<\/(?:h[34]|pre|ul|ol|li|p)>)<br>/g, '$1');
    html = html.replace(/<br>(<(?:h[34]|pre|ul|ol|li))/g, '$1');
    if (!html.startsWith('<')) html = '<p>' + html + '</p>';
    return html;
}

// ===== Health Check =====
async function checkHealth() {
    try {
        const resp = await fetch(`${backendUrl}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (resp.ok) {
            isConnected = true;
            connectionBar.classList.remove('visible');
        } else {
            throw new Error('not ok');
        }
    } catch {
        isConnected = false;
        connectionBar.textContent = `Cannot reach backend at ${backendUrl}`;
        connectionBar.classList.add('visible');
    }
}

// ===== Player Context =====
async function refreshPlayerContext() {
    if (!currentRsn) {
        playerContext = null;
        playerBanner.classList.remove('visible');
        return;
    }

    try {
        playerContext = await window.askbob.getPlayerContext(currentRsn);
        if (playerContext) {
            playerNameEl.textContent = playerContext.player_name;
            playerTypeEl.textContent = playerContext.account_type !== 'NORMAL' ? `[${playerContext.account_type}]` : '';
            playerStatsEl.textContent = `CB ${playerContext.combat_level} | Total ${playerContext.total_level}`;
            playerBanner.classList.add('visible');
        } else {
            playerBanner.classList.remove('visible');
        }
    } catch (e) {
        console.error('Hiscores error:', e);
        playerBanner.classList.remove('visible');
    }
}

// ===== Copy Chat =====
function getChatText() {
    const date = new Date().toLocaleString();
    let text = `AskBob.Ai Chat Export \u2014 ${date}\n\n`;
    conversationHistory.forEach(msg => {
        const label = msg.role === 'user' ? '[You]' : '[Bob the Cat]';
        text += `${label}: ${msg.content}\n\n`;
    });
    return text.trim();
}

copyBtn.addEventListener('click', () => {
    const text = getChatText();
    if (!text || conversationHistory.length === 0) return;
    navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = 'Copied!';
        copyBtn.classList.add('flash');
        setTimeout(() => {
            copyBtn.textContent = 'Copy';
            copyBtn.classList.remove('flash');
        }, 1200);
    });
});

// ===== Clear Chat =====
clearBtn.addEventListener('click', clearChat);
function clearChat() {
    conversationHistory = [];
    saveState();
    chat.innerHTML = `<div class="bot-row">
        <div class="bot-avatar"><img src="${AVATAR_SRC}" alt="Bob"></div>
        <div class="message bot">
            <div class="answer">Meow! I'm Bob the Cat \u2014 ask me anything about Old School RuneScape.</div>
        </div>
    </div>
    <div id="starterQuestions" class="starter-grid">
        <button class="starter-pill" data-q="What are the requirements for Dragon Slayer II?">Dragon Slayer II requirements?</button>
        <button class="starter-pill" data-q="What are good mid-level money making methods?">Mid-level money making?</button>
        <button class="starter-pill" data-q="How do I get to Fossil Island and what can I do there?">Getting to Fossil Island?</button>
        <button class="starter-pill" data-q="What gear should I bring to fight Zulrah?">Zulrah gear setup?</button>
        <button class="starter-pill" data-q="Can you explain tick manipulation for skilling?">Tick manipulation explained?</button>
        <button class="starter-pill" data-q="What quests do I need for Barrows Gloves?">Barrows Gloves quest reqs?</button>
    </div>`;
}

// ===== Ask Question (SSE Streaming) =====
async function askQuestion(retryQuestion) {
    const q = retryQuestion || input.value.trim();
    if (!q) return;

    lastQuestion = q;
    hideStarters();

    if (!retryQuestion) {
        conversationHistory.push({ role: 'user', content: q });

        const userMsg = document.createElement('div');
        userMsg.className = 'message user';
        userMsg.textContent = q;
        chat.appendChild(userMsg);

        input.value = '';
        input.style.height = 'auto';
    }

    sendBtn.disabled = true;

    const botRow = document.createElement('div');
    botRow.className = 'bot-row';
    botRow.innerHTML = `<div class="bot-avatar"><img src="${AVATAR_SRC}" alt="Bob"></div>`;

    const botMsg = document.createElement('div');
    botMsg.className = 'message bot';
    botMsg.innerHTML = '<div class="answer typing">Thinking</div>';
    botRow.appendChild(botMsg);
    chat.appendChild(botRow);
    chat.scrollTop = chat.scrollHeight;

    const answerDiv = botMsg.querySelector('.answer');

    const abortController = new AbortController();
    activeAbort = abortController;

    try {
        const recentMessages = conversationHistory.slice(-10);
        const body = {
            question: q,
            game_mode: currentGameMode,
            messages: recentMessages,
        };

        // Attach player context if available
        if (playerContext) {
            body.player_context = playerContext;
        }

        const response = await fetch(`${backendUrl}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: abortController.signal,
        });

        if (!response.ok) {
            throw new Error(`Server error (${response.status})`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let sources = [];
        let model = '';
        let buffer = '';
        let renderScheduled = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'sources') {
                        sources = data.sources;
                    } else if (data.type === 'chunk') {
                        if (answerDiv.classList.contains('typing')) {
                            answerDiv.classList.remove('typing');
                            answerDiv.textContent = '';
                        }
                        fullText += data.text;
                        if (!renderScheduled) {
                            renderScheduled = true;
                            requestAnimationFrame(() => {
                                answerDiv.innerHTML = renderMarkdown(fullText);
                                renderScheduled = false;
                                if (!userScrolledUp) chat.scrollTop = chat.scrollHeight;
                            });
                        }
                    } else if (data.type === 'done') {
                        model = data.model;
                        playChime();
                    }
                } catch (parseErr) {}
            }
        }

        activeAbort = null;

        if (fullText) {
            answerDiv.innerHTML = renderMarkdown(fullText);
            conversationHistory.push({ role: 'assistant', content: fullText });
            saveState();
        }

        if (sources.length > 0) {
            const srcDiv = document.createElement('div');
            srcDiv.className = 'sources';
            const srcLinks = sources.map(s => {
                const safeTitle = s.title.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const safeUrl = encodeURI(s.url);
                return `<a href="#" data-url="${safeUrl}">${safeTitle}</a>`;
            }).join(' \u00b7 ');
            srcDiv.innerHTML = 'Sources: ' + srcLinks;
            botMsg.appendChild(srcDiv);

            // Open source links externally
            srcDiv.querySelectorAll('a[data-url]').forEach(a => {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.askbob.openExternal(a.dataset.url);
                });
            });
        }

        if (model) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'meta';
            metaDiv.textContent = `${model} \u00b7 ${currentGameMode}`;
            botMsg.appendChild(metaDiv);
        }

    } catch (err) {
        activeAbort = null;
        answerDiv.classList.remove('typing');

        if (err.name === 'AbortError') {
            const partialText = answerDiv.textContent || '';
            if (partialText) {
                answerDiv.innerHTML = renderMarkdown(partialText);
            } else {
                answerDiv.innerHTML = '<span style="color:var(--color-sources)">Request cancelled.</span>';
            }
            const cancelDiv = document.createElement('div');
            cancelDiv.className = 'cancelled';
            cancelDiv.textContent = '(cancelled)';
            botMsg.appendChild(cancelDiv);
            if (conversationHistory.length && conversationHistory[conversationHistory.length - 1].role === 'user') {
                conversationHistory.pop();
            }
        } else {
            answerDiv.innerHTML = `<span style="color:var(--color-red)">Could not get a response. Is the backend running?</span>
                <br><button class="retry-btn" onclick="retryLast()">Retry</button>`;
            if (!retryQuestion && conversationHistory.length && conversationHistory[conversationHistory.length - 1].role === 'user') {
                conversationHistory.pop();
            }
        }
    }

    sendBtn.disabled = false;
    input.focus();
    chat.scrollTop = chat.scrollHeight;
}

function retryLast() {
    if (!lastQuestion) return;
    const rows = chat.querySelectorAll('.bot-row');
    if (rows.length > 0) {
        const lastRow = rows[rows.length - 1];
        const errBtn = lastRow.querySelector('.retry-btn');
        if (errBtn) lastRow.remove();
    }
    askQuestion(lastQuestion);
}

// Make retryLast available to inline onclick
window.retryLast = retryLast;

sendBtn.addEventListener('click', () => askQuestion());
input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        askQuestion();
    }
});

// ===== Keyboard Shortcuts =====
const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
function isModKey(e) { return isMac ? e.metaKey : e.ctrlKey; }

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (settingsOverlay.classList.contains('visible')) {
            settingsOverlay.classList.remove('visible');
            return;
        }
        if (shortcutsOverlay.classList.contains('visible')) {
            shortcutsOverlay.classList.remove('visible');
            return;
        }
        if (activeAbort) {
            activeAbort.abort();
            activeAbort = null;
            return;
        }
        if (input.value) {
            input.value = '';
            input.style.height = 'auto';
            return;
        }
    }
    if (isModKey(e) && e.key === 'l') {
        e.preventDefault();
        clearChat();
        return;
    }
    if (isModKey(e) && e.key === '/') {
        e.preventDefault();
        shortcutsOverlay.classList.toggle('visible');
        return;
    }
    if (isModKey(e) && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        copyBtn.click();
        return;
    }
});

shortcutsClose.addEventListener('click', () => shortcutsOverlay.classList.remove('visible'));
shortcutsOverlay.addEventListener('click', (e) => {
    if (e.target === shortcutsOverlay) shortcutsOverlay.classList.remove('visible');
});

if (isMac) {
    document.querySelectorAll('.shortcut-row kbd').forEach(kbd => {
        kbd.textContent = kbd.textContent.replace('Ctrl', '\u2318');
    });
}

// ===== Settings Panel =====
function openSettings() {
    window.askbob.getSettings().then(settings => {
        settingRsn.value = settings.rsn || '';
        settingGameMode.value = settings.gameMode || 'main';
        settingBackendUrl.value = settings.backendUrl || 'http://127.0.0.1:8001';
        settingOpacity.value = settings.opacity || 0.95;
        opacityValue.textContent = Math.round((settings.opacity || 0.95) * 100) + '%';
        settingTheme.value = settings.theme || 'dark';
        if (settings.launchOnBoot) {
            settingBoot.classList.add('active');
        } else {
            settingBoot.classList.remove('active');
        }
        settingsOverlay.classList.add('visible');
    });
}

settingsBtn.addEventListener('click', openSettings);
window.askbob.onOpenSettings(openSettings);

settingOpacity.addEventListener('input', () => {
    opacityValue.textContent = Math.round(settingOpacity.value * 100) + '%';
});

settingBoot.addEventListener('click', () => {
    settingBoot.classList.toggle('active');
});

settingsCancel.addEventListener('click', () => {
    settingsOverlay.classList.remove('visible');
});

settingsOverlay.addEventListener('click', (e) => {
    if (e.target === settingsOverlay) settingsOverlay.classList.remove('visible');
});

settingsSave.addEventListener('click', async () => {
    const newSettings = {
        rsn: settingRsn.value.trim(),
        gameMode: settingGameMode.value,
        backendUrl: settingBackendUrl.value.trim() || 'http://127.0.0.1:8001',
        opacity: parseFloat(settingOpacity.value),
        theme: settingTheme.value,
        launchOnBoot: settingBoot.classList.contains('active'),
    };

    await window.askbob.saveSettings(newSettings);

    // Apply changes
    backendUrl = newSettings.backendUrl;
    currentGameMode = newSettings.gameMode;
    applyTheme(newSettings.theme);

    // If RSN changed, refresh player context
    if (newSettings.rsn !== currentRsn) {
        currentRsn = newSettings.rsn;
        refreshPlayerContext();
    }

    settingsOverlay.classList.remove('visible');

    // Re-check health with new backend URL
    checkHealth();
});

// ===== Auto-Update Banner =====
const updateBanner = document.getElementById('updateBanner');
window.askbob.onUpdateDownloaded((version) => {
    updateBanner.textContent = `Update v${version} ready — click to restart`;
    updateBanner.classList.add('visible');
});
updateBanner.addEventListener('click', () => {
    window.askbob.installUpdate();
});

// ===== Boot =====
initSettings();
