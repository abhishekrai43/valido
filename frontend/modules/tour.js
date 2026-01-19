// Lightweight guided tour (no dependencies). Click to advance.
// - Safe to include on any page.
// - Never throws; fails silently.
// - Persists "dismissed" state in localStorage.
//
// Usage:
//   window.ValidoTour.start([...steps])
//   window.ValidoTour.maybeStart([...steps], { key: 'valido.tour.v1', startDelayMs: 600 })

(() => {
  const STORAGE_PREFIX = 'valido.tour.';

  async function sendTelemetry(action, details) {
    try {
      // Best-effort POST to the local backend (FastAPI) endpoint.
      await fetch('/api/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, details: details || undefined })
      });
    } catch {
      // ignore
    }
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function safeGetRect(el) {
    try {
      return el.getBoundingClientRect();
    } catch {
      return null;
    }
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = safeGetRect(el);
    if (!rect) return false;
    if (rect.width <= 0 || rect.height <= 0) return false;
    // Check basic display/visibility
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    return true;
  }

  function findTarget(step) {
    if (!step) return null;
    if (typeof step.getTarget === 'function') {
      try {
        return step.getTarget() || null;
      } catch {
        return null;
      }
    }
    if (step.selector) return document.querySelector(step.selector);
    return null;
  }

  function createOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'valido-tour-overlay';
    overlay.innerHTML = `
      <div class="valido-tour-dim"></div>
      <div class="valido-tour-popover" role="dialog" aria-live="polite">
        <div class="valido-tour-title"></div>
        <div class="valido-tour-body"></div>
        <div class="valido-tour-actions">
          <button type="button" class="btn btn-ghost valido-tour-skip">Skip</button>
          <div class="valido-tour-actions-right">
            <button type="button" class="btn btn-secondary valido-tour-back" style="display:none">Back</button>
            <button type="button" class="btn btn-primary valido-tour-next">Next</button>
          </div>
        </div>
        <div class="valido-tour-footnote">
          Tip: click outside to go next.
        </div>
      </div>
    `;
    return overlay;
  }

  function positionPopover(popover, targetEl, placement) {
    const margin = 12;
    const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

    const popRect = popover.getBoundingClientRect();
    let x = Math.round((vw - popRect.width) / 2);
    let y = Math.round(vh * 0.18);

    const rect = targetEl ? safeGetRect(targetEl) : null;
    if (rect) {
      const prefer = placement || 'bottom';
      const candidates = [];

      // bottom
      candidates.push({
        name: 'bottom',
        x: rect.left + rect.width / 2 - popRect.width / 2,
        y: rect.bottom + margin,
      });
      // top
      candidates.push({
        name: 'top',
        x: rect.left + rect.width / 2 - popRect.width / 2,
        y: rect.top - popRect.height - margin,
      });
      // right
      candidates.push({
        name: 'right',
        x: rect.right + margin,
        y: rect.top + rect.height / 2 - popRect.height / 2,
      });
      // left
      candidates.push({
        name: 'left',
        x: rect.left - popRect.width - margin,
        y: rect.top + rect.height / 2 - popRect.height / 2,
      });

      // Put preferred first
      candidates.sort((a, b) => (a.name === prefer ? -1 : b.name === prefer ? 1 : 0));

      function fits(c) {
        return c.x >= margin && c.y >= margin && c.x + popRect.width <= vw - margin && c.y + popRect.height <= vh - margin;
      }

      const best = candidates.find(fits) || candidates[0];
      x = best.x;
      y = best.y;
    }

    x = clamp(Math.round(x), margin, Math.max(margin, vw - popRect.width - margin));
    y = clamp(Math.round(y), margin, Math.max(margin, vh - popRect.height - margin));

    popover.style.transform = `translate(${x}px, ${y}px)`;
  }

  function scrollIntoViewIfNeeded(targetEl) {
    if (!targetEl) return;
    try {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    } catch {
      // ignore
    }
  }

  function setHighlight(targetEl) {
    // Remove existing highlights
    document.querySelectorAll('.valido-tour-highlight').forEach(el => el.classList.remove('valido-tour-highlight'));
    if (targetEl) targetEl.classList.add('valido-tour-highlight');
  }

  function clearHighlight() {
    document.querySelectorAll('.valido-tour-highlight').forEach(el => el.classList.remove('valido-tour-highlight'));
  }

  function once(targetEl, eventName, handler, opts) {
    if (!targetEl) return () => {};
    const wrapped = (e) => {
      try { handler(e); } finally { targetEl.removeEventListener(eventName, wrapped, opts); }
    };
    targetEl.addEventListener(eventName, wrapped, opts);
    return () => targetEl.removeEventListener(eventName, wrapped, opts);
  }

  const Tour = {
    _active: false,
    _steps: [],
    _index: 0,
    _overlay: null,
    _storageKey: STORAGE_PREFIX + 'v1',
    _detachCurrent: null,

    isActive() {
      return !!this._active;
    },

    dismissPermanently() {
      try {
        localStorage.setItem(this._storageKey, 'dismissed');
      } catch {
        // ignore
      }
    },

    _shouldRun() {
      try {
        return localStorage.getItem(this._storageKey) !== 'dismissed';
      } catch {
        return true;
      }
    },

    maybeStart(steps, opts = {}) {
      try {
        this._storageKey = (opts.key || this._storageKey);
        if (!this._shouldRun()) return;
        const startDelayMs = Number.isFinite(opts.startDelayMs) ? opts.startDelayMs : 600;
        window.setTimeout(() => this.start(steps, opts), startDelayMs);
      } catch {
        // ignore
      }
    },

    start(steps, opts = {}) {
      try {
        if (this._active) return;
        this._storageKey = (opts.key || this._storageKey);
        this._steps = Array.isArray(steps) ? steps.slice() : [];
        if (!this._steps.length) return;

        // Telemetry: tour start
        sendTelemetry('tour_start', { key: this._storageKey, steps: this._steps.length });

        this._active = true;
        this._index = 0;
        this._overlay = createOverlay();
        document.body.appendChild(this._overlay);

        const dim = this._overlay.querySelector('.valido-tour-dim');
        const pop = this._overlay.querySelector('.valido-tour-popover');
        const titleEl = this._overlay.querySelector('.valido-tour-title');
        const bodyEl = this._overlay.querySelector('.valido-tour-body');
        const btnSkip = this._overlay.querySelector('.valido-tour-skip');
        const btnBack = this._overlay.querySelector('.valido-tour-back');
        const btnNext = this._overlay.querySelector('.valido-tour-next');

        const onNext = () => this.next();
        const onBack = () => this.back();
        const onSkip = () => this.stop({ dismiss: true });

        btnNext.addEventListener('click', onNext);
        btnBack.addEventListener('click', onBack);
        btnSkip.addEventListener('click', onSkip);

        // Click outside = next (keeps it simple)
        dim.addEventListener('click', onNext);

        // Reposition on resize/scroll
        const onRelayout = () => {
          const step = this._steps[this._index];
          const t = findTarget(step);
          positionPopover(pop, t, step?.placement);
        };
        window.addEventListener('resize', onRelayout);
        window.addEventListener('scroll', onRelayout, true);

        this._cleanupOverlayEvents = () => {
          try {
            btnNext.removeEventListener('click', onNext);
            btnBack.removeEventListener('click', onBack);
            btnSkip.removeEventListener('click', onSkip);
            dim.removeEventListener('click', onNext);
            window.removeEventListener('resize', onRelayout);
            window.removeEventListener('scroll', onRelayout, true);
          } catch {
            // ignore
          }
        };

        this._renderCurrent();
      } catch {
        // ignore
      }
    },

    stop({ dismiss } = {}) {
      try {
        this._active = false;
        this._steps = [];
        this._index = 0;

        if (typeof this._detachCurrent === 'function') {
          try { this._detachCurrent(); } catch { /* ignore */ }
        }
        this._detachCurrent = null;

        clearHighlight();

        if (this._cleanupOverlayEvents) {
          try { this._cleanupOverlayEvents(); } catch { /* ignore */ }
        }
        this._cleanupOverlayEvents = null;

        if (this._overlay) {
          this._overlay.remove();
        }
        this._overlay = null;

        if (dismiss) this.dismissPermanently();

        // Telemetry: tour finished
        sendTelemetry(dismiss ? 'tour_skip' : 'tour_complete', { key: this._storageKey });
      } catch {
        // ignore
      }
    },

    next() {
      try {
        if (!this._active) return;
        if (this._index >= this._steps.length - 1) {
          this.stop({ dismiss: true });
          return;
        }
        this._index += 1;
        this._renderCurrent();
      } catch {
        // ignore
      }
    },

    back() {
      try {
        if (!this._active) return;
        this._index = Math.max(0, this._index - 1);
        this._renderCurrent();
      } catch {
        // ignore
      }
    },

    _renderCurrent() {
      if (!this._overlay) return;

      // Detach previous step listeners
      if (typeof this._detachCurrent === 'function') {
        try { this._detachCurrent(); } catch { /* ignore */ }
      }
      this._detachCurrent = null;

      const step = this._steps[this._index];
      const pop = this._overlay.querySelector('.valido-tour-popover');
      const titleEl = this._overlay.querySelector('.valido-tour-title');
      const bodyEl = this._overlay.querySelector('.valido-tour-body');
      const btnBack = this._overlay.querySelector('.valido-tour-back');
      const btnNext = this._overlay.querySelector('.valido-tour-next');

      const t = findTarget(step);
      const targetVisible = isVisible(t);

      titleEl.textContent = step?.title || '';
      bodyEl.textContent = step?.body || '';

      // Telemetry: per-step impression
      sendTelemetry('tour_step', {
        key: this._storageKey,
        index: this._index,
        title: step?.title || ''
      });

      btnBack.style.display = this._index > 0 ? 'inline-flex' : 'none';
      btnNext.textContent = this._index >= this._steps.length - 1 ? 'Finish' : (step?.nextLabel || 'Next');

      if (targetVisible) {
        scrollIntoViewIfNeeded(t);
        setHighlight(t);
      } else {
        clearHighlight();
      }

      // Position after content changes
      // (needs rAF so popover rect is accurate)
      window.requestAnimationFrame(() => {
        positionPopover(pop, targetVisible ? t : null, step?.placement);
      });

      // Optional: auto-advance when user performs an action
      const detachFns = [];
      if (targetVisible && step?.advanceOn) {
        const { event, predicate } = step.advanceOn;
        if (event) {
          const detach = once(t, event, (e) => {
            try {
              if (typeof predicate === 'function' && !predicate(e)) return;
            } catch {
              // ignore
            }
            window.setTimeout(() => this.next(), 200);
          }, true);
          detachFns.push(detach);
        }
      }

      // Optional: run hook
      if (typeof step?.onShow === 'function') {
        try {
          step.onShow({ index: this._index, step, target: t });
        } catch {
          // ignore
        }
      }

      this._detachCurrent = () => {
        detachFns.forEach(fn => {
          try { fn(); } catch { /* ignore */ }
        });
      };
    }
  };

  window.ValidoTour = Tour;
})();
