(function(){
  const $ = id => document.getElementById(id);
  const escape = v => String(v == null ? '' : v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const people = [
    'Kevin Warsh','Philip Jefferson','Christopher Waller','Michelle Bowman',
    'Michael Barr','Lisa Cook','Jerome Powell','John Williams','Susan Collins',
    'Anna Paulson','Thomas Barkin','Beth Hammack','Austan Goolsbee',
    'Alberto Musalem','Jeff Schmid','Lorie Logan','Mary Daly','Neel Kashkari','Cheryl Venable'
  ];
  let all=[],shown=[],mode='all',speaker='all',search='',period='all';
  const short = s=>s.replace(/（规则初判）/,'');
  function status(x){
    return x.stance?.includes('偏鹰')?'hawk':x.stance?.includes('偏鸽')?'dove':x.stance?.includes('混合')?'mixed':'unknown';
  }
  function summarize(){
    const latest = new Map();
    const observed = new Set(all.map(v=>v.speaker));
    const today = new Date();
    const threshold = new Date(today.getTime()-45*86400000).toISOString().slice(0,10);
    // Use the most recent EXPLICIT policy statement of each speaker, not a later non-policy speech.
    for(const v of all.slice().sort((a,b)=>b.date.localeCompare(a.date))){
      if(v.date<threshold || !['hawk','dove','mixed'].includes(status(v)))continue;
      if(!latest.has(v.speaker))latest.set(v.speaker,v);
    }
    const sample=[...latest.values()];
    const hawks=sample.filter(v=>status(v)==='hawk').length;
    const doves=sample.filter(v=>status(v)==='dove').length;
    const mixed=sample.filter(v=>status(v)==='mixed').length;
    const enough=sample.length>=5 && sample.length/Math.max(people.length,1)>=.25;
    let view='证据不足，暂无法判断总体鹰鸽倾向';
    if(enough){
      if(hawks>doves+2)view='已分类样本：偏鹰';
      else if(doves>hawks+2)view='已分类样本：偏鸽';
      else view='已分类样本：鹰鸽分歧／接近均衡';
    }
    $('all-fed-overall').textContent=view;
    $('all-fed-counts').innerHTML=[
      ['偏鹰',hawks,'hawk'],['偏鸽',doves,'dove'],
      ['混合',mixed,'mixed'],['无明确分类',observed.size-sample.length,'unknown']
    ].map(x=>'<span class="fed-pill '+x[2]+'">'+x[0]+' '+x[1]+'</span>').join('');
    $('all-fed-scope').textContent='2026-09-01起｜收录 '+all.length+' 项官方来源记录；已覆盖 '+observed.size+'/'+people.length+' 位预设跟踪对象；近45天有明确规则初判 '+sample.length+' 人。其余不计入偏鹰偏鸽。';
  }
  function render(){
    summarize();
    shown=all.filter(x=>{
      const st=status(x);
      return (mode==='all'||mode===st) && (speaker==='all'||speaker===x.speaker)
        && (period==='all'||x.date.startsWith(period))
        && (!search || [x.title,x.speaker,x.source,x.summary,x.evidence,(x.points||[]).map(p=>p.quote).join(' ')].join(' ').toLowerCase().includes(search));
    }).sort((a,b)=>b.date.localeCompare(a.date));
    $('all-fed-total').textContent=shown.length;
    $('all-fed-entries').innerHTML=shown.slice(0,180).map(x=>{
      const s=status(x);
      const q=(x.points||[]).slice(0,5).map((p,i)=>'<div class="fed-quote"><b>'+(i+1)+'. '+escape(p.topic)+'</b><span>'+escape(p.quote)+'</span></div>').join('');
      return '<article class="fed-entry"><div class="fed-entry-top"><div><b>'+escape(x.speaker)+'</b><span class="fed-date">'+escape(x.date)+' · '+escape(x.source||'官方来源')+'</span></div><span class="fed-pill '+s+'">'+escape(short(x.stance||'未判定'))+'</span></div>'
        +'<h4>'+escape(x.title)+'</h4>'
        +'<p class="fed-muted">'+escape(x.summary||'待提取核心观点')+'</p>'
        +(q?'<div class="fed-quotes">'+q+'</div>':'<p class="fed-muted">正文要点尚待核验，不以标题替代实际观点。</p>')
        +'<div class="fed-entry-foot"><span>利率幅度：'+escape(x.rateBp||'未核实')+'</span>'
        +'<span>证据状态：'+escape(x.confidence||x.reviewStatus||'待核验')+'</span>'
        +'<a href="'+escape(x.url)+'" target="_blank" rel="noopener noreferrer">官方原文 / 完整实录 ↗</a></div></article>'
    }).join('')||'<p class="fed-muted">当前筛选无匹配记录。自动回填范围可能存在缺漏，请通过来源链接核查。</p>';
    $('all-fed-shown').textContent=shown.length>180?'仅显示最新180条，可通过筛选缩小范围':'';
  }
  function init(data){
    all=Array.isArray(data)?data.filter(x=>x.date>='2026-09-01'&&x.date<='2026-11-23'||x.date>'2026-11-23'):[];
    all.sort((a,b)=>b.date.localeCompare(a.date));
    const persons=[...new Set(people.concat(all.map(x=>x.speaker)))];
    $('all-fed-person').innerHTML='<option value="all">全部官员</option>'+persons.map(x=>'<option value="'+escape(x)+'">'+escape(x)+'</option>').join('');
    $('all-fed-date').textContent='数据刷新：'+new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})+'（北京时间，网页读取）';
    document.querySelectorAll('[data-fed-mode]').forEach(btn=>btn.addEventListener('click',()=>{
      mode=btn.dataset.fedMode;
      document.querySelectorAll('[data-fed-mode]').forEach(b=>b.classList.toggle('selected',b===btn));
      render();
    }));
    $('all-fed-person').onchange=e=>{speaker=e.target.value;render()};
    $('all-fed-period').onchange=e=>{period=e.target.value;render()};
    $('all-fed-search').oninput=e=>{search=e.target.value.trim().toLowerCase();render()};
    render();
  }
  fetch('data/all_fed_officials.json?cb='+Date.now(),{cache:'no-store'})
    .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
    .then(init)
    .catch(e=>{$('all-fed-overall').textContent='暂无法加载全体官员数据';$('all-fed-entries').textContent=String(e)});
})();