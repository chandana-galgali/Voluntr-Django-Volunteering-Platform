(()=>{
  const el=document.getElementById('vol-map'),data=document.getElementById('map-points');
  if(!el||!data)return;
  if(!window.L){el.classList.add('map-unavailable');el.textContent='The interactive map could not load. Use the opportunity list below.';return;}
  const points=JSON.parse(data.textContent);
  const map=L.map(el,{scrollWheelZoom:false}).setView([20.59,78.96],5);
  // OpenStreetMap's tile policy requires a Referer header.
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'strict-origin-when-cross-origin',attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
  map.on('focus',()=>map.scrollWheelZoom.enable());map.on('blur',()=>map.scrollWheelZoom.disable());
  const bounds=[];
  points.forEach(p=>{
    const div=document.createElement('div');div.className='map-popup';
    const a=document.createElement('a');a.href=p.url;a.textContent=p.title;
    const meta=document.createElement('span');meta.textContent=(p.category?p.category+' · ':'')+p.city+(p.mode?' · '+p.mode:'')+(p.approximate?' (approximate)':'');
    const more=document.createElement('a');more.href=p.url;more.textContent='View opportunity →';more.className='map-more';
    div.append(a,document.createElement('br'),meta,document.createElement('br'),more);
    L.marker(p.coords,{title:p.title,alt:p.title}).addTo(map).bindPopup(div);
    bounds.push(p.coords);
  });
  if(bounds.length)map.fitBounds(bounds,{padding:[30,30],maxZoom:12});
  setTimeout(()=>map.invalidateSize(),200);
})();
