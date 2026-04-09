/**
 * Draft Backup — saves form state to localStorage on every change,
 * restores it on page load if a draft exists. Clears on successful htmx save.
 *
 * Usage: <script src=".../draft_backup.js" data-draft-key="forge_draft_strength"></script>
 *        (place after the <form>)
 */
(function () {
  const script = document.currentScript;
  const key = script?.getAttribute('data-draft-key');
  if (!key) return;

  const form = document.querySelector('form[hx-post]');
  if (!form) return;

  // ── Save draft (debounced) ──────────────────────────────
  let timer;
  function saveDraft() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const data = new FormData(form);
      const obj = {};
      data.forEach((v, k) => {
        if (obj[k]) {
          if (!Array.isArray(obj[k])) obj[k] = [obj[k]];
          obj[k].push(v);
        } else {
          obj[k] = v;
        }
      });
      obj._ts = Date.now();
      try { localStorage.setItem(key, JSON.stringify(obj)); } catch (_) {}
    }, 1000);
  }

  form.addEventListener('input', saveDraft);
  form.addEventListener('change', saveDraft);

  // ── Clear draft on successful save ──────────────────────
  document.addEventListener('htmx:afterRequest', function (e) {
    if (e.detail.elt === form && e.detail.successful) {
      localStorage.removeItem(key);
    }
  });

  // ── Restore banner ──────────────────────────────────────
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return;
    const draft = JSON.parse(raw);
    // Ignore drafts older than 24 hours
    if (draft._ts && Date.now() - draft._ts > 86400000) {
      localStorage.removeItem(key);
      return;
    }

    const banner = document.createElement('div');
    banner.style.cssText =
      'background:var(--surface2);border:1px solid var(--accent);border-radius:8px;' +
      'padding:12px 16px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;gap:12px;';
    banner.innerHTML =
      '<span style="font-size:13px;color:var(--text);">Unsaved workout found. Restore?</span>' +
      '<span style="display:flex;gap:8px;">' +
      '  <button type="button" class="btn btn-primary btn-sm" id="draft-restore">Restore</button>' +
      '  <button type="button" class="btn btn-secondary btn-sm" id="draft-discard">Discard</button>' +
      '</span>';
    form.parentNode.insertBefore(banner, form);

    document.getElementById('draft-restore').addEventListener('click', function () {
      Object.entries(draft).forEach(([k, v]) => {
        if (k === '_ts') return;
        const vals = Array.isArray(v) ? v : [v];
        const inputs = form.querySelectorAll(`[name="${CSS.escape(k)}"]`);
        inputs.forEach((inp, i) => {
          if (i < vals.length) {
            inp.value = vals[i];
            inp.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });
      });
      banner.remove();
    });

    document.getElementById('draft-discard').addEventListener('click', function () {
      localStorage.removeItem(key);
      banner.remove();
    });
  } catch (_) {}
})();
