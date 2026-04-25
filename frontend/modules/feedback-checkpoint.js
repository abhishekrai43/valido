(() => {
  const STORAGE_KEY = 'valido.feedback.checkpoint.v1';
  const MIN_TEXT_LENGTH = 20;

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return {
          defers: 0,
          submitted: false,
          blocked: false,
          runContext: null
        };
      }
      const parsed = JSON.parse(raw);
      return {
        defers: Number(parsed.defers) || 0,
        submitted: !!parsed.submitted,
        blocked: !!parsed.blocked,
        runContext: parsed.runContext || null
      };
    } catch {
      return { defers: 0, submitted: false, blocked: false, runContext: null };
    }
  }

  function writeState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // ignore storage failures
    }
  }

  async function sendTelemetry(action, details) {
    try {
      await fetch('/api/v1/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, details: details || undefined })
      });
    } catch {
      // best effort
    }
  }

  function isRunStartBlocked() {
    const state = readState();
    return state.blocked && !state.submitted;
  }

  function recordRunContext(context) {
    const state = readState();
    state.runContext = context || null;
    state.submitted = false;
    writeState(state);
  }

  function markSuccessfulDownload(context) {
    const state = readState();
    state.runContext = context || state.runContext;
    writeState(state);

    sendTelemetry('result_downloaded', {
      feedback_state: {
        defers: state.defers,
        blocked: state.blocked,
        submitted: state.submitted
      },
      ...(state.runContext || {})
    });

    if (!state.submitted) {
      showModal({ blocking: false });
    }
  }

  function removeExistingModal() {
    const existing = document.getElementById('feedbackCheckpointModal');
    if (existing) existing.remove();
  }

  function showModal({ blocking }) {
    const state = readState();
    const effectiveBlocking = blocking || (state.blocked && !state.submitted);

    removeExistingModal();

    const modal = document.createElement('div');
    modal.id = 'feedbackCheckpointModal';
    modal.className = 'feedback-checkpoint-modal';
    modal.innerHTML = `
      <div class="feedback-checkpoint-overlay"></div>
      <div class="feedback-checkpoint-card" role="dialog" aria-modal="true">
        <h3>${effectiveBlocking ? 'Feedback Required Before Next Run' : 'Quick Feedback Before Your Next Run'}</h3>
        <p>
          ${effectiveBlocking
            ? 'Please submit brief feedback to continue starting new validation runs.'
            : 'Tell us what worked (or did not). You can defer this twice, then feedback becomes required.'}
        </p>
        <form id="feedbackCheckpointForm" class="feedback-checkpoint-form">
          <label for="feedbackCategory">Category</label>
          <select id="feedbackCategory" required>
            <option value="">Select one</option>
            <option value="ease_of_use">Ease of use</option>
            <option value="accuracy">Validation accuracy</option>
            <option value="performance">Speed/performance</option>
            <option value="automation_cloud">Automation/cloud setup</option>
            <option value="export_results">Export/results quality</option>
            <option value="other">Other</option>
          </select>

          <label for="feedbackText">What should we improve?</label>
          <textarea id="feedbackText" minlength="${MIN_TEXT_LENGTH}" required placeholder="Please include what you expected, what happened, and what would make this better."></textarea>

          <div class="feedback-checkpoint-actions">
            <button type="submit" class="btn btn-primary">Submit Feedback</button>
            ${effectiveBlocking ? '' : '<button type="button" id="feedbackCheckpointDefer" class="btn btn-ghost">Defer for now</button>'}
          </div>
          <div id="feedbackCheckpointError" class="feedback-checkpoint-error" style="display:none"></div>
        </form>
      </div>
    `;

    document.body.appendChild(modal);

    sendTelemetry('feedback_checkpoint_shown', {
      blocking: effectiveBlocking,
      defers: state.defers,
      ...(state.runContext || {})
    });

    const form = modal.querySelector('#feedbackCheckpointForm');
    const errorEl = modal.querySelector('#feedbackCheckpointError');
    const deferBtn = modal.querySelector('#feedbackCheckpointDefer');

    if (deferBtn) {
      deferBtn.addEventListener('click', () => {
        const next = readState();
        next.defers += 1;
        next.blocked = next.defers >= 2;
        next.submitted = false;
        writeState(next);

        sendTelemetry('feedback_checkpoint_deferred', {
          defers: next.defers,
          blocked: next.blocked,
          ...(next.runContext || {})
        });

        modal.remove();
      });
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const category = modal.querySelector('#feedbackCategory').value;
      const text = modal.querySelector('#feedbackText').value.trim();

      if (!category) {
        errorEl.style.display = 'block';
        errorEl.textContent = 'Please select a category.';
        return;
      }
      if (text.length < MIN_TEXT_LENGTH) {
        errorEl.style.display = 'block';
        errorEl.textContent = `Please enter at least ${MIN_TEXT_LENGTH} characters.`;
        return;
      }

      const next = readState();
      next.submitted = true;
      next.blocked = false;
      writeState(next);

      await sendTelemetry('feedback_submitted', {
        category,
        feedback_text: text,
        run_stage: 'post_result_download',
        ...(next.runContext || {})
      });

      modal.remove();
    });

    modal.querySelector('.feedback-checkpoint-overlay')?.addEventListener('click', () => {
      if (!effectiveBlocking) {
        modal.remove();
      }
    });
  }

  function showBlockingModal() {
    showModal({ blocking: true });
  }

  window.ValidoFeedbackCheckpoint = {
    isRunStartBlocked,
    recordRunContext,
    markSuccessfulDownload,
    showBlockingModal
  };
})();
