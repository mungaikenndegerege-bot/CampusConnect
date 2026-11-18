let communityPage = 1;
let communityPages = 1;

async function renderCommunity() {
  communityPage = 1;
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  await loadCommunityPosts(true);
}

async function loadCommunityPosts(reset) {
  const mc = document.getElementById('main-content');
  try {
    const data = await api('GET', `/api/posts?page=${communityPage}`);
    communityPages = data.pages || 1;
    const withAds = injectAds(data.items);
    let html = reset ? '<div class="section-header"><h2 class="section-title">&#128172; Community</h2></div>' : (mc.querySelector('.section-header') ? mc.innerHTML.replace(/<button[^>]*load-more[^>]*>[^<]*<\/button>/, '') : '');
    if (!data.items.length && reset) {
      mc.innerHTML = html + '<div class="empty-state"><div class="empty-icon">&#128172;</div><p>No posts yet. Start the conversation!</p></div>';
      return;
    }
    withAds.forEach(item => {
      if (item.type === 'ad') { html += renderAdBanner(item); return; }
      html += renderCommunityCard(item);
    });
    if (communityPage < communityPages) {
      html += `<button class="load-more-btn" onclick="communityPage++;loadCommunityPosts(false)">Load more</button>`;
    }
    mc.innerHTML = html;
    // Attach comment toggles
    mc.querySelectorAll('.toggle-comments').forEach(btn => {
      btn.addEventListener('click', () => toggleComments(btn));
    });
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load posts.</p></div>';
  }
}

function renderCommunityCard(p) {
  return `<div class="card" data-post-id="${p.id}" data-post-title="${escHtml(p.title)}" data-post-body="${escHtml(p.body)}" data-post-topic="${escHtml(p.topic || 'General')}">
    <div class="card-header">
      <div class="avatar">${escHtml(avatarLetter(p.poster_name))}</div>
      <div class="poster-info"><div class="poster-name">${escHtml(p.poster_name)}</div><div class="post-time">${timeAgo(p.created_at)}</div></div>
    </div>
    <div class="card-title">${escHtml(p.title)}</div>
    <div class="card-body">${escHtml(p.body)}</div>
    ${p.file_url && p.file_type === 'image' ? `<img src="${escHtml(p.file_url)}" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;margin-top:8px">` : ''}
    ${p.file_url && p.file_type === 'file' ? `<a href="${escHtml(p.file_url)}" target="_blank" style="color:#6C3CE1;font-size:.85rem">&#128196; View Attachment</a>` : ''}
    <div class="card-meta"><span class="badge">${escHtml(p.topic || 'General')}</span></div>
    <div class="card-actions">
      <button class="btn-edit" onclick="editPost(${p.id})">&#9998;&#65039; Edit</button>
      <button class="toggle-comments" data-id="${p.id}" data-count="${p.comment_count}">${p.comment_count > 0 ? `View ${p.comment_count} comment${p.comment_count !== 1 ? 's' : ''}` : 'Add a comment'}</button>
    </div>
    <div class="comments-section" id="comments-${p.id}" style="display:none"></div>
  </div>`;
}

async function toggleComments(btn) {
  const pid = btn.dataset.id;
  const section = document.getElementById('comments-' + pid);
  if (section.style.display !== 'none') { section.style.display = 'none'; return; }
  section.style.display = 'block';
  section.innerHTML = '<div class="spinner"></div>';
  try {
    const comments = await api('GET', `/api/posts/${pid}/comments`);
    let html = '';
    comments.forEach(c => {
      html += `<div class="comment"><span class="comment-name">${escHtml(c.poster_name)}</span><span class="comment-time"> &bull; ${timeAgo(c.created_at)}</span><div class="comment-body">${escHtml(c.body)}</div></div>`;
    });
    html += `<div class="add-comment-form">
      <input type="text" placeholder="Your name" id="cn-name-${pid}">
      <textarea placeholder="Write a comment..." id="cn-body-${pid}" rows="2"></textarea>
      <button onclick="submitComment(${pid})">Post Comment</button>
    </div>`;
    section.innerHTML = html;
  } catch(e) {
    section.innerHTML = '<p style="color:#c62828;font-size:0.85rem">Could not load comments.</p>';
  }
}

async function submitComment(pid) {
  const name = document.getElementById('cn-name-' + pid).value.trim();
  const body = document.getElementById('cn-body-' + pid).value.trim();
  if (!name || !body) { showToast('Please fill in name and comment.', 'error'); return; }
  try {
    await api('POST', `/api/posts/${pid}/comments`, { poster_name: name, body });
    showToast('Comment posted!', 'success');
    // Reload comments
    const btn = document.querySelector(`.toggle-comments[data-id="${pid}"]`);
    if (btn) { const section = document.getElementById('comments-' + pid); section.style.display = 'none'; btn.click(); }
  } catch(e) { showToast('Could not post comment.', 'error'); }
}

function openCommunityForm() {
  openModal(`<div class="form-title">&#128172; New Post</div>
    <div class="form-group"><label>Your Name *</label><input type="text" id="cf-name" placeholder="e.g. John Doe"></div>
    <div class="form-group"><label>Contact/Phone <span class="optional-label">(optional)</span></label><input type="text" id="cf-contact" placeholder="e.g. 0712345678"></div>
    <div class="form-group"><label>Topic</label><select id="cf-topic"><option>General</option><option>Academic</option><option>Study Groups</option><option>Q&amp;A</option></select></div>
    <div class="form-group"><label>Title *</label><input type="text" id="cf-title" placeholder="Post title"></div>
    <div class="form-group"><label>Message *</label><textarea id="cf-body" placeholder="What's on your mind?"></textarea></div>
    <div class="form-group"><label style="font-size:.8rem;color:#9ca3af;margin-top:4px">&#128206; Attach image or file (optional, max 10MB)<input type="file" id="post-attachment" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx" style="margin-top:4px;display:block"></label></div>
    <button class="btn-primary" onclick="submitCommunityPost()">Post</button>`);
}

async function submitCommunityPost() {
  const name = document.getElementById('cf-name').value.trim();
  const contact = document.getElementById('cf-contact').value.trim();
  const topic = document.getElementById('cf-topic').value;
  const title = document.getElementById('cf-title').value.trim();
  const body = document.getElementById('cf-body').value.trim();
  if (!name || !title || !body) { showToast('Name, title and message are required.', 'error'); return; }
  const fileInput = document.getElementById('post-attachment');
  const file = fileInput && fileInput.files && fileInput.files[0];
  try {
    if (file) {
      const fd = new FormData();
      fd.append('poster_name', name);
      fd.append('poster_contact', contact);
      fd.append('topic', topic);
      fd.append('title', title);
      fd.append('body', body);
      fd.append('attachment', file);
      await api('POST', '/api/posts', fd, true);
    } else {
      await api('POST', '/api/posts', { poster_name: name, poster_contact: contact, topic, title, body });
    }
    closeModal();
    showToast('Post published!', 'success');
    renderCommunity();
  } catch(e) { showToast('Could not publish post.', 'error'); }
}

function editPost(pid) {
  const card = document.querySelector(`.card[data-post-id="${pid}"]`);
  const title = card ? card.dataset.postTitle : '';
  const body = card ? card.dataset.postBody : '';
  const topic = card ? card.dataset.postTopic : 'General';
  const name = prompt('Enter your name to edit:');
  if (!name) return;
  openModal(`<div class="form-title">&#9998;&#65039; Edit Post</div>
    <div class="form-group"><label>Topic</label><select id="ep-topic"><option${topic==='General'?' selected':''}>General</option><option${topic==='Academic'?' selected':''}>Academic</option><option${topic==='Study Groups'?' selected':''}>Study Groups</option><option${topic==='Q&A'?' selected':''}>Q&amp;A</option></select></div>
    <div class="form-group"><label>Title *</label><input type="text" id="ep-title" value="${escHtml(title)}"></div>
    <div class="form-group"><label>Message *</label><textarea id="ep-body">${escHtml(body)}</textarea></div>
    <button class="btn-primary" onclick="submitEditPost(${pid}, '${escHtml(name)}')">Save Changes</button>`);
}

async function submitEditPost(pid, poster_name) {
  const title = document.getElementById('ep-title').value.trim();
  const body = document.getElementById('ep-body').value.trim();
  const topic = document.getElementById('ep-topic').value;
  if (!title || !body) { showToast('Title and message are required.', 'error'); return; }
  try {
    await api('PUT', `/api/posts/${pid}`, { poster_name, title, body, topic });
    closeModal();
    showToast('Post updated!', 'success');
    renderCommunity();
  } catch(e) {
    if (e.status === 403) { showToast('Name does not match the original poster', 'error'); }
    else { showToast('Could not update post.', 'error'); }
  }
}
