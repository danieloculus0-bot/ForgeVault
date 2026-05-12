(() => {
  const STORAGE_KEY = 'forgevault.onboarding.dismissed.v2';

  function esc(value = '') {
    return String(value).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function setStatus(message, error = false) {
    const el = document.querySelector('#status');
    if (!el) return;
    el.textContent = message;
    el.className = error ? 'footer error' : 'footer';
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
      .fv-install-overlay { position:fixed; inset:0; z-index:6000; background:rgba(0,0,0,.72); display:grid; place-items:center; }
      .fv-install-card { width:min(720px, calc(100vw - 32px)); max-height:calc(100vh - 32px); overflow:auto; background:#111820; border:1px solid #43505f; border-radius:10px; box-shadow:0 20px 70px rgba(0,0,0,.6); padding:18px; color:#e6ebf2; }
      .fv-install-card h2 { margin:0 0 8px; font-size:22px; }
      .fv-install-card h3 { margin:14px 0 6px; font-size:15px; color:#f0b278; }
      .fv-install-card p { color:#9aa7b6; line-height:1.4; }
      .fv-install-card ol { line-height:1.5; }
      .fv-install-card pre { white-space:pre-wrap; background:#080c10; border:1px solid #303b47; border-radius:6px; padding:10px; color:#dce4ee; }
      .fv-install-actions { display:flex; justify-content:flex-end; gap:8px; margin-top:14px; flex-wrap:wrap; }
    `;
    document.head.appendChild(style);
  }

  function installGuideHtml() {
    return `
      <div class="fv-install-overlay">
        <div class="fv-install-card" role="dialog" aria-modal="true" aria-label="ForgeVault setup guide">
          <h2>ForgeVault Setup Guide</h2>
          <p>This is the setup path. Do this first, then index your engineering folder. Nothing here deletes your real files.</p>
          <h3>Option A: Windows desktop EXE</h3>
          <ol>
            <li>Download the <code>ForgeVaultDesktop-windows</code> artifact from GitHub Actions.</li>
            <li>Unzip it.</li>
            <li>Double-click <code>ForgeVaultDesktop.exe</code>.</li>
          </ol>
          <p>The EXE stores its local database and vault under <code>%LOCALAPPDATA%\\ForgeVault</code>. If this screen opened, the app is already running.</p>
          <h3>Option B: Run from source</h3>
          <ol>
            <li>Install Python 3.11 or newer.</li>
            <li>Open PowerShell in the ForgeVault folder.</li>
            <li>Run this:</li>
          </ol>
          <pre>.\\scripts\\Launch-ForgeVault.ps1 --manage-folder "C:\\Engineering\\Jobs"</pre>
          <p>The launcher creates the virtual environment, installs the app, starts the local server, opens the browser UI, and pre-fills the folder path.</p>
          <h3>First folder setup</h3>
          <ol>
            <li>Click <strong>Browse for Source Folder</strong>, or paste a path into <strong>Folder path</strong>.</li>
            <li>Click <strong>Add Source Folder</strong>.</li>
            <li>Click <strong>Index Selected</strong>.</li>
            <li>Search <code>UNMAPPED</code> to see files that need cleanup.</li>
          </ol>
          <p>Safe rule: removing a source folder only removes it from ForgeVault's index. It does not delete files from disk.</p>
          <div class="fv-install-actions">
            <button id="fv-copy-launch" type="button">Copy PowerShell Launch Command</button>
            <button id="fv-close-install-guide" class="primary" type="button">Got It</button>
          </div>
        </div>
      </div>
    `;
  }

  function showInstallGuide() {
    injectStyle();
    let root = document.querySelector('#fv-install-guide-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'fv-install-guide-root';
      document.body.appendChild(root);
    }
    root.innerHTML = installGuideHtml();
    document.querySelector('#fv-close-install-guide')?.addEventListener('click', () => {
      root.innerHTML = '';
      localStorage.setItem(STORAGE_KEY, 'yes');
    });
    document.querySelector('#fv-copy-launch')?.addEventListener('click', async () => {
      const command = '.\\scripts\\Launch-ForgeVault.ps1 --manage-folder "C:\\Engineering\\Jobs"';
      try {
        await navigator.clipboard.writeText(command);
        setStatus('Copied launch command. Replace the folder path with your real engineering folder.');
      } catch {
        setStatus(command);
      }
    });
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
          <button id="fv-show-install-guide" type="button">Install / Setup Help</button>
          <button id="fv-fill-example-path" type="button">Fill Example Path</button>
          <button id="fv-dismiss-start" class="ghost" type="button">Hide This Help</button>
        </div>
        <div class="fv-start-note">If you launched the Windows EXE, installation is already done. This screen is the setup: choose a folder, add it, index it.</div>
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
    document.querySelector('#fv-show-install-guide')?.addEventListener('click', showInstallGuide);
    document.querySelector('#fv-fill-example-path')?.addEventListener('click', () => {
      const folder = document.querySelector('#folder');
      const display = document.querySelector('#display_name');
      if (folder && !folder.value) folder.value = 'C:\\Engineering\\Jobs';
      if (display && !display.value) display.value = 'Engineering Jobs';
      setStatus('Example path filled. Replace it with your real folder before adding.');
    });
    document.querySelector('#fv-dismiss-start')?.addEventListener('click', () => {
      localStorage.setItem(STORAGE_KEY, 'yes');
      document.querySelector('#fv-start-card')?.remove();
    });
  }

  function enhanceInputs() {
    const folder = document.querySelector('#folder');
    if (folder && !document.querySelector('#fv-folder-hint')) {
      folder.placeholder = 'Example: C:\\Engineering\\Jobs or P:\\Blue Prints';
      folder.insertAdjacentHTML('afterend', '<div id="fv-folder-hint" class="fv-field-hint">Pick the top folder ForgeVault should manage. Example: C:\\Engineering\\Jobs or P:\\Blue Prints.</div>');
    }
    const display = document.querySelector('#display_name');
    if (display && !document.querySelector('#fv-display-hint')) {
      display.placeholder = 'Friendly name, example: Blue Prints';
      display.insertAdjacentHTML('afterend', '<div id="fv-display-hint" class="fv-field-hint">Friendly name only. Leave blank and ForgeVault will use the folder name.</div>');
    }
    const q = document.querySelector('#q');
    if (q) q.placeholder = 'Search files, part numbers, revisions, paths, metadata, or UNMAPPED';
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

  function maybeShowInstallGuide() {
    if (localStorage.getItem(STORAGE_KEY) === 'yes') return;
    if (hasSources()) return;
    setTimeout(showInstallGuide, 500);
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
    maybeShowInstallGuide();
  }

  window.showForgeVaultSetupGuide = showInstallGuide;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
