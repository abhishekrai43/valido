const API = '/api/v1/rulesets/'

async function listRulesets() {
  const res = await fetch(API + '/')
  const data = await res.json()
  const container = document.getElementById('list')
  container.innerHTML = ''
  data.forEach(r => {
    const el = document.createElement('div')
    el.className = 'ruleset' + (r.is_active ? ' active' : '')
    el.innerHTML = `<strong>${r.name}</strong> <button data-id="${r.id}" class="act">Activate</button> <pre>${JSON.stringify(r.rules, null, 2)}</pre>`
    container.appendChild(el)
  })

  // attach handlers
  document.querySelectorAll('.act').forEach(b => b.addEventListener('click', async (ev) => {
    const id = ev.target.getAttribute('data-id')
    await fetch(`${API}/${id}/activate`, { method: 'POST' })
    listRulesets()
  }))
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

  const res = await fetch(API + '/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, rules }) })
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
