async function renderAnnouncements() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  try {
    const items = await api('GET', '/api/announcements');
    if (!items.length) {
      mc.innerHTML = '<div class="section-header"><h2 class="section-title">&#128226; Announcements</h2></div><div class="empty-state"><div class="empty-icon">&#128226;</div><p>No announcements yet.</p></div>';
      return;
    }
    let html = '<div class="section-header"><h2 class="section-title">&#128226; Announcements</h2></div>';
    items.forEach(a => {
      html += `<div class="card announcement-card">
        ${a.pinned ? '<span class="pinned-badge">&#128204; Pinned</span>' : ''}
        <div class="card-title">${escHtml(a.title)}</div>
        <div class="card-body">${escHtml(a.body)}</div>
        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:8px">${timeAgo(a.created_at)}</div>
      </div>`;
    });
    mc.innerHTML = html;
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load announcements.</p></div>';
  }
}
