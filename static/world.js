import {sceneEntry,portraitEntry,drawArt} from './art.js';
/* Сад точных желаний — illustrated locations and point-and-click navigation.
 * Bundled original artwork; no external images, fonts, telemetry or requests.
 */
const W = 1000, H = 650;
const TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const PALETTES = [
  {name:'Ворота караванов', sky:'#162f46', stone:'#b98759', light:'#e6bf88', floor:'#c49a6e', shade:'#8c634b', tile:'#267c80', water:'#186f7e', glow:'#ffc66d', night:false},
  {name:'Мастерская Сафара', sky:'#243949', stone:'#ab775b', light:'#e1b27c', floor:'#ba8c65', shade:'#775747', tile:'#2b8387', water:'#286d79', glow:'#ffc063', night:false},
  {name:'Библиотека и обсерватория', sky:'#101d34', stone:'#6c6d7d', light:'#b9a69b', floor:'#737487', shade:'#45485c', tile:'#357d8d', water:'#214b68', glow:'#f9d99e', night:true},
  {name:'Сад возвращённой воды', sky:'#263d43', stone:'#ae9770', light:'#e1cea3', floor:'#b3ae82', shade:'#777a63', tile:'#448e86', water:'#286f73', glow:'#ffdb8a', night:false}
];
const STATIONS = [
  {id:'gate',x:178,y:316,name:'Хамид',label:'Ворота',color:'#d5a25f'},
  {id:'archive',x:806,y:286,name:'Лейла',label:'Архив',color:'#b87386'},
  {id:'workshop',x:236,y:493,name:'Сафар',label:'Мастерская',color:'#e9d8b8'},
  {id:'observatory',x:798,y:488,name:'Нур',label:'Обсерватория',color:'#78d4d1'},
  {id:'garden',x:515,y:555,name:'Мина',label:'Сад',color:'#92b878'}
];
const SCENE_LAYOUTS = [
  [{x:172,y:400,label:'Вход в сад'},{x:783,y:393,label:'Терраса историй'},{x:259,y:537,label:'Павильон'},{x:777,y:548,label:'Галерея'},{x:500,y:575,label:'Фонтан'}],
  [{x:186,y:378,label:'Галерея чертежей'},{x:749,y:345,label:'Архив образцов'},{x:334,y:530,label:'Лаборатория'},{x:809,y:539,label:'Стол опытов'},{x:575,y:575,label:'Внутренний двор'}],
  [{x:213,y:453,label:'Звёздные карты'},{x:773,y:390,label:'Библиотека'},{x:381,y:565,label:'Счётный зал'},{x:574,y:365,label:'Обсерватория'},{x:811,y:579,label:'Лунная терраса'}],
  [{x:160,y:398,label:'Дворцовая арка'},{x:799,y:440,label:'Зал летописей'},{x:303,y:551,label:'Дом мастеров'},{x:720,y:570,label:'Терраса совета'},{x:500,y:474,label:'Возвращённый сад'}]
];
const OBSTACLES = [
  {x:30,y:72,w:222,h:203},{x:276,y:75,w:448,h:126},{x:749,y:76,w:222,h:171},
  {x:66,y:373,w:244,h:79},{x:724,y:374,w:217,h:79},
  {x:438,y:289,w:124,h:118},
  {x:80,y:534,w:45,h:48},{x:891,y:535,w:43,h:48},
  {x:334,y:214,w:30,h:33},{x:649,y:214,w:30,h:33}
];

export class World {
  constructor(canvas, {onInteract=()=>{}, onMove=()=>{}} = {}) {
    this.canvas=canvas; this.ctx=canvas.getContext('2d');
    this.onInteract=onInteract; this.onMove=onMove;
    this.location=1; this.player={x:500,y:475}; this.completed=[]; this.inventory=[];
    this.mission=null; this.keys=new Set(); this.paused=false; this.reducedMotion=false;
    this.stations=STATIONS.map(s=>({...s})); this.path=[]; this.targetStation=null;
    this.direction={x:0,y:1}; this.walk=0; this.moving=false; this.time=0;
    this.lastTime=0; this.lastMoveNotify=0; this.lastInteraction=-Infinity;
    this.sigils=[]; this.flash=null; this.destroyed=false;this.drawNeeded=true;this.artActive=false;
    this.background=document.createElement('canvas'); this.background.width=W; this.background.height=H;
    this.canvas.setAttribute('aria-label','Игровой мир. Движение: стрелки или WASD. Разговор: E или пробел. Можно нажать на место, чтобы подойти.');
    if (!this.canvas.hasAttribute('tabindex')) this.canvas.tabIndex=0;
    this.canvas.style.touchAction='none';
    this._down=e=>this.keyDown(e); this._up=e=>{this.keys.delete(e.code);if(!this.keys.size&&!this.paused)this.notifyMove();};
    this._blur=()=>{this.keys.clear();this.path=[];this.moving=false;};
    this._pointer=e=>this.pointer(e);
    window.addEventListener('keydown',this._down); window.addEventListener('keyup',this._up);
    window.addEventListener('blur',this._blur); canvas.addEventListener('pointerdown',this._pointer);
    this.resizeObserver=new ResizeObserver(()=>this.resize()); this.resizeObserver.observe(canvas);
    this.resize(); this.drawBackground(); this.frame=requestAnimationFrame(t=>this.tick(t));
  }
  setState(state={}) {
    const changed=this.location!==clamp(Number(state.location)||1,1,4);
    const milestonesChanged=JSON.stringify(this.completed)!==JSON.stringify(Array.isArray(state.completed)?state.completed:[]);
    this.location=clamp(Number(state.location)||1,1,4);
    if(sceneEntry(this.location))this.stations=STATIONS.map((station,i)=>({...station,...SCENE_LAYOUTS[this.location-1][i]}));
    this.drawNeeded=true;
    if(state.player&&Number.isFinite(state.player.x)&&Number.isFinite(state.player.y)){
      this.player={x:clamp(state.player.x,24,W-24),y:clamp(state.player.y,216,H-35)};
      if(this.blocked(this.player.x,this.player.y)) this.player=this.nearestFree(this.player);
    }
    this.completed=Array.isArray(state.completed)?state.completed:[];
    this.inventory=Array.isArray(state.inventory)?state.inventory:[];
    this.sigils=Array.isArray(state.sigils)?[...state.sigils]:[];
    if(changed) {this.path=[];this.targetStation=null;}
    if(changed||milestonesChanged)this.drawBackground();
  }
  setMission(mission) {this.mission=mission||null;this.drawNeeded=true;const station=this.stations.find(x=>x.id===mission?.station);if(station&&mission.npc)station.name=mission.npc;}
  setPaused(paused) {this.drawNeeded=true;const wasPaused=this.paused;this.paused=Boolean(paused);if(paused){this.keys.clear();this.moving=false;if(!wasPaused)this.notifyMove();}}
  setReducedMotion(enabled) {this.reducedMotion=Boolean(enabled);this.drawNeeded=true;}
  navigateTo(id) {
    const station=this.stations.find(s=>s.id===id); if(!station) return false;
    this.targetStation=station; this.path=this.findPath(this.player,{x:station.x,y:station.y+36});
    return this.path.length>0;
  }
  destroy() {
    this.destroyed=true;cancelAnimationFrame(this.frame);this.resizeObserver.disconnect();
    window.removeEventListener('keydown',this._down);window.removeEventListener('keyup',this._up);
    window.removeEventListener('blur',this._blur);this.canvas.removeEventListener('pointerdown',this._pointer);
  }
  resize() {
    this.drawNeeded=true;
    const r=this.canvas.getBoundingClientRect(), dpr=Math.min(window.devicePixelRatio||1,2);
    this.canvas.width=Math.max(1,Math.round(r.width*dpr));this.canvas.height=Math.max(1,Math.round(r.height*dpr));
    this.scale=Math.min(this.canvas.width/W,this.canvas.height/H);
    this.offsetX=(this.canvas.width-W*this.scale)/2;this.offsetY=(this.canvas.height-H*this.scale)/2;
  }
  editable(e) {return /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(e.target?.tagName)||e.target?.isContentEditable;}
  keyDown(e) {
    if(this.paused||this.editable(e))return;
    if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','KeyW','KeyA','KeyS','KeyD'].includes(e.code)){
      e.preventDefault();this.keys.add(e.code);this.path=[];this.targetStation=null;
    }
    if(['KeyE','Space','Enter'].includes(e.code)&&!e.repeat){
      e.preventDefault();this.interact();
    }
  }
  pointer(e) {
    if(this.paused)return;
    this.canvas.focus({preventScroll:true});
    const rect=this.canvas.getBoundingClientRect();
    const p={x:((e.clientX-rect.left)*this.canvas.width/rect.width-this.offsetX)/this.scale,
      y:((e.clientY-rect.top)*this.canvas.height/rect.height-this.offsetY)/this.scale};
    const s=this.stations.find(v=>distance(p,v)<46||Math.abs(p.x-v.x)<69&&p.y>v.y-66&&p.y<v.y-27);
    if(s){
      if(distance(this.player,s)<79){this.interact(s);return;}
      this.targetStation=s;this.path=this.findPath(this.player,{x:s.x,y:s.y+36});
    } else {this.targetStation=null;this.path=this.findPath(this.player,this.nearestFree(p));}
    if(this.path.length)this.flash={x:this.path.at(-1).x,y:this.path.at(-1).y,start:this.time};
  }
  interact(explicit=null) {
    const now=performance.now()/1000;
    if(now-this.lastInteraction<.3)return false;
    const nearest=explicit||this.stations.reduce((best,s)=>distance(this.player,s)<distance(this.player,best)?s:best,this.stations[0]);
    if(distance(this.player,nearest)<84){this.lastInteraction=now;this.path=[];this.onInteract(nearest.id);return true;}
    return false;
  }
  blocked(x,y,r=12) {
    if(this.artActive)return x<44||x>W-44||y<310||y>H-28;
    if(x<24||x>W-24||y<214||y>H-28)return true;
    return OBSTACLES.some(o=>x+r>o.x&&x-r<o.x+o.w&&y+r>o.y&&y-r<o.y+o.h);
  }
  nearestFree(p) {
    const target={x:clamp(p.x,25,975),y:clamp(p.y,215,621)};
    if(!this.blocked(target.x,target.y))return target;
    for(let radius=16;radius<250;radius+=12)for(let i=0;i<32;i++){
      const q={x:target.x+Math.cos(i/32*TAU)*radius,y:target.y+Math.sin(i/32*TAU)*radius};
      if(!this.blocked(q.x,q.y))return q;
    }
    return{x:500,y:475};
  }
  findPath(start,end) {
    const cell=20, cols=W/cell, rows=Math.floor(H/cell);
    const position=n=>({x:(n%cols)*cell+cell/2,y:Math.floor(n/cols)*cell+cell/2});
    const idx=p=>clamp(Math.floor(p.y/cell),0,rows-1)*cols+clamp(Math.floor(p.x/cell),0,cols-1);
    const startId=idx(this.nearestFree(start)), endId=idx(this.nearestFree(end));
    const open=[startId], closed=new Set(), previous=new Map(), score=new Map([[startId,0]]);
    const heuristic=id=>distance(position(id),position(endId));
    let reached=null;
    while(open.length&&closed.size<1700){
      open.sort((a,b)=>(score.get(a)+heuristic(a))-(score.get(b)+heuristic(b)));
      const current=open.shift(); if(current===endId){reached=current;break;}
      closed.add(current);const p=position(current);
      for(const[dx,dy]of [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]]){
        const q={x:p.x+dx*cell,y:p.y+dy*cell};const n=idx(q);
        if(closed.has(n)||this.blocked(q.x,q.y)||this.blocked(p.x+dx*cell,p.y)||this.blocked(p.x,p.y+dy*cell))continue;
        const next=score.get(current)+Math.hypot(dx,dy)*cell;
        if(!score.has(n)||next<score.get(n)){score.set(n,next);previous.set(n,current);if(!open.includes(n))open.push(n);}
      }
    }
    if(reached===null)return[];
    const path=[];while(reached!==startId){path.push(position(reached));reached=previous.get(reached);}
    path.reverse();
    if(!this.blocked(end.x,end.y)&&distance(path.at(-1)||start,end)<32)path.push({...end});
    return path;
  }
  tick(timestamp) {
    if(this.destroyed)return;
    const dt=Math.min((timestamp-(this.lastTime||timestamp))/1000,.05);this.lastTime=timestamp;
    if(!this.paused){this.time+=dt;this.update(dt);}
    if(!this.paused||this.drawNeeded){this.draw();this.drawNeeded=false;}this.frame=requestAnimationFrame(t=>this.tick(t));
  }
  update(dt) {
    let dx=(this.keys.has('ArrowRight')||this.keys.has('KeyD')?1:0)-(this.keys.has('ArrowLeft')||this.keys.has('KeyA')?1:0);
    let dy=(this.keys.has('ArrowDown')||this.keys.has('KeyS')?1:0)-(this.keys.has('ArrowUp')||this.keys.has('KeyW')?1:0);
    if(!dx&&!dy&&this.path.length){const p=this.path[0],d=distance(this.player,p);if(d<5){this.path.shift();}else{dx=(p.x-this.player.x)/d;dy=(p.y-this.player.y)/d;}}
    const magnitude=Math.hypot(dx,dy);this.moving=magnitude>0;
    if(magnitude){dx/=magnitude;dy/=magnitude;this.direction={x:dx,y:dy};const step=154*dt;
      if(!this.blocked(this.player.x+dx*step,this.player.y))this.player.x+=dx*step;
      if(!this.blocked(this.player.x,this.player.y+dy*step))this.player.y+=dy*step;
      this.walk+=dt*10;
      if(this.time-this.lastMoveNotify>.3){this.notifyMove();}
    }
    if(!this.path.length&&this.targetStation){const target=this.targetStation;if(distance(this.player,target)<84){if(this.interact(target)){this.targetStation=null;this.notifyMove();}}else this.targetStation=null;}
    const stars=[{id:`${this.location}-0`,x:374,y:285},{id:`${this.location}-1`,x:644,y:470},{id:`${this.location}-2`,x:366,y:570}];
    for(const star of stars)if(!this.sigils.includes(star.id)&&distance(this.player,star)<22){this.sigils.push(star.id);this.flash={...star,start:this.time,collected:true};this.notifyMove();}
  }
  notifyMove(){this.lastMoveNotify=this.time;this.onMove({x:Math.round(this.player.x*100)/100,y:Math.round(this.player.y*100)/100,location:this.location,sigils:[...this.sigils]});}
  rounded(c,x,y,w,h,r,fill,stroke=null){c.beginPath();c.roundRect(x,y,w,h,r);if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.stroke();}}
  ellipse(c,x,y,rx,ry,fill){c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fillStyle=fill;c.fill();}
  star(c,x,y,r,color,rotation=0){c.save();c.translate(x,y);c.rotate(rotation);c.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4,rr=i%2?r*.32:r;c.lineTo(Math.cos(a)*rr,Math.sin(a)*rr);}c.closePath();c.fillStyle=color;c.fill();c.restore();}
  arch(c,x,y,w,h,fill,stroke=null){c.beginPath();c.moveTo(x,y+h);c.lineTo(x,y+w*.52);c.quadraticCurveTo(x,y+w*.14,x+w/2,y);c.quadraticCurveTo(x+w,y+w*.14,x+w,y+w*.52);c.lineTo(x+w,y+h);c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.stroke();}}
  dome(c,x,y,w,h,p){c.fillStyle=p.tile;c.beginPath();c.moveTo(x,y);c.bezierCurveTo(x,y-h*.6,x+w*.35,y-h*.8,x+w*.5,y-h);c.bezierCurveTo(x+w*.65,y-h*.8,x+w,y-h*.6,x+w,y);c.closePath();c.fill();c.strokeStyle='#c4c39a88';c.lineWidth=2;for(let i=1;i<5;i++){c.beginPath();c.moveTo(x+w*i/5,y);c.quadraticCurveTo(x+w*i/5,y-h*.65,x+w/2,y-h);c.stroke();}c.fillStyle='#e3be78';c.fillRect(x+w/2-1,y-h-13,2,14);this.star(c,x+w/2,y-h-15,4,'#edce8c');}
  mosaic(c,x,y,w,h,p){c.fillStyle=p.tile;c.fillRect(x,y,w,h);c.save();c.beginPath();c.rect(x,y,w,h);c.clip();for(let a=x+8;a<x+w;a+=16)for(let b=y+8;b<y+h;b+=16){c.strokeStyle='#b8c6a878';c.lineWidth=.8;c.beginPath();c.moveTo(a,b-6);c.lineTo(a+6,b);c.lineTo(a,b+6);c.lineTo(a-6,b);c.closePath();c.stroke();this.ellipse(c,a,b,1.6,1.6,'#d3bd84');}c.restore();}
  tower(c,x,y,w,h,p){
    c.fillStyle='#182a383a';c.fillRect(x+12,y+12,w,h+11);
    const gradient=c.createLinearGradient(x,y,x+w,y);gradient.addColorStop(0,p.shade);gradient.addColorStop(.35,p.light);gradient.addColorStop(.82,p.stone);gradient.addColorStop(1,p.shade);
    this.rounded(c,x,y,w,h,5,gradient);this.mosaic(c,x-3,y+22,w+6,15,p);this.mosaic(c,x-3,y+h-22,w+6,12,p);
    c.fillStyle=p.light;c.fillRect(x-5,y-3,w+10,12);for(let i=0;i<5;i++){c.fillRect(x-5+i*(w+4)/4,y-10,7,14);}
    this.arch(c,x+w*.3,y+51,w*.4,31,'#243c46','#c4a67b');
    c.strokeStyle=p.shade;c.lineWidth=1;for(let yy=y+100;yy<y+h-25;yy+=14){c.beginPath();c.moveTo(x+4,yy);c.lineTo(x+w-4,yy);c.stroke();}
  }
  rug(c,x,y,w,h){this.rounded(c,x+4,y+4,w,h,2,'#423d4c30');c.fillStyle='#8b4d4d';c.fillRect(x,y,w,h);c.strokeStyle='#d3a577';c.lineWidth=3;c.strokeRect(x+5,y+5,w-10,h-10);c.strokeStyle='#b57462';c.lineWidth=2;c.strokeRect(x+11,y+11,w-22,h-22);for(let yy=y+21;yy<y+h-15;yy+=21)for(let xx=x+23;xx<x+w-13;xx+=26)this.star(c,xx,yy,8,'#e5bc86',Math.PI/4);c.strokeStyle='#e4c39a';c.lineWidth=1;for(let xx=x+3;xx<x+w;xx+=5){c.beginPath();c.moveTo(xx,y-4);c.lineTo(xx,y+1);c.moveTo(xx,y+h-1);c.lineTo(xx,y+h+4);c.stroke();}}
  tree(c,x,y,s=1,p=PALETTES[0],flower=false){
    this.ellipse(c,x+9*s,y+3*s,36*s,14*s,'#152b3038');
    c.strokeStyle='#665344';c.lineWidth=8*s;c.beginPath();c.moveTo(x,y);c.lineTo(x+2*s,y-43*s);c.moveTo(x,y-20*s);c.lineTo(x-17*s,y-44*s);c.moveTo(x+1*s,y-26*s);c.lineTo(x+21*s,y-50*s);c.stroke();
    const colors=p.night?['#324f58','#42676b','#597677']:['#476a58','#5f8062','#849b6a'];
    [[-22,-45,23],[-8,-66,26],[18,-57,28],[0,-38,29],[29,-34,20]].forEach(([a,b,r],i)=>this.ellipse(c,x+a*s,y+b*s,r*s,r*.8*s,colors[i%3]));
    if(flower)for(let i=0;i<19;i++){const a=i*2.4,r=12+Math.sin(i*4)*23;this.ellipse(c,x+Math.cos(a)*r*s,y-51*s+Math.sin(a)*r*.65*s,2.6*s,2.6*s,'#e6b8a1');}
  }
  pot(c,x,y,green=true){this.ellipse(c,x+4,y+4,13,5,'#213c3a33');c.fillStyle='#9d6552';c.beginPath();c.moveTo(x-10,y-15);c.lineTo(x+10,y-15);c.lineTo(x+7,y);c.lineTo(x-7,y);c.closePath();c.fill();c.fillStyle='#d09a6e';c.fillRect(x-11,y-17,22,5);if(green){c.strokeStyle='#506c4b';c.lineWidth=2;for(let i=0;i<5;i++){c.beginPath();c.moveTo(x,y-14);c.quadraticCurveTo(x+(i-2)*10,y-37,x+(i-2)*8,y-27);c.stroke();}}}
  drawBackground(){
    const c=this.background.getContext('2d'),p=PALETTES[this.location-1];
    const gateOpen=this.completed.includes('m01'),gardenRestored=this.completed.includes('m40');
    c.clearRect(0,0,W,H);
    this.artActive=drawArt(c,sceneEntry(this.location),0,0,W,H);
    if(this.artActive){const shade=c.createLinearGradient(0,240,0,H);shade.addColorStop(0,'#081e2100');shade.addColorStop(1,'#081e2155');c.fillStyle=shade;c.fillRect(0,0,W,H);this.drawNeeded=true;return;}
    const sky=c.createLinearGradient(0,0,0,270);sky.addColorStop(0,p.sky);sky.addColorStop(1,p.shade);c.fillStyle=sky;c.fillRect(0,0,W,H);
    if(p.night){for(let i=0;i<54;i++){const x=(i*137.51)%W,y=12+(i*29.33)%157;this.ellipse(c,x,y,i%7?1:1.6,i%7?1:1.6,'#e1d0aa8a');}this.ellipse(c,581,47,17,17,'#e7d3a7');this.ellipse(c,589,40,15,15,p.sky);}
    if(this.location>=3&&this.completed.includes('m30')){
      const stars=[[414,43],[458,25],[499,59],[541,31],[588,65],[633,28],[672,49]];
      c.strokeStyle='#a5dcce88';c.lineWidth=1.2;c.beginPath();stars.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();
      for(const[x,y]of stars){this.star(c,x,y,4,'#e8e0ab');const g=c.createRadialGradient(x,y,1,x,y,13);g.addColorStop(0,'#a7e3cd55');g.addColorStop(1,'#a7e3cd00');c.fillStyle=g;c.fillRect(x-13,y-13,26,26);}
    }
    // Distant skyline makes each little courtyard feel part of a larger city.
    c.fillStyle='#152e3b66';for(let i=0;i<16;i++){const x=i*69-20,h=50+(i*17)%50;c.fillRect(x,174-h,61,h);if(i%3===0){c.beginPath();c.arc(x+30,174-h,30,Math.PI,TAU);c.fill();}}
    c.fillStyle=p.floor;c.fillRect(0,180,W,H-180);
    // Deterministic paving, with narrow grout and soft wear marks.
    for(let row=0;row<20;row++)for(let col=-1;col<22;col++){
      const x=col*51+(row%2)*25,y=180+row*28;
      c.fillStyle=(row*17+col*7)%5===0?'#ffffff08':'#00000006';c.fillRect(x+1,y+1,49,26);
      c.strokeStyle='#3c443219';c.lineWidth=.6;c.strokeRect(x,y,51,28);
      if((col*3+row)%7===0){c.strokeStyle='#f6dab31b';c.beginPath();c.moveTo(x+8,y+19);c.lineTo(x+28,y+17);c.stroke();}
    }
    // Inlaid turquoise paths around the central fountain.
    for(const x of[400,595]){c.fillStyle='#e8d3aa44';c.fillRect(x,210,5,406);c.fillStyle=p.tile+'55';c.fillRect(x+6,210,2,406);}
    c.fillStyle='#e9d4b342';c.fillRect(32,337,936,5);c.fillRect(32,424,936,5);
    // Rear arcade.
    c.fillStyle='#1d323d35';c.fillRect(284,89,448,125);
    c.fillStyle=p.stone;c.fillRect(274,75,452,122);this.mosaic(c,274,76,452,15,p);
    c.fillStyle=p.light;c.fillRect(268,69,464,8);c.fillRect(275,189,450,8);
    for(let i=0;i<8;i++){const x=290+i*54;this.arch(c,x,101,37,84,'#293c46');this.arch(c,x+5,107,27,78,'#203541');c.strokeStyle='#e4c29255';c.lineWidth=1;for(let j=0;j<4;j++){c.beginPath();c.moveTo(x+6+j*7,130);c.lineTo(x+6+j*7,184);c.stroke();}}
    // Gate with glazed tiles and paired minarets.
    c.fillStyle='#1f313f30';c.fillRect(56,92,186,195);
    c.fillStyle=p.stone;c.fillRect(58,98,180,167);this.dome(c,76,105,146,57,p);
    this.mosaic(c,83,119,130,132,p);this.arch(c,104,139,88,125,p.light);this.arch(c,114,149,68,116,'#233b47');
    c.fillStyle='#ba9362';c.fillRect(118,gateOpen?182:238,60,5);c.strokeStyle='#9c764d';c.lineWidth=2;for(let x=123;x<180;x+=10){c.beginPath();c.moveTo(x,gateOpen?163:185);c.lineTo(x,gateOpen?194:258);c.stroke();}
    if(gateOpen){const light=c.createLinearGradient(115,198,115,271);light.addColorStop(0,'#ddc58508');light.addColorStop(1,'#ddc58570');c.fillStyle=light;c.fillRect(115,198,66,67);c.strokeStyle='#d8c49a66';c.lineWidth=1;for(let i=0;i<4;i++){c.beginPath();c.moveTo(124+i*15,222);c.lineTo(122+i*16,265);c.stroke();}}
    this.tower(c,37,80,41,186,p);this.tower(c,217,80,38,186,p);
    this.rounded(c,102,267,93,7,1,'#e5c89a');
    // Library / observatory façade.
    c.fillStyle='#24303930';c.fillRect(760,103,212,153);
    c.fillStyle=p.stone;c.fillRect(752,100,215,144);this.dome(c,779,103,160,61,p);
    this.mosaic(c,750,105,219,14,p);c.fillStyle=p.light;c.fillRect(747,238,225,8);
    for(let i=0;i<3;i++){this.arch(c,774+i*58,137,40,89,p.light);this.arch(c,780+i*58,145,28,81,'#273d4a');}
    c.strokeStyle='#bb9f74';c.lineWidth=1;for(let x=785;x<924;x+=8){c.beginPath();c.moveTo(x,181);c.lineTo(x,222);c.stroke();}
    // Living craft spaces rather than empty decorative boxes.
    this.rug(c,122,453,162,57);this.rug(c,741,455,153,58);
    c.fillStyle='#26384433';c.fillRect(76,395,244,66);
    c.fillStyle=p.shade;c.fillRect(70,380,238,63);c.fillStyle=p.stone;c.fillRect(77,391,223,50);
    for(let i=0;i<8;i++){c.fillStyle=i%2?'#a2544c':'#d9b083';c.fillRect(66+i*31,374,31,24);c.beginPath();c.moveTo(66+i*31,398);c.lineTo(81+i*31,406);c.lineTo(97+i*31,398);c.fill();}
    c.fillStyle='#5e5348';c.fillRect(90,427,204,6);c.fillRect(94,430,7,13);c.fillRect(279,430,7,13);
    for(let i=0;i<6;i++){const x=110+i*28;this.rounded(c,x,409-(i%2)*5,17,17+(i%2)*5,2,i%2?'#b78159':'#327b7f');c.fillStyle='#edc58b';c.fillRect(x+4,406-(i%2)*5,9,4);}
    c.fillStyle=p.shade;c.fillRect(728,387,208,60);c.fillStyle=p.light;c.fillRect(724,380,216,10);this.mosaic(c,736,393,191,11,p);
    c.fillStyle='#6d554c';c.fillRect(750,433,165,7);c.fillRect(753,440,6,13);c.fillRect(903,440,6,13);
    for(let i=0;i<7;i++){c.fillStyle=['#4e7778','#9d6f5c','#cbb58a'][i%3];c.fillRect(760+i*11,412-i%3*3,8,21+i%3*3);}
    c.save();c.translate(877,419);c.rotate(-.45);this.rounded(c,-18,-6,47,12,3,'#baa075','#e8c589');c.fillStyle='#365f6b';c.fillRect(23,-7,8,14);c.restore();c.strokeStyle='#c6ad7b';c.lineWidth=3;c.beginPath();c.moveTo(877,420);c.lineTo(866,434);c.moveTo(877,420);c.lineTo(889,434);c.stroke();
    // Fountain basin; the water surface itself is animated separately.
    this.ellipse(c,509,400,69,16,'#28393d33');
    c.fillStyle=p.shade;c.beginPath();c.moveTo(440,316);c.lineTo(460,290);c.lineTo(540,290);c.lineTo(562,316);c.lineTo(562,385);c.lineTo(540,408);c.lineTo(460,408);c.lineTo(438,385);c.closePath();c.fill();
    c.strokeStyle=p.light;c.lineWidth=7;c.stroke();c.strokeStyle=p.tile;c.lineWidth=4;c.stroke();
    // Garden corners, planters, niches and climbing ivy.
    this.tree(c,103,562,.92,p,gardenRestored);this.tree(c,913,563,.98,p,gardenRestored);
    this.tree(c,350,237,.67,p,gardenRestored);this.tree(c,665,237,.67,p,gardenRestored);
    this.pot(c,288,281);this.pot(c,711,278);this.pot(c,324,465);this.pot(c,688,461);
    for(let i=0;i<5;i++){this.pot(c,445+i*26,612,i!==2);}
    c.strokeStyle='#607964';c.lineWidth=3;c.beginPath();c.moveTo(471,603);c.bezierCurveTo(462,576,478,570,470,548);c.moveTo(551,602);c.bezierCurveTo(563,580,550,562,559,545);c.stroke();
    // Low perimeter wall and tile edging.
    c.fillStyle=p.shade;c.fillRect(0,622,W,28);c.fillStyle=p.light;c.fillRect(0,619,W,6);this.mosaic(c,0,630,W,13,p);
    if(this.location===2){this.mosaic(c,447,230,107,28,p);for(let i=0;i<6;i++){this.rounded(c,458+i*15,238,9,11,2,i%2?'#e8c48c':'#84bcb0');}for(let i=0;i<5;i++){c.strokeStyle='#e8b87066';c.lineWidth=1.2;c.beginPath();c.moveTo(321+i*4,446);c.lineTo(396+i*4,446);c.lineTo(396+i*4,410);c.stroke();}}
    if(this.location===3){c.strokeStyle='#d4c59980';c.lineWidth=1;for(let i=0;i<12;i++){const a=i/12*TAU;c.beginPath();c.moveTo(500+Math.cos(a)*87,350+Math.sin(a)*75);c.lineTo(500+Math.cos(a)*93,350+Math.sin(a)*80);c.stroke();}}
    if(this.location===4){for(const bed of [{x:319,y:511,w:90,h:19},{x:602,y:511,w:90,h:19},{x:311,y:310,w:91,h:15},{x:601,y:310,w:91,h:15}]){this.rounded(c,bed.x,bed.y,bed.w,bed.h,7,'#586c50');for(let i=0;i<8;i++){const x=bed.x+7+i*10,y=bed.y+7+(i%2)*5;this.ellipse(c,x,y,4,3,['#d19b8f','#d4bf83','#c4cf9d'][i%3]);}}for(let i=0;i<(gardenRestored?80:16);i++){const x=40+(i*127)%920,y=278+(i*79)%321;if(!this.blocked(x,y,0)&&Math.abs(x-500)>100){this.ellipse(c,x,y,2,2,['#d9908b','#dcc184','#e8d6bc'][i%3]);}}}
    if(gardenRestored){
      for(let side=0;side<2;side++){
        const x=side?561:469;c.strokeStyle='#60835c';c.lineWidth=4;c.beginPath();c.moveTo(x,609);c.bezierCurveTo(x+(side?22:-22),570,x+(side?-6:6),537,x+(side?-19:19),517);c.stroke();
        for(let i=0;i<9;i++){const yy=526+i*9,xx=x+Math.sin(i*.7)*(side?12:-12);this.ellipse(c,xx,yy,7,3,'#89a471');this.star(c,xx+(side?5:-5),yy-3,4,i%2?'#efc5a4':'#f1d6a1');}
      }
      c.strokeStyle='#dfcd9c88';c.lineWidth=1.2;c.beginPath();c.ellipse(515,565,70,39,0,0,TAU);c.stroke();
    }
    // Vignette, kept gentle for navigation readability.
    const vignette=c.createRadialGradient(500,355,210,500,355,600);vignette.addColorStop(0,'#102b3800');vignette.addColorStop(1,p.night?'#08132677':'#1c303b33');c.fillStyle=vignette;c.fillRect(0,0,W,H);
  }
  drawWater(c,p){
    c.save();c.beginPath();c.moveTo(449,320);c.lineTo(466,302);c.lineTo(534,302);c.lineTo(550,320);c.lineTo(550,382);c.lineTo(535,397);c.lineTo(465,397);c.lineTo(449,382);c.closePath();c.clip();
    const water=c.createLinearGradient(450,300,555,410);water.addColorStop(0,p.water);water.addColorStop(1,'#418c8b');c.fillStyle=water;c.fillRect(442,297,117,108);
    const t=this.reducedMotion?0:this.time;
    c.strokeStyle='#bbdcc35a';c.lineWidth=1;for(let i=0;i<9;i++){c.beginPath();for(let x=447;x<=556;x+=5){const y=310+i*11+Math.sin(x*.07+t*.8+i)*2;if(x===447)c.moveTo(x,y);else c.lineTo(x,y);}c.stroke();}
    for(let i=0;i<3;i++){c.strokeStyle='#d8ecce'+(i===0?'6a':'3a');c.beginPath();c.ellipse(500,350,13+i*13+Math.sin(t)*2,6+i*6,0,0,TAU);c.stroke();}
    c.restore();
    c.fillStyle='#ddcaa5';c.fillRect(492,336,16,23);this.ellipse(c,500,337,15,7,p.light);this.ellipse(c,500,334,10,4,p.tile);
    if(this.location===3){c.save();c.translate(500,331);c.strokeStyle='#d5b779';c.lineWidth=2;c.beginPath();c.ellipse(0,-9,22,22,.5,0,TAU);c.stroke();c.beginPath();c.ellipse(0,-9,10,22,-.5,0,TAU);c.stroke();c.restore();}
    if(this.completed.includes('m18')){
      const motion=this.reducedMotion?0:Math.sin(this.time*1.6)*2;
      c.strokeStyle='#d4f0d4b3';c.lineWidth=1.6;
      for(const direction of[-1,1]){c.beginPath();c.moveTo(500,330);c.quadraticCurveTo(500+direction*18,300+motion,500+direction*31,351);c.stroke();this.ellipse(c,500+direction*31,352,7,2,'#d4f0d46a');}
      this.star(c,500,328,4,'#eef1ce');
    }
    if(this.completed.length>=10){const glow=c.createRadialGradient(500,332,0,500,332,37);glow.addColorStop(0,'#d5e9ba33');glow.addColorStop(1,'#d5e9ba00');c.fillStyle=glow;c.fillRect(463,295,74,74);}
  }
  drawLantern(c,x,y,p){
    const flicker=this.reducedMotion?1:1+Math.sin(this.time*1.8+x)*.07;
    const gateLit=this.completed.includes('m03')&&y===238;
    const glow=c.createRadialGradient(x,y,0,x,y,(gateLit?56:36)*flicker);glow.addColorStop(0,gateLit?'#ffd28a96':p.night?'#ffd28a50':'#ffd28a2d');glow.addColorStop(1,'#ffd28a00');c.fillStyle=glow;c.fillRect(x-60,y-60,120,120);
    c.strokeStyle='#665c4d';c.lineWidth=2;c.beginPath();c.moveTo(x,y-15);c.lineTo(x,y-8);c.stroke();this.rounded(c,x-5,y-7,10,13,2,'#f4ca7f','#7a6650');c.fillStyle='#77654e';c.fillRect(x-6,y-8,12,3);c.fillRect(x-6,y+5,12,3);
  }
  person(c,x,y,type='player',walk=0,dir={x:0,y:1}){
    const moving=walk!==0, stride=moving?Math.sin(walk)*3:0, bob=moving?Math.abs(Math.sin(walk))*1.2:0;
    this.ellipse(c,x+2,y+1,type==='nur'?13:12,5,type==='nur'?'#16374728':'#172c3b45');
    c.save();c.translate(x,y-bob);
    const body={player:'#3e8282',safar:'#e5d4b4',leila:'#9d5c77',nur:'#71d1c7',hamid:'#c39963',mina:'#789667'}[type];
    if(type==='nur'){
      const glow=c.createRadialGradient(0,-18,1,0,-18,30);glow.addColorStop(0,'#81e9dd44');glow.addColorStop(1,'#81e9dd00');c.fillStyle=glow;c.fillRect(-30,-48,60,60);c.globalAlpha=.9;
      c.fillStyle=body;c.beginPath();c.moveTo(-9,-25);c.quadraticCurveTo(-13,-9,-2,-2);c.quadraticCurveTo(4,5,12,-4);c.quadraticCurveTo(3,-4,7,-13);c.lineTo(9,-25);c.closePath();c.fill();
    }else{
      c.strokeStyle='#4d4542';c.lineWidth=5;c.lineCap='round';c.beginPath();c.moveTo(-4,-9);c.lineTo(-5-stride*.45,stride*.5);c.moveTo(4,-9);c.lineTo(5+stride*.45,-stride*.5);c.stroke();
      c.fillStyle=body;c.beginPath();c.moveTo(-8,-27);c.lineTo(8,-27);c.lineTo(12,-7);c.quadraticCurveTo(0,-3,-12,-7);c.closePath();c.fill();
      c.strokeStyle=body;c.lineWidth=5;c.beginPath();c.moveTo(-8,-24);c.lineTo(-12,-13-stride);c.moveTo(8,-24);c.lineTo(12,-13+stride);c.stroke();
      c.fillStyle=type==='player'?'#d5ab77':'#bb9a77';c.fillRect(-9,-14,18,3);
    }
    this.ellipse(c,0,-32,7,8,type==='nur'?'#c5f4dd':'#c6936c');
    if(type==='player'){
      c.fillStyle='#3e3e3d';c.beginPath();c.arc(0,-35,7.5,Math.PI,TAU);c.lineTo(7,-31);c.lineTo(-6,-34);c.closePath();c.fill();
      c.fillStyle='#e0c39a';c.fillRect(-8,-27,16,4);c.fillRect(3,-25,4,14);
      c.strokeStyle='#d3ad78';c.lineWidth=2;c.beginPath();c.moveTo(-5,-21);c.lineTo(7,-13);c.stroke();
    }else if(type==='safar'){
      this.ellipse(c,0,-38,9,5,'#e5d9bc');c.fillStyle='#425d6f';c.fillRect(-8,-37,16,3);c.fillStyle='#ded5b9';c.beginPath();c.moveTo(-4,-29);c.lineTo(5,-29);c.lineTo(0,-20);c.closePath();c.fill();
      c.strokeStyle='#65513e';c.lineWidth=2;c.beginPath();c.moveTo(13,-25);c.lineTo(16,2);c.stroke();
    }else if(type==='leila'){
      c.fillStyle='#654e65';c.beginPath();c.arc(0,-34,9,Math.PI,TAU);c.lineTo(10,-23);c.lineTo(4,-26);c.lineTo(6,-34);c.lineTo(-5,-35);c.lineTo(-5,-25);c.lineTo(-10,-22);c.closePath();c.fill();
      this.rounded(c,8,-20,9,12,1,'#d3b887','#775b56');
    }else if(type==='hamid'){
      this.ellipse(c,0,-39,9,4,'#f0dfb2');c.fillStyle='#b98350';c.fillRect(-8,-38,16,2);c.strokeStyle='#75644e';c.lineWidth=2;c.beginPath();c.moveTo(16,-40);c.lineTo(16,2);c.stroke();this.star(c,16,-41,4,'#d2b374');
    }else if(type==='mina'){
      this.ellipse(c,0,-39,11,3,'#d0ba81');this.ellipse(c,0,-41,7,4,'#bfa46f');
    }else{this.star(c,0,-45,4,'#d9f4d2');}
    if(dir.y>=-.5){c.fillStyle=type==='nur'?'#31575a':'#493a36';this.ellipse(c,-2.7+dir.x,-31,1,1,'#493a36');this.ellipse(c,2.7+dir.x,-31,1,1,'#493a36');}
    c.restore();
  }
  label(c,s,current,near){
    const p=PALETTES[this.location-1],width=current?148:111;
    this.rounded(c,s.x-width/2,s.y-74,width,23,6,current?'#173f4ee8':'#172b3bce',current?'#d6ba80':'#b7b89933');
    c.fillStyle=current?'#f4d69d':'#e9d9bc';c.textAlign='center';c.textBaseline='middle';c.font='600 11px system-ui, sans-serif';c.fillText(s.label,s.x,s.y-62);
    c.font='11px system-ui, sans-serif';c.fillStyle='#fff2d5';c.shadowColor='#17303c';c.shadowBlur=3;c.fillText(s.name,s.x,s.y+14);c.shadowBlur=0;
    if(current){
      const bob=this.reducedMotion?0:Math.sin(this.time*2.5)*3;
      this.star(c,s.x,s.y-91+bob,6,p.glow);
      c.strokeStyle='#e3c58b75';c.lineWidth=1;c.beginPath();c.ellipse(s.x,s.y+1,24,10,0,0,TAU);c.stroke();
    }
    if(near){this.rounded(c,s.x-62,s.y+26,124,25,7,'#f0dec0');c.fillStyle='#27424a';c.font='600 11px system-ui, sans-serif';c.fillText('E · поговорить',s.x,s.y+38);}
  }
  drawIllustrated(c){
    const p=PALETTES[this.location-1];
    // Small animated light keeps the authored scene calm; illustrations carry
    // the architecture, materials and atmosphere instead of procedural blocks.
    if(!this.reducedMotion)for(let i=0;i<13;i++){
      const x=80+((i*137+Math.sin(this.time*.12+i)*32)%840),y=230+(i*61)%350+Math.sin(this.time*.23+i)*11;
      this.ellipse(c,x,y,1.3,1.3,p.night?'#f6e2a17a':'#fff5d45a');
    }
    if(this.path.length){c.strokeStyle='#ffebc08a';c.lineWidth=2;c.setLineDash([3,9]);c.beginPath();c.moveTo(this.player.x,this.player.y);for(const point of this.path)c.lineTo(point.x,point.y);c.stroke();c.setLineDash([]);}
    const nearest=this.stations.reduce((best,item)=>distance(this.player,item)<distance(this.player,best)?item:best,this.stations[0]);
    for(const station of this.stations){
      const active=this.mission?.station===station.id;
      const near=nearest.id===station.id&&distance(this.player,station)<79&&!this.paused;
      const radius=active?25:17,y=station.y-27;
      c.save();c.globalAlpha=active?1:.83;
      this.ellipse(c,station.x,station.y+2,active?28:20,7,'#071b2870');
      c.beginPath();c.arc(station.x,y,radius+3,0,TAU);c.fillStyle='#142f36ee';c.fill();
      c.beginPath();c.arc(station.x,y,radius+3,0,TAU);c.lineWidth=active?2:1;c.strokeStyle=active?'#e8cb91':'#d2c5a27c';c.stroke();
      c.save();c.beginPath();c.arc(station.x,y,radius,0,TAU);c.clip();
      const drawn=drawArt(c,portraitEntry(station.name),station.x-radius,y-radius,radius*2,radius*2);
      if(!drawn){c.fillStyle='#2e5b57';c.fillRect(station.x-radius,y-radius,radius*2,radius*2);this.star(c,station.x,y,12,'#d4c48d');this.ellipse(c,station.x,y,4,4,'#2e5b57');}
      c.restore();
      if(active){const pulse=this.reducedMotion?0:Math.sin(this.time*2)*2;this.star(c,station.x,y-radius-14+pulse,5,'#ffe3a0');}
      const width=Math.max(100,station.label.length*6.4+18);this.rounded(c,station.x-width/2,station.y+12,width,24,5,active?'#143540f2':'#102c37cc',active?'#c9b382':'#b7b89944');
      c.textAlign='center';c.textBaseline='middle';c.fillStyle='#f8edcf';c.font='11px system-ui';c.fillText(station.label,station.x,station.y+24);
      if(active){c.font='10px system-ui';c.fillStyle='#e8ddc6';c.fillText(station.name,station.x,station.y+47);}
      if(near&&active){this.rounded(c,station.x-71,station.y-95,142,27,6,'#f0dec0');c.fillStyle='#243f47';c.font='600 11px system-ui';c.fillText('E · открыть разговор',station.x,station.y-81);}
      c.restore();
    }
    // A guide light travels over the illustrated map; it does not pretend the
    // painted pool/table is a physically walkable three-dimensional floor.
    this.ellipse(c,this.player.x,this.player.y,15,15,'#173f45db');
    c.beginPath();c.arc(this.player.x,this.player.y,15,0,TAU);c.strokeStyle='#e4c68d';c.lineWidth=1.5;c.stroke();
    this.star(c,this.player.x,this.player.y,10,'#f4ddab');
    this.ellipse(c,this.player.x,this.player.y,3,3,'#174049');
    this.rounded(c,25,22,355,55,7,'#102b3ce3','#d3bd874d');c.textAlign='left';c.textBaseline='middle';c.fillStyle='#d9c393';c.font='10px system-ui';c.fillText('АКТ '+['I','II','III','IV'][this.location-1]+'  /  PERSIAN FAIRYTALE',42,39);c.fillStyle='#fff1d8';c.font='18px Georgia';c.fillText(p.name,42,60);
    if(this.completed.length){this.rounded(c,806,23,167,32,6,'#102b3cce','#d3bd8733');c.fillStyle='#ead5a8';c.textAlign='center';c.font='11px system-ui';c.fillText(this.completed.length+' сохранённых открытий',889,39);}
  }
  draw(){
    const c=this.ctx;if(!this.scale)return;
    c.setTransform(1,0,0,1,0,0);c.fillStyle='#112632';c.fillRect(0,0,this.canvas.width,this.canvas.height);
    c.setTransform(this.scale,0,0,this.scale,this.offsetX,this.offsetY);
    c.drawImage(this.background,0,0);if(this.artActive){this.drawIllustrated(c);return;}const p=PALETTES[this.location-1];this.drawWater(c,p);
    for(const[x,y]of[[95,238],[204,238],[758,224],[950,224],[80,420],[299,420],[736,426],[927,426]])this.drawLantern(c,x,y,p);
    if(!this.reducedMotion){
      for(let i=0;i<8;i++){const x=360+Math.sin(this.time*.21+i*2.3)*240,y=300+Math.cos(this.time*.27+i*1.7)*220;this.ellipse(c,x,y,1,1,p.night?'#d7e5bf9a':'#fff3c94a');}
    }
    const stars=[{id:`${this.location}-0`,x:374,y:285},{id:`${this.location}-1`,x:644,y:470},{id:`${this.location}-2`,x:366,y:570}];
    for(const s of stars)if(!this.sigils.includes(s.id)){
      const bob=this.reducedMotion?0:Math.sin(this.time*1.6+s.x)*3;
      this.ellipse(c,s.x,s.y+5,6,2,'#5f68683d');this.star(c,s.x,s.y-4+bob,5,'#ffe4a1',this.reducedMotion?0:this.time*.2);
    }
    if(this.path.length){c.strokeStyle='#f4ddb666';c.lineWidth=2;c.setLineDash([2,8]);c.lineCap='round';c.beginPath();c.moveTo(this.player.x,this.player.y);for(const point of this.path)c.lineTo(point.x,point.y);c.stroke();c.setLineDash([]);}
    if(this.flash&&this.time-this.flash.start<.8){const age=(this.time-this.flash.start)/.8;c.strokeStyle=`rgba(255,228,174,${1-age})`;c.lineWidth=1.5;c.beginPath();c.ellipse(this.flash.x,this.flash.y,6+age*19,3+age*9,0,0,TAU);c.stroke();}
    const actors=this.stations.map((s,i)=>({...s,type:['hamid','leila','safar','nur','mina'][i]}));actors.push({...this.player,type:'player'});actors.sort((a,b)=>a.y-b.y);
    for(const a of actors){const float=a.type==='nur'&&!this.reducedMotion?Math.sin(this.time*1.5)*2:0;this.person(c,a.x,a.y+float,a.type,a.type==='player'&&this.moving&&!this.reducedMotion?this.walk:0,a.type==='player'?this.direction:{x:0,y:1});}
    const nearest=this.stations.reduce((best,s)=>distance(this.player,s)<distance(this.player,best)?s:best,this.stations[0]);
    for(const s of this.stations)this.label(c,s,this.mission?.station===s.id,nearest.id===s.id&&distance(this.player,s)<79&&!this.paused);
    // Small place plaque: the main app supplies the full narrative HUD.
    this.rounded(c,96,15,306,40,9,'#112b3cdd','#c5b38644');
    c.textAlign='left';c.textBaseline='middle';c.fillStyle='#dec797';c.font='600 10px system-ui, sans-serif';c.fillText(`АКТ ${['I','II','III','IV'][this.location-1]}  /  САД ТОЧНЫХ ЖЕЛАНИЙ`,110,28);
    c.fillStyle='#f5ead5';c.font='15px Georgia, serif';c.fillText(p.name,110,44);
    const got=this.sigils.filter(s=>s.startsWith(this.location+'-')).length;
    this.rounded(c,800,16,132,27,8,'#122c3cc9','#c5b38633');this.star(c,816,29,4,'#f4d59a');c.textAlign='left';c.font='11px system-ui, sans-serif';c.fillStyle='#e8d9bb';c.fillText(`Тихий свет ${got}/3`,826,30);
    if(this.paused){c.fillStyle='#10263816';c.fillRect(0,0,W,H);}
  }
}
