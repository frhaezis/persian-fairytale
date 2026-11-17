/* Teaching is data, not prose inferred from a test result. Every practice view
 * receives the exact mission/exercise preparation authored with that task. */
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text=value=>esc(Array.isArray(value)?value.join('\n'):value).replace(/\n/g,'<br>');
const code=value=>value?'<pre class="teaching-code"><code>'+esc(value)+'</code></pre>':'';
function example(value){if(!value)return '';if(typeof value==='object')return '<div class="worked-note">'+text(value.text||value.explanation||JSON.stringify(value))+'</div>';if(/(^|\n)\s*(def |class |import |from \w+ import |for .+:|with .+:|return |print\()/m.test(value))return code(value);return '<div class="worked-note">'+text(value)+'</div>';}
export function teachingSections(teaching={},fallback={}){
  const sections=[];
  if(teaching.prerequisites?.length)sections.push({id:'foundations',title:'Что понадобится',html:'<p class="section-lead">Эти опоры можно повторить сейчас и открыть во время практики.</p>'+teaching.prerequisites.map(x=>'<article class="foundation"><h4>'+esc(x.name)+'</h4><p>'+text(x.explanation)+'</p>'+example(x.example)+code(x.code)+'</article>').join('')});
  const steps=teaching.steps?.length?teaching.steps:(fallback.lesson||[]).map((value,i)=>({title:'Шаг '+(i+1),text:value}));
  steps.forEach((x,i)=>sections.push({id:x.id||'step-'+i,title:x.title||'Шаг '+(i+1),html:'<div class="lesson-copy">'+text(x.text||x.body||'')+'</div>'+example(x.example)+code(x.code)}));
  const worked=teaching.workedExample;
  if(worked)sections.push({id:'worked',title:worked.title||'Разобранный пример',html:(typeof worked==='string'?example(worked):'<ol class="worked-steps">'+(worked.steps||[]).map(s=>'<li>'+text(s)+'</li>').join('')+'</ol>'+code(worked.code))});
  else if(fallback.workedExample)sections.push({id:'worked',title:'Разобранный пример',html:example(fallback.workedExample)});
  if(teaching.taskBridge)sections.push({id:'bridge',title:'От примера к задаче',html:'<p class="lesson-copy">'+text(teaching.taskBridge)+'</p>'});
  return sections.length?sections:[{id:'intro',title:'Объяснение',html:'<p>'+text(fallback.objective||teaching.goal||'')+'</p>'}];
}
export function pitfallsHTML(teaching={}){
  return (teaching.pitfalls||[]).map(x=>'<details class="pitfall"><summary>'+esc(x.symptom||x.title||'Разобрать затруднение')+'</summary><p>'+text(x.explanation||x.text)+'</p>'+code(x.code)+'</details>').join('');
}
export function lessonHTML(mission,page){
  const teaching=mission.teaching||{},sections=teachingSections(teaching,mission),idx=Math.max(0,Math.min(page||0,sections.length-1)),section=sections[idx];
  return {sections,index:idx,html:'<div class="learning-layout"><nav class="learning-map" aria-label="Разделы объяснения"><div class="eyebrow">МАРШРУТ МЫСЛИ</div>'+sections.map((x,i)=>'<button data-lesson-section="'+i+'" class="'+(i===idx?'selected':'')+'"><span>'+String(i+1).padStart(2,'0')+'</span>'+esc(x.title)+'</button>').join('')+'</nav><article class="learning-page"><div class="lesson-goal">'+text(teaching.goal||mission.objective)+'</div><div class="eyebrow">ШАГ '+(idx+1)+' ИЗ '+sections.length+'</div><h3>'+esc(section.title)+'</h3>'+section.html+((mission.id==='m19'&&/dropout/i.test(section.title+' '+section.html))?dropoutHTML():'')+'</article></div>'};
}
export function helpHTML(mission,exercise,state={}){
  const sources=[{id:'mission',title:'Смысл и теория',teaching:mission.teaching||{},fallback:mission}];
  if(exercise?.teaching)sources.unshift({id:'exercise',title:'Код и API',teaching:exercise.teaching,fallback:{}});
  const selected=sources.find(x=>x.id===state.source)||sources[0];
  const sections=teachingSections(selected.teaching,selected.fallback);
  const idx=Math.max(0,Math.min(state.page||0,sections.length-1));
  return '<div class="help-heading"><div><div class="eyebrow">ОПОРА РЯДОМ</div><h3>Разобраться по шагам</h3></div><button id="toggleHelp" class="text-button" aria-expanded="true">Свернуть</button></div><div id="helpInner"><div class="help-tabs">'+sources.map(x=>'<button data-help-source="'+x.id+'" class="'+(x.id===selected.id?'selected':'')+'">'+esc(x.title)+'</button>').join('')+'</div><label class="help-select"><span>Нужный шаг</span><select id="helpSection">'+sections.map((x,i)=>'<option value="'+i+'" '+(i===idx?'selected':'')+'>'+esc(x.title)+'</option>').join('')+'</select></label><article class="help-page"><h4>'+esc(sections[idx].title)+'</h4>'+sections[idx].html+'</article><div class="help-pager"><button id="helpPrev" '+(idx?'':'disabled')+'>←</button><span>'+(idx+1)+' / '+sections.length+'</span><button id="helpNext" '+(idx===sections.length-1?'disabled':'')+'>→</button></div>'+((selected.teaching.pitfalls||[]).length?'<details class="help-errors"><summary>Разобрать возможную ошибку</summary>'+pitfallsHTML(selected.teaching)+'</details>':'')+'</div>';
}
export function bindHelp(root,mission,exercise,state,onChange){
  const sources=exercise?.teaching?['exercise','mission']:['mission'];
  state.source=sources.includes(state.source)?state.source:sources[0];
  const refresh=()=>{root.innerHTML=helpHTML(mission,exercise,state);bindHelp(root,mission,exercise,state,onChange);onChange?.();};
  root.querySelectorAll('[data-help-source]').forEach(b=>b.onclick=()=>{state.source=b.dataset.helpSource;state.page=0;refresh();});
  root.querySelector('#helpSection').onchange=e=>{state.page=+e.target.value;refresh();};
  root.querySelector('#helpPrev').onclick=()=>{state.page=Math.max(0,(state.page||0)-1);refresh();};
  root.querySelector('#helpNext').onclick=()=>{state.page=(state.page||0)+1;refresh();};
  root.querySelector('#toggleHelp').onclick=e=>{const inner=root.querySelector('#helpInner');inner.hidden=!inner.hidden;e.target.textContent=inner.hidden?'Показать':'Свернуть';e.target.setAttribute('aria-expanded',String(!inner.hidden));};
}
export function chartHTML(artifact){
  if(artifact?.kind!=='training-curves'||!Array.isArray(artifact.series))return '';
  const series=artifact.series.filter(s=>Array.isArray(s.values)&&s.values.length&&s.values.every(Number.isFinite));
  if(!series.length)return '';
  const colors=['#197a78','#b97539','#a34c6e','#5664a2','#679141','#9b5645'];
  const xValues=series.flatMap(s=>s.steps?.length===s.values.length?s.steps:s.values.map((_,i)=>i));
  const minX=Math.min(...xValues),maxX=Math.max(...xValues),maxY=Math.max(...series.flatMap(s=>s.values),.001);
  const px=x=>58+(x-minX)/(maxX-minX||1)*594,py=y=>234-y/maxY*198;
  const paths=series.map((s,i)=>'<path d="'+s.values.map((y,j)=>(j?'L':'M')+px(s.steps?.[j]??j).toFixed(2)+','+py(y).toFixed(2)).join(' ')+'" fill="none" stroke="'+colors[i%colors.length]+'" stroke-width="2.3" '+(/validation|val|провер/i.test(s.label)?'stroke-dasharray="7 4"':'')+'/>').join('');
  return '<section class="experiment-results"><div class="eyebrow">РЕЗУЛЬТАТ ВАШЕГО ЗАПУСКА</div><h3>'+esc(artifact.title||'Кривые обучения')+'</h3><svg viewBox="0 0 680 290" role="img" aria-label="График ошибок обучения и проверки, рассчитанных вашим кодом">'+[0,.25,.5,.75,1].map(f=>'<line x1="58" x2="652" y1="'+py(maxY*f)+'" y2="'+py(maxY*f)+'" stroke="#d5d9d0"/><text x="49" y="'+(py(maxY*f)+4)+'" text-anchor="end" font-size="10">'+(maxY*f).toPrecision(3)+'</text>').join('')+paths+'<text x="354" y="272" text-anchor="middle" font-size="12">'+esc(artifact.xLabel||'Шаг')+'</text><text x="58" y="20" font-size="12">'+esc(artifact.yLabel||'Ошибка')+'</text><text x="58" y="250" font-size="10">'+minX+'</text><text x="652" y="250" text-anchor="end" font-size="10">'+maxX+'</text></svg><div class="chart-legend">'+series.map((s,i)=>'<span><i style="background:'+colors[i%colors.length]+'"></i>'+esc(s.label)+'</span>').join('')+'</div>'+((artifact.observations||[]).map(o=>'<p>'+text(o)+'</p>').join(''))+'<details><summary>Параметры и численные результаты</summary><pre>'+esc(JSON.stringify({parameters:artifact.parameters,series},null,2))+'</pre></details></section>';
}
export function agentTraceHTML(result){
  if(!result)return '<p class="smallprint">Используются адрес API и имя модели из панели подключения выше.</p>';
  const reasons={final_answer:'Модель вернула итоговый ответ',tool_stop:'Инструмент запросил остановку',budget:'Исчерпан бюджет шагов',api_error:'API недоступен',invalid_action:'Недопустимое действие отклонено'};
  return '<div class="agent-trace"><div class="callout '+(result.success?'success':'warning')+'"><strong>'+esc(reasons[result.stoppedReason]||result.stoppedReason)+'</strong><p>Вызовов модели: '+esc(result.modelCalls||0)+' · инструментов: '+esc(result.toolCalls||0)+'.</p>'+text(result.answer||result.error||'')+'</div><ol>'+((result.trace||[]).map(item=>'<li><strong>Шаг '+esc(item.step)+': '+esc(item.tool?'вызов '+item.tool:item.action==='final_answer'?'итоговый ответ':'ответ модели')+'</strong>'+ (item.tool?'<p>Аргументы</p><pre>'+esc(JSON.stringify(item.arguments,null,2))+'</pre><p>Наблюдение инструмента</p><pre>'+esc(JSON.stringify(item.observation,null,2))+'</pre>':'')+(item.error?'<p>'+text(item.error)+'</p>':'')+'<details><summary>Точный ответ модели</summary><pre>'+esc(item.modelContent||'')+'</pre></details></li>').join(''))+'</ol><p class="smallprint">'+text(result.note||'Штатное завершение протокола само по себе не доказывает, что цель решена правильно.')+'</p><details><summary>Полный журнал обмена</summary><pre>'+esc(JSON.stringify(result,null,2))+'</pre></details></div>';
}
export function dropoutHTML(){return '<section class="dropout-demo"><div class="eyebrow">ПОСМОТРЕТЬ НА ОДИН ШАГ</div><p>Четыре промежуточных значения: 2, 4, 6, 8. При обучении каждое независимо остаётся с вероятностью 1 − p. Сохранённые значения делятся на 1 − p.</p><label>Вероятность обнуления p: <strong id="dropoutP">0.5</strong><input id="dropoutRange" type="range" min="0" max=".8" step=".1" value=".5"></label><div class="dropout-units" id="dropoutUnits"></div><div class="inline-actions"><button id="dropoutDraw" class="secondary">Новая случайная маска</button><button id="dropoutEval" class="secondary">Режим проверки: eval()</button></div><p id="dropoutExplanation" class="smallprint"></p></section>';}
export function bindDropout(root=document){
  const slider=root.querySelector('#dropoutRange');if(!slider)return;let evalMode=false;
  function draw(){const p=+slider.value;root.querySelector('#dropoutP').textContent=p.toFixed(1);const xs=[2,4,6,8];const values=xs.map(x=>evalMode?x:Math.random()<p?0:x/(1-p));root.querySelector('#dropoutUnits').innerHTML=values.map((v,i)=>'<div class="dropout-unit '+(!v?'off':'')+'"><small>'+xs[i]+'</small><span>↓</span><strong>'+Number(v.toFixed(2))+'</strong></div>').join('');root.querySelector('#dropoutExplanation').textContent=evalMode?'В eval() Dropout пропускает значения без изменения. Это не отключает autograd: для проверки дополнительно используют no_grad().':'Это один случайный отбор, а не обещание обнулить ровно p долю четырёх значений. При большом p обучению может не хватить сигнала.';root.querySelector('#dropoutEval').textContent=evalMode?'Вернуться к train()':'Режим проверки: eval()';}
  slider.oninput=draw;root.querySelector('#dropoutDraw').onclick=()=>{evalMode=false;draw();};root.querySelector('#dropoutEval').onclick=()=>{evalMode=!evalMode;draw();};draw();
}
