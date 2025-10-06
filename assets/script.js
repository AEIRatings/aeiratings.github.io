// AEIRatings front-end script
document.addEventListener('DOMContentLoaded', async () => {

  // Helpers
  const qs = (sel) => document.querySelector(sel)
  const n = (v) => Number(v) || 0

  function parseCSV(text) {
    const [headerLine, ...lines] = text.trim().split(/\r?\n/)
    const headers = headerLine.split(',').map(h => h.trim())
    const rows = lines.map(line => {
      const cols = line.split(',')
      const obj = {}
      headers.forEach((h, i) => obj[h] = (cols[i] || '').trim())
      return obj
    })
    return { headers, rows }
  }

  function renderTable(data, headers) {
    const tbody = qs('#teamsTable tbody')
    tbody.innerHTML = ''
    data.forEach((r, i) => {
      const tr = document.createElement('tr')
      tr.innerHTML = `
        <td>${i + 1}</td>
        <td>${r.Team}</td>
        <td>${r.Elo}</td>
        <td>${r.Wins}</td>
        <td>${r.Losses}</td>
        <td>${r.Conference}</td>
      `
      tbody.appendChild(tr)
    })
  }

  // Determine which league we’re on
  const main = document.querySelector('main[data-league]')
  if (!main) return // skip if not a league page (e.g. index.html)
  const league = main.getAttribute('data-league')
  const csvPath = `/data/${league}.csv`

  // Controls
  const filterInput = qs('#filter')
  const sortSelect = qs('#sortBy')
  const rowsPerPageSelect = qs('#rowsPerPage')

  let parsed = { headers: [], rows: [] }
  try {
    const resp = await fetch(csvPath, { cache: 'no-store' })
    if (!resp.ok) throw new Error('Not found')
    const txt = await resp.text()
    parsed = parseCSV(txt)
  } catch (err) {
    const tbody = qs('#teamsTable tbody')
    tbody.innerHTML = `<tr><td colspan="6">Unable to load CSV: ${csvPath}</td></tr>`
    console.error(err)
    return
  }

  // Normalize
  const rows = parsed.rows.map(r => ({
    Team: r.Team || r.team || '',
    Elo: (n(r.Elo || r.elo)).toString(),
    Wins: r.Wins || r.wins || '',
    Losses: r.Losses || r.losses || '',
    Conference: r.Conference || r.conference || r.Notes || ''
  }))

  function applyFiltersAndSort() {
    const q = filterInput ? filterInput.value.trim().toLowerCase() : ''
    let out = rows.filter(r => {
      if (!q) return true
      return (r.Team || '').toLowerCase().includes(q) ||
             (r.Conference || '').toLowerCase().includes(q)
    })

    const sortBy = sortSelect ? sortSelect.value : 'elo'
    if (sortBy === 'elo') out.sort((a, b) => n(b.Elo) - n(a.Elo))
    else if (sortBy === 'team') out.sort((a, b) => (a.Team || '').localeCompare(b.Team || ''))
    else if (sortBy === 'wins') out.sort((a, b) => n(b.Wins) - n(a.Wins))

    const rowsPerPage = Number(rowsPerPageSelect ? rowsPerPageSelect.value : 0)
    return rowsPerPage > 0 ? out.slice(0, rowsPerPage) : out
  }

  function refresh() {
    const shown = applyFiltersAndSort()
    renderTable(shown, parsed.headers)
  }

  // Bind events
  if (filterInput) filterInput.addEventListener('input', refresh)
  if (sortSelect) sortSelect.addEventListener('change', refresh)
  if (rowsPerPageSelect) rowsPerPageSelect.addEventListener('change', refresh)

  // Initial render
  refresh()
})
