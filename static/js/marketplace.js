let marketPage = 1;
let marketPages = 1;

async function renderMarketplace() {
  marketPage = 1;
  const mc = document.getElementById('main-content');
  mc.innerHTML = '<div class="spinner"></div>';
  await loadMarketItems(true);
}

async function loadMarketItems(reset) {
  const mc = document.getElementById('main-content');
  try {
    const data = await api('GET', `/api/marketplace?page=${marketPage}`);
    marketPages = data.pages || 1;
    const withAds = injectAds(data.items);
    let html = reset ? '<div class="section-header"><h2 class="section-title">&#128722; Marketplace</h2></div>' : mc.innerHTML.replace(/<button[^>]*load-more[^>]*>[^<]*<\/button>/, '');
    if (!data.items.length && reset) {
      mc.innerHTML = html + '<div class="empty-state"><div class="empty-icon">&#128722;</div><p>No listings yet. List something!</p></div>';
      return;
    }
    withAds.forEach(item => {
      if (item.type === 'ad') { html += renderAdBanner(item); return; }
      html += renderMarketItem(item);
    });
    if (marketPage < marketPages) {
      html += `<button class="load-more-btn" onclick="marketPage++;loadMarketItems(false)">Load more</button>`;
    }
    mc.innerHTML = html;
  } catch(e) {
    mc.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128565;</div><p>Could not load marketplace.</p></div>';
  }
}

function renderMarketItem(m) {
  return `<div class="card" data-item-id="${m.id}" data-item-title="${escHtml(m.title)}" data-item-desc="${escHtml(m.description)}" data-item-price="${escHtml(m.price || '')}" data-item-cat="${escHtml(m.category)}">
    ${m.image_path ? `<img class="card-image" src="${escHtml(m.image_path)}" alt="">` : ''}
    <div class="card-title">${escHtml(m.title)}</div>
    <div class="card-body">${escHtml(m.description)}</div>
    ${m.price ? `<div class="card-price">KSh ${escHtml(m.price)}</div>` : '<div class="card-price" style="color:var(--text-muted);font-size:0.85rem">Price negotiable</div>'}
    <div class="card-meta"><span class="badge badge-accent">${escHtml(m.category)}</span></div>
    <div class="contact-row">&#128222; ${escHtml(m.poster_contact)} &bull; ${escHtml(m.poster_name)} &bull; ${timeAgo(m.created_at)}</div>
    <div class="card-actions"><button class="btn-edit" onclick="editMarketItem(${m.id})">&#9998;&#65039; Edit</button></div>
  </div>`;
}

function openMarketplaceForm() {
  openModal(`<div class="form-title">&#128722; List an Item</div>
    <div class="form-group"><label>Your Name *</label><input type="text" id="mf-name" placeholder="e.g. Jane Kamau"></div>
    <div class="form-group"><label>Contact/Phone *</label><input type="text" id="mf-contact" placeholder="e.g. 0712345678"></div>
    <div class="form-group"><label>Title *</label><input type="text" id="mf-title" placeholder="e.g. Engineering Textbook"></div>
    <div class="form-group"><label>Description *</label><textarea id="mf-desc" placeholder="Describe the item..."></textarea></div>
    <div class="form-group"><label>Price <span class="optional-label">(leave blank if negotiable)</span></label><input type="text" id="mf-price" placeholder="e.g. 500"></div>
    <div class="form-group"><label>Category</label><select id="mf-cat"><option>Books</option><option>Electronics</option><option>Accessories</option><option>Accommodation</option><option>Other</option></select></div>
    <div class="form-group"><label>Photo <span class="optional-label">(optional, max 5MB)</span></label><input type="file" id="mf-image" accept="image/jpeg,image/png,image/webp"></div>
    <button class="btn-primary" onclick="submitMarketItem()">List Item</button>`);
}

async function submitMarketItem() {
  const name = document.getElementById('mf-name').value.trim();
  const contact = document.getElementById('mf-contact').value.trim();
  const title = document.getElementById('mf-title').value.trim();
  const desc = document.getElementById('mf-desc').value.trim();
  const price = document.getElementById('mf-price').value.trim();
  const cat = document.getElementById('mf-cat').value;
  const imageFile = document.getElementById('mf-image').files[0];
  if (!name || !contact || !title || !desc) { showToast('Name, contact, title and description are required.', 'error'); return; }
  const fd = new FormData();
  fd.append('poster_name', name);
  fd.append('poster_contact', contact);
  fd.append('title', title);
  fd.append('description', desc);
  fd.append('price', price);
  fd.append('category', cat);
  if (imageFile) fd.append('image', imageFile);
  try {
    const created = await api('POST', '/api/marketplace', fd, true, idempotencyHeaders('marketplace'));
    rememberContentOwnerToken('marketplace', created.id, created.owner_token);
    completeIdempotentSubmission('marketplace');
    closeModal();
    showToast('Item listed!', 'success');
    renderMarketplace();
  } catch(e) { showToast('Could not list item. ' + (e.data && e.data.error ? e.data.error : ''), 'error'); }
}

function editMarketItem(mid) {
  const card = document.querySelector(`.card[data-item-id="${mid}"]`);
  const title = card ? card.dataset.itemTitle : '';
  const desc = card ? card.dataset.itemDesc : '';
  const price = card ? card.dataset.itemPrice : '';
  const cat = card ? card.dataset.itemCat : 'Other';
  const ownerToken = getContentOwnerToken('marketplace', mid) || prompt('Enter this listing\'s edit token:');
  if (!ownerToken) return;
  openModal(`<div class="form-title">&#9998;&#65039; Edit Listing</div>
    <input type="hidden" id="edit-owner-token" value="${escHtml(ownerToken)}">
    <div class="form-group"><label>Title *</label><input type="text" id="em-title" value="${escHtml(title)}"></div>
    <div class="form-group"><label>Description *</label><textarea id="em-desc">${escHtml(desc)}</textarea></div>
    <div class="form-group"><label>Price <span class="optional-label">(leave blank if negotiable)</span></label><input type="text" id="em-price" value="${escHtml(price)}"></div>
    <div class="form-group"><label>Category</label><select id="em-cat"><option${cat==='Books'?' selected':''}>Books</option><option${cat==='Electronics'?' selected':''}>Electronics</option><option${cat==='Accessories'?' selected':''}>Accessories</option><option${cat==='Accommodation'?' selected':''}>Accommodation</option><option${cat==='Other'?' selected':''}>Other</option></select></div>
    <button class="btn-primary" onclick="submitEditMarket(${mid})">Save Changes</button>`);
}

async function submitEditMarket(mid) {
  const owner_token = document.getElementById('edit-owner-token').value;
  const title = document.getElementById('em-title').value.trim();
  const description = document.getElementById('em-desc').value.trim();
  const price = document.getElementById('em-price').value.trim();
  const category = document.getElementById('em-cat').value;
  if (!title || !description) { showToast('Title and description are required.', 'error'); return; }
  try {
    await api('PUT', `/api/marketplace/${mid}`, { owner_token, title, description, price, category });
    closeModal();
    showToast('Listing updated!', 'success');
    renderMarketplace();
  } catch(e) {
    if (e.status === 403) { showToast('The edit token is missing or invalid.', 'error'); }
    else { showToast('Could not update listing.', 'error'); }
  }
}
