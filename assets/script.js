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
    // Convert to lowercase, replace spaces with underscores, and remove non-alphanumeric/underscore characters
    return teamName.toLowerCase().trim().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
  }

  function getLogoPath(teamName, league) {
    if (!teamName || !league) return ''
    const normalizedName = normalizeTeamName(teamName)
    // Constructs the path: /logos/{league}/{normalized_team_name}.png
    return `/logos/${league}/${normalizedName}.png`
  }

  // Define the FBS Conferences for filtering the CFB Top 5
  const FBS_CONFERENCES = [
    'American', 'ACC', 'Big 10', 'Big 12', 'CUSA', 'MAC', 'PAC 12', 'SEC', 'Sun Belt', 'Mountain West', 'FBS Independent'
  ];

  function isFBS(conference) {
    return FBS_CONFERENCES.includes(conference)
  }

  // --- NEW HOMEPAGE LOGIC ---

  const LEAGUES = {
    'nfl': { name: 'NFL', file: 'nfl.csv', id: 'top-5-nfl' },
    'cfb': { name: 'College Football', file: 'cfb.csv', id: 'top-5-cfb' },
    'mcbb': { name: "NCAA Men's Basketball", file: 'mcbb.csv', id: 'top-5-mcbb' },
    'wcbb': { name: "NCAA Women's Basketball", file: 'wcbb.csv', id: 'top-5-wcbb' },
    'nba': { name: 'NBA', file: 'nba.csv', id: 'top-5-nba' },
    'nhl': { name: 'NHL', file: 'nhl.csv', id: 'top-5-nhl' },
  };

  /**
   * Filters (for CFB) and sorts the data to return the top N teams by Elo/rating.
   * Assumes incoming 'rows' are already normalized to contain 'Team', 'Elo' (as string), and 'Conference' (for CFB).
   * @param {Array<Object>} rows - The normalized rows of data.
   * @param {string} leagueId - The league ID to apply specific filters (like CFB/FBS).
   * @returns {Array<Object>} The top 5 teams with numeric Elo.
   */
  function getTop5Teams(rows, leagueId) {
    
    let filteredRows = rows;
    
    // **APPLY FBS FILTER FOR COLLEGE FOOTBALL**
    if (leagueId === 'cfb') {
        filteredRows = filteredRows.filter(r => isFBS(r.Conference));
    }

    // Convert Elo string to number for sorting and filter out bad data
    // This step is now explicit and robust.
    const finalRows = filteredRows.map(r => ({
        Team: r.Team, 
        Elo: n(r.Elo), // Correctly converts the 'Elo' property (which contains the string rating) to a number
    })).filter(r => r.Team && r.Elo > 0);

    // Sort by Elo in descending order
    finalRows.sort((a, b) => b.Elo - a.Elo);

    return finalRows.slice(0, 5);
  }

  /**
   * Renders the top 5 teams into the dedicated div on the homepage.
   * @param {string} leagueId - The league ID (e.g., 'nfl', 'mcbb').
   * @param {Array<Object>} topTeams - The top 5 teams data.
   */
  function renderTop5(leagueId, topTeams) {
    const container = qs(`#${LEAGUES[leagueId].id}`);
    if (!container) return;

    // Check if the league is CFB and specifically report if no FBS teams are found
    if (leagueId === 'cfb' && topTeams.length === 0) {
        container.innerHTML = `<p class="top-5-placeholder">No FBS ratings found.</p>`;
        return;
    }
    
    if (topTeams.length === 0) {
        container.innerHTML = `<p class="top-5-placeholder">Ratings data not available.</p>`;
        return;
    }

    // Determine the logo path for College sports
    const logoLeague = (leagueId === 'mcbb' || leagueId === 'wcbb') ? 'cfb' : leagueId;

    let html = `<h3>Top 5 Elo Ratings</h3><ol class="top-5-list">`;
    topTeams.forEach((team, index) => {
        const logoPath = getLogoPath(team.Team, logoLeague);
        const rank = index + 1;
        html += `
            <li>
                <span class="top-5-rank">${rank}.</span>
                <span class="top-5-team">
                    <img src="${logoPath}" alt="${team.Team} Logo" class="team-logo" onerror="this.style.display='none'">
                    <span class="team-name-text">${team.Team}</span>
                </span>
                <span class="top-5-elo">${team.Elo.toFixed(1)}</span>
            </li>
        `;
    });
    html += `</ol>`;
    container.innerHTML = html;
  }

  async function loadHomePageRatings() {
    const leagueKeys = Object.keys(LEAGUES);
    const promises = leagueKeys.map(async (key) => {
        const league = LEAGUES[key];
        const csvPath = `/data/${league.file}`;
        try {
            const resp = await fetch(csvPath, { cache: 'no-store' });
            if (!resp.ok) throw new Error('Not found');
            const text = await resp.text();
            const parsed = parseCSV(text);
            
            // Normalize all necessary fields once for use in filtering and sorting
            const normalizedRows = parsed.rows.map(r => ({
              Team: r.Team || r.team || '',
              // Consolidate the rating into a single 'Elo' property as a string
              Elo: r.Elo || r.elo || r.Points || r.points || '0', 
              Wins: r.Wins || r.wins || '',
              Losses: r.Losses || r.losses || '',
              // Important: Capture Conference/Division/Notes for FBS check
              Conference: r.Conference || r.conference || r.Division || r.Notes || ''
            }));

            // Pass the normalized rows and league key for filtering/sorting
            const top5 = getTop5Teams(normalizedRows, key);
            renderTop5(key, top5);
        } catch (error) {
            console.error(`Failed to load or parse ${league.file}:`, error);
            // Render a placeholder on error
            const container = qs(`#${league.id}`);
            if(container) container.innerHTML = `<p class="top-5-placeholder">Failed to load rankings.</p>`;
        }
    });
    await Promise.all(promises);
  }
  // --- END NEW HOMEPAGE LOGIC ---


  // Determine which league we’re on
  const main = document.querySelector('main[data-league]')
  if (!main) {
      // This is the index.html page
      loadHomePageRatings();
      return // Stop execution of league-specific logic
  }

  // If on a league page, proceed with league-specific logic

  const league = main.getAttribute('data-league')
  const csvPath = `/data/${league}.csv`

  // *MODIFIED RENDERER*: Handles different table layouts for different leagues
  function renderTable(data, headers) {
    const tbody = qs('#teamsTable tbody')
    tbody.innerHTML = ''
    
    const isCollegeBasketball = league === 'mcbb' || league === 'wcbb';
    const logoLeague = isCollegeBasketball ? 'cfb' : league;

    data.forEach((r, i) => {
      const tr = document.createElement('tr')

      // Get the logo path for the team
      const logoPath = getLogoPath(r.Team, logoLeague)

      // Create the Team cell content with the logo. onerror hides the image if the file is not found.
      const teamCellContent = `
        <img src="${logoPath}" alt="${r.Team} Logo" class="team-logo" onerror="this.style.display='none'">
        <span class="team-name-text">${r.Team}</span>
      `
      
      let rowHtml = `<td>${i + 1}</td><td class="team-cell">${teamCellContent}</td>`;

      if (league === 'nhl') {
        // NHL: Rank, Team, Elo, Points
        // The original nhl.html template uses Elo and Points headers.
        rowHtml += `
          <td>${r.Elo}</td>
          <td>${r.Points}</td>
        `;
      } else if (league === 'nfl' || league === 'nba') {
        // NFL/NBA: Rank, Team, Elo, Wins, Losses
        rowHtml += `
          <td>${r.Elo}</td>
          <td>${r.Wins}</td>
          <td>${r.Losses}</td>
        `;
      } else {
        // CFB/College Basketball (mcbb, wcbb): Rank, Team, Elo, Wins, Losses, Conference
        rowHtml += `
          <td>${r.Elo}</td>
          <td>${r.Wins}</td>
          <td>${r.Losses}</td>
          <td>${r.Conference}</td>
        `;
      }
      
      tr.innerHTML = rowHtml;
      tbody.appendChild(tr)
    })
  }
  // *END MODIFIED RENDERER*

  function isFBS(conference) {
    return FBS_CONFERENCES.includes(conference)
  }

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

  // Normalize data for filtering and sorting on league pages
  // Note: This block converts the relevant rating column to a string 'Elo' for consistency.
  const rows = parsed.rows.map(r => ({
    Team: r.Team || r.team || '',
    Elo: (r.Elo || r.elo || r.Points || r.points || '0').toString(), // The rating is stored as string 'Elo'
    Wins: r.Wins || r.wins || '',
    Losses: r.Losses || r.losses || '',
    Points: r.Points || r.points || '', // Keep Points for NHL if present
    Conference: r.Conference || r.conference || r.Division || r.Notes || ''
  }))

  // Populate conference dropdown (only runs if conferenceSelect exists)
  if (conferenceSelect) {
      // Filter out empty or non-useful conference names for display
      const uniqueConfs = [...new Set(rows.map(r => r.Conference).filter(c => c && !['', 'FBS Independent'].includes(c)))].sort()
      uniqueConfs.forEach(conf => {
        const opt = document.createElement('option')
        opt.value = conf
        opt.textContent = conf
        conferenceSelect.appendChild(opt)
      })
  }

  function applyFiltersAndSort() {
    const q = filterInput ? filterInput.value.trim().toLowerCase() : ''
    // Check if conferenceSelect exists before reading its value
    const selectedConf = conferenceSelect ? conferenceSelect.value : 'all'
    const selectedLeagueType = leagueTypeSelect ? leagueTypeSelect.value : 'fbs' // Default to FBS

    let out = rows.filter(r => {
      // 1. League Type Filter
      let matchesLeagueType = true
      if (league === 'cfb') { // Only apply this logic for CFB
        if (selectedLeagueType === 'fbs') {
          matchesLeagueType = isFBS(r.Conference)
        } else if (selectedLeagueType === 'fcs') {
          matchesLeagueType = !isFBS(r.Conference)
        }
      }
      if (!matchesLeagueType) return false


      // 2. Text search
      const matchesText = !q || (r.Team || '').toLowerCase().includes(q) || (r.Conference || '').toLowerCase().includes(q)
      if (!matchesText) return false
      
      // 3. Conference filter (only applies if the element exists)
      const matchesConf = !conferenceSelect || selectedConf === 'all' || r.Conference === selectedConf

      return matchesText && matchesConf
    })

    const sortBy = sortSelect ? sortSelect.value : 'elo'
    // Ensure sorting correctly handles different rating columns for different leagues
    const sortKey = (league === 'nhl' && sortBy === 'points') ? 'Points' : 'Elo';
    
    // Sort by converting the string value of the relevant key to a number
    if (sortBy === 'elo' || sortBy === 'points') out.sort((a, b) => n(b[sortKey]) - n(a[sortKey]))
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
