```js


// Read league slug from main[data-league]
const main = document.querySelector('main[data-league]')
if(!main) return // no league page (e.g. index.html)
const league = main.getAttribute('data-league')
const csvPath = `/data/${league}.csv`


// controls
const filterInput = qs('#filter')
const sortSelect = qs('#sortBy')
const rowsPerPageSelect = qs('#rowsPerPage')


let parsed = {headers:[], rows:[]}
try{
const resp = await fetch(csvPath, {cache: 'no-store'})
if(!resp.ok) throw new Error('Not found')
const txt = await resp.text()
parsed = parseCSV(txt)
}catch(err){
const tbody = qs('#teamsTable tbody')
tbody.innerHTML = `<tr><td colspan="6">Unable to load CSV: ${csvPath}</td></tr>`
console.error(err); return
}


// normalize rows: ensure Team, Elo, Wins, Losses
const rows = parsed.rows.map(r=>({
Team: r.Team || r.team || '',
Elo: (n(r.Elo||r.elo)||0).toString(),
Wins: r.Wins || r.wins || '',
Losses: r.Losses || r.losses || '',
Conference: r.Conference || r.conference || r.Notes || ''
}))


function applyFiltersAndSort(){
const q = filterInput ? filterInput.value.trim().toLowerCase() : ''
let out = rows.filter(r=>{
if(!q) return true
return (r.Team||'').toLowerCase().includes(q) || (r.Conference||'').toLowerCase().includes(q)
})


const sortBy = sortSelect ? sortSelect.value : 'elo'
if(sortBy==='elo') out.sort((a,b)=> (Number(b.Elo)||0) - (Number(a.Elo)||0))
else if(sortBy==='team') out.sort((a,b)=> (a.Team||'').localeCompare(b.Team||''))
else if(sortBy==='wins') out.sort((a,b)=> (Number(b.Wins)||0) - (Number(a.Wins)||0))


const rowsPerPage = Number(rowsPerPageSelect ? rowsPerPageSelect.value : 0)
return rowsPerPage>0 ? out.slice(0, rowsPerPage) : out
}


function refresh(){
const shown = applyFiltersAndSort()
renderTable(shown, parsed.headers)
}


// wire up
if(filterInput) filterInput.addEventListener('input', refresh)
if(sortSelect) sortSelect.addEventListener('change', refresh)
if(rowsPerPageSelect) rowsPerPageSelect.addEventListener('change', refresh)


// initial render
refresh()


})();
```