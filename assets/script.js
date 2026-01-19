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

  async function loadNFLStats() {
    try {
        // Updated path to point correctly to the CSV file
        const response = await fetch('/stats/nflstats.xlsx');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.text();
        
        // Split by line and filter out empty rows or those starting with //
        const rows = data.split(/\r?\n/).filter(row => row.trim() !== '' && !row.startsWith('//'));
        
        const tbody = document.getElementById('stats-body');
        if (!tbody) return; // Ensure element exists

        // Clear existing rows (optional, but good practice)
        tbody.innerHTML = '';
        
        // Skip header row and iterate through data
        for (let i = 1; i < rows.length; i++) {
            const cols = rows[i].split(',');
            const tr = document.createElement('tr');
            
            cols.forEach(col => {
                const td = document.createElement('td');
                td.textContent = col.trim();
                tr.appendChild(td);
            });
            
            tbody.appendChild(tr);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadNFLStats);

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

      // Convert the string rating values to a number and format to one decimal place
      const formattedElo = n(r.Elo).toFixed(1);
      const formattedPoints = n(r.Points).toFixed(1);

      if (league === 'nhl') {
        // NHL: Rank, Team, Elo, Points
        // The original nhl.html template uses Elo and Points headers.
        rowHtml += `
          <td>${formattedElo}</td>
          <td>${formattedPoints}</td>
        `;
      } else if (league === 'nfl' || league === 'nba') {
        // NFL/NBA: Rank, Team, Elo, Wins, Losses
        rowHtml += `
          <td>${formattedElo}</td>
          <td>${r.Wins}</td>
          <td>${r.Losses}</td>
        `;
      } else {
        // CFB/College Basketball (mcbb, wcbb): Rank, Team, Elo, Wins, Losses, Conference
        rowHtml += `
          <td>${formattedElo}</td>
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

  // Controls
  const filterInput = qs('#filter')
  const sortSelect = qs('#sortBy')
  const rowsPerPageSelect = qs('#rowsPerPage')
  const weekFilterSelect = qs('#weekFilter') // New: Get the week filter control

  // League Type filter
  const leagueTypeSelect = qs('#leagueTypeFilter')

  // Existing control for conference filtering
  let conferenceSelect = qs('#conferenceFilter')
  // Check if conference filter needs dynamic injection (currently only for CFB that doesn't have it in HTML)
  if (!conferenceSelect) {
    // If not already in HTML, inject dynamically next to Sort by
    const sortRow = sortSelect?.closest('.row.small')
    // Added explicit check for 'cfb' since other leagues might not want this filter
    if (sortRow && league === 'cfb') { 
      const label = document.createElement('label')
      label.textContent = 'Conference'
      conferenceSelect = document.createElement('select')
      conferenceSelect.id = 'conferenceFilter'
      conferenceSelect.innerHTML = `<option value="all" selected>All Conferences</option>`
      sortRow.insertBefore(label, rowsPerPageSelect.closest('label').previousElementSibling)
      sortRow.insertBefore(conferenceSelect, rowsPerPageSelect.closest('label').previousElementSibling)
      // Add event listener immediately
      conferenceSelect.addEventListener('change', refresh) 
    }
  }

  let parsed = { headers: [], rows: [] }
  let allRows = [] // The main array that holds the full normalized data

  // New utility function to fetch and parse a CSV file
  async function fetchAndParseCSV(fileName) {
    const filePath = `/data/${fileName}`;
    try {
      const resp = await fetch(filePath, { cache: 'no-store' });
      if (!resp.ok) {
        // Use an intentional status code for "Not found, but expected to check"
        if (resp.status === 404) return { status: 404 };
        throw new Error(`Failed to fetch ${filePath}: ${resp.status} ${resp.statusText}`);
      }
      const txt = await resp.text();
      return { status: 200, data: parseCSV(txt) };
    } catch (err) {
      console.error(`Error loading CSV: ${filePath}`, err);
      // Return a status indicating a general failure
      return { status: 500, error: err };
    }
  }

  // New function to handle loading the selected data file and updating the table
  async function loadDataAndRefresh() {
    let fileName = `${league}.csv`;
    
    // Check if the current league supports a week filter and one is selected
    if (league === 'nfl' && weekFilterSelect && weekFilterSelect.value) {
      fileName = weekFilterSelect.value;
    }
    
    const result = await fetchAndParseCSV(fileName);
    
    if (result.status !== 200) {
      const tbody = qs('#teamsTable tbody');
      // Use the original CSV path for the error message, or the selected filename
      const displayPath = fileName;
      tbody.innerHTML = `<tr><td colspan="6">Unable to load rankings data from: /data/${displayPath}</td></tr>`;
      allRows = []; // Clear old data
      refresh(); // Re-render empty table
      return;
    }

    parsed = result.data;
    
    // Normalize data (common to all leagues)
    allRows = parsed.rows.map(r => ({
      Team: r.Team || r.team || '',
      Elo: (r.Elo || r.elo || r.Points || r.points || '0').toString(),
      Wins: r.Wins || r.wins || '',
      Losses: r.Losses || r.losses || '',
      Points: r.Points || r.points || '', 
      // Use 'Division' for NFL/NBA/NHL, 'Conference' for CBB/CFB where applicable
      Conference: r.Conference || r.conference || r.Division || r.Notes || ''
    }));

    // Re-run the conference population logic if present (currently only auto-populated for CFB)
    if (league === 'cfb' && conferenceSelect) {
      // Clear previous options except the default
      conferenceSelect.innerHTML = `<option value="all" selected>All Conferences</option>`;
      const uniqueConfs = [...new Set(allRows.map(r => r.Conference).filter(c => c && !['', 'FBS Independent'].includes(c)))].sort()
      uniqueConfs.forEach(conf => {
        const opt = document.createElement('option')
        opt.value = conf
        opt.textContent = conf
        conferenceSelect.appendChild(opt)
      })
    }

    refresh();
  }

  /**
   * Probes for NFL weekly files and populates the dropdown.
   */
  async function loadNFLWeekOptions() {
    if (league !== 'nfl' || !weekFilterSelect) return;

    let optionsHtml = '<option value="nfl.csv" selected>Current Week</option>';
    let foundAWeek = false;
    const maxWeek = 18; // Max regular season weeks

    // Probe for files starting from week 1, up to maxWeek
    for (let i = 1; i <= maxWeek; i++) {
        const weekFileName = `nfl_week_${i}.csv`;
        const weekLabel = `Week ${i}`;
        
        const result = await fetchAndParseCSV(weekFileName);

        if (result.status === 200) {
            optionsHtml += `<option value="${weekFileName}">${weekLabel}</option>`;
            foundAWeek = true;
        }
    }
    
    // Only display dynamic options if files are found. The HTML already contains 'Current Week'.
    if (foundAWeek) {
        weekFilterSelect.innerHTML = optionsHtml;
    }
  }


  function applyFiltersAndSort() {
    const q = filterInput ? filterInput.value.trim().toLowerCase() : ''
    // Check if conferenceSelect exists before reading its value
    const selectedConf = conferenceSelect ? conferenceSelect.value : 'all'
    const selectedLeagueType = leagueTypeSelect ? leagueTypeSelect.value : 'fbs' // Default to FBS

    let out = allRows.filter(r => { // <--- Uses allRows
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
  
  // Initial setup for the selected league
  if (league === 'nfl') {
    // NFL has the new week filter logic
    loadNFLWeekOptions();
    
  } 
  
  // Start data load on initial page load for all leagues
  loadDataAndRefresh();


  // Bind events
  if (filterInput) filterInput.addEventListener('input', refresh)
  if (sortSelect) sortSelect.addEventListener('change', refresh)
  if (rowsPerPageSelect) rowsPerPageSelect.addEventListener('change', refresh)
  // For CFB: conferenceSelect listener is added dynamically if needed
  if (leagueTypeSelect) leagueTypeSelect.addEventListener('change', refresh)
  
  // New week filter event listener (only relevant for NFL)
  if (weekFilterSelect) {
      weekFilterSelect.addEventListener('change', loadDataAndRefresh);
  }

})



