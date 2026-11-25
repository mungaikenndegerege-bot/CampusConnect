// messaging.js — Private Messaging for CampusConnect (polling-based)

(function () {
  let _pollTimer = null;
  let _currentConvId = null;
  let _lastMessageId = 0;

  function _stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer);
      _pollTimer = null;
    }
  }

  function _msgApi(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    const token = getAccountToken();
    if (token) opts.headers['X-Account-Token'] = token;
    if (body) opts.body = JSON.stringify(body);
    return fetch(path, opts).then(async r => {
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw d;
      return d;
    });
  }

  async function updateUnreadBadge() {
    const token = getAccountToken();
    if (!token) return;
    try {
      const data = await _msgApi('GET', '/api/messages/unread-count');
      const btn = document.querySelector('#bottom-nav button[data-section="messages"]');
      if (!btn) return;
      let badge = btn.querySelector('.nav-unread-badge');
      if (data.count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'nav-unread-badge';
          btn.appendChild(badge);
        }
        badge.textContent = data.count > 99 ? '99+' : data.count;
      } else {
        if (badge) badge.remove();
      }
    } catch (e) { /* ignore */ }
  }

  async function loadConversations() {
    const list = document.getElementById('conv-list');
    if (!list) return;
    try {
      const convs = await _msgApi('GET', '/api/messages/conversations');
      if (!document.getElementById('conv-list')) return;
      if (!convs.length) {
        list.innerHTML = '<div class="empty-state" style="padding:24px;text-align:center"><p>No conversations yet.<br>Start one below.</p></div>';
        return;
      }
      list.innerHTML = convs.map(c => `
        <div class="conv-item${c.id === _currentConvId ? ' active' : ''}" data-conv-id="${c.id}" onclick="openConversation(${c.id})">
          <div style="display:flex;align-items:center;gap:8px">
            <div style="flex:1">
              <div class="conv-name">${escHtml(c.other_name || 'Unknown')}</div>
              <div class="conv-preview">${escHtml(c.last_message_preview || 'No messages yet')}</div>
            </div>
            ${c.unread_count > 0 ? `<div class="unread-dot" title="${c.unread_count} unread"></div>` : ''}
          </div>
        </div>
      `).join('');
    } catch (e) {
      if (document.getElementById('conv-list')) {
        document.getElementById('conv-list').innerHTML = '<div style="padding:16px;color:#ef4444">Failed to load conversations.</div>';
      }
    }
  }

  async function openConversation(convId) {
    _stopPolling();
    _currentConvId = convId;
    _lastMessageId = 0;

    // Highlight active conv
    document.querySelectorAll('.conv-item').forEach(el =>
      el.classList.toggle('active', Number(el.dataset.convId) === convId)
    );

    const threadArea = document.getElementById('msg-thread-area');
    if (!threadArea) return;
    threadArea.innerHTML = '<div class="spinner" style="margin:32px auto"></div>';

    try {
      const data = await _msgApi('GET', `/api/messages/conversations/${convId}`);
      _renderThread(data);
      // Mark as read
      _msgApi('PUT', `/api/messages/conversations/${convId}/read`).catch(() => {});
      updateUnreadBadge();
      // Start polling
      _pollTimer = setInterval(() => _pollMessages(convId), 5000);
    } catch (e) {
      if (document.getElementById('msg-thread-area')) {
        document.getElementById('msg-thread-area').innerHTML = '<div style="padding:16px;color:#ef4444">Failed to load messages.</div>';
      }
    }
  }

  function _renderThread(data) {
    const threadArea = document.getElementById('msg-thread-area');
    if (!threadArea) return;
    const account = getAccountData();
    const myId = account ? account.id : null;
    const otherName = data.conversation ? (data.conversation.other_name || 'Conversation') : 'Conversation';

    const msgs = (data.messages || []);
    if (msgs.length) {
      _lastMessageId = msgs[msgs.length - 1].id;
    }

    threadArea.innerHTML = `
      <div class="message-thread" id="active-thread">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:.95rem">${escHtml(otherName)}</div>
        <div class="messages-list" id="messages-list">
          ${msgs.map(m => _renderBubble(m, myId)).join('')}
        </div>
        <div class="message-input-bar">
          <input id="msg-input" type="text" placeholder="Type a message…" maxlength="2000" onkeydown="if(event.key==='Enter')window._sendMsg()">
          <button onclick="window._sendMsg()">Send</button>
        </div>
      </div>
    `;
    _scrollToBottom();
  }

  function _renderBubble(msg, myId) {
    const isSent = msg.sender_id === myId;
    const timeStr = msg.created_at ? new Date(msg.created_at.endsWith('Z') ? msg.created_at : msg.created_at + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    const readIndicator = isSent && msg.read_at ? ' ✓✓' : (isSent ? ' ✓' : '');
    return `
      <div style="display:flex;flex-direction:column;align-items:${isSent ? 'flex-end' : 'flex-start'}">
        ${!isSent ? `<div style="font-size:.72rem;color:var(--text-muted);margin-bottom:2px;padding-left:4px">${escHtml(msg.sender_name || '')}</div>` : ''}
        <div class="msg-bubble ${isSent ? 'sent' : 'received'}">${escHtml(msg.body)}</div>
        <div class="msg-time" style="text-align:${isSent ? 'right' : 'left'}">${timeStr}${readIndicator}</div>
      </div>`;
  }

  function _scrollToBottom() {
    const list = document.getElementById('messages-list');
    if (list) list.scrollTop = list.scrollHeight;
  }

  async function _pollMessages(convId) {
    if (!document.getElementById('messages-list')) {
      _stopPolling();
      return;
    }
    try {
      const data = await _msgApi('GET', `/api/messages/conversations/${convId}`);
      const msgs = (data.messages || []);
      const account = getAccountData();
      const myId = account ? account.id : null;
      const list = document.getElementById('messages-list');
      if (!list) { _stopPolling(); return; }
      // Find new messages
      const newMsgs = msgs.filter(m => m.id > _lastMessageId);
      if (newMsgs.length) {
        newMsgs.forEach(m => {
          list.insertAdjacentHTML('beforeend', _renderBubble(m, myId));
        });
        _lastMessageId = newMsgs[newMsgs.length - 1].id;
        _scrollToBottom();
        _msgApi('PUT', `/api/messages/conversations/${convId}/read`).catch(() => {});
        updateUnreadBadge();
      }
      // Also refresh conv list unread counts
      loadConversations();
    } catch (e) { /* ignore poll errors */ }
  }

  window._sendMsg = async function () {
    if (!_currentConvId) return;
    const input = document.getElementById('msg-input');
    if (!input) return;
    const body = input.value.trim();
    if (!body) return;
    input.value = '';
    try {
      const msg = await _msgApi('POST', `/api/messages/conversations/${_currentConvId}`, { body });
      const account = getAccountData();
      const myId = account ? account.id : null;
      const list = document.getElementById('messages-list');
      if (list) {
        list.insertAdjacentHTML('beforeend', _renderBubble(msg, myId));
        _lastMessageId = Math.max(_lastMessageId, msg.id);
        _scrollToBottom();
      }
      loadConversations();
    } catch (e) {
      showToast((e && e.error) ? e.error : 'Failed to send message.', 'error');
    }
  };

  async function startNewConversation(recipientId, recipientName) {
    try {
      const conv = await _msgApi('POST', '/api/messages/conversations', { recipient_id: recipientId });
      closeModal();
      await loadConversations();
      openConversation(conv.id);
    } catch (e) {
      showToast((e && e.error) ? e.error : 'Could not start conversation.', 'error');
    }
  }

  window.startNewConversation = startNewConversation;
  window.openConversation = openConversation;

  async function openNewMessageModal() {
    openModal(`
      <div style="max-width:360px;margin:0 auto">
        <h3 style="margin-bottom:12px">New Message</h3>
        <input id="new-msg-search" class="form-input" placeholder="Search by name…" oninput="searchForRecipient(this.value)" autocomplete="off">
        <div id="recipient-results" style="margin-top:8px"></div>
      </div>
    `);
  }

  window.searchForRecipient = async function (q) {
    const container = document.getElementById('recipient-results');
    if (!container) return;
    if (!q.trim()) { container.innerHTML = ''; return; }
    try {
      const opts = { headers: { 'Content-Type': 'application/json' } };
      const token = getAccountToken();
      if (token) opts.headers['X-Account-Token'] = token;
      const r = await fetch('/api/accounts/search?q=' + encodeURIComponent(q), opts);
      const results = await r.json();
      if (!document.getElementById('recipient-results')) return;
      if (!results.length) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:.85rem;padding:8px 0">No users found.</div>';
        return;
      }
      container.innerHTML = results.map(u => `
        <div style="padding:10px 12px;cursor:pointer;border-radius:8px;margin-bottom:4px;background:#f9f9f9" onclick="startNewConversation(${u.id}, '${escHtml(u.name).replace(/'/g, "\\'")}')">
          <div style="font-weight:600">${escHtml(u.name)}</div>
          ${u.institution_name ? `<div style="font-size:.78rem;color:var(--text-muted)">${escHtml(u.institution_name)}</div>` : ''}
        </div>
      `).join('');
    } catch (e) {
      /* ignore */
    }
  };

  window.renderMessages = function () {
    _stopPolling();
    _currentConvId = null;
    _lastMessageId = 0;

    const account = getAccountData();
    const main = document.getElementById('main-content');

    if (!account) {
      main.innerHTML = `
        <div class="empty-state" style="margin-top:40px;text-align:center">
          <div style="font-size:2.5rem">💬</div>
          <h3 style="margin:12px 0 8px">Private Messaging</h3>
          <p style="color:var(--text-muted);margin-bottom:16px">Sign in to send and receive messages.</p>
          <button class="btn btn-primary" onclick="openAccountModal()">Sign In / Register</button>
        </div>`;
      return;
    }

    main.innerHTML = `
      <div class="messages-layout">
        <div class="conv-list" id="conv-list">
          <div class="spinner" style="margin:24px auto"></div>
        </div>
        <div id="msg-thread-area" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted)">
          <div style="text-align:center">
            <div style="font-size:2rem">💬</div>
            <p>Select a conversation or start a new one.</p>
            <button class="btn btn-primary" style="margin-top:12px" onclick="window._openNewMsg()">+ New Message</button>
          </div>
        </div>
      </div>`;

    window._openNewMsg = openNewMessageModal;
    loadConversations();
    updateUnreadBadge();
  };

  // Poll unread badge every 30 seconds globally
  setInterval(updateUnreadBadge, 30000);
  document.addEventListener('DOMContentLoaded', () => {
    updateUnreadBadge();
  });

})();
