(() => {
  const STORAGE_KEY = 'forgevault.onboarding.dismissed.v1';

  function esc(value = '') {
    return String(value).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function setupCard() {
    return document.querySelector('#setup');
  }

  function hasSources() {
    return !document.querySelector('#sources .source-title')?.textContent?.includes('No source folders yet');
  }

  function injectStyle() {
    if (document.querySelector('#fv-onboarding-style')) return;
    const style = document.createElement('style');
    style.id = 'fv-onboarding-style';
    style.textContent = `
      .fv-start-card { border:1px solid #735b35; background:linear-gradient(180deg,#1a1f25,#111820); border-radius:8px; padding:12px; margin-bottom:10px; color:#e6ebf2; box-shadow:0 8px 22px rgba(0,0,0,.22); }
      .fv-start-card h3 { margin:0 0 6px; font-size:16px; color:#f08a2b; }
      .fv-start-card p { margin:0 0 9px; color:#b7c0cb; line-height:1.35; font-size:13px; }
      .fv-start-card ol { margin:0 0 10px 18px; padding:0; color:#d9e0e8; line-height:1.42; font-size:13px; }
      .fv-start-card li { margin:4px 0; }
      .fv-start-card .fv-start-actions { display:flex; gap:8px; flex-wrap:wrap; }
      .fv-start-card .fv-start-note { color:#8f9baa; font-size:12px; margin-top:8px; }
      .fv-field-hint { color:#f0c084; font-size:12px; line-height:1.3; margin-top:-4px; }
      .fv-empty-main { padding:18px; color:#9aa7b6; line-height:1.45; }
      .fv-empty-main strong { color:#e6ebf2; }
    `;
    document.head.appendChild(style);
  }

  function starterCardHtml() {
    return `
      <div id="fv-start-card" class="fv-start-card">
        <h3>Start here</h3>
        <p>ForgeVault manages an existing folder. It does not delete your files. First, point it at the folder where drawings, CAD, PDFs, or job files live.</p>
        <ol>
          <li>Click <strong>Browse for Source Folder</strong> or paste a folder path.</li>
          <li>Click <strong>Add Source Folder</strong>.</li>
          <li>Click <strong>Index Selected</strong>.</li>
          <li>Select a file in the table to check out, check in a new version, or send it for review.</li>
        </ol>
        <div class="fv-start-actions">
          <button id="fv-focus-folder" class="primary" type="button">Choose Folder Now</button>
          <button id="fv-dismiss-start" class="ghost" type="button">Hide This Help</button>
        </div>
        <div class="fv-start-note">Install note: if you launched the Windows EXE, setup is already done. This screen is the setup.</div>
      </div>
    `;
  }

  function enhanceLeftPane() {
    injectStyle();
    const card = setupCard();
    if (!card || document.querySelector('#fv-start-card')) return;
    if (localStorage.getItem(STORAGE_KEY) === 'yes' && hasSources()) return;
    card.insertAdjacentHTML('beforebegin', starterCardHtml());
    document.querySelector('#fv-focus-folder')?.addEventListener('click', () => {
      const browse = document.querySelector('#browse-source');
      const folder = document.querySelector('#folder');
      if (browse && !browse.disabled) browse.click();
      else folder?.focus();
    });
    document.querySelector('#fv-dismiss-start')?.addEventListener('click', () => {
      localStorage.setItem(STORAGE_KEY, 'yes');
      document.querySelector('#fv-start-card')?.remove();
    });
  }

  function enhanceInputs() {
    const folder = document.querySelector('#folder');
    if (folder && !document.querySelector('#fv-folder-hint')) {
      folder.insertAdjacentHTML('afterend', '<div id="fv-folder-hint" class="fv-field-hint">Pick the top folder you want ForgeVault to manage. Example: C:\\Engineering\\Jobs or P:\\Blue Prints.</div>');
    }
    const display = document.querySelector('#display_name');
    if (display && !document.querySelector('#fv-display-hint')) {
      display.insertAdjacentHTML('afterend', '<div id="fv-display-hint" class="fv-field-hint">Friendly name only. Leave blank and ForgeVault will use the folder name.</div>');
    }
  }

  function enhanceEmptyTable() {
    const records = document.querySelector('#records');
    if (!records) return;
    if (records.dataset.fvEnhanced === 'yes') return;
    const text = records.textContent || '';
    if (!text.includes('Add a source folder')) return;
    records.innerHTML = '<tr><td colspan="6"><div class="fv-empty-main"><strong>No files indexed yet.</strong><br>Use the left panel: choose a source folder, add it, then click Index Selected. After indexing, files show here for checkout, check-in, review, and release work.</div></td></tr>';
    records.dataset.fvEnhanced = 'yes';
  }

  function watchForChanges() {
    const observer = new MutationObserver(() => {
      enhanceLeftPane();
      enhanceInputs();
      enhanceEmptyTable();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function init() {
    enhanceLeftPane();
    enhanceInputs();
    enhanceEmptyTable();
    watchForChanges();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
