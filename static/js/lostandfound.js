let lfPage = 1;
let lfPages = 1;

async function renderLostFound() {
  lfPage = 1;
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  await loadLFItems(true);
}

async function loadLFItems(reset) {
  const mc = document.getElementById('main-content');
  try {
    const data = await api('GET', `/api/lostandfound?page=${lfPage}`);
    lfPages = data.pages || 1;
    let html = reset ? '<div class="section-header"><h2 class="section-title">&#128269; Lost &amp; Found</h2></div>' : mc.innerHTML.replace(/<button[^>]*load-more[^>]*>[^<]*<\/button>/, '');
    if (!data.items.length && reset) {
      mc.innerHTML = html + '<div class="empty-state"><div class="empty-icon">&#128269;</div><p>Nothing reported yet.</p></div>';
      return;
    }
    data.items.forEach(item => { html += renderLFItem(item); });
    if (lfPage < lfPages) {
      html += `<button class="load-more-btn" onclick="lfPage++;loadLFItems(false)">Load more</button>`;
    }
    mc.innerHTML = html;
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load items.</p></div>';
  }
}

function renderLFItem(l) {
  const cls = l.item_type === 'lost' ? 'badge-red' : 'badge-green';
  const label = l.item_type === 'lost' ? '&#128531; Lost' : '&#128515; Found';
  return `<div class="card" data-lf-id="${l.id}" data-lf-title="${escHtml(l.title)}" data-lf-desc="${escHtml(l.description)}" data-lf-location="${escHtml(l.location)}" data-lf-type="${escHtml(l.item_type)}">
    <div class="card-meta" style="margin-bottom:8px"><span class="badge ${cls}">${label}</span></div>
    <div class="card-title">${escHtml(l.title)}</div>
    <div class="card-body">${escHtml(l.description)}</div>
    <div class="contact-row">&#128205; ${escHtml(l.location)}</div>
    <div class="contact-row">&#128222; ${escHtml(l.poster_contact)} &bull; ${escHtml(l.poster_name)} &bull; ${timeAgo(l.created_at)}</div>
    <div class="card-actions"><button class="btn-edit" onclick="editLFItem(${l.id})">&#9998;&#65039; Edit</button></div>
  </div>`;
}

function openLostFoundForm() {
  openModal(`<div class="form-title">&#128269; Report Lost / Found</div>
    <div class="form-group"><label>Your Name *</label><input type="text" id="lf-name" placeholder="e.g. Ali Hassan"></div>
    <div class="form-group"><label>Contact/Phone *</label><input type="text" id="lf-contact" placeholder="e.g. 0712345678"></div>
    <div class="form-group"><label>Type *</label><select id="lf-type"><option value="lost">I Lost Something</option><option value="found">I Found Something</option></select></div>
    <div class="form-group"><label>Item Title *</label><input type="text" id="lf-title" placeholder="e.g. Blue backpack"></div>
    <div class="form-group"><label>Description *</label><textarea id="lf-desc" placeholder="Describe the item..."></textarea></div>
    <div class="form-group"><label>Location *</label><input type="text" id="lf-location" placeholder="e.g. Library Block B"></div>
    <button class="btn-primary" onclick="submitLFItem()">Submit Report</button>`);
}

async function submitLFItem() {
  const name = document.getElementById('lf-name').value.trim();
  const contact = document.getElementById('lf-contact').value.trim();
  const type = document.getElementById('lf-type').value;
  const title = document.getElementById('lf-title').value.trim();
  const desc = document.getElementById('lf-desc').value.trim();
  const location = document.getElementById('lf-location').value.trim();
  if (!name || !contact || !title || !desc || !location) { showToast('All fields are required.', 'error'); return; }
  try {
    const created = await api('POST', '/api/lostandfound', { poster_name: name, poster_contact: contact, item_type: type, title, description: desc, location }, false, idempotencyHeaders('lostandfound'));
    rememberContentOwnerToken('lostandfound', created.id, created.owner_token);
    completeIdempotentSubmission('lostandfound');
    closeModal();
    showToast('Report submitted!', 'success');
    renderLostFound();
  } catch(e) { showToast('Could not submit report.', 'error'); }
}

function editLFItem(lid) {
  const card = document.querySelector(`.card[data-lf-id="${lid}"]`);
  const title = card ? card.dataset.lfTitle : '';
  const desc = card ? card.dataset.lfDesc : '';
  const location = card ? card.dataset.lfLocation : '';
  const itype = card ? card.dataset.lfType : 'lost';
  const ownerToken = getContentOwnerToken('lostandfound', lid) || prompt('Enter this report\'s edit token:');
  if (!ownerToken) return;
  openModal(`<div class="form-title">&#9998;&#65039; Edit Report</div>
    <input type="hidden" id="edit-owner-token" value="${escHtml(ownerToken)}">
    <div class="form-group"><label>Type *</label><select id="el-type"><option value="lost"${itype==='lost'?' selected':''}>I Lost Something</option><option value="found"${itype==='found'?' selected':''}>I Found Something</option></select></div>
    <div class="form-group"><label>Item Title *</label><input type="text" id="el-title" value="${escHtml(title)}"></div>
    <div class="form-group"><label>Description *</label><textarea id="el-desc">${escHtml(desc)}</textarea></div>
    <div class="form-group"><label>Location *</label><input type="text" id="el-location" value="${escHtml(location)}"></div>
    <button class="btn-primary" onclick="submitEditLF(${lid})">Save Changes</button>`);
}

async function submitEditLF(lid) {
  const owner_token = document.getElementById('edit-owner-token').value;
  const title = document.getElementById('el-title').value.trim();
  const description = document.getElementById('el-desc').value.trim();
  const location = document.getElementById('el-location').value.trim();
  const item_type = document.getElementById('el-type').value;
  if (!title || !description || !location) { showToast('All fields are required.', 'error'); return; }
  try {
    await api('PUT', `/api/lostandfound/${lid}`, { owner_token, title, description, location, item_type });
    closeModal();
    showToast('Report updated!', 'success');
    renderLostFound();
  } catch(e) {
    if (e.status === 403) { showToast('The edit token is missing or invalid.', 'error'); }
    else { showToast('Could not update report.', 'error'); }
  }
}
