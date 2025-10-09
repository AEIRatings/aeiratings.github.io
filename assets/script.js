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

  // League Type filter
  const leagueTypeSelect = qs('#leagueTypeFilter')

  // Existing control for conference filtering
  let conferenceSelect = qs('#conferenceFilter')
  if (!conferenceSelect) {
    // If not already in HTML, inject dynamically next to Sort by
    const sortRow = sortSelect?.closest('.row.small')
    if (sortRow) {
      const label = document.createElement('label')
      label.textContent = 'Conference'
      conferenceSelect = document.createElement('select')
      conferenceSelect.id = 'conferenceFilter'
      conferenceSelect.innerHTML = `<option value="all" selected>All Conferences</option>`
      // The original script injected this logic, but with the HTML modification above, this section
      // for conferenceSelect is largely unnecessary, but we'll leave it as a safeguard.

      // We'll skip the original dynamic injection logic since we modified the HTML
      // for the cfb page.
    }
  }

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

  // Define the FBS Conferences based on user request and CSV data consistency
  const FBS_CONFERENCES = [
    'American', 'ACC', 'Big 10', 'Big 12', 'CUSA', 'MAC', 'PAC 12', 'SEC', 'Sun Belt', 'Mountain West', 'FBS Independent'
  ];

  function isFBS(conference) {
    return FBS_CONFERENCES.includes(conference)
  }

  // Populate conference dropdown
  const uniqueConfs = [...new Set(rows.map(r => r.Conference).filter(Boolean))].sort()
  uniqueConfs.forEach(conf => {
    const opt = document.createElement('option')
    opt.value = conf
    opt.textContent = conf
    // Ensure the select element exists before appending
    if(conferenceSelect) conferenceSelect.appendChild(opt)
  })

  function applyFiltersAndSort() {
    const q = filterInput ? filterInput.value.trim().toLowerCase() : ''
    const selectedConf = conferenceSelect ? conferenceSelect.value : 'all'
    const selectedLeagueType = leagueTypeSelect ? leagueTypeSelect.value : 'fbs' // Default to FBS

    let out = rows.filter(r => {
      // 1. League Type Filter
      let matchesLeagueType = true
      if (selectedLeagueType === 'fbs') {
        matchesLeagueType = isFBS(r.Conference)
      } else if (selectedLeagueType === 'fcs') {
        matchesLeagueType = !isFBS(r.Conference)
      }
      if (!matchesLeagueType) return false


      // 2. Text search
      const matchesText = !q || (r.Team || '').toLowerCase().includes(q) || (r.Conference || '').toLowerCase().includes(q)
      if (!matchesText) return false
      
      // 3. Conference filter
      const matchesConf = selectedConf === 'all' || r.Conference === selectedConf

      return matchesText && matchesConf
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
  if (conferenceSelect) conferenceSelect.addEventListener('change', refresh)
  // Bind the new filter
  if (leagueTypeSelect) leagueTypeSelect.addEventListener('change', refresh)

  // Initial render
  refresh()
})
