// ─── Theme ────────────────────────────────────────────────────────────────────
const html = document.documentElement;
const themeBtn = document.getElementById('theme-toggle');

function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    themeBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('theme', theme);
}

// Initialise theme from storage or system preference
const savedTheme = localStorage.getItem('theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
applyTheme(savedTheme);

themeBtn.addEventListener('click', () => {
    applyTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

// ─── State ────────────────────────────────────────────────────────────────────
let isStreaming = false;

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const chatContainer = document.getElementById('chat-container');
const msgInput      = document.getElementById('msg-input');
const sendBtn       = document.getElementById('send-btn');
const typingEl      = document.getElementById('typing-indicator');

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function scrollBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setStreaming(val) {
    isStreaming = val;
    sendBtn.disabled = val;
    msgInput.disabled = val;
    typingEl.classList.toggle('visible', val);
    scrollBottom();
}

// ─── Append a chat bubble ─────────────────────────────────────────────────────
function appendMessage(content, role) {
    const now = new Date();
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
        <div class="msg-content">${content}</div>
        <div class="msg-meta">${role === 'agent' ? 'AGENT' : 'YOU'} &bull; ${formatTime(now)}</div>
    `;
    chatContainer.appendChild(div);
    scrollBottom();
    return div;
}

// ─── Trace Panel ──────────────────────────────────────────────────────────────
let currentTraceBody = null;
let currentAgentTraceItems = {};
let currentAgentContent = null;

window.toggleTrace = function(header) {
    const body = header.nextElementSibling;
    const icon = header.querySelector('.trace-toggle-icon');
    body.classList.toggle('open');
    icon.textContent = body.classList.contains('open') ? '▲' : '▼';
};

function addTraceItem(traceBody, text, status = 'processing', nested = false) {
    const item = document.createElement('div');
    item.className = `trace-item${nested ? ' nested' : ''}`;
    item.innerHTML = `
        <span class="status-dot ${status}"></span>
        <span>${text}</span>
    `;
    traceBody.appendChild(item);
    scrollBottom();
    return item;
}

function handleTraceEvent(event) {
    const { type, name, status, args, result, from, to, content } = event;

    if (!currentTraceBody) return;

    if (type === 'agent') {
        Object.values(currentAgentTraceItems).forEach(item => {
            const dot = item.querySelector('.status-dot');
            if (dot && (dot.classList.contains('active') || dot.classList.contains('processing'))) {
                dot.className = 'status-dot done';
            }
        });
        const item = addTraceItem(currentTraceBody, `● ${name}`, status === 'active' ? 'active' : 'processing');
        currentAgentTraceItems[name] = item;
    }

    if (type === 'route') {
        addTraceItem(currentTraceBody, `↪ ${from} → ${to}`, 'active');
    }

    if (type === 'tool_call') {
        const argsStr = args ? Object.entries(args).map(([k,v]) => `${k}="${v}"`).join(', ') : '';
        addTraceItem(currentTraceBody, `⚙ ${name}(${argsStr})`, 'processing', true);
    }

    if (type === 'tool_result') {
        const nestedItems = [...currentTraceBody.querySelectorAll('.nested')];
        const lastNested = nestedItems[nestedItems.length - 1];
        if (lastNested) {
            lastNested.querySelector('.status-dot').className = 'status-dot done';
        }
        addTraceItem(currentTraceBody, `✓ ${name} completed`, 'done', true);
    }

    if (type === 'done') {
        currentTraceBody.querySelectorAll('.status-dot.active, .status-dot.processing').forEach(dot => {
            dot.className = 'status-dot done';
        });
    }
}

// ─── Main send function ───────────────────────────────────────────────────────
async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;

    msgInput.value = '';
    appendMessage(trimmed, 'user');

    setStreaming(true);

    const now = new Date();
    const agentDiv = document.createElement('div');
    agentDiv.className = 'message agent';
    agentDiv.innerHTML = `
        <div class="trace-panel">
            <div class="trace-header" onclick="toggleTrace(this)">
                <span>🔍 Agent Trace</span>
                <span class="trace-toggle-icon">▲</span>
            </div>
            <div class="trace-body open"></div>
        </div>
        <div class="msg-content">...</div>
        <div class="msg-meta">AGENT &bull; ${formatTime(now)}</div>
    `;
    chatContainer.appendChild(agentDiv);
    scrollBottom();

    currentTraceBody = agentDiv.querySelector('.trace-body');
    currentAgentContent = agentDiv.querySelector('.msg-content');
    currentAgentTraceItems = {};

    try {
        const resp = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: trimmed }),
        });

        if (!resp.ok) {
            throw new Error(`Server error: ${resp.status}`);
        }

        const reader  = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer    = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete last line

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const raw = line.slice(6).trim();
                if (!raw) continue;

                let event;
                try { event = JSON.parse(raw); }
                catch { continue; }

                if (event.type === 'message') {
                    setStreaming(false);
                    if (currentAgentContent) {
                        currentAgentContent.innerHTML = event.content;
                    }
                } else if (event.type === 'done') {
                    setStreaming(false);
                    handleTraceEvent(event);
                } else if (event.type === 'error') {
                    setStreaming(false);
                    if (currentAgentContent) {
                        currentAgentContent.innerHTML = `⚠️ ${event.content}`;
                    } else {
                        appendMessage(`⚠️ ${event.content}`, 'agent');
                    }
                } else {
                    handleTraceEvent(event);
                }
            }
        }
    } catch (err) {
        console.error('SSE error:', err);
        if (currentAgentContent && currentAgentContent.innerHTML === '...') {
            currentAgentContent.innerHTML = '⚠️ Could not reach the agent. Is the server running?';
        } else {
            appendMessage('⚠️ Could not reach the agent. Is the server running?', 'agent');
        }
    } finally {
        setStreaming(false);
    }
}

// ─── Event listeners ─────────────────────────────────────────────────────────
sendBtn.addEventListener('click', () => sendMessage(msgInput.value));
msgInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(msgInput.value);
    }
});

// ─── Quick-action chips ───────────────────────────────────────────────────────
document.querySelectorAll('.action-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const cmd = chip.dataset.cmd;
        if (cmd) sendMessage(cmd);
    });
});

const welcomeMeta = document.getElementById('welcome-msg-meta');
if (welcomeMeta) {
    welcomeMeta.innerHTML = `AGENT &bull; ${formatTime(new Date())}`;
}
