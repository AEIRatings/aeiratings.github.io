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

  function normalizeTeamName(teamName) {
    return teamName.toLowerCase().trim().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
  }

  function getLogoPath(teamName, league) {
    if (!teamName || !league) return ''
    const normalizedName = normalizeTeamName(teamName)
    return `/logos/${league}/${normalizedName}.png`
  }

  const FBS_CONFERENCES = [
    'American', 'ACC', 'Big 10', 'Big 12', 'CUSA', 'MAC', 'PAC 12', 'SEC', 'Sun Belt', 'Mountain West', 'FBS Independent'
  ];

  function isFBS(conference) {
    return FBS_CONFERENCES.includes(conference)
  }

  const LEAGUES = {
    'nfl': { name: 'NFL', file: 'nfl.csv', id: 'top-5-nfl' },
    'cfb': { name: 'College Football', file: 'cfb.csv', id: 'top-5-cfb' },
    'mcbb': { name: "NCAA Men's Basketball", file: 'mcbb.csv', id: 'top-5-mcbb' },
    'wcbb': { name: "NCAA Women's Basketball", file: 'wcbb.csv', id: 'top-5-wcbb' },
    'nba': { name: 'NBA', file: 'nba.csv', id: 'top-5-nba' },
    'nhl': { name: 'NHL', file: 'nhl.csv', id: 'top-5-nhl' },
  };

  async function loadHomePageRatings() {
    for (const [key, leagueInfo] of Object.entries(LEAGUES)) {
      try {
        const resp = await fetch(`/data/${leagueInfo.file}`)
        if (!resp.ok) continue
        const text = await resp.text()
        const parsed = parseCSV(text)
        const top5 = getTop5Teams(parsed.rows, key)
        renderTop5(key, top5)
      } catch (err) {
        console.error(`Error loading homepage ${key}:`, err)
      }
    }
  }

  function getTop5Teams(rows, leagueId) {
    let filteredRows = rows;
    if (leagueId === 'cfb') {
        filteredRows = filteredRows.filter(r => isFBS(r.Conference));
    }
    const finalRows = filteredRows.map(r => ({
        Team: r.Team, 
        Elo: n(r.Elo),
    })).filter(r => r.Team && r.Elo > 0);
    finalRows.sort((a, b) => b.Elo - a.Elo);
    return finalRows.slice(0, 5);
  }

  function renderTop5(leagueId, topTeams) {
    const container = qs(`#${LEAGUES[leagueId].id}`);
    if (!container) return;
    if (topTeams.length === 0) {
        container.innerHTML = `<p class="top-5-placeholder">Ratings data not available.</p>`;
        return;
    }

    let html = '<table class="top-5-table"><tbody>';
    topTeams.forEach((team, idx) => {
      const logoPath = getLogoPath(team.Team, leagueId);
      html += `
        <tr>
          <td class="rank-col">${idx + 1}</td>
          <td class="team-col">
            <img src="${logoPath}" class="top-5-logo" onerror="this.style.visibility='hidden'">
            <span>${team.Team}</span>
          </td>
          <td class="elo-col">${team.Elo.toFixed(1)}</td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  const main = document.querySelector('main[data-league]')
  if (!main) {
    loadHomePageRatings();
    return
  }

  const league = main.getAttribute('data-league')

  // UPDATED RENDERER: Handles NHL specifically and fallback for other leagues
  function renderTable(data, headers) {
    const tbody = qs('#teamsTable tbody')
    if (!tbody) return;
    tbody.innerHTML = ''
    
    const isCollegeBasketball = league === 'mcbb' || league === 'wcbb';
    const logoLeague = isCollegeBasketball ? 'cfb' : league;

    data.forEach((r, i) => {
      const tr = document.createElement('tr')
      const logoPath = getLogoPath(r.Team, logoLeague)
      
      const teamCellContent = `
        <img src="${logoPath}" alt="${r.Team} Logo" class="team-logo" onerror="this.style.display='none'">
        <span class="team-name-text">${r.Team}</span>
      `

      // Logic to determine which columns to show based on CSV headers
      let rowHtml = `<td>${i + 1}</td><td class="team-cell">${teamCellContent}</td>`;
      
      if (headers.includes('Elo')) {
        rowHtml += `<td>${n(r.Elo).toFixed(1)}</td>`;
      }
      
      // Add Division (NHL) or Conference (Other leagues) if present
      if (headers.includes('Division')) {
        rowHtml += `<td class="hide-mobile">${r.Division}</td>`;
      } else if (headers.includes('Conference')) {
        rowHtml += `<td class="hide-mobile">${r.Conference}</td>`;
      }

      tr.innerHTML = rowHtml
      tbody.appendChild(tr)
    })
  }

  const filterInput = qs('#filter')
  const sortSelect = qs('#sortSelect')
  const rowsPerPageSelect = qs('#rowsPerPage')
  const paginationDiv = qs('#pagination')
  const weekFilterSelect = qs('#weekFilter')

  let parsed = { headers: [], rows: [] }
  let allRows = []
  let currentPage = 1

  async function loadData(fileName) {
    const resp = await fetch(`/data/${fileName}`, { cache: 'no-store' })
    const text = await resp.text()
    parsed = parseCSV(text)
    allRows = parsed.rows
    currentPage = 1
    refresh()
  }

  function refresh() {
    const shown = applyFiltersAndSort()
    renderTable(shown, parsed.headers)
  }

  function applyFiltersAndSort() {
    let filtered = [...allRows]
    const val = filterInput.value.toLowerCase()
    if (val) {
      filtered = filtered.filter(r => 
        r.Team.toLowerCase().includes(val) || 
        (r.Conference && r.Conference.toLowerCase().includes(val)) ||
        (r.Division && r.Division.toLowerCase().includes(val))
      )
    }

    const sortVal = sortSelect.value
    filtered.sort((a, b) => {
      if (sortVal === 'eloDesc') return n(b.Elo) - n(a.Elo)
      if (sortVal === 'eloAsc') return n(a.Elo) - n(b.Elo)
      if (sortVal === 'teamAsc') return a.Team.localeCompare(b.Team)
      return 0
    })

    return filtered
  }

  filterInput.addEventListener('input', refresh)
  sortSelect.addEventListener('change', refresh)

  loadData(LEAGUES[league].file)
})
