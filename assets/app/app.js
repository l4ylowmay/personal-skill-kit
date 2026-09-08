'use strict';
(() => {
const DATA=JSON.parse(document.getElementById('exam-data').textContent);
const Q=DATA.questions, M=DATA.materials, LETTERS='ABCD', N=Q.length, DURATION=DATA.minutes*60*1000;
const KEY='sz-practice:'+DATA.version;
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paras=s=>String(s).split('\n').map(x=>'<p>'+esc(x)+'</p>').join('');
let state={status:'ready',answers:{}}, storageOK=true, lastPersist=0, fontSize=17;
function notice(text){ $('#notice').textContent=text;$('#notice').hidden=false; }
function validState(raw){
 if(!raw || !['ready','running','submitted'].includes(raw.status) || !raw.answers || typeof raw.answers!=='object') return null;
 if(raw.status!=='ready' && (!Number.isFinite(raw.startedAt)||!Number.isFinite(raw.deadline)||raw.deadline-raw.startedAt!==DURATION||typeof raw.attempt!=='string'))return null;
 if(raw.status==='submitted' && !Number.isFinite(raw.submittedAt))return null;
 const answers={};for(const q of Q){const a=raw.answers[q.number];if(LETTERS.includes(a)&&typeof a==='string'&&a.length===1)answers[q.number]=a;}
 return {...raw,answers};
}
function load(){
 try {const raw=localStorage.getItem(KEY);if(raw){const checked=validState(JSON.parse(raw));if(checked)state=checked;else notice('保存记录无法识别，请重新开始本卷。');}
 const probe=KEY+':probe';localStorage.setItem(probe,'1');localStorage.removeItem(probe);
 }catch(e){storageOK=false;notice('浏览器不允许保存本地进度，或保存记录无法读取。本次仍可作答，请保持页面打开。');}
}
function persist(){if(!storageOK)return;try{localStorage.setItem(KEY,JSON.stringify(state));lastPersist=Date.now();}catch(e){storageOK=false;notice('本次进度无法保存。仍可正常考试，请保持页面打开，避免刷新或关闭。');}}
function svg(body,w=100,h=100,label='题目图形'){return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${body}</svg>`;}
function graphic(q,includeChoices=false){
 const g=q.graphic;if(!g)return '';
 let result='<div class="portable-svg">'+g.svg+'</div>';
 if(includeChoices&&g.choices_svg)result+='<div class="zoom-choices">'+g.choices_svg.map((x,i)=>'<div><b>'+LETTERS[i]+'</b>'+x+'</div>').join('')+'</div>';
 return result;
}
function chart(m){return m.svg;}
function table(headers,rows){return `<div class="table-scroll" tabindex="0" role="region" aria-label="资料数据表，可左右滚动"><table><thead><tr>${headers.map(x=>`<th scope="col">${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((x,i)=>i?`<td>${esc(x)}</td>`:`<th scope="row">${esc(x)}</th>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function material(id){
 const m=M[id];let body='';
 if(m.kind==='text')body=paras(m.text);
 if(m.kind==='chart')body='<div class="chart-scroll" data-zoom-material="'+id+'">'+chart(m)+'</div><button class="text-button" data-zoom-material="'+id+'">放大统计图 ↗</button>'+table(m.headers,m.rows);
 if(m.kind==='table')body=table(m.headers,m.rows)+'<p class="muted small">窄屏可左右滑动查看完整数据。</p>';
 const ids=Q.filter(q=>q.material_group===id).map(q=>q.number);
 return '<section class="material" id="material-'+id+'"><div class="eyebrow">共用资料 · '+ids.join('、')+'题</div><h3>'+esc(m.title)+'</h3><p class="material-note">'+esc(m.note)+'</p>'+body+'</section>';
}
function resultFor(q){let selected=state.answers[q.number];return selected?(selected===q.answer?'correct':'wrong'):'unanswered';}
function questionHTML(q){
 const done=state.status==='submitted', chosen=state.answers[q.number], isGraphic=q.graphic?.choices_svg;
 const compact=!isGraphic&&q.options.every(x=>x.length<13);
 const medium=!isGraphic&&!compact&&q.options.every(x=>x.length<38);
 const status=done?resultFor(q):'';
 let out=`<article class="question ${status}" id="q${q.number}" tabindex="-1"><fieldset ${done?'disabled':''}><legend><span class="q-number">${q.number}.</span> ${esc(q.stem).replace(/\n/g,'<br>')}</legend>`;
 if(q.material_group)out+=`<a href="#material-${q.material_group}" class="material-link">↑ 返回本组资料</a>`;
 if(q.graphic)out+=graphic(q)+`<button type="button" class="text-button" data-zoom="${q.number}">放大图形与选项 ↗</button>`;
 out+=`<div class="options ${isGraphic?'graph-options':compact?'compact':medium?'medium':''}">`;
 q.options.forEach((o,i)=>{const l=LETTERS[i];const cls=done?(l===q.answer?'answer-correct':chosen===l?'answer-wrong':''):'';out+=`<label class="option ${cls}"><input type="radio" name="q${q.number}" value="${l}" ${chosen===l?'checked':''} aria-label="第${q.number}题，${l}选项：${esc(isGraphic?'图形见下方':o)}"><span class="letter">${l}</span><span class="option-content">${isGraphic?q.graphic.choices_svg[i]:esc(o)}${done&&l===q.answer?'<span class="answer-mark">正确答案</span>':''}</span></label>`;});
 out+='</div></fieldset>';
 if(done){
 const label=chosen?`你选的是：<strong>${chosen}</strong> <span class="${status}">${status==='correct'?'正确 ✅':'错误 ❌'}</span>`:'<strong>你未作答</strong> <span class="unanswered">本题 0 分</span>';
 out+=`<div class="analysis"><p class="selection-result">${label}</p><p><strong>正确答案：${q.answer}</strong></p><p class="explanation">${esc(q.explanation)}</p><div class="tags"><span>${esc(q.module)}</span><span>${esc(q.secondary_type)}</span><span>${esc(q.core_concept)}</span><span>难度：${q.difficulty}</span></div>${q.sources?.length?`<details class="sources"><summary>核验依据</summary>${q.sources.map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`).join('')}<p>事实核验日期：${esc(q.verified_at||DATA.fact_cutoff)}。离线时仍可阅读上方完整解析。</p></details>`:''}</div>`;
 }
 return out+'</article>';
}
function renderPaper(){
 let current='',out='',seen=new Set();
 Q.forEach(q=>{if(q.module!==current){current=q.module;out+=`<section class="module-title" id="module-${q.number}"><span>${String(DATA.modules.indexOf(current)+1).padStart(2,'0')}</span><div><h2>${esc(current)}</h2><p>${Q.filter(x=>x.module===current).length} 道单项选择题 · 每题 ${(100/N).toFixed(2).replace(/\.00$/,'')} 分</p></div></section>`;}
 if(q.material_group&&!seen.has(q.material_group)){out+=material(q.material_group);seen.add(q.material_group);}
 out+=questionHTML(q);});
 $('#paper').innerHTML=out;
 // Fieldset disables form controls only: keep zoom available while reviewing.
 $$('#paper [data-zoom]').forEach(b=>{if(state.status==='submitted'){const f=b.closest('fieldset');f.after(b);}});
 renderAnswerCard();
}
function renderAnswerCard(){
 let out='';DATA.modules.forEach(mod=>{const list=Q.filter(q=>q.module===mod);out+=`<div class="card-group"><a href="#module-${list[0].number}" class="card-module">${esc(mod)}</a><div class="number-grid">${list.map(q=>`<a href="#q${q.number}" data-nav="${q.number}" aria-label="第${q.number}题" class="nav-number">${q.number}</a>`).join('')}</div></div>`;});$('#answer-grid').innerHTML=out;updateProgress();
}
function updateProgress(){
 const count=Object.keys(state.answers).length;$('#answered').textContent=count;$('#mobile-count').textContent=count;$('#card-count').textContent=`${count} / ${N}`;$('#progress-fill').style.width=(count/N*100)+'%';
 $$('[data-nav]').forEach(a=>{const n=+a.dataset.nav,q=Q[n-1];const st=state.status==='submitted'?resultFor(q):(state.answers[n]?'answered':'empty');a.className='nav-number '+st;a.setAttribute('aria-label',`第${n}题，${({correct:'正确',wrong:'错误',unanswered:'未答',answered:'已答',empty:'未答'})[st]}`);});
}
function score(){const correct=Q.filter(q=>resultFor(q)==='correct').length,unanswered=Q.filter(q=>!state.answers[q.number]).length;return {correct,unanswered,wrong:N-correct-unanswered};}
function renderResult(){
 const s=score();$('#results').innerHTML=`<div class="result-top"><div class="score-ring" style="--score:${s.correct/N*100}%"><div><strong>${(s.correct/N*100).toFixed(2).replace(/\.00$/,'')}</strong><span>/ 100 分</span></div></div><div><div class="eyebrow">${state.reason==='timeout'?'时间到 · 已自动交卷':'已交卷 · 本次成绩'}</div><h2 tabindex="-1" id="result-heading">复盘，让每一题都有收获。</h2><p class="result-counts"><span class="correct">正确 ${s.correct}</span><span class="wrong">错误 ${s.wrong}</span><span>未答 ${s.unanswered}</span></p><p class="muted">用时 ${formatDuration(state.submittedAt-state.startedAt)} · 答案与解析已展开在每道题下方。</p></div></div><div class="module-scores">${DATA.modules.map(mod=>{const qs=Q.filter(q=>q.module===mod),c=qs.filter(q=>resultFor(q)==='correct').length;return `<div><span>${esc(mod)}</span><strong>${c}<small> / ${qs.length}</small></strong></div>`;}).join('')}</div>`;
 $('#results').hidden=false;
}
function formatDuration(ms){const seconds=Math.max(0,Math.min(DURATION/1000,Math.floor(ms/1000)));return `${Math.floor(seconds/60)}分${seconds%60}秒`;}
function showExam(){
 $('#home').hidden=true;$('#exam').hidden=false;$('#exam-toolbar').hidden=false;$('#home-label').hidden=true;
 $('#submit').hidden=state.status!=='running';$('#restart').hidden=false;
 $('#card-legend').innerHTML=state.status==='submitted'?'<span><i class="correct"></i>正确</span><span><i class="wrong"></i>错误</span><span><i></i>未答</span>':'<span><i class="answered"></i>已答</span><span><i></i>未答</span>';
 renderPaper();if(state.status==='submitted')renderResult();else $('#results').hidden=true;
 tick();
}
function start(){
 if(state.status!=='ready')return;
 const now=Date.now();state={status:'running',answers:{},startedAt:now,deadline:now+DURATION,lastSeen:now,attempt:now+'-'+Math.random().toString(36).slice(2),scrollY:0};persist();showExam();window.scrollTo(0,0);$('#q1').focus({preventScroll:true});
}
function submit(reason){
 if(state.status!=='running')return;
 const now=Math.max(Date.now(),state.lastSeen||0);state.status='submitted';state.reason=reason;state.submittedAt=reason==='timeout'?state.deadline:Math.min(now,state.deadline);state.scrollY=0;persist();
 if($('#confirm-dialog').open)$('#confirm-dialog').close();if($('#zoom-dialog').open)$('#zoom-dialog').close();showExam();window.scrollTo({top:0,behavior:'instant'});$('#result-heading').focus({preventScroll:true});
}
function tick(){
 if(state.status==='ready')return;
 if(state.status==='submitted'){$('#timer').textContent=state.reason==='timeout'?'00:00':'已交卷';$('#timer').classList.remove('urgent');return;}
 const now=Math.max(Date.now(),state.lastSeen||0);state.lastSeen=now;
 const remaining=Math.max(0,Math.ceil((state.deadline-now)/1000));$('#timer').textContent=String(Math.floor(remaining/60)).padStart(2,'0')+':'+String(remaining%60).padStart(2,'0');
 $('#timer').classList.toggle('urgent',remaining<=300);
 if(!remaining){submit('timeout');return;}if(now-lastPersist>15000)persist();
}
function confirmAction(kind){
 if(kind==='submit'){tick();if(state.status!=='running')return;const left=N-Object.keys(state.answers).length;$('#dialog-title').textContent='确认交卷？';$('#dialog-description').textContent=left?`还有 ${left} 道题未作答。交卷后将按当前答案评分，未答题计 0 分，且不能再修改答案。`:`${N} 道题已全部作答。交卷后显示成绩与逐题解析，且不能再修改答案。`;}
 else {$('#dialog-title').textContent='重新开始本卷？';$('#dialog-description').textContent=`当前答案与成绩将被清除。本卷题目不变，倒计时重新从 ${DATA.minutes} 分钟开始。`;}
 $('#confirm-action').dataset.kind=kind;$('#confirm-action').textContent=kind==='submit'?'确认交卷':'重新开始';$('#confirm-dialog').showModal();$('#cancel-action').focus();
}
$('#start').addEventListener('click',start);
$('#toggle-card').addEventListener('click',()=>{$('#answer-card').open=!$('#answer-card').open;$('#answer-card').scrollIntoView({block:'start'});});
$('#submit').addEventListener('click',()=>confirmAction('submit'));
$('#restart').addEventListener('click',()=>confirmAction('restart'));
$('#cancel-action').addEventListener('click',()=>$('#confirm-dialog').close());
$('#confirm-action').addEventListener('click',()=>{const kind=$('#confirm-action').dataset.kind;$('#confirm-dialog').close();if(kind==='submit')submit(Date.now()>=state.deadline?'timeout':'manual');else {state={status:'ready',answers:{}};start();}});
$('#paper').addEventListener('change',e=>{
 if(!e.target.matches('input[type=radio]'))return;tick();if(state.status!=='running')return;
 const n=+e.target.name.slice(1);if(!Q[n-1]||!LETTERS.includes(e.target.value))return;state.answers[n]=e.target.value;persist();updateProgress();
});
function zoom(content,title){$('#zoom-title').textContent=title;$('#zoom-content').innerHTML=content;$('#zoom-dialog').showModal();$('#close-zoom').focus();}
$('#paper').addEventListener('click',e=>{const b=e.target.closest('[data-zoom],[data-zoom-material]');if(!b)return;if(b.dataset.zoom){const q=Q[+b.dataset.zoom-1];zoom(graphic(q,true),`第 ${q.number} 题 · 图形放大`);}else zoom(chart(M[b.dataset.zoomMaterial]),'统计图 · 放大查看');});
$('#close-zoom').addEventListener('click',()=>$('#zoom-dialog').close());
$('#answer-card').addEventListener('click',e=>{if(e.target.closest('a')&&window.matchMedia('(max-width: 959px)').matches)$('#answer-card').open=false;});
$$('[data-font]').forEach(b=>b.addEventListener('click',()=>{fontSize=Math.max(15,Math.min(23,fontSize+(+b.dataset.font)));document.documentElement.style.setProperty('--question-size',fontSize+'px');}));
let scrollTimeout;window.addEventListener('scroll',()=>{if(state.status==='ready')return;clearTimeout(scrollTimeout);scrollTimeout=setTimeout(()=>{state.scrollY=window.scrollY;persist();},250);},{passive:true});
function syncAndTick(){tick();if(state.status!=='ready')persist();}
window.addEventListener('pagehide',syncAndTick);document.addEventListener('visibilitychange',syncAndTick);window.addEventListener('focus',tick);window.addEventListener('pageshow',tick);
window.addEventListener('storage',e=>{if(e.key!==KEY||!e.newValue)return;try{const incoming=validState(JSON.parse(e.newValue));if(!incoming)return;const y=window.scrollY;if(state.attempt===incoming.attempt&&state.status==='submitted'&&incoming.status!=='submitted')return;state=incoming;showExam();window.scrollTo(0,y);}catch(_){}});
const media=window.matchMedia('(min-width: 960px)');function cardMode(){ $('#answer-card').open=media.matches; }cardMode();media.addEventListener?.('change',cardMode);
load();if(state.status!=='ready'){const y=state.scrollY||0;if(state.status==='running'&&Math.max(Date.now(),state.lastSeen||0)>=state.deadline)submit('timeout');else{showExam();requestAnimationFrame(()=>window.scrollTo(0,y));}}
setInterval(tick,250);
})();
