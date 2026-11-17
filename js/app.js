const state = { items: [], cat: '全部', q: '', lang: '全部', sort: 'new', date: '全部', shown: 24 };
const CATS = ['全部','宏观政策','股市','美股全球','基金理财','外汇黄金','科技公司','综合'];

const $ = s => document.querySelector(s);

function fmtTime(iso){
  try{
    const d = new Date(iso);
    return d.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});
  }catch{ return iso?.slice(0,16) ?? ''; }
}
function fmtFull(iso){
  try{ return new Date(iso).toLocaleString('zh-CN'); }catch{ return iso ?? ''; }
}

async function load(){
  try{
    const res = await fetch('data/news.json?t=' + Date.now());
    const data = await res.json();
    state.items = data.items || [];
    $('#statCount').textContent = data.count ?? state.items.length;
    $('#statDate').textContent = (data.date || '').replaceAll('-','/');
    $('#statUpdate').textContent = fmtFull(data.updated_at);
    $('#statSources').textContent = (data.sources || []).length + ' 个来源';
    buildChips(); buildDates(); render();
  }catch(e){
    $('#grid').innerHTML = `<div class="empty">数据加载失败：${e.message}<br>请确认已运行 <kbd>python scripts/fetch_news.py</kbd> 生成 data/news.json</div>`;
  }
}

function buildChips(){
  const box = $('#chips'); box.innerHTML = '';
  const counts = {};
  state.items.forEach(i => counts[i.category] = (counts[i.category]||0)+1);
  CATS.forEach(c => {
    const b = document.createElement('button');
    b.className = 'chip' + (state.cat === c ? ' active' : '');
    b.textContent = c === '全部' ? `全部 ${state.items.length}` : `${c} ${counts[c]||0}`;
    b.onclick = () => { state.cat = c; state.shown = 24; buildChips(); render(); };
    box.appendChild(b);
  });
}

function buildDates(){
  const sel = $('#dateSel');
  const dates = [...new Set(state.items.map(i => (i.published_at||'').slice(0,10)).filter(Boolean))].sort().reverse();
  sel.innerHTML = '<option>全部</option>' + dates.map(d => `<option>${d}</option>`).join('');
}

function filtered(){
  let arr = [...state.items];
  if(state.cat !== '全部') arr = arr.filter(i => i.category === state.cat);
  if(state.lang !== '全部') arr = arr.filter(i => (i.lang === 'zh' ? '中文' : '英文') === state.lang);
  if(state.date !== '全部') arr = arr.filter(i => (i.published_at||'').startsWith(state.date));
  if(state.q){
    const q = state.q.toLowerCase();
    arr = arr.filter(i => (i.title + ' ' + (i.summary||'')).toLowerCase().includes(q));
  }
  arr.sort((a,b) => state.sort === 'new'
    ? b.published_at.localeCompare(a.published_at)
    : a.published_at.localeCompare(b.published_at));
  return arr;
}

function esc(s){ return (s||'').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

function render(){
  const arr = filtered();
  $('#metaLine').textContent = `共 ${arr.length} 条 · 分类：${state.cat} · ${state.sort === 'new' ? '最新优先' : '最早优先'}`;
  const grid = $('#grid');
  if(!arr.length){
    grid.innerHTML = '<div class="empty">没有符合条件的新闻，换个关键词或分类试试。</div>';
    $('#moreBtn').style.display = 'none';
    return;
  }
  const list = arr.slice(0, state.shown);
  grid.innerHTML = list.map(i => `
    <article class="card">
      <div class="tags">
        <span class="tag cat">${esc(i.category||'综合')}</span>
        <span class="tag">${esc(i.source||'')}</span>
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
  state.cat = '全部'; state.q = ''; state.lang = '全部'; state.date = '全部'; state.shown = 24;
  $('#searchInput').value = ''; $('#langSel').value = '全部'; $('#sortSel').value = 'new'; $('#dateSel').value = '全部';
  buildChips(); render();
  window.scrollTo({top: 0, behavior: 'smooth'});
});

$('#refreshBtn').addEventListener('click', () => load());

document.getElementById('year').textContent = new Date().getFullYear();
load();
