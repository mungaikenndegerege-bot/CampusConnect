async function renderEvents() {
  const content = document.getElementById('main-content');
  content.innerHTML = '<div class="spinner"></div>';
  try {
    const data = await api('GET', '/api/events');
    let html = '<div class="section-header"><h2 class="section-title">&#128197; Campus Events</h2></div>';
    if (!data.items.length) {
      html += '<div class="empty-state"><div class="empty-icon">&#128197;</div><p>No events posted yet.</p></div>';
    }
    data.items.forEach(event => {
      html += `<article class="card">
        ${event.poster_url ? `<img class="card-image" src="${escHtml(event.poster_url)}" alt="">` : ''}
        <h3 class="card-title">${escHtml(event.title)}</h3>
        <p class="card-body">${escHtml(event.description)}</p>
        <div class="card-meta"><span class="badge">${escHtml(new Date(event.starts_at).toLocaleString())}</span><span class="badge badge-accent">${escHtml(event.venue)}</span></div>
        <div class="contact-row">Organized by ${escHtml(event.poster_name)}${event.contact ? ` · ${escHtml(event.contact)}` : ''}</div>
        ${getContentOwnerToken('event', event.id) ? `<button class="btn-edit" onclick="deactivateEvent(${event.id})">Remove my event</button>` : ''}
        <div class="reactions-bar">
          <button class="reaction-btn" data-type="like" data-target="event" data-id="${event.id}">&#128077; Like</button>
          <button class="reaction-btn" data-type="celebrate" data-target="event" data-id="${event.id}">&#127881; Celebrate</button>
          <button class="reaction-btn" data-type="support" data-target="event" data-id="${event.id}">&#10084; Support</button>
        </div>
      </article>`;
    });
    content.innerHTML = html;
  } catch(e) {
    content.innerHTML = '<div class="empty-state"><p>Could not load events.</p></div>';
  }
}

function openEventForm() {  openModal(`<h2 class="form-title">Create a campus event</h2>
    <div class="form-group"><label>Your name *</label><input id="event-name" maxlength="100"></div>
    <div class="form-group"><label>Title *</label><input id="event-title" maxlength="200"></div>
    <div class="form-group"><label>Description *</label><textarea id="event-description" maxlength="5000"></textarea></div>
    <div class="form-group"><label>Venue *</label><input id="event-venue" maxlength="200"></div>
    <div class="form-group"><label>Starts *</label><input id="event-starts" type="datetime-local"></div>
    <div class="form-group"><label>Ends</label><input id="event-ends" type="datetime-local"></div>
    <div class="form-group"><label>Contact</label><input id="event-contact" maxlength="100"></div>
    <div class="form-group"><label>Poster (optional, 5 MB max)</label><input id="event-poster" type="file" accept="image/jpeg,image/png,image/webp"></div>
    <button class="btn-primary" onclick="submitEvent()">Publish Event</button>`);
}

async function submitEvent() {
  const startsAt = document.getElementById('event-starts').value;
  const endsAt = document.getElementById('event-ends').value;
  const form = new FormData();
  form.append('poster_name', document.getElementById('event-name').value.trim());
  form.append('title', document.getElementById('event-title').value.trim());
  form.append('description', document.getElementById('event-description').value.trim());
  form.append('venue', document.getElementById('event-venue').value.trim());
  form.append('starts_at', startsAt ? new Date(startsAt).toISOString() : '');
  if (endsAt) form.append('ends_at', new Date(endsAt).toISOString());
  form.append('contact', document.getElementById('event-contact').value.trim());
  const poster = document.getElementById('event-poster').files[0];
  if (poster) form.append('poster', poster);
  try {
    const created = await api('POST', '/api/events', form, true, idempotencyHeaders('event'));
    rememberContentOwnerToken('event', created.id, created.owner_token);
    completeIdempotentSubmission('event');
    closeModal();
    showToast('Event published.', 'success');
    renderEvents();
  } catch(e) {
    showToast(e.data && e.data.error ? e.data.error : 'Could not publish event.', 'error');
  }
}

async function deactivateEvent(eventId) {
  if (!confirm('Remove this event?')) return;
  try {
    await api('DELETE', `/api/events/${eventId}`, {
      owner_token: getContentOwnerToken('event', eventId)
    });
    showToast('Event removed.', 'success');
    renderEvents();
  } catch(e) {
    showToast('Could not remove the event.', 'error');
  }
}

async function renderOpportunities() {
  const content = document.getElementById('main-content');
  content.innerHTML = '<div class="spinner"></div>';
  try {
    const data = await api('GET', '/api/opportunities');
    let html = '<div class="section-header"><h2 class="section-title">&#128188; Jobs & Internships</h2></div>';
    if (!data.items.length) {
      html += '<div class="empty-state"><div class="empty-icon">&#128188;</div><p>No opportunities posted yet.</p></div>';
    }
    data.items.forEach(item => {
      html += `<article class="card">
        <span class="badge badge-accent">${escHtml(item.opportunity_type)}</span>
        <h3 class="card-title">${escHtml(item.title)}</h3>
        <div class="contact-row">${escHtml(item.organization)}${item.location ? ` · ${escHtml(item.location)}` : ''}</div>
        <p class="card-body">${escHtml(item.description)}</p>
        ${item.closes_at ? `<div class="post-time">Apply by ${escHtml(new Date(item.closes_at).toLocaleDateString())}</div>` : ''}
        ${item.application_url ? `<a class="ad-link" href="${escHtml(item.application_url)}" target="_blank" rel="noopener noreferrer">Application details</a>` : ''}
        <div class="reactions-bar">
          <button class="reaction-btn" data-type="like" data-target="opportunity" data-id="${item.id}">&#128077; Like</button>
          <button class="reaction-btn" data-type="celebrate" data-target="opportunity" data-id="${item.id}">&#127881; Celebrate</button>
          <button class="reaction-btn" data-type="support" data-target="opportunity" data-id="${item.id}">&#10084; Support</button>
        </div>
      </article>`;
    });
    content.innerHTML = html;
  } catch(e) {
    content.innerHTML = '<div class="empty-state"><p>Could not load opportunities.</p></div>';
  }
}

function openOpportunityForm() {
  openModal(`<h2 class="form-title">Post a job or internship</h2>
    <div class="form-group"><label>Your name *</label><input id="opp-name" maxlength="100"></div>
    <div class="form-group"><label>Type *</label><select id="opp-type"><option value="internship">Internship</option><option value="job">Job</option><option value="scholarship">Scholarship</option><option value="attachment">Attachment</option></select></div>
    <div class="form-group"><label>Title *</label><input id="opp-title" maxlength="200"></div>
    <div class="form-group"><label>Organization *</label><input id="opp-organization" maxlength="200"></div>
    <div class="form-group"><label>Description *</label><textarea id="opp-description" maxlength="5000"></textarea></div>
    <div class="form-group"><label>Location</label><input id="opp-location" maxlength="200"></div>
    <div class="form-group"><label>Application URL (HTTPS)</label><input id="opp-url" type="url" maxlength="500" placeholder="https://"></div>
    <div class="form-group"><label>Closing date/time</label><input id="opp-closes" type="datetime-local"></div>
    <button class="btn-primary" onclick="submitOpportunity()">Publish Opportunity</button>`);
}

async function submitOpportunity() {
  const closesAt = document.getElementById('opp-closes').value;
  const data = {
    poster_name: document.getElementById('opp-name').value.trim(),
    opportunity_type: document.getElementById('opp-type').value,
    title: document.getElementById('opp-title').value.trim(),
    organization: document.getElementById('opp-organization').value.trim(),
    description: document.getElementById('opp-description').value.trim(),
    location: document.getElementById('opp-location').value.trim(),
    application_url: document.getElementById('opp-url').value.trim(),
    closes_at: closesAt ? new Date(closesAt).toISOString() : null
  };
  try {
    const created = await api('POST', '/api/opportunities', data, false, idempotencyHeaders('opportunity'));
    rememberContentOwnerToken('opportunity', created.id, created.owner_token);
    completeIdempotentSubmission('opportunity');
    closeModal();
    showToast('Opportunity published.', 'success');
    renderOpportunities();
  } catch(e) {
    showToast(e.data && e.data.error ? e.data.error : 'Could not publish opportunity.', 'error');
  }
}
