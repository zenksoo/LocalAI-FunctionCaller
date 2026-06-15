// store data localy in label named fc_chats
const STORAGE_KEY = 'fc_chats';

function loadChats() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
    catch { return []; }
}

function saveChats(chats) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
}

function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

let chats = loadChats();
let activeChatId = null;

// render left slider with his content
function renderSidebar() {
    const list = document.getElementById('chat-list');
    list.innerHTML = '';

    if (chats.length === 0) {
        list.innerHTML = `
      <div class="no-chats">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        No chats yet.<br/>Hit "New chat" to start.
      </div>`;
        return;
    }

    [...chats].reverse().forEach(chat => {
        const el = document.createElement('div');
        el.className = 'chat-item' + (chat.id === activeChatId ? ' active' : '');
        el.dataset.id = chat.id;
        el.innerHTML = `
      <div class="chat-item-icon">
        <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </div>
      <div class="chat-item-info">
        <div class="chat-item-title">${escHtml(chat.title)}</div>
        <div class="chat-item-meta">${formatDate(chat.createdAt)}</div>
      </div>
      <button class="chat-delete-btn" data-delete="${chat.id}" aria-label="Delete chat">
        <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
      </button>
    `;

        el.addEventListener('click', e => {
            if (e.target.closest('[data-delete]')) return;
            switchChat(chat.id);
        });

        el.querySelector('[data-delete]').addEventListener('click', e => {
            e.stopPropagation();
            confirmDelete(chat.id, chat.title);
        });

        list.appendChild(el);
    });
}

/* ================================================================
   RENDER MESSAGES for active chat
================================================================ */
function renderMessages() {
    const container = document.getElementById('messages');
    container.innerHTML = '';

    const chat = chats.find(c => c.id === activeChatId);

    if (!chat || !activeChatId || chat.messages.length === 0) {
        container.innerHTML = `
      <div class="empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
        </div>
        <h2>What do you need?</h2>
        <p>Ask in plain language — the model picks the right function and returns the result.</p>
        <div class="chips">
          <span class="chip">What is the sum of 12 and 29?</span>
          <span class="chip">Multiply 7 by 8</span>
          <span class="chip">What time is it?</span>
          <span class="chip">Search for "python"</span>
        </div>
      </div>`;

        container.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.getElementById('user-input').value = chip.textContent;
                document.getElementById('user-input').focus();
                autoResize(document.getElementById('user-input'));
            });
        });
        return;
    }

    chat.messages.forEach(msg => {
        container.appendChild(buildMsgEl(msg));
    });

    container.scrollTop = container.scrollHeight;
}

/* ================================================================
   BUILD A MESSAGE ELEMENT from a stored message object
   msg = { role: 'user'|'ai', text, time, fn?: { name, args, result } }
================================================================ */
function buildMsgEl(msg) {
    const el = document.createElement('div');
    el.className = 'msg ' + (msg.role === 'user' ? 'user' : 'ai');

    let fnHtml = '';
    if (msg.fn) {
        const argsHtml = Object.entries(msg.fn.args || {}).map(([k, v]) => `
      <div class="arg-row">
        <span class="arg-key">${escHtml(k)}</span>
        <span class="arg-val">${escHtml(String(v))}</span>
      </div>`).join('');

        const resultHtml = msg.fn.result !== undefined ? `
      <div class="result-box">
        <span class="result-label">Result</span>
        <span class="result-val">${escHtml(String(msg.fn.result))}</span>
      </div>` : '';

        fnHtml = `
      <div class="fn-card">
        <div class="fn-card-head">
          <span class="fn-badge">function</span>
          <span class="fn-card-name">${escHtml(msg.fn.name)}</span>
        </div>
        <div class="fn-card-body">
          ${argsHtml ? `<p class="args-label">Arguments</p><div class="args-grid">${argsHtml}</div>` : ''}
          ${resultHtml}
        </div>
      </div>`;
    }

    if (msg.role === 'user') {
        el.innerHTML = `
      <div class="avatar usr">U</div>
      <div class="bubble">
        <div class="bubble-text">${escHtml(msg.text)}</div>
        <span class="ts">${msg.time}</span>
      </div>`;
    } else {
        el.innerHTML = `
      <div class="avatar ai">AI</div>
      <div class="bubble">
        <div class="bubble-text">${escHtml(msg.text)}</div>
        ${fnHtml}
        <span class="ts">${msg.time}</span>
      </div>`;
    }

    return el;
}

/* ================================================================
   CHAT ACTIONS
================================================================ */
function createChat() {
    const chat = {
        id: uid(),
        title: 'New chat',
        createdAt: Date.now(),
        messages: [],
    };
    chats.push(chat);
    saveChats(chats);
    switchChat(chat.id);
}

function switchChat(id) {
    activeChatId = id;
    renderSidebar();
    renderMessages();
    document.getElementById('user-input').focus();
}

/* ── ADD a message to active chat and persist ── */
function addMessage(msg) {
    const chat = chats.find(c => c.id === activeChatId);
    if (!chat) return;
    chat.messages.push(msg);

    /* auto-title from first user message */
    if (chat.title === 'New chat' && msg.role === 'user') {
        chat.title = msg.text.slice(0, 36) + (msg.text.length > 36 ? '…' : '');
    }

    saveChats(chats);
    renderSidebar();

    const container = document.getElementById('messages');
    /* remove empty state if present */
    const empty = container.querySelector('.empty');
    if (empty) empty.remove();

    container.appendChild(buildMsgEl(msg));
    container.scrollTop = container.scrollHeight;
}

/* ── THINKING indicator ── */
function showThinking() {
    const container = document.getElementById('messages');
    const el = document.createElement('div');
    el.className = 'msg ai'; el.id = 'thinking-row';
    el.innerHTML = `
    <div class="avatar ai">AI</div>
    <div class="thinking">
      <div class="dot"></div><div class="dot"></div><div class="dot"></div>
    </div>`;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
}

function hideThinking() {
    const el = document.getElementById('thinking-row');
    if (el) el.remove();
}

/* ================================================================
   DELETE WITH TOAST CONFIRM
================================================================ */
let pendingDeleteId = null;

function confirmDelete(id, title) {
    pendingDeleteId = id;
    document.getElementById('toast-msg').textContent =
        'Delete "' + title.slice(0, 28) + (title.length > 28 ? '…' : '') + '"?';
    document.getElementById('toast').classList.add('show');
}

document.getElementById('toast-confirm').addEventListener('click', () => {
    if (!pendingDeleteId) return;
    chats = chats.filter(c => c.id !== pendingDeleteId);
    saveChats(chats);
    if (activeChatId === pendingDeleteId) {
        activeChatId = chats.length ? chats[chats.length - 1].id : null;
    }
    pendingDeleteId = null;
    document.getElementById('toast').classList.remove('show');
    renderSidebar();
    renderMessages();
});

document.getElementById('toast-cancel').addEventListener('click', () => {
    pendingDeleteId = null;
    document.getElementById('toast').classList.remove('show');
});

/* ================================================================
   INPUT HANDLING
================================================================ */
const textarea = document.getElementById('user-input');

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

textarea.addEventListener('input', () => autoResize(textarea));

textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
});

document.getElementById('send-btn').addEventListener('click', handleSend);

function handleSend() {
    const text = textarea.value.trim();
    if (!text) return;

    /* auto-create a chat if none is active */
    if (!activeChatId) {
        const chat = { id: uid(), title: 'New chat', createdAt: Date.now(), messages: [] };
        chats.push(chat);
        saveChats(chats);
        activeChatId = chat.id;
        renderSidebar();
        renderMessages();
    }

    textarea.value = '';
    textarea.style.height = 'auto';

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    /* add user message */
    addMessage({ role: 'user', text, time });

    /* show thinking */
    showThinking();

    /*
    ── WIRE YOUR LLM PIPELINE HERE ──

    Call your local LLM / Flask API, then when you get the response:

      hideThinking();
      addMessage({
        role: 'ai',
        text: 'I used fn_add_numbers to compute that.',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        fn: {                        // omit this key if no function was called
          name: 'fn_add_numbers',
          args: { a: 2, b: 5 },
          result: 7
        }
      });
    */
}

// new chat button
document.getElementById('new-chat-btn').addEventListener('click', createChat);

// healpers
function escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDate(ts) {
    const d = new Date(ts);
    const now = new Date();
    const diffDays = Math.floor((now - d) / 86400000);
    if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}


(function init() {
    if (chats.length > 0) {
        activeChatId = chats[chats.length - 1].id;
    }
    renderSidebar();
    renderMessages();
})();
