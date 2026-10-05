let map, geoLayer, markerLayer, selected;
let municipalities=[];
const fmt=n=>new Intl.NumberFormat('pt-BR').format(Number(n||0));
const pct=n=>n==null?'—':`${Number(n).toLocaleString('pt-BR',{maximumFractionDigits:2})}%`;
async function api(u){const r=await fetch(u);if(!r.ok)throw new Error(await r.text());return r.json();}

async function loadGeo(){
  // Dataset público com malha municipal baseada no IBGE.
  const url='https://cdn.jsdelivr.net/gh/henriquemalvar/br-geojson@main/dist/municipios/MA.geojson';
  const gj=await fetch(url).then(r=>r.json());
  geoLayer=L.geoJSON(gj,{
    style:()=>({color:'#667085',weight:.8,fillColor:'#7c3aed',fillOpacity:.12}),
    onEachFeature:(f,l)=>{
      const p=f.properties||{};
      const code=String(p.cd_geocmu||p.codigo||p.CD_MUN||'');
      const code5=code.length===7?code.slice(2):code.padStart(5,'0');
      const m=municipalities.find(x=>String(x.codigo)===code5);
      if(m){
        l.bindTooltip(`${m.nome}<br><b>${fmt(m.votos)} votos</b>`);
        l.on('click',()=>openMunicipio(m));
      }
    }
  }).addTo(map);
  map.fitBounds(geoLayer.getBounds());
}

function colorize(){
  const vals=municipalities.map(x=>Number(x.votos||0)); const max=Math.max(...vals,1);
  if(!geoLayer)return;
  geoLayer.eachLayer(l=>{
    const p=l.feature?.properties||{};const code=String(p.cd_geocmu||p.codigo||'');const c=code.length===7?code.slice(2):code.padStart(5,'0');
    const m=municipalities.find(x=>String(x.codigo)===c);const v=m?Number(m.votos):0;
    const q=v/max;
    l.setStyle({fillColor:q>.75?'#4c1d95':q>.5?'#6d28d9':q>.25?'#8b5cf6':'#c4b5fd',fillOpacity:v?0.55:0.08});
  });
}

async function openMunicipio(m){
  selected=m;
  document.querySelector('#detailTitle').textContent=m.nome;
  document.querySelector('#detailSub').textContent=`${fmt(m.votos)} votos do candidato no município. Carregando seções...`;
  const bounds=geoLayer?.getBounds();
  if(m.latitude&&m.longitude)map.setView([m.latitude,m.longitude],11);
  markerLayer?.clearLayers(); markerLayer=L.layerGroup().addTo(map);
  let rows=[];
  try{rows=await api(`/api/municipios/${m.codigo}/secoes`)}catch(e){document.querySelector('#sectionGrid').innerHTML='<p>Não foi possível consultar as seções.</p>';return}
  let html='<table><thead><tr><th>Zona</th><th>Seção</th><th>Local</th><th>Votos</th></tr></thead><tbody>';
  for(const r of rows){
    html+=`<tr class="section" onclick="openSection('${m.codigo}','${r.zona}','${r.secao}','${(r.local_votacao||'').replaceAll("'","")}')"><td>${r.zona}</td><td>${r.secao}</td><td>${r.local_votacao||'Consultar BU'}</td><td id="v-${r.zona}-${r.secao}">—</td></tr>`;
  }
  html+='</tbody></table>';
  document.querySelector('#sectionGrid').innerHTML=html;
  document.querySelector('#detailSub').textContent=`${rows.length} seções cadastradas. Clique em uma seção para consultar o BU e a votação nominal.`;
}

async function openSection(m,z,s,local){
  const title=document.querySelector('#detailTitle');
  title.textContent=`Zona ${z} · Seção ${s}`;
  document.querySelector('#detailSub').textContent=`Consultando arquivo de urna do TSE${local?' · '+local:''}...`;
  try{
    const d=await api(`/api/secoes/${m}/${z}/${s}`);
    document.querySelector('#detailSub').innerHTML=d.arquivo_disponivel
      ? `<b>${fmt(d.votos)} votos</b> para o candidato nesta urna · Situação: ${d.situacao||'—'}`
      : d.mensagem;
    const cell=document.querySelector(`#v-${z}-${s}`);if(cell)cell.textContent=d.votos==null?'—':fmt(d.votos);
  }catch(e){document.querySelector('#detailSub').textContent='Não foi possível obter o arquivo da seção.'}
}

async function init(){
  map=L.map('map').setView([-5.1,-45],6.5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);
  const c=await api('/api/candidato');
  document.querySelector('#candidate').textContent=c.nome||'Candidato';
  document.querySelector('#party').textContent=[c.partido_sigla,c.partido_nome].filter(Boolean).join(' · ');
  document.querySelector('#number').textContent=c.numero||'—';
  document.querySelector('#votes').textContent=fmt(c.votos);
  document.querySelector('#percent').textContent=pct(c.percentual);
  municipalities=await api('/api/municipios');
  renderList(); await loadGeo(); colorize();
}
function renderList(){
  const box=document.querySelector('#municipalityList');
  box.innerHTML=municipalities.slice().sort((a,b)=>b.votos-a.votos).map(m=>`<div class="item" onclick='openMunicipio(${JSON.stringify(m)})'><b>${m.nome}</b><span>${fmt(m.votos)} votos</span></div>`).join('');
}
document.querySelector('#search').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();document.querySelectorAll('.item').forEach(el=>el.style.display=el.innerText.toLowerCase().includes(q)?'block':'none');
});
document.querySelector('#back').onclick=()=>geoLayer&&map.fitBounds(geoLayer.getBounds());
init().catch(e=>{document.querySelector('#candidate').textContent='Erro ao carregar dados';document.querySelector('#detailSub').textContent=e.message});
