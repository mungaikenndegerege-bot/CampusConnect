// account.js — Optional account UI for CampusConnect

function getAccountToken() {
  return localStorage.getItem('cc_account_token');
}

function getAccountData() {
  const raw = localStorage.getItem('cc_account_data');
  return raw ? JSON.parse(raw) : null;
}

function setAccountData(token, account) {
  localStorage.setItem('cc_account_token', token);
  localStorage.setItem('cc_account_data', JSON.stringify(account));
}

function clearAccountData() {
  localStorage.removeItem('cc_account_token');
  localStorage.removeItem('cc_account_data');
}

async function accountApi(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  const token = getAccountToken();
  if (token) opts.headers['X-Account-Token'] = token;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, data };
  return data;
}

function renderAccountBar() {
  const bar = document.getElementById('account-bar');
  if (!bar) return;
  const account = getAccountData();
  if (account) {
    bar.innerHTML = `
      <button class="account-bar-btn" onclick="showMyPosts()">My Posts</button>
      <button class="account-bar-btn" onclick="signOut()">Sign Out</button>
    `;
  } else {
    bar.innerHTML = `
      <button class="account-bar-btn" onclick="openAccountModal()">Sign In / Register</button>
    `;
  }
}

function openAccountModal() {
  openModal(`
    <div style="max-width:340px;margin:0 auto">
      <h3 style="margin-bottom:16px;text-align:center">Account</h3>
      <div style="display:flex;border-bottom:2px solid #e5e7eb;margin-bottom:16px">
        <button id="tab-login" onclick="switchAccountTab('login')" style="flex:1;padding:8px;border:none;background:none;font-weight:600;cursor:pointer;border-bottom:2px solid #6C3CE1;color:#6C3CE1">Login</button>
        <button id="tab-register" onclick="switchAccountTab('register')" style="flex:1;padding:8px;border:none;background:none;font-weight:600;cursor:pointer;color:#9ca3af">Register</button>
      </div>
      <div id="account-modal-content"></div>
    </div>
  `);
  switchAccountTab('login');
}

function switchAccountTab(tab) {
  const loginBtn = document.getElementById('tab-login');
  const registerBtn = document.getElementById('tab-register');
  const content = document.getElementById('account-modal-content');
  if (!loginBtn || !registerBtn || !content) return;

  if (tab === 'login') {
    loginBtn.style.borderBottom = '2px solid #6C3CE1';
    loginBtn.style.color = '#6C3CE1';
    registerBtn.style.borderBottom = '2px solid transparent';
    registerBtn.style.color = '#9ca3af';
    content.innerHTML = `
      <div>
        <div style="margin-bottom:10px">
          <label style="font-size:0.85rem;font-weight:600">Email</label>
          <input id="login-email" class="form-input" type="email" placeholder="you@example.com" style="margin-top:4px">
        </div>
        <div style="margin-bottom:10px">
          <label style="font-size:0.85rem;font-weight:600">Password</label>
          <input id="login-password" class="form-input" type="password" placeholder="Password" style="margin-top:4px">
        </div>
        <div id="login-error" style="color:#ef4444;font-size:0.82rem;margin-bottom:8px;display:none"></div>
        <button onclick="submitLogin()" class="btn btn-primary" style="width:100%">Sign In</button>
        <div style="text-align:center;margin-top:12px">
          <button onclick="showForgotPassword()" style="background:none;border:none;color:#6C3CE1;cursor:pointer;font-size:.85rem;text-decoration:underline">Forgot password?</button>
        </div>
      </div>
    `;
  } else {
    loginBtn.style.borderBottom = '2px solid transparent';
    loginBtn.style.color = '#9ca3af';
    registerBtn.style.borderBottom = '2px solid #6C3CE1';
    registerBtn.style.color = '#6C3CE1';
    content.innerHTML = `
      <div>
        <div style="margin-bottom:10px">
          <label style="font-size:0.85rem;font-weight:600">Name</label>
          <input id="reg-name" class="form-input" placeholder="Your name" style="margin-top:4px">
        </div>
        <div style="margin-bottom:10px">
          <label style="font-size:0.85rem;font-weight:600">Email</label>
          <input id="reg-email" class="form-input" type="email" placeholder="you@example.com" style="margin-top:4px">
        </div>
        <div style="margin-bottom:10px">
          <label style="font-size:0.85rem;font-weight:600">Password (min 8 chars)</label>
          <input id="reg-password" class="form-input" type="password" placeholder="Password" style="margin-top:4px">
        </div>
        <div id="reg-error" style="color:#ef4444;font-size:0.82rem;margin-bottom:8px;display:none"></div>
        <button onclick="submitRegister()" class="btn btn-primary" style="width:100%">Create Account</button>
      </div>
    `;
  }
}

async function submitLogin() {
  const email = (document.getElementById('login-email').value || '').trim();
  const password = document.getElementById('login-password').value || '';
  const errEl = document.getElementById('login-error');
  errEl.style.display = 'none';
  try {
    const res = await accountApi('POST', '/api/accounts/login', { email, password });
    setAccountData(res.token, res.account);
    closeModal();
    renderAccountBar();
    showToast('Welcome back, ' + res.account.name + '!', 'success');
  } catch(e) {
    const msg = (e.data && e.data.error) ? e.data.error : 'Login failed';
    errEl.textContent = msg;
    errEl.style.display = 'block';
  }
}

async function submitRegister() {
  const name = (document.getElementById('reg-name').value || '').trim();
  const email = (document.getElementById('reg-email').value || '').trim();
  const password = document.getElementById('reg-password').value || '';
  const errEl = document.getElementById('reg-error');
  errEl.style.display = 'none';
  try {
    const res = await accountApi('POST', '/api/accounts/register', { name, email, password });
    setAccountData(res.token, res.account);
    closeModal();
    renderAccountBar();
    showToast('Account created! Welcome, ' + res.account.name + '!', 'success');
  } catch(e) {
    const msg = (e.data && e.data.error) ? e.data.error : 'Registration failed';
    errEl.textContent = msg;
    errEl.style.display = 'block';
  }
}

async function signOut() {
  try { await accountApi('POST', '/api/accounts/logout'); } catch(e) { /* ignore */ }
  clearAccountData();
  renderAccountBar();
  showToast('Signed out', 'success');
}

function showMyPosts() {
  showToast('My Posts feature coming soon!', 'info');
}

function showForgotPassword() {
  const content = document.getElementById('account-modal-content');
  if (!content) return;
  content.innerHTML = `
    <div>
      <h4 style="margin-bottom:12px;font-size:.95rem">Reset Your Password</h4>
      <p style="font-size:.82rem;color:#6b7280;margin-bottom:12px">Step 1: Enter your email to get a reset token.</p>
      <div style="margin-bottom:10px">
        <label style="font-size:0.85rem;font-weight:600">Email</label>
        <input id="reset-email" class="form-input" type="email" placeholder="you@example.com" style="margin-top:4px">
      </div>
      <div id="reset-error" style="color:#ef4444;font-size:0.82rem;margin-bottom:8px;display:none"></div>
      <button onclick="submitResetRequest()" class="btn btn-primary" style="width:100%">Get Reset Token</button>
      <div style="text-align:center;margin-top:10px">
        <button onclick="switchAccountTab('login')" style="background:none;border:none;color:#6C3CE1;cursor:pointer;font-size:.82rem">Back to Login</button>
      </div>
    </div>
  `;
}

async function submitResetRequest() {
  const email = (document.getElementById('reset-email').value || '').trim();
  const errEl = document.getElementById('reset-error');
  errEl.style.display = 'none';
  if (!email) {
    errEl.textContent = 'Please enter your email.';
    errEl.style.display = 'block';
    return;
  }
  try {
    const res = await fetch('/api/accounts/reset-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json().catch(() => ({}));
    const content = document.getElementById('account-modal-content');
    if (!content) return;
    if (data.token) {
      content.innerHTML = `
        <div>
          <h4 style="margin-bottom:10px">Your Reset Token</h4>
          <p style="font-size:.82rem;color:#6b7280;margin-bottom:10px">Copy this token now — it expires in 1 hour.</p>
          <div class="reset-token-box">${escHtml(data.token)}</div>
          <p style="font-size:.78rem;color:#6b7280;margin:10px 0">Keep it safe. Use it on the next screen.</p>
          <button onclick="showResetConfirm('${escHtml(email).replace(/'/g,"\\'")}', '${escHtml(data.token).replace(/'/g,"\\'")}');" class="btn btn-primary" style="width:100%;margin-top:8px">I've Copied It — Continue</button>
        </div>
      `;
    } else {
      // Account not found (but we don't reveal that explicitly)
      content.innerHTML = `
        <div style="text-align:center">
          <p style="margin-bottom:14px;font-size:.88rem">If that email is registered, a reset token was generated. Check this page.</p>
          <button onclick="switchAccountTab('login')" class="btn btn-primary">Back to Login</button>
        </div>
      `;
    }
  } catch (e) {
    const errEl = document.getElementById('reset-error');
    if (errEl) {
      errEl.textContent = 'Request failed. Please try again.';
      errEl.style.display = 'block';
    }
  }
}

function showResetConfirm(email, token) {
  const content = document.getElementById('account-modal-content');
  if (!content) return;
  content.innerHTML = `
    <div>
      <h4 style="margin-bottom:10px">Step 2: Set New Password</h4>
      <div style="margin-bottom:10px">
        <label style="font-size:0.85rem;font-weight:600">Email</label>
        <input id="rc-email" class="form-input" type="email" value="${escHtml(email)}" style="margin-top:4px">
      </div>
      <div style="margin-bottom:10px">
        <label style="font-size:0.85rem;font-weight:600">Reset Token</label>
        <input id="rc-token" class="form-input" value="${escHtml(token)}" style="margin-top:4px;font-family:monospace">
      </div>
      <div style="margin-bottom:14px">
        <label style="font-size:0.85rem;font-weight:600">New Password (min 8 chars)</label>
        <input id="rc-password" class="form-input" type="password" placeholder="New password" style="margin-top:4px">
      </div>
      <div id="rc-error" style="color:#ef4444;font-size:0.82rem;margin-bottom:8px;display:none"></div>
      <button onclick="submitResetConfirm()" class="btn btn-primary" style="width:100%">Reset Password</button>
    </div>
  `;
}

async function submitResetConfirm() {
  const email = (document.getElementById('rc-email').value || '').trim();
  const token = (document.getElementById('rc-token').value || '').trim();
  const new_password = document.getElementById('rc-password').value || '';
  const errEl = document.getElementById('rc-error');
  errEl.style.display = 'none';
  if (!email || !token || !new_password) {
    errEl.textContent = 'All fields are required.';
    errEl.style.display = 'block';
    return;
  }
  try {
    const res = await fetch('/api/accounts/reset-confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, token, new_password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw data;
    closeModal();
    showToast('Password reset! You can now log in.', 'success');
  } catch (e) {
    errEl.textContent = (e && e.error) ? e.error : 'Reset failed. Check your token and try again.';
    errEl.style.display = 'block';
  }
}

function openReportModal(contentType, contentId) {
  openModal(`
    <div style="max-width:320px;margin:0 auto">
      <h3 style="margin-bottom:12px">🚩 Report Content</h3>
      <p style="font-size:0.85rem;color:#6b7280;margin-bottom:14px">Help keep CampusConnect safe by reporting inappropriate content.</p>
      <div style="margin-bottom:12px">
        <label style="font-size:0.85rem;font-weight:600">Reason</label>
        <select id="report-reason" class="form-input" style="margin-top:4px">
          <option value="Spam">Spam</option>
          <option value="Inappropriate content">Inappropriate content</option>
          <option value="Misinformation">Misinformation</option>
          <option value="Other">Other</option>
        </select>
      </div>
      <div id="report-error" style="color:#ef4444;font-size:0.82rem;margin-bottom:8px;display:none"></div>
      <button onclick="submitReport('${escHtml(contentType)}', ${contentId})" class="btn btn-primary" style="width:100%">Submit Report</button>
    </div>
  `);
}

async function submitReport(contentType, contentId) {
  const reason = document.getElementById('report-reason').value;
  const errEl = document.getElementById('report-error');
  errEl.style.display = 'none';
  try {
    await fetch('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_type: contentType, content_id: contentId, reason })
    });
    closeModal();
    showToast('Report submitted. Thank you!', 'success');
  } catch(e) {
    errEl.textContent = 'Failed to submit report. Please try again.';
    errEl.style.display = 'block';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  renderAccountBar();
});
