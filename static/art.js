/* Original illustrations are bundled locally. This module only places/crops
 * atlas cells at render time; it does not fetch external artwork. */
let manifest = {scenes:{}, portraits:{}};
const pictures = new Map();
let ready;
const safe = value => String(value || '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function localSource(entry) {const src=entry?.src||''; return /^\/?art\/[a-zA-Z0-9_.\-/ ]+$/.test(src)?(src.startsWith('/')?src:'/'+src):'';}
export function loadArt() {
  if (ready) return ready;
  ready=fetch('/art/manifest.json').then(r=>{if(!r.ok)throw Error('Illustration manifest unavailable');return r.json();}).then(async data=>{
    manifest={scenes:{},portraits:{},...data};
    const entries=[...Object.values(manifest.scenes),...Object.values(manifest.portraits)];
    await Promise.all([...new Set(entries.map(localSource).filter(Boolean))].map(src=>new Promise(resolve=>{
      const img=new Image(); pictures.set(src,img);img.onload=()=>resolve();img.onerror=()=>resolve();img.src=src;
    })));
    document.body.dataset.artReady=String([...pictures.values()].filter(x=>x.complete&&x.naturalWidth).length);
    document.dispatchEvent(new Event('persianartready'));
    return manifest;
  }).catch(()=>manifest);
  return ready;
}
export function sceneEntry(id){return manifest.scenes[String(id)]||manifest.scenes[id];}
export function portraitEntry(name){return manifest.portraits[name];}
export function artStyle(entry){
  const src=localSource(entry);if(!src)return '';
  const a=entry.atlas;const size=a?`${a.cols*100}% ${a.rows*100}%`:(entry.size||'cover');
  const position=a?`${a.cols>1?a.col/(a.cols-1)*100:50}% ${a.rows>1?a.row/(a.rows-1)*100:50}%`:(entry.position||'50% 50%');
  return `background-image:url('${safe(src)}');background-size:${safe(size)};background-position:${safe(position)};`;
}
export function sceneMarkup(id, className='scene-image'){return `<div class="${safe(className)}" style="${artStyle(sceneEntry(id))}" aria-hidden="true"></div>`;}
export function portraitMarkup(name,className='portrait-image'){
  const entry=portraitEntry(name);return entry?`<div class="${safe(className)}" style="${artStyle(entry)}" role="img" aria-label="${safe(name)}"></div>`:'';
}
export function drawArt(ctx,entry,x,y,width,height){
  const img=pictures.get(localSource(entry));if(!img?.complete||!img.naturalWidth)return false;
  const a=entry.atlas||{cols:1,rows:1,col:0,row:0};
  const sw=img.naturalWidth/a.cols,sh=img.naturalHeight/a.rows;
  const cover=Math.max(width/sw,height/sh),cw=width/cover,ch=height/cover;
  ctx.drawImage(img,a.col*sw+(sw-cw)/2,a.row*sh+(sh-ch)/2,cw,ch,x,y,width,height);return true;
}
