'use strict';

// ── Shared Exercise Search Component ──────────────────────────────────────────
//
// Usage (explicit):
//   new ExerciseSearch(inputEl, exercises, { hiddenInputEl, onSelect });
//
// Usage (bulk init — finds all [data-exercise-wrap] containers not yet inited):
//   ExerciseSearch.initAll(exercises);
//
// HTML contract:
//   <div data-exercise-wrap>
//     <input type="text"   class="form-control ex-search-input" ...>
//     <input type="hidden" class="exercise-id-input" name="...">
//   </div>

class ExerciseSearch {
  constructor(inputEl, exercises, { hiddenInputEl = null, onSelect = null } = {}) {
    this.inputEl   = inputEl;
    this.exercises = exercises; // shared array — push here to make new exercises visible everywhere
    this.hiddenEl  = hiddenInputEl || inputEl.nextElementSibling;
    this.onSelect  = onSelect;
    this._dropEl   = null;
    this._modalEl  = null;
    inputEl.dataset.esInit = '1';
    this._setup();
  }

  // ── Static helpers ─────────────────────────────────────────────────────────

  // Init all uninitialised exercise search inputs on the page
  static initAll(exercises) {
    document.querySelectorAll('[data-exercise-wrap] .ex-search-input:not([data-es-init])').forEach(el => {
      new ExerciseSearch(el, exercises, { hiddenInputEl: el.nextElementSibling });
    });
  }

  // Show a "create new exercise" modal anchored to a container element.
  // Useful for pages that already have their own autocomplete and just need the modal.
  static showCreateModal(name, exercises, container, onCreated) {
    container.querySelector('.es-create-modal')?.remove();
    const modal = ExerciseSearch._buildModal(name);
    container.appendChild(modal);
    ExerciseSearch._wireModal(modal, name, exercises, onCreated, () => modal.remove());
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  static _buildModal(name) {
    const modal = document.createElement('div');
    modal.className = 'es-create-modal';
    modal.style.cssText = `
      margin-top:6px;padding:14px;
      background:var(--surface2);border:1px solid var(--accent);border-radius:10px;
    `;
    modal.innerHTML = `
      <div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;">New Exercise</div>
      <div style="font-size:14px;font-weight:600;margin-bottom:12px;">${name}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
        <div>
          <label style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Muscle Group</label>
          <select class="form-control es-muscle-sel" style="font-size:13px;">
            <option value="">— Select —</option>
            <option value="Chest">Chest</option>
            <option value="Back">Back</option>
            <option value="Legs">Legs</option>
            <option value="Shoulders">Shoulders</option>
            <option value="Arms">Arms</option>
            <option value="Core">Core</option>
            <option value="Full Body">Full Body</option>
            <option value="Cardio">Cardio</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div>
          <label style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Category</label>
          <select class="form-control es-cat-sel" style="font-size:13px;">
            <option value="strength">Strength</option>
            <option value="cardio">Cardio</option>
            <option value="plyometric">Plyometric</option>
            <option value="mobility">Mobility</option>
          </select>
        </div>
      </div>
      <div style="display:flex;gap:8px;">
        <button type="button" class="btn btn-primary btn-sm" style="flex:1;" data-action="confirm">Add to Library</button>
        <button type="button" class="btn btn-secondary btn-sm" data-action="cancel">Cancel</button>
      </div>
    `;
    return modal;
  }

  static _wireModal(modal, name, exercises, onCreated, onCancel) {
    modal.querySelector('[data-action="confirm"]').addEventListener('click', async () => {
      const muscleGroup = modal.querySelector('.es-muscle-sel').value;
      const category    = modal.querySelector('.es-cat-sel').value;
      try {
        const res = await fetch('/exercises/find-or-create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, muscle_group: muscleGroup, category }),
        });
        if (!res.ok) { alert('Could not save exercise.'); return; }
        const data = await res.json();
        if (!exercises.find(e => e.id == data.id)) {
          exercises.push({ id: data.id, name: data.name, group: data.muscle_group || '' });
        }
        modal.remove();
        if (onCreated) onCreated(data);
      } catch(e) {
        alert('Error creating exercise.');
      }
    });

    modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
      modal.remove();
      if (onCancel) onCancel();
    });
  }

  // ── Instance: setup ────────────────────────────────────────────────────────

  _setup() {
    // Ensure the immediate parent of the input is position:relative for dropdown
    const inputParent = this.inputEl.parentElement;
    if (getComputedStyle(inputParent).position === 'static') {
      inputParent.style.position = 'relative';
    }

    // Dropdown div
    this._dropEl = document.createElement('div');
    this._dropEl.style.cssText = `
      display:none;position:absolute;top:calc(100% + 2px);left:0;right:0;z-index:200;
      background:var(--surface2);border:1px solid var(--border);border-radius:8px;
      max-height:220px;overflow-y:auto;box-shadow:0 4px 16px rgba(0,0,0,.4);
    `;
    inputParent.appendChild(this._dropEl);

    this.inputEl.addEventListener('input',     () => this._onInput());
    this.inputEl.addEventListener('focus',     () => this._render());
    this.inputEl.addEventListener('blur',      () => setTimeout(() => this._hide(), 180));
    this._dropEl.addEventListener('mousedown', e  => e.preventDefault());
    this._dropEl.addEventListener('click',     e  => this._onDropClick(e));
  }

  // ── Instance: dropdown ─────────────────────────────────────────────────────

  _buildHtml(query) {
    const q = query.toLowerCase().trim();
    const filtered = q
      ? this.exercises.filter(ex =>
          ex.name.toLowerCase().includes(q) ||
          (ex.group || '').toLowerCase().includes(q))
      : this.exercises.slice(0, 60);

    let html = '';
    let curGroup = null;
    filtered.forEach(ex => {
      if (ex.group !== curGroup) {
        html += `<div style="padding:5px 14px 3px;font-size:10px;font-weight:700;letter-spacing:0.08em;color:var(--muted);text-transform:uppercase;background:var(--surface);position:sticky;top:0;">${ex.group || 'Other'}</div>`;
        curGroup = ex.group;
      }
      html += `<div class="es-opt" data-id="${ex.id}" data-name="${ex.name.replace(/"/g, '&quot;')}"
        style="padding:10px 14px;cursor:pointer;font-size:14px;"
        onmouseover="this.style.background='var(--surface)'" onmouseout="this.style.background=''">${ex.name}</div>`;
    });

    const hasExact = this.exercises.some(ex => ex.name.toLowerCase() === q);
    if (q && !hasExact) {
      html += `<div class="es-opt" data-id="__add__" data-name="${q.replace(/"/g, '&quot;')}"
        style="padding:10px 14px;cursor:pointer;font-size:13px;color:var(--accent);border-top:1px solid var(--border);"
        onmouseover="this.style.background='var(--surface)'" onmouseout="this.style.background=''">
        ➕ Add "<strong>${q}</strong>" to library
      </div>`;
    }

    return html || '<div style="padding:10px 14px;color:var(--muted);font-size:13px;">No matches</div>';
  }

  _render() {
    this._dropEl.innerHTML = this._buildHtml(this.inputEl.value);
    this._dropEl.style.display = 'block';
  }

  _onInput() {
    this._render();
    if (this.hiddenEl) this.hiddenEl.value = '';
    if (this.onSelect) this.onSelect(null);
  }

  _hide() {
    this._dropEl.style.display = 'none';
  }

  _onDropClick(e) {
    const opt = e.target.closest('.es-opt');
    if (!opt) return;
    const id   = opt.dataset.id;
    const name = opt.dataset.name;
    if (id === '__add__') {
      this._showCreateModal(name);
    } else {
      this._select(parseInt(id, 10), name);
    }
  }

  _select(id, name) {
    this.inputEl.value = name;
    if (this.hiddenEl) this.hiddenEl.value = id;
    this._hide();
    this._removeModal();
    if (this.onSelect) this.onSelect({ id, name });
  }

  // ── Instance: create modal ─────────────────────────────────────────────────

  _showCreateModal(name) {
    this._hide();
    this._removeModal();

    const modal = ExerciseSearch._buildModal(name);
    const wrap = this.inputEl.closest('[data-exercise-wrap]') || this.inputEl.parentElement;
    wrap.appendChild(modal);
    this._modalEl = modal;

    ExerciseSearch._wireModal(modal, name, this.exercises,
      (data) => {
        this._modalEl = null;
        this._select(data.id, data.name);
      },
      () => {
        this._modalEl = null;
        this.inputEl.value = '';
        if (this.hiddenEl) this.hiddenEl.value = '';
      }
    );
  }

  _removeModal() {
    if (this._modalEl) {
      this._modalEl.remove();
      this._modalEl = null;
    }
  }
}
