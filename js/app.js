const state = { items: [], region: '全部', sector: '全部', q: '', lang: '全部', sort: 'new', date: '全部', shown: 24 };
const SECTORS = ['全部','宏观政策','股市','科技','汽车出行','医疗健康','贵金属','能源','基金理财','房地产','综合'];
const REGIONS = ['全部','中国','全球'];

const $ = s => document.querySelector(s);

function fmtTime(iso){
  try{
    const d = new Date(iso);
    return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});
  }catch{ return (iso||'').slice(0,16); }
}
function fmtFull(iso){
  try{ return new Date(iso).toLocaleString('zh-CN'); }catch{ return iso ?? ''; }
}

async function load(){
  try{
    const res = await fetch('data/news.json?t=' + Date.now());
    const data = await res.json();
    state.items = data.items || [];
    const cn = state.items.filter(i => i.region === '中国').length;
    const gl = state.items.filter(i => i.region === '全球').length;
    $('#statCount').textContent = data.count ?? state.items.length;
    $('#statCN').textContent = cn;
    $('#statGL').textContent = gl;
    $('#statUpdate').textContent = fmtFull(data.updated_at);
    buildRegions(cn, gl); buildSectors(); buildDates(); render();
  }catch(e){
    $('#grid').innerHTML = `<div class="empty">数据加载失败：${e.message}<br>请确认已运行 <kbd>python scripts/fetch_news.py</kbd> 生成 data/news.json</div>`;
  }
}

function buildRegions(cn, gl){
  const box = $('#regions'); box.innerHTML = '';
  const counts = { '全部': state.items.length, '中国': cn, '全球': gl };
  REGIONS.forEach(r => {
    const b = document.createElement('button');
    b.className = 'tab' + (state.region === r ? ' active' : '');
    b.textContent = (r === '全部' ? '🌐 全部 ' : r === '中国' ? '🇨🇳 中国 ' : '🌍 全球 ') + (counts[r] ?? 0);
    b.onclick = () => { state.region = r; state.shown = 24; buildRegions(cn, gl); buildSectors(); render(); };
    box.appendChild(b);
  });
}

function scopedItems(){
  let arr = state.items;
  if(state.region !== '全部') arr = arr.filter(i => i.region === state.region);
  return arr;
}

function buildSectors(){
  const box = $('#chips'); box.innerHTML = '';
  const arr = scopedItems();
  const counts = {};
  arr.forEach(i => counts[i.sector] = (counts[i.sector] || 0) + 1);
  SECTORS.forEach(s => {
    const b = document.createElement('button');
    b.className = 'chip' + (state.sector === s ? ' active' : '');
    b.textContent = s === '全部' ? `全部 ${arr.length}` : `${s} ${counts[s] || 0}`;
    b.onclick = () => { state.sector = s; state.shown = 24; buildSectors(); render(); };
    box.appendChild(b);
  });
}

function buildDates(){
  const sel = $('#dateSel');
  const dates = [...new Set(state.items.map(i => (i.published_at || '').slice(0, 10)).filter(Boolean))].sort().reverse();
  sel.innerHTML = '<option>全部</option>' + dates.map(d => `<option>${d}</option>`).join('');
}

function filtered(){
  let arr = scopedItems();
  if(state.sector !== '全部') arr = arr.filter(i => i.sector === state.sector);
  if(state.lang !== '全部') arr = arr.filter(i => (i.lang === 'zh' ? '中文' : '英文') === state.lang);
  if(state.date !== '全部') arr = arr.filter(i => (i.published_at || '').startsWith(state.date));
  if(state.q){
    const q = state.q.toLowerCase();
    arr = arr.filter(i => (i.title + ' ' + (i.summary || '')).toLowerCase().includes(q));
  }
  arr = [...arr].sort((a, b) => state.sort === 'new'
    ? b.published_at.localeCompare(a.published_at)
    : a.published_at.localeCompare(b.published_at));
  return arr;
}

function esc(s){ return (s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

function render(){
  const arr = filtered();
  $('#metaLine').textContent = `${state.region} · ${state.sector}，共 ${arr.length} 条 · ${state.sort === 'new' ? '最新优先' : '最早优先'}`;
  const grid = $('#grid');
  if(!arr.length){
    grid.innerHTML = '<div class="empty">没有符合条件的新闻，换个地区、板块或关键词试试。</div>';
    $('#moreBtn').style.display = 'none';
    return;
  }
  const list = arr.slice(0, state.shown);
  grid.innerHTML = list.map(i => `
    <article class="card">
      <div class="tags">
        <span class="tag region">${i.region === '中国' ? '🇨🇳 中国' : '🌍 全球'}</span>
        <span class="tag cat">${esc(i.sector || '综合')}</span>
        <span class="tag">${esc(i.source || '')}</span>
        <span class="tag">${i.lang === 'zh' ? '中文' : '英文'}</span>
      </div>
      <h3><a href="${esc(i.link)}" target="_blank" rel="noopener">${esc(i.title)}</a></h3>
      ${i.summary ? `<p class="summary">${esc(i.summary)}</p>` : ''}
      <div class="card-foot">
        <span>🕒 ${fmtTime(i.published_at)}</span>
        <a class="read" href="${esc(i.link)}" target="_blank" rel="noopener">阅读原文 →</a>
      </div>
    </article>`).join('');
  $('#moreBtn').style.display = arr.length > state.shown ? 'block' : 'none';
  $('#moreBtn').textContent = `加载更多（还剩 ${arr.length - state.shown} 条）`;
}

$('#searchInput').addEventListener('input', e => { state.q = e.target.value.trim(); state.shown = 24; render(); });
$('#langSel').addEventListener('change', e => { state.lang = e.target.value; state.shown = 24; render(); });
$('#sortSel').addEventListener('change', e => { state.sort = e.target.value; state.shown = 24; render(); });
$('#dateSel').addEventListener('change', e => { state.date = e.target.value; state.shown = 24; render(); });
$('#moreBtn').addEventListener('click', () => { state.shown += 24; render(); });

$('#themeBtn').addEventListener('click', () => {
  const cur = document.documentElement.dataset.theme === 'dark' ? '' : 'dark';
  document.documentElement.dataset.theme = cur;
  localStorage.setItem('fn-theme', cur);
  $('#themeBtn').textContent = cur === 'dark' ? '☀️ 浅色' : '🌙 深色';
});
(function(){
  const t = localStorage.getItem('fn-theme') || '';
  document.documentElement.dataset.theme = t;
  if(t === 'dark') $('#themeBtn').textContent = '☀️ 浅色';
})();

$('#todayBtn').addEventListener('click', () => {
  state.region = '全部'; state.sector = '全部'; state.q = ''; state.lang = '全部'; state.date = '全部'; state.shown = 24;
  $('#searchInput').value = ''; $('#langSel').value = '全部'; $('#sortSel').value = 'new'; $('#dateSel').value = '全部';
  const cn = state.items.filter(i => i.region === '中国').length;
  const gl = state.items.filter(i => i.region === '全球').length;
  buildRegions(cn, gl); buildSectors(); render();
  window.scrollTo({top: 0, behavior: 'smooth'});
});

$('#refreshBtn').addEventListener('click', () => load());

document.getElementById('year').textContent = new Date().getFullYear();
load();
