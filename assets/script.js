/**
 * AEIRatings Master Script
 * Handles loading CSV data, rendering league tables, 
 * and includes logic for the new NFL Game Predictor.
 */

// Global variables to hold data
let allRows = [];
const teamLogos = {
    'nfl': {
        'Arizona Cardinals': 'logos/nfl/arizona_cardinals.png',
        'Atlanta Falcons': 'logos/nfl/atlanta_falcons.png',
        'Baltimore Ravens': 'logos/nfl/baltimore_ravens.png',
        'Buffalo Bills': 'logos/nfl/buffalo_bills.png',
        'Carolina Panthers': 'logos/nfl/carolina_panthers.png',
        'Chicago Bears': 'logos/nfl/chicago_bears.png',
        'Cincinnati Bengals': 'logos/nfl/cincinnati_bengals.png',
        'Cleveland Browns': 'logos/nfl/cleveland_browns.png',
        'Dallas Cowboys': 'logos/nfl/dallas_cowboys.png',
        'Denver Broncos': 'logos/nfl/denver_broncos.png',
        'Detroit Lions': 'logos/nfl/detroit_lions.png',
        'Green Bay Packers': 'logos/nfl/green_bay_packers.png',
        'Houston Texans': 'logos/nfl/houston_texans.png',
        'Indianapolis Colts': 'logos/nfl/indianapolis_colts.png',
        'Jacksonville Jaguars': 'logos/nfl/jacksonville_jaguars.png',
        'Kansas City Chiefs': 'logos/nfl/kansas_city_chiefs.png',
        'Las Vegas Raiders': 'logos/nfl/las_vegas_raiders.png',
        'Los Angeles Chargers': 'logos/nfl/los_angeles_chargers.png',
        'Los Angeles Rams': 'logos/nfl/los_angeles_rams.png',
        'Miami Dolphins': 'logos/nfl/miami_dolphins.png',
        'Minnesota Vikings': 'logos/nfl/minnesota_vikings.png',
        'New England Patriots': 'logos/nfl/new_england_patriots.png',
        'New Orleans Saints': 'logos/nfl/new_orleans_saints.png',
        'New York Giants': 'logos/nfl/new_york_giants.png',
        'New York Jets': 'logos/nfl/new_york_jets.png',
        'Philadelphia Eagles': 'logos/nfl/philadelphia_eagles.png',
        'Pittsburgh Steelers': 'logos/nfl/pittsburgh_steelers.png',
        'San Francisco 49ers': 'logos/nfl/san_francisco_49ers.png',
        'Seattle Seahawks': 'logos/nfl/seattle_seahawks.png',
        'Tampa Bay Buccaneers': 'logos/nfl/tampa_bay_buccaneers.png',
        'Tennessee Titans': 'logos/nfl/tennessee_titans.png',
        'Washington Commanders': 'logos/nfl/washington_commanders.png'
    }
    // Add other league logos here (cfb, nba, nhl, etc.)
};

// Helper function for querying the DOM
const qs = (selector) => document.querySelector(selector);
// Helper function to safely parse numbers
const n = (val) => parseFloat(val) || 0;

/**
 * Loads and parses CSV data from a specified file name.
 * @param {string} fileName The name of the CSV file in the data folder.
 */
async function loadDataAndRefresh(fileName) {
    try {
        const response = await fetch(`/data/${fileName}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const csvText = await response.text();
        allRows = parseCSV(csvText);
    } catch (error) {
        console.error("Error fetching or parsing CSV data:", error);
        // Clear old data on error
        allRows = []; 
    }
}

/**
 * Basic CSV parsing function. Assumes header row and comma delimiter.
 * @param {string} csvText Raw CSV string content.
 * @returns {Array<Object>} Array of objects where keys are column headers.
 */
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    if (lines.length === 0) return [];

    const headers = lines[0].split(',').map(h => h.trim());
    const rows = [];

    for (let i = 1; i < lines.length; i++) {
        const line = lines[i];
        // Skip empty lines or comment lines
        if (!line || line.startsWith('#')) continue;

        const values = line.split(',').map(v => v.trim());
        const row = {};
        
        // Ensure values match headers length to prevent index errors
        for (let j = 0; j < headers.length; j++) {
            row[headers[j]] = values[j];
        }
        rows.push(row);
    }
    return rows;
}

/**
 * Custom Elo Win Probability Calculation as requested:
 * 1 / (1 + 10^((awayrating - homerating) / 400))
 * @param {number} homeRating The Elo rating of the home team.
 * @param {number} awayRating The Elo rating of the away team.
 * @returns {number} The probability (0.0 to 1.0) that the home team wins.
 */
function calculateEloWinProbability(homeRating, awayRating) {
    const exponent = (awayRating - homeRating) / 400;
    return 1 / (1 + Math.pow(10, exponent));
}

/**
 * Renders the full data table based on the loaded allRows data.
 * This is the standard view for the /leagues/* pages.
 * @param {string} league The league identifier (e.g., 'nfl', 'nba').
 */
function renderTable(league) {
    const tableBody = qs('#ratings-table tbody');
    const tableHeader = qs('#table-header');
    
    if (!tableBody || !tableHeader) return;

    // Clear previous content
    tableBody.innerHTML = '';

    // Determine data columns (e.g., Team, Elo, Wins, Losses)
    const dataHeaders = allRows.length > 0 ? Object.keys(allRows[0]) : [];

    // --- FIX: RENDER TABLE HEADERS CORRECTLY INCLUDING 'Rank' ---
    const displayHeaders = ['Rank', ...dataHeaders];
    
    tableHeader.innerHTML = displayHeaders.map(header => {
        // Apply text alignment/styling to headers based on content
        let className = 'text-left';
        if (header === 'Rank' || header === 'Elo' || header === 'Wins' || header === 'Losses') {
            className = 'text-right';
        }
        
        return `<th class="py-2 px-4 border-b border-gray-700 ${className}">${header}</th>`;
    }).join('');

    // Sort by Elo descending
    // Ensure all rows are sorted by Elo and use index for rank
    const sortedRows = [...allRows].sort((a, b) => n(b.Elo) - n(a.Elo)); 

    // Render table rows
    sortedRows.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-800 transition-colors duration-100';

        // 1. Add Rank column (index + 1)
        const rankCell = document.createElement('td');
        rankCell.className = 'py-2 px-4 border-b border-gray-700 text-right font-bold text-gray-400';
        rankCell.textContent = index + 1;
        tr.appendChild(rankCell);
        
        // 2. Add other data cells using the original dataHeaders
        dataHeaders.forEach(header => {
            const td = document.createElement('td');
            td.className = 'py-2 px-4 border-b border-gray-700 whitespace-nowrap';
            
            let content = row[header] || '';

            if (header === 'Team') {
                const logoPath = teamLogos[league]?.[row.Team];
                if (logoPath) {
                    td.innerHTML = `<img src="/${logoPath}" alt="${row.Team} logo" class="inline-block h-6 w-6 mr-2 object-contain" onerror="this.onerror=null; this.src='https://placehold.co/24x24/1f2937/a0aec0?text=?'"/><span>${row.Team}</span>`;
                } else {
                    td.textContent = row.Team;
                }
                td.className += ' text-left';
            } else if (header === 'Elo') {
                // Format Elo ratings to one decimal place
                td.textContent = n(content).toFixed(1);
                td.className += ' font-mono text-right';
            } else {
                // Handle other numeric content for right alignment
                const numContent = n(content);
                if (!isNaN(numContent) && numContent !== 0 && !isNaN(parseInt(content))) {
                    if (numContent === parseInt(content)) {
                        td.textContent = content; 
                    } else {
                        td.textContent = numContent.toFixed(1); 
                    }
                    td.className += ' text-right';
                } else {
                     td.textContent = content;
                     td.className += ' text-left';
                }
            }
            tr.appendChild(td);
        });

        tableBody.appendChild(tr);
    });
}


document.addEventListener('DOMContentLoaded', async () => {
    const main = qs('main');
    if (!main) return;

    const league = main.getAttribute('data-league');

    // --- NFL PREDICTOR LOGIC BRANCH ---
    if (league === 'nfl-predictor') {
        // Load the main NFL ratings (nfl.csv) for the predictor
        await loadDataAndRefresh('nfl.csv'); 
        
        const homeSelect = qs('#homeTeam');
        const awaySelect = qs('#awayTeam');
        const calculateBtn = qs('#calculateBtn');
        const resultDiv = qs('#result');

        // Extract and sort unique team names
        const teams = allRows.map(r => r.Team).sort();

        // Function to create and insert options into a select element
        const populateDropdown = (selectEl) => {
            selectEl.innerHTML = '<option value="">-- Select Team --</option>';
            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team;
                option.textContent = team;
                selectEl.appendChild(option);
            });
        };

        populateDropdown(homeSelect);
        populateDropdown(awaySelect);

        // Add calculation event listener
        calculateBtn.addEventListener('click', () => {
            const homeTeamName = homeSelect.value;
            const awayTeamName = awaySelect.value;

            if (!homeTeamName || !awayTeamName) {
                resultDiv.innerHTML = "<p class='text-yellow-400'>Please select both a **Home** and **Away** team.</p>";
                return;
            }

            if (homeTeamName === awayTeamName) {
                resultDiv.innerHTML = "<p class='text-red-400'>A team cannot play itself! Select two different teams.</p>";
                return;
            }

            // Look up ratings
            const homeTeamData = allRows.find(r => r.Team === homeTeamName);
            const awayTeamData = allRows.find(r => r.Team === awayTeamName);

            const homeRating = n(homeTeamData ? homeTeamData.Elo : 0);
            const awayRating = n(awayTeamData ? awayTeamData.Elo : 0);

            if (homeRating === 0 || awayRating === 0) {
                 resultDiv.innerHTML = `<p class='text-yellow-400'>Could not find valid ratings for one or both teams. Home Elo: ${homeRating.toFixed(1)}, Away Elo: ${awayRating.toFixed(1)}.</p>`;
                 return;
            }

            // Perform calculation using the requested Elo formula
            const winProb = calculateEloWinProbability(homeRating, awayRating);

            // Display result
            const winPercent = (winProb * 100).toFixed(1);
            const homeElo = homeRating.toFixed(1);
            const awayElo = awayRating.toFixed(1);

            resultDiv.innerHTML = `
                <div class="text-xl">
                    **${homeTeamName}** has a <span class="text-green-400">${winPercent}%</span> chance to beat **${awayTeamName}**.
                </div>
                <div class="muted text-sm mt-2">
                    (Home Elo: ${homeElo}, Away Elo: ${awayElo})
                </div>
            `;
        });
        
        // Stop processing the regular page logic
        return;
    }
    // --- END NFL PREDICTOR LOGIC BRANCH ---

    // --- STANDARD LEAGUE TABLE LOGIC (Existing code) ---
    if (league) {
        // For regular league pages, load the main data file
        await loadDataAndRefresh(`${league}.csv`);
        renderTable(league);
    }

    // Event listener for Week Selector (only for NFL pages)
    const weekSelector = qs('#week-selector');
    if (league === 'nfl' && weekSelector) {
        weekSelector.addEventListener('change', async (event) => {
            const selectedWeek = event.target.value;
            const fileName = selectedWeek === 'current' ? 'nfl.csv' : `nfl_week_${selectedWeek}.csv`;
            
            // Check if the file exists before attempting to load
            const fileExists = await checkFileExists(`/data/${fileName}`);
            
            if (fileExists) {
                await loadDataAndRefresh(fileName);
                renderTable(league);
            } else {
                console.warn(`File not found: ${fileName}. Falling back to nfl.csv`);
                await loadDataAndRefresh('nfl.csv');
                renderTable(league);
            }
        });
    }
});

// Assuming an existing helper function to check file existence (optional but recommended)
async function checkFileExists(url) {
    try {
        const response = await fetch(url, { method: 'HEAD' });
        return response.ok;
    } catch (e) {
        return false;
    }
}
