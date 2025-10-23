// aeiratings/aeiratings.github.io/aeiratings.github.io-e5b431b005feee3690bb5dbde4cb6fecb9bc4144/assets/script.js

// ... (existing code for qs, n, parseCSV, normalizeTeamName, getLogoPath remains unchanged)

  /**
   * Calculates the predicted probability of the home team winning.
   * Formula: 1 / (1 + 10^((awayElo - homeElo) / 400))
   * @param {number} homeElo - The Elo rating of the home team (R_H).
   * @param {number} awayElo - The Elo rating of the away team (R_A).
   * @returns {number} The win probability (0 to 1).
   */
  function calculateHomeWinProbability(homeElo, awayElo) {
      // Per the user's provided formula: 1/(1+POWER(10,(awayrating-homerating)/400))
      if (homeElo === 0 || awayElo === 0) return 0.5; // Default if rating is missing
      const diff = (awayElo - homeElo) / 400;
      return 1 / (1 + Math.pow(10, diff));
  }

  // New generic function to fetch and parse CSV
  async function fetchAndParseCSV(fileName) {
    const filePath = `/data/${fileName}`;
    try {
      const resp = await fetch(filePath, { cache: 'no-store' });
      if (!resp.ok) {
        if (resp.status === 404) return { status: 404, error: 'File not found.' };
        throw new Error(`Failed to fetch ${filePath}: ${resp.status} ${resp.statusText}`);
      }
      const text = await resp.text();
      return { status: 200, data: parseCSV(text) };
    } catch (err) {
      console.error(`Error loading CSV: ${filePath}`, err);
      return { status: 500, error: err.message };
    }
  }
  
  // --- NEW NFL SCHEDULE PREDICTOR LOGIC ---
  async function loadNFLSchedulePredictor() {
    const loadingStatus = qs('#loadingStatus');
    const gamesTable = qs('#gamesTable');
    const tbody = qs('#gamesTable tbody');

    // 1. Fetch current NFL Elo Ratings (data/nfl.csv)
    loadingStatus.textContent = 'Loading current NFL ratings...';
    const ratingsResult = await fetchAndParseCSV('nfl.csv');
    if (ratingsResult.status !== 200) {
        loadingStatus.textContent = `Error: Could not load NFL Elo ratings from /data/nfl.csv. ${ratingsResult.error || ''}`;
        return;
    }

    // Create an Elo lookup map: Team Name -> Elo Rating
    const eloMap = {};
    ratingsResult.data.rows.forEach(r => {
        // Assuming the rating file has a column named 'Team' and 'Elo'
        if (r.Team) eloMap[r.Team.trim()] = n(r.Elo);
    });

    // 2. Fetch the Game Schedule (data/nfl_games.csv)
    loadingStatus.textContent = 'Loading NFL game schedule...';
    const scheduleResult = await fetchAndParseCSV('nfl_games.csv');
    if (scheduleResult.status !== 200) {
        loadingStatus.textContent = `Error: Could not load NFL schedule from /data/nfl_games.csv. ${scheduleResult.error || ''}`;
        return;
    }

    const games = scheduleResult.data.rows;
    let html = '';

    if (games.length === 0) {
        loadingStatus.textContent = `No games found in /data/nfl_games.csv.`;
        return;
    }

    games.forEach(game => {
        // Column names are assumed based on standard Elo file formats
        const homeTeam = (game['home team'] || '').trim();
        const awayTeam = (game['road team'] || '').trim();
        const gameDate = (game['date'] || '').trim();

        const homeElo = eloMap[homeTeam] || 1500; // Default to a standard Elo 1500 if missing
        const awayElo = eloMap[awayTeam] || 1500;

        const winProb = calculateHomeWinProbability(homeElo, awayElo);
        const winProbPercent = (winProb * 100).toFixed(1) + '%';
        const homeLogoPath = getLogoPath(homeTeam, 'nfl');
        const awayLogoPath = getLogoPath(awayTeam, 'nfl');

        html += `
            <tr>
                <td>${gameDate}</td>
                <td class="team-cell">
                    <img src="${awayLogoPath}" alt="${awayTeam} Logo" class="team-logo" onerror="this.style.display='none'">
                    <span>${awayTeam} (${homeElo.toFixed(1)})</span>
                </td>
                <td class="team-cell">
                    <img src="${homeLogoPath}" alt="${homeTeam} Logo" class="team-logo" onerror="this.style.display='none'">
                    <span>${homeTeam} (${awayElo.toFixed(1)})</span>
                </td>
                <td class="odds-cell">${winProbPercent}</td>
                <td></td>
            </tr>
        `;
    });

    // Render results
    tbody.innerHTML = html;
    gamesTable.style.display = 'table';
    loadingStatus.textContent = `Successfully loaded and calculated ${games.length} games.`;
    loadingStatus.classList.add('success');
  }


  // --- MAIN EXECUTION LOGIC ---
  const main = qs('main[data-league], main[data-page-type]');
  const pageType = main ? main.getAttribute('data-page-type') : null;

  if (pageType === 'nfl-schedule-predictor') {
    loadNFLSchedulePredictor();
  } 
  // ... (Existing logic for other pages continues here)

// ... (Rest of existing script.js code)
