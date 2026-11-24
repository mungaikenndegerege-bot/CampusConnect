const featureCatalog = [
  { kind: 'jobs', icon: '\uD83D\uDCBC', title: 'Jobs & Attachments', description: 'Find internships, attachments, and work opportunities.' },
  { kind: 'accommodation', icon: '\uD83C\uDFE0', title: 'Accommodation', description: 'Discover hostels, rooms, and potential roommates.' },
  { kind: 'resources', icon: '\uD83D\uDCD6', title: 'Notes & Resources', description: 'Share revision notes, study guides, and learning links.' },
  { kind: 'deals', icon: '\uD83C\uDFF7\uFE0F', title: 'Campus Deals', description: 'Explore discounts and offers for students.' },
  { kind: 'events', icon: '\uD83D\uDCC5', title: 'Events Calendar', description: 'Find campus meetups, talks, and activities.' },
  { kind: 'polls', icon: '\uD83D\uDCCA', title: 'Student Polls', description: 'Ask a question and see what the community thinks.' },
  { kind: 'confessions', icon: '\uD83D\uDCAC', title: 'Anonymous Confessions', description: 'Share a thought without attaching your name.' },
  { kind: 'lost_documents', icon: '\uD83E\uDDC3', title: 'Lost Documents', description: 'Help return lost IDs and documents without posting contact details.' },
  { kind: 'services', icon: '\uD83D\uDEE0\uFE0F', title: 'Buy & Sell Services', description: 'Discover services offered by students and local businesses.' },
  { kind: 'study-assistant', icon: '\uD83E\uDDE0', title: 'AI Study Assistant', description: 'Get step-by-step explanations for study questions.' },
];

const featureFields = {
  jobs: [
    ['author_name', 'Your name', 'text', 'Your name'],
    ['category', 'Opportunity type', 'select', ['Job', 'Internship', 'Attachment', 'Graduate trainee', 'Volunteer']],
    ['location', 'Location', 'text', 'Town, county, or remote'],
    ['deadline', 'Application deadline', 'date'],
    ['contact', 'Application contact', 'text', 'Email or phone'],
    ['external_url', 'Application link', 'url', 'https://'],
  ],
  accommodation: [
    ['author_name', 'Your name', 'text', 'Your name'],
    ['category', 'Accommodation type', 'select', ['Hostel', 'Bedsitter', 'Shared room', 'Roommate wanted', 'Other']],
    ['location', 'Location', 'text', 'Near campus, town, county'],
    ['price', 'Rent / budget', 'text', 'e.g. KSh 8,000 per month'],
    ['contact', 'Contact', 'text', 'Email or phone'],
  ],
  resources: [
    ['author_name', 'Your name', 'text', 'Your name'],
    ['category', 'Resource type', 'select', ['Notes', 'Revision guide', 'Study group', 'Course material', 'Other']],
    ['external_url', 'Resource link', 'url', 'https://'],
  ],
  deals: [
    ['author_name', 'Your name / business', 'text', 'Your name or business'],
    ['category', 'Deal category', 'select', ['Food', 'Transport', 'Books', 'Technology', 'Other']],
    ['price', 'Offer / discount', 'text', 'e.g. 10% off'],
    ['location', 'Where to redeem', 'text', 'Location or online'],
    ['contact', 'Contact', 'text', 'Email or phone'],
    ['external_url', 'Offer link', 'url', 'https://'],
  ],
  events: [
    ['author_name', 'Organizer name', 'text', 'Name or organization'],
    ['event_date', 'Event date', 'date'],
    ['location', 'Location', 'text', 'Venue or online'],
    ['contact', 'Organizer contact', 'text', 'Email or phone'],
    ['external_url', 'Event / registration link', 'url', 'https://'],
  ],
  polls: [
    ['author_name', 'Your name (optional)', 'text', 'Community member'],
  ],
  confessions: [],
  lost_documents: [
    ['location', 'Where it was lost / found', 'text', 'General location only'],
    ['category', 'Document type', 'select', ['Student ID', 'National ID', 'Bank card', 'Certificate', 'Other']],
  ],
  services: [
    ['author_name', 'Your name / business', 'text', 'Your name or business'],
    ['category', 'Service category', 'select', ['Tutoring', 'Design', 'Repairs', 'Photography', 'Delivery', 'Other']],
    ['price', 'Price / rate', 'text', 'e.g. KSh 500 per hour'],
    ['location', 'Location', 'text', 'Town, county, or remote'],
    ['contact', 'Contact', 'text', 'Email or phone'],
    ['external_url', 'Website / portfolio', 'url', 'https://'],
  ],
};

function getFeature(kind) {
  return featureCatalog.find(feature => feature.kind === kind);
}

function renderFeatureGrid() {
  return `<div class="feature-grid home-feature-grid">${featureCatalog.map(feature => `
      <button class="feature-tile" type="button" data-feature-kind="${escHtml(feature.kind)}">
        <span class="feature-tile-icon" aria-hidden="true">${feature.icon}</span>
        <span class="feature-tile-title">${escHtml(feature.title)}</span>
        <span class="feature-tile-description">${escHtml(feature.description)}</span>
      </button>`).join('')}</div>`;
}

function wireFeatureGrid(main) {
  main.querySelectorAll('[data-feature-kind]').forEach(button => {
    button.addEventListener('click', () => renderFeatureKind(button.dataset.featureKind));
  });
}

function renderFeatureHub() {
  const main = document.getElementById('main-content');
  main.innerHTML = renderFeatureGrid();
  wireFeatureGrid(main);
}

function renderFeatureCard(item) {
  const feature = getFeature(item.kind);
  const author = item.kind === 'confessions' ? 'Anonymous' : item.author_name;
  const detail = [
    item.category,
    item.location,
    item.event_date ? `Date: ${item.event_date}` : '',
    item.deadline ? `Deadline: ${item.deadline}` : '',
    item.price,
  ].filter(Boolean);
  let extra = '';
  if (item.kind === 'polls') {
    const total = item.counts.reduce((sum, count) => sum + count, 0);
    extra = `<div class="feature-poll-options">${item.options.map((option, index) => {
      const votes = item.counts[index] || 0;
      const percentage = total ? Math.round((votes / total) * 100) : 0;
      return `<button type="button" class="feature-poll-option" data-poll-id="${item.id}" data-option-index="${index}">
        <span class="feature-poll-option-text">${escHtml(option)}</span>
        <span class="feature-poll-meter"><span style="width:${percentage}%"></span></span>
        <span class="feature-poll-count">${votes} vote${votes === 1 ? '' : 's'}${total ? ` \u00B7 ${percentage}%` : ''}</span>
      </button>`;
    }).join('')}</div>`;
  }
  if (item.external_url) {
    extra += `<a class="feature-external-link" href="${escHtml(item.external_url)}" target="_blank" rel="noopener noreferrer">Open link</a>`;
  }
  if (item.file_url && item.file_name) {
    extra += `<a class="feature-external-link feature-download-link" href="${escHtml(item.file_url)}?download=1" download="${escHtml(item.file_name)}">Download ${escHtml(item.file_name)}</a>`;
  }
  if (item.contact && item.kind !== 'lost_documents') {
    extra += `<p class="feature-contact">Contact: ${escHtml(item.contact)}</p>`;
  }
  const safetyNote = item.kind === 'lost_documents'
    ? '<p class="feature-safety-note">For your safety, never post ID numbers, card numbers, or photos that show sensitive details.</p>'
    : '';
  const pollCount = item.kind === 'polls'
    ? `<span class="badge">${item.counts.reduce((sum, count) => sum + count, 0)} votes</span>`
    : '';
  return `<article class="card feature-card">
    <div class="feature-card-heading">
      <span class="feature-card-icon" aria-hidden="true">${feature.icon}</span>
      <div><div class="poster-name">${escHtml(author || 'CampusConnect community')}</div><div class="post-time">${timeAgo(item.created_at)}</div></div>
    </div>
    <h3 class="card-title">${escHtml(item.title)}</h3>
    <p class="card-body">${escHtml(item.body)}</p>
    ${detail.length ? `<div class="card-meta">${detail.map(value => `<span class="badge">${escHtml(value)}</span>`).join('')}</div>` : ''}
    ${pollCount ? `<div class="card-meta">${pollCount}</div>` : ''}
    ${extra}
    ${safetyNote}
  </article>`;
}

async function renderFeatureKind(kind) {
  const feature = getFeature(kind);
  if (!feature || kind === 'study-assistant') {
    if (kind === 'study-assistant') return openStudyAssistant();
    return renderFeatureHub();
  }
  state.section = 'features';
  document.querySelectorAll('#bottom-nav button').forEach(button => {
    button.classList.toggle('active', button.dataset.section === 'features');
  });
  const main = document.getElementById('main-content');
  main.innerHTML = '<div class="spinner" role="status" aria-label="Loading"></div>';
  try {
    const data = await api('GET', `/api/features?kind=${encodeURIComponent(kind)}`);
    const items = data.items || [];
    main.innerHTML = `
      <div class="section-header feature-section-header">
        <button class="feature-back" type="button" id="feature-back">\u2190 All features</button>
        <h2 class="section-title">${feature.icon} ${escHtml(feature.title)}</h2>
        <p class="feature-hub-intro">${escHtml(feature.description)}</p>
        <button class="btn-primary feature-create-button" type="button" id="feature-create">+ Add ${escHtml(feature.title.replace(/s$/, ''))}</button>
      </div>
      ${items.length ? items.map(renderFeatureCard).join('') : `<div class="empty-state"><div class="empty-icon">${feature.icon}</div><p>Nothing here yet. Be the first to share!</p></div>`}`;
    document.getElementById('feature-back').addEventListener('click', renderFeatureHub);
    document.getElementById('feature-create').addEventListener('click', () => openFeatureForm(kind));
    main.querySelectorAll('.feature-poll-option').forEach(button => {
      button.addEventListener('click', () => voteFeaturePoll(Number(button.dataset.pollId), Number(button.dataset.optionIndex), kind));
    });
  } catch (error) {
    main.innerHTML = '<div class="empty-state"><p>Could not load this feature. Please try again.</p></div>';
  }
}

function renderFeatureField(field) {
  const [name, label, type, placeholder] = field;
  const id = `feature-${name}`;
  if (type === 'select') {
    return `<div class="form-group"><label for="${id}">${escHtml(label)}</label><select id="${id}">${placeholder.map(option => `<option>${escHtml(option)}</option>`).join('')}</select></div>`;
  }
  return `<div class="form-group"><label for="${id}">${escHtml(label)}</label><input id="${id}" type="${type}" ${placeholder ? `placeholder="${escHtml(placeholder)}"` : ''} ${type === 'url' ? 'inputmode="url"' : ''}></div>`;
}

function openFeatureForm(kind) {
  const feature = getFeature(kind);
  const privacyWarning = kind === 'lost_documents'
    ? '<p class="feature-safety-note">Do not include document numbers, card numbers, addresses, or photos with sensitive details.</p>'
    : '';
  const confessionNote = kind === 'confessions'
    ? '<p class="feature-safety-note">Your name and contact are not requested or shown. Avoid sharing information that identifies you or someone else.</p>'
    : '';
  const pollOptions = kind === 'polls'
    ? `<div class="form-group"><label for="feature-options">Choices (one per line, 2\u20136 choices)</label><textarea id="feature-options" rows="5" placeholder="First choice&#10;Second choice"></textarea></div>`
    : '';
  const resourceUpload = kind === 'resources'
    ? `<div class="form-group"><label for="feature-resource-file">Upload a file (optional)</label><input id="feature-resource-file" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.csv"><span class="optional-label">PDF, Word, PowerPoint, Excel, TXT, or CSV; max 5 MB. You can also share a link instead.</span></div>`
    : '';
  openModal(`<form id="feature-form">
    <h2 class="form-title">${feature.icon} Share ${escHtml(feature.title)}</h2>
    ${privacyWarning}${confessionNote}
    <div class="form-group"><label for="feature-title">Title *</label><input id="feature-title" maxlength="160" required></div>
    <div class="form-group"><label for="feature-body">${kind === 'polls' ? 'Question / context *' : 'Description *'}</label><textarea id="feature-body" maxlength="4000" rows="4" required></textarea></div>
    ${featureFields[kind].map(renderFeatureField).join('')}
    ${resourceUpload}
    ${pollOptions}
    <button class="btn-primary" type="submit">Publish</button>
  </form>`);
  document.getElementById('feature-form').addEventListener('submit', event => {
    event.preventDefault();
    submitFeature(kind);
  });
}

async function submitFeature(kind) {
  const payload = {
    kind,
    title: document.getElementById('feature-title').value.trim(),
    body: document.getElementById('feature-body').value.trim(),
  };
  (featureFields[kind] || []).forEach(([name]) => {
    const field = document.getElementById(`feature-${name}`);
    if (field) payload[name] = field.value.trim();
  });
  if (kind === 'polls') {
    payload.options = document.getElementById('feature-options').value.split(/\r?\n/).map(option => option.trim()).filter(Boolean);
  }
  try {
    const resourceFile = kind === 'resources' && document.getElementById('feature-resource-file')?.files[0];
    if (resourceFile) {
      if (resourceFile.size > 5 * 1024 * 1024) {
        showToast('Files must be 5 MB or smaller.', 'error');
        return;
      }
      const formData = new FormData();
      Object.entries(payload).forEach(([name, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(name, typeof value === 'string' ? value : JSON.stringify(value));
        }
      });
      formData.append('resource_file', resourceFile);
      await api('POST', '/api/features', formData, true);
    } else {
      await api('POST', '/api/features', payload);
    }
    closeModal();
    showToast('Published successfully!', 'success');
    renderFeatureKind(kind);
  } catch (error) {
    showToast(error.data?.error || 'Could not publish. Please check the details and try again.', 'error');
  }
}

function getFeatureVoterKey() {
  let voterKey = localStorage.getItem('cc_feature_voter_key');
  if (!voterKey) {
    voterKey = window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : `${Date.now()}-${Math.random()}-${Math.random()}`;
    localStorage.setItem('cc_feature_voter_key', voterKey);
  }
  return voterKey;
}

async function voteFeaturePoll(featureId, optionIndex, kind) {
  try {
    await api('POST', `/api/features/${featureId}/vote`, {
      voter_key: getFeatureVoterKey(),
      option_index: optionIndex,
    });
    showToast('Your vote has been counted.', 'success');
    renderFeatureKind(kind);
  } catch (error) {
    showToast(error.data?.error || 'Could not submit your vote.', 'error');
  }
}

function openStudyAssistant() {
  openModal(`<section class="study-assistant">
    <h2 class="form-title">\uD83E\uDDE0 AI Study Assistant</h2>
    <p class="feature-safety-note">Ask a learning question and get a step-by-step explanation. Questions are sent to our configured AI provider. Do not include passwords, personal details, or private information.</p>
    <form id="study-assistant-form">
      <div class="form-group"><label for="study-question">What would you like help understanding?</label><textarea id="study-question" maxlength="4000" rows="5" required placeholder="For example: Can you explain how supply and demand affect market prices?"></textarea></div>
      <button class="btn-primary" type="submit">Ask the Study Assistant</button>
    </form>
    <div id="study-answer" aria-live="polite"></div>
  </section>`);
  document.getElementById('study-assistant-form').addEventListener('submit', submitStudyQuestion);
}

async function submitStudyQuestion(event) {
  event.preventDefault();
  const question = document.getElementById('study-question').value.trim();
  const button = event.currentTarget.querySelector('button[type="submit"]');
  const answer = document.getElementById('study-answer');
  button.disabled = true;
  button.textContent = 'Thinking\u2026';
  answer.innerHTML = '<div class="spinner" role="status" aria-label="Generating an explanation"></div>';
  try {
    const result = await api('POST', '/api/study-assistant', { question });
    answer.innerHTML = `<div class="study-answer-card"><h3>Explanation</h3><p>${escHtml(result.answer).replace(/\n/g, '<br>')}</p></div>`;
  } catch (error) {
    answer.innerHTML = `<p class="feature-safety-note" role="alert">${escHtml(error.data?.error || 'The Study Assistant could not answer right now.')}</p>`;
  } finally {
    button.disabled = false;
    button.textContent = 'Ask the Study Assistant';
  }
}
