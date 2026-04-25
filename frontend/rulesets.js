const API = '/api/v1/rulesets/'

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function setStatusMessage(message) {
  const container = document.getElementById('list')
  container.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`
}

async function listRulesets() {
  const container = document.getElementById('list')
  setStatusMessage('Loading rulesets...')

  try {
    const res = await fetch(API + '/')
    if (!res.ok) {
      throw new Error(`Failed with status ${res.status}`)
    }

    const data = await res.json()
    container.innerHTML = ''

    if (!Array.isArray(data) || data.length === 0) {
      setStatusMessage('No rulesets yet. Create your first ruleset above.')
      return
    }

    data.forEach(r => {
      const el = document.createElement('article')
      el.className = 'ruleset' + (r.is_active ? ' active' : '')
      const name = escapeHtml(r.name || 'Untitled ruleset')
      const prettyRules = escapeHtml(JSON.stringify(r.rules || {}, null, 2))

      el.innerHTML = `
        <div class="ruleset-head">
          <div>
            <div class="ruleset-title">${name}</div>
            <span class="status-pill${r.is_active ? ' active' : ''}">${r.is_active ? 'Active' : 'Inactive'}</span>
          </div>
          <button data-id="${r.id}" class="btn btn-ghost act" type="button">Set Active</button>
        </div>
        <details>
          <summary>View Rules JSON</summary>
          <pre>${prettyRules}</pre>
        </details>
      `
      container.appendChild(el)
    })

    // attach handlers
    document.querySelectorAll('.act').forEach(b => b.addEventListener('click', async (ev) => {
      const id = ev.target.getAttribute('data-id')
      try {
        await fetch(`${API}/${id}/activate`, { method: 'POST' })
        listRulesets()
      } catch (err) {
        alert('Could not activate ruleset. Please try again.')
      }
    }))
  } catch (err) {
    setStatusMessage('Unable to load rulesets. Check backend connectivity and refresh.')
  }
}

document.getElementById('create').addEventListener('click', async () => {
  const name = document.getElementById('rs-name').value
  let rulesText = document.getElementById('rs-json').value
  let rules = {}
  try {
    rules = rulesText ? JSON.parse(rulesText) : {}
  } catch (e) {
    alert('Invalid JSON in rules')
    return
  }

  if (!name.trim()) {
    alert('Please enter a ruleset name')
    return
  }

  const res = await fetch(API + '/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name.trim(), rules }) })
  if (res.status === 201 || res.status === 200) {
    document.getElementById('rs-name').value = ''
    document.getElementById('rs-json').value = ''
    listRulesets()
  } else {
    const err = await res.json()
    alert('Error: ' + (err.detail || res.status))
  }
})

// initial load
listRulesets()
