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

  function actor() {
    return document.querySelector('#actor')?.value || 'desktop';
  }

  function setStatus(message, error = false) {
    const el = document.querySelector('#status');
    if (!el) return;
    el.textContent = message;
    el.className = error ? 'footer error' : 'footer';
  }

  function selectedInternalRecordId() {
    const meta = document.querySelector('#detail .meta');
    if (!meta) return '';
    const cells = Array.from(meta.children);
    for (let i = 0; i < cells.length - 1; i += 2) {
      if (cells[i].textContent.trim() === 'Record ID') return cells[i + 1].textContent.trim();
    }
    return '';
  }

  function selectedDisplayName() {
    return document.querySelector('#detail h2')?.textContent?.trim() || selectedInternalRecordId();
  }

  function currentModeIsCloud() {
    const browse = document.querySelector('#browse-source');
    const setupText = document.querySelector('#setup')?.textContent || '';
    return !!browse?.disabled && /cloud demo|workspace|desktop bridge disabled|replit/i.test(setupText + ' ' + document.body.textContent);
  }

  function installStyles() {
    if (document.querySelector('#fv-polish-style')) return;
    const style = document.createElement('style');
    style.id = 'fv-polish-style';
    style.textContent = `
      .fv-empty-help { padding:18px; line-height:1.45; color:#9aa7b6; }
      .fv-empty-help strong { color:#e6ebf2; }
      .fv-empty-help code { background:#080c10; border:1px solid #303b47; border-radius:4px; padding:1px 4px; color:#f0b278; }
      .fv-soft-warning { border:1px solid #735b35; background:#15120d; border-radius:6px; color:#f0c084; padding:8px; margin:8px 0; line-height:1.35; }
    `;
    document.head.appendChild(style);
  }

  async function releaseSelectedRecord() {
    const recordId = selectedInternalRecordId();
    if (!recordId) {
      setStatus('Select a record before release.', true);
      return;
    }
    const name = selectedDisplayName();
    const ok = confirm(`Release this record?\n\n${name}\n${recordId}\n\nForgeVault will block release if unresolved dependencies exist.`);
    if (!ok) return;
    try {
      setStatus(`Releasing ${recordId}...`);
      let result;
      try {
        result = await jsonFetch(`/api/v1/records/${encodeURIComponent(recordId)}/lifecycle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to_state: 'Released', actor: actor(), reason: 'Released from ForgeVault UI' }),
        });
      } catch (firstError) {
        const message = String(firstError.message || '');
        if (!message.includes('invalid lifecycle transition')) throw firstError;
        await jsonFetch(`/api/v1/records/${encodeURIComponent(recordId)}/lifecycle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to_state: 'Review', actor: actor(), reason: 'Moved to review before release from ForgeVault UI' }),
        });
        result = await jsonFetch(`/api/v1/records/${encodeURIComponent(recordId)}/lifecycle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to_state: 'Released', actor: actor(), reason: 'Released from ForgeVault UI after review transition' }),
        });
      }
      const packageText = result.package_number ? ` Package ${result.package_number} created.` : '';
      setStatus(`${recordId} released.${packageText}`);
      document.querySelector('#refresh')?.click();
    } catch (e) {
      setStatus(`Release blocked: ${e.message}`, true);
    }
  }

  function wireReleaseButtons() {
    const detail = document.querySelector('#detail');
    if (!detail || detail.dataset.fvReleaseWired === 'yes') return;
    detail.dataset.fvReleaseWired = 'yes';
    detail.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button.textContent.trim() !== 'Release') return;
      event.preventDefault();
      releaseSelectedRecord();
    });
  }

  function improveEmptyState() {
    const records = document.querySelector('#records');
    if (!records) return;
    const text = records.textContent || '';
    if (!/No records found|Add a source folder/.test(text)) return;
    const cloud = currentModeIsCloud();
    records.innerHTML = `
      <tr><td colspan="6"><div class="fv-empty-help">
        <strong>No files indexed yet.</strong><br>
        ${cloud
          ? 'Cloud demo path: click <strong>Create Demo Folder</strong>, add <code>./demo_source</code> as a source folder, then click <strong>Index Selected</strong>.'
          : 'Local desktop path: choose a source folder, add it, then click <strong>Index Selected</strong>.'}
        <br>After indexing, records appear here for checkout, check-in, review, and release.
      </div></td></tr>`;
  }

  function reducePreviewOverpromise() {
    const detail = document.querySelector('#detail');
    if (!detail) return;
    const paras = Array.from(detail.querySelectorAll('p.muted'));
    for (const p of paras) {
      if (p.textContent.includes('Preview, metadata, versions')) {
        p.textContent = 'Select a record to see metadata, versions, checkout state, review actions, and release controls.';
      }
    }
  }

  function addModeBadge() {
    const pathbar = document.querySelector('#pathbar');
    if (!pathbar || pathbar.dataset.fvModeBadged === 'yes') return;
    pathbar.dataset.fvModeBadged = 'yes';
    const update = async () => {
      try {
        const caps = await jsonFetch('/api/v1/desktop/capabilities');
        const prefix = caps.desktop_bridge_enabled ? 'Desktop vault' : 'Cloud demo';
        if (!pathbar.textContent.startsWith(prefix)) pathbar.textContent = `${prefix}: ${pathbar.textContent}`;
      } catch {
        if (!pathbar.textContent.startsWith('Vault')) pathbar.textContent = `Vault: ${pathbar.textContent}`;
      }
    };
    setTimeout(update, 350);
  }

  function runPolish() {
    installStyles();
    wireReleaseButtons();
    improveEmptyState();
    reducePreviewOverpromise();
    addModeBadge();
  }

  const observer = new MutationObserver(runPolish);
  function init() {
    runPolish();
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
