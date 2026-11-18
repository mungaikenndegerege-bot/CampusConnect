async function renderAnnouncements() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  try {
    const items = await api('GET', '/api/announcements');
    let html = '<div class="section-header"><h2 class="section-title">&#128226; Announcements</h2></div>';
    html += '<div style="background:#f0f4ff;border:1px solid #c7d2fe;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:0.88rem;color:#3730a3">&#128226; Official announcements are posted by CampusConnect administrators.</div>';
    if (!items.length) {
      html += '<div class="empty-state"><div class="empty-icon">&#128226;</div><p>No announcements yet.</p></div>';
      mc.innerHTML = html;
      return;
    }
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
