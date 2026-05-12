(() => {
  function esc(value = '') {
    return String(value).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  async function jsonFetch(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  function getActor() {
    return document.querySelector('#actor')?.value || 'desktop';
  }

  function setStatus(message, error = false) {
    const el = document.querySelector('#status');
    if (!el) return;
    el.textContent = message;
    el.className = error ? 'footer error' : 'footer';
  }

  function selectedRecordFromPage() {
    if (!window.state || typeof window.selectedRecord !== 'function') return null;
    return window.selectedRecord();
  }

  function selectedVersion(item) {
    return item?.latest_version || null;
  }

  function initialDirectory(item) {
    const version = selectedVersion(item);
    return version?.original_source_path || null;
  }

  function ensureModalRoot() {
    let root = document.querySelector('#fv-modal-root');
    if (root) return root;
    root = document.createElement('div');
    root.id = 'fv-modal-root';
    document.body.appendChild(root);
    const style = document.createElement('style');
    style.textContent = `
      .fv-overlay { position:fixed; inset:0; background:rgba(0,0,0,.68); display:grid; place-items:center; z-index:5000; }
      .fv-modal { width:min(560px, calc(100vw - 32px)); max-height:calc(100vh - 32px); overflow:auto; background:#111820; border:1px solid #43505f; border-radius:8px; box-shadow:0 18px 60px rgba(0,0,0,.55); padding:16px; color:#e6ebf2; }
      .fv-modal h3 { margin:0 0 8px; font-size:18px; }
      .fv-modal p { margin:0 0 12px; color:#9aa7b6; line-height:1.35; }
      .fv-modal .fv-grid { display:grid; gap:10px; }
      .fv-modal .fv-row { display:grid; grid-template-columns:1fr auto; gap:8px; align-items:end; }
      .fv-modal .fv-check { display:flex; align-items:center; gap:8px; color:#9aa7b6; font-size:13px; }
      .fv-modal .fv-check input { width:auto; }
      .fv-modal .fv-actions { display:flex; justify-content:flex-end; gap:8px; margin-top:14px; }
      .fv-modal .fv-small { color:#748293; font-size:12px; }
    `;
    document.head.appendChild(style);
    return root;
  }

  function closeModal() {
    const root = document.querySelector('#fv-modal-root');
    if (root) root.innerHTML = '';
  }

  function renderCheckinModal(item, filePath = '') {
    const root = ensureModalRoot();
    const record = item.record;
    const version = selectedVersion(item);
    root.innerHTML = `
      <div class="fv-overlay">
        <div class="fv-modal" role="dialog" aria-modal="true" aria-label="Check in new version">
          <h3>Check In New Version</h3>
          <p>${esc(version?.filename || record.internal_record_id)}<br><span class="fv-small">${esc(record.internal_record_id)}</span></p>
          <div class="fv-grid">
            <label>Replacement file path
              <div class="fv-row"><input id="fv-checkin-path" value="${esc(filePath)}" placeholder="Choose or paste replacement file path" /><button id="fv-browse-checkin" type="button">Browse</button></div>
            </label>
            <label>Check-in note<textarea id="fv-checkin-note" placeholder="What changed?">Updated file checked in from ForgeVault Desktop.</textarea></label>
            <div class="fv-row">
              <label>Customer revision<input id="fv-customer-rev" value="${esc(record.customer_revision || '')}" placeholder="Optional" /></label>
              <label>Internal revision<input id="fv-internal-rev" value="${esc(record.internal_revision || '')}" placeholder="Optional" /></label>
            </div>
            <label>Assigned checker<input id="fv-checker" placeholder="Optional checker email/name" /></label>
            <label>Risk level<select id="fv-risk"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
            <label class="fv-check"><input id="fv-submit-review" type="checkbox" checked /> Submit checked-in version for review</label>
          </div>
          <div class="fv-actions"><button id="fv-cancel-checkin" type="button">Cancel</button><button id="fv-submit-checkin" class="primary" type="button">Check In</button></div>
        </div>
      </div>
    `;

    document.querySelector('#fv-cancel-checkin').addEventListener('click', closeModal);
    document.querySelector('#fv-browse-checkin').addEventListener('click', async () => {
      try {
        setStatus('Opening file browser...');
        const result = await jsonFetch('/api/v1/desktop/browse-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'Choose replacement file to check in', initial_dir: initialDirectory(item) }),
        });
        if (!result.selected) {
          setStatus('File selection cancelled.');
          return;
        }
        document.querySelector('#fv-checkin-path').value = result.path;
        setStatus('Replacement file selected.');
      } catch (e) {
        setStatus(e.message, true);
      }
    });
    document.querySelector('#fv-submit-checkin').addEventListener('click', async () => submitCheckin(item));
  }

  async function openCheckinFlow() {
    try {
      const item = selectedRecordFromPage();
      if (!item) throw new Error('Select a record first.');
      renderCheckinModal(item);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function submitCheckin(item) {
    try {
      const record = item.record;
      const filePath = document.querySelector('#fv-checkin-path').value.trim();
      if (!filePath) throw new Error('Choose or paste a replacement file path first.');
      const payload = {
        actor: getActor(),
        file_path: filePath,
        note: document.querySelector('#fv-checkin-note').value || null,
        customer_revision: document.querySelector('#fv-customer-rev').value || null,
        internal_revision: document.querySelector('#fv-internal-rev').value || null,
        submit_for_review: document.querySelector('#fv-submit-review').checked,
        assigned_checker: document.querySelector('#fv-checker').value || null,
        risk_level: document.querySelector('#fv-risk').value || 'low',
      };
      setStatus(`Checking in ${record.internal_record_id}...`);
      const result = await jsonFetch(`/api/v1/records/${encodeURIComponent(record.internal_record_id)}/checkin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      closeModal();
      setStatus(`Checked in v${result.file_version.version_number}: ${result.file_version.filename}`);
      if (typeof window.search === 'function') await window.search();
      if (typeof window.showReviews === 'function' && result.review) await window.showReviews();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  function wireButtons() {
    const detail = document.querySelector('#detail');
    if (!detail) return;
    detail.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button.textContent.trim() !== 'Check In New Version') return;
      event.preventDefault();
      openCheckinFlow();
    });
  }

  window.openForgeVaultCheckinFlow = openCheckinFlow;
  wireButtons();
})();
