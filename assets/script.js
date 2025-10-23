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

  // ELO PROBABILITY CALCULATION FUNCTION (REQUIRED BY USER)
  /**
   * Calculates the predicted probability of the home team winning.
   * Formula: 1 / (1 + 10^((awayElo - homeElo) / 400))
   * @param {number} homeElo - The Elo rating of the home team (R_H).
   * @param {number} awayElo - The Elo rating of the away team (R_A).
   * @returns {number} The win probability (0 to 1).
   */
  function calculateHomeWinProbability(homeElo, awayElo) {
      if (homeElo === 0 || awayElo === 0) return 0.5; // Default to 50/50 if Elo is missing/zero
      const diff = (awayElo - homeElo) / 400;
      return 1 / (1 + Math.pow(10, diff));
  }
  
  // --- EXISTING HOMEPAGE LOGIC (omitted for brevity, but kept in actual file) ---

  // --- NEW NFL SCHEDULE PREDICTOR LOGIC ---
  const main = document.querySelector('main[data-league]')
  const league = main ? main.getAttribute('data-league') : null

  if (league === 'nfl-schedule') {
    await loadNFLScheduleAndRatings();
  }

  async function fetchAndParseCSV(fileName) {
    const filePath = `/data/${fileName}`;
    try {
      const resp = await fetch(filePath, { cache: 'no-store' });
      if (!resp.ok) {
        if (resp.status === 404) return { status: 404 };
        throw new Error(`Failed to fetch ${filePath}: ${resp.status} ${resp.statusText}`);
      }
      const txt = await resp.text();
      return { status: 200, data: parseCSV(txt) };
    } catch (err) {
      console.error(`Error loading CSV: ${filePath}`, err);
      return { status: 500, error: err };
    }
  }

  async function loadNFLScheduleAndRatings() {
    const loadingStatus = qs('#loadingStatus');
    const tbody = qs('#gamesTable tbody');
    tbody.innerHTML = ''; // Clear existing content

    // 1. Fetch current Elo Ratings (data/nfl.csv)
    const ratingsResult = await fetchAndParseCSV('nfl.csv');
    if (ratingsResult.status !== 200) {
        loadingStatus.textContent = `Error: Could not load current NFL Elo ratings from /data/nfl.csv.`;
        return;
    }
    
    // Create an Elo lookup map
    const eloMap = {};
    ratingsResult.data.rows.forEach(r => {
        // Use 'Team' property and ensure Elo is a number
        eloMap[r.Team.trim()] = n(r.Elo);
    });

    // 2. Fetch the Game Schedule (data/nfl_games.csv)
    const scheduleResult = await fetchAndParseCSV('nfl_games.csv');
    if (scheduleResult.status !== 200) {
        loadingStatus.textContent = `Error: Could not load NFL schedule from /data/nfl_games.csv.`;
        return;
    }

    const games = scheduleResult.data.rows;
    let html = '';
    
    games.forEach(game => {
        const homeTeam = game['home team'].trim();
        const awayTeam = game['road team'].trim();
        const gameDate = game['date'].trim();

        const homeElo = eloMap[homeTeam] || 1000; // Default to 1000 if rating is missing
        const awayElo = eloMap[awayTeam] || 1000;
        
        const winProb = calculateHomeWinProbability(homeElo, awayElo);
        // Format to percentage with one decimal place
        const winProbPercent = (winProb * 100).toFixed(1) + '%';
        
        // Determine logo paths for NFL ('nfl')
        const homeLogoPath = getLogoPath(homeTeam, 'nfl');
        const awayLogoPath = getLogoPath(awayTeam, 'nfl');

        html += `
            <tr>
                <td class="date-cell">${gameDate}</td>
                <td class="team-cell">
                    <img src="${awayLogoPath}" alt="${awayTeam} Logo" class="team-logo" onerror="this.style.display='none'">
                    <span>${awayTeam} (${awayElo.toFixed(1)})</span>
                </td>
                <td class="team-cell">
                    <img src="${homeLogoPath}" alt="${homeTeam} Logo" class="team-logo" onerror="this.style.display='none'">
                    <span>${homeTeam} (${homeElo.toFixed(1)})</span>
                </td>
                <td class="odds-cell">${winProbPercent}</td>
                <td></td> </tr>
        `;
    });

    if (games.length > 0) {
        tbody.innerHTML = html;
        loadingStatus.textContent = `Successfully loaded and calculated ${games.length} games.`;
    } else {
        loadingStatus.textContent = `No games found in /data/nfl_games.csv.`;
    }
  }

  // --- EXISTING LEAGUE-SPECIFIC LOGIC (omitted for brevity, but kept in actual file) ---
  // ... (all other existing functions/logic remain here)
});
