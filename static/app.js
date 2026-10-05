let map, geoLayer, markerLayer, selected;
let municipalities=[];
let allCandidates=[];
let selectedCandidate=null;
const fmt=n=>new Intl.NumberFormat('pt-BR').format(Number(n||0));
const pct=n=>n==null?'—':`${Number(n).toLocaleString('pt-BR',{maximumFractionDigits:2})}%`;
async function api(u){const r=await fetch(u);if(!r.ok)throw new Error(await r.text());return r.json();}

async function loadGeo(){
  const url='https://cdn.jsdelivr.net/gh/henriquemalvar/br-geojson@main/dist/municipios/MA.geojson';
  try {
    const gj=await fetch(url).then(r=>r.json());
    if(geoLayer) map.removeLayer(geoLayer);
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
    if(geoLayer.getBounds().isValid()) map.fitBounds(geoLayer.getBounds());
  } catch(e) {
    console.error('Erro ao carregar GeoJSON:',e);
  }
}

function colorize(){
  if(!geoLayer || municipalities.length===0) return;
  const vals=municipalities.map(x=>Number(x.votos||0));
  const max=Math.max(...vals,1);
  geoLayer.eachLayer(l=>{
    const p=l.feature?.properties||{};
    const code=String(p.cd_geocmu||p.codigo||'');
    const c=code.length===7?code.slice(2):code.padStart(5,'0');
    const m=municipalities.find(x=>String(x.codigo)===c);
    const v=m?Number(m.votos):0;
    const q=v/max;
    l.setStyle({fillColor:q>.75?'#4c1d95':q>.5?'#6d28d9':q>.25?'#8b5cf6':'#c4b5fd',fillOpacity:v?0.55:0.08});
  });
}

async function openMunicipio(m){
  if(!m) return;
  selected=m;
  document.querySelector('#detailTitle').textContent=m.nome;
  document.querySelector('#detailSub').textContent=`${fmt(m.votos)} votos do candidato no município. Carregando seções...`;
  if(m.latitude&&m.longitude) map.setView([m.latitude,m.longitude],11);
  markerLayer?.clearLayers();
  markerLayer=L.layerGroup().addTo(map);
  let rows=[];
  try{
    rows=await api(`/api/municipios/${m.codigo}/secoes`);
  }catch(e){
    document.querySelector('#sectionGrid').innerHTML='<p>Não há seções cadastradas para este município neste momento.</p>';
    return;
  }
  let html='<table><thead><tr><th>Zona</th><th>Seção</th><th>Local</th><th>Votos</th></tr></thead><tbody>';
  if(rows.length===0){
    html+='<tr><td colspan="4" style="text-align:center">Nenhuma seção disponível</td></tr>';
  }else{
    for(const r of rows){
      html+=`<tr class="section" onclick="openSection('${m.codigo}','${r.zona}','${r.secao}','${(r.local_votacao||'').replaceAll("'","")}')"><td>${r.zona}</td><td>${r.secao}</td><td>${r.local_votacao||'—'}</td><td id="v-${r.zona}-${r.secao}">—</td></tr>`;
    }
  }
  html+='</tbody></table>';
  document.querySelector('#sectionGrid').innerHTML=html;
  document.querySelector('#detailSub').textContent=rows.length===0?'Nenhuma seção cadastrada':`${rows.length} seções cadastradas. Clique em uma seção para consultar o BU e a votação nominal.`;
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
    const cell=document.querySelector(`#v-${z}-${s}`);
    if(cell) cell.textContent=d.votos==null?'—':fmt(d.votos);
  }catch(e){
    document.querySelector('#detailSub').textContent='Não foi possível obter o arquivo da seção.';
  }
}

async function selectCandidate(numero){
  if(!numero) return;
  const cand=allCandidates.find(c=>String(c.numero)===String(numero));
  if(!cand) return;
  selectedCandidate=cand;
  localStorage.setItem('selectedCandidate',JSON.stringify(selectedCandidate));
  await loadCandidateData();
}

async function loadCandidateData(){
  if(!selectedCandidate) return;
  try{
    const params=new URLSearchParams({numero:String(selectedCandidate.numero)});
    const c=await api(`/api/candidato?${params.toString()}`);
    document.querySelector('#candidate').textContent=c.nome||'Candidato';
    document.querySelector('#party').textContent=[c.partido_sigla,c.partido_nome].filter(Boolean).join(' · ');
    document.querySelector('#number').textContent=c.numero||'—';
    document.querySelector('#votes').textContent=fmt(c.votos);
    document.querySelector('#percent').textContent=pct(c.percentual);
    municipalities=await api(`/api/municipios?${params.toString()}`);
    updateMunicipalitySelector();
    renderList();
    await loadGeo();
    colorize();
  }catch(e){
    console.error('Erro ao carregar candidato:',e);
    document.querySelector('#detailSub').textContent=`Erro: ${e.message}`;
  }
}

function updateMunicipalitySelector(){
  const selector=document.querySelector('#municipalitySelector');
  if(!selector) return;
  selector.innerHTML='<option value="">Todos os municípios</option>';
  municipalities.forEach(m=>{
    const opt=document.createElement('option');
    opt.value=m.codigo;
    opt.textContent=`${m.nome} (${fmt(m.votos)} votos)`;
    selector.appendChild(opt);
  });
  selector.onchange=()=>{
    const code=selector.value;
    if(code){
      const m=municipalities.find(x=>x.codigo===code);
      if(m) openMunicipio(m);
    }else if(geoLayer){
      map.fitBounds(geoLayer.getBounds());
    }
  };
}

async function loadCandidateSelector(){
  try{
    allCandidates=await api('/api/candidatos');
    const selector=document.querySelector('#candidateSelector');
    if(!selector) return;
    selector.innerHTML='<option value="">-- Selecione um candidato --</option>';
    allCandidates.forEach(c=>{
      const opt=document.createElement('option');
      opt.value=c.numero;
      opt.textContent=`${c.nome} (${c.numero}) - ${c.partido||'—'}`;
      selector.appendChild(opt);
    });
    selector.onchange=()=>selectCandidate(selector.value);
  }catch(e){
    console.error('Erro ao carregar candidatos:',e);
    const configSection=document.querySelector('#configSection');
    if(configSection) configSection.innerHTML=`<p style="color:red;padding:10px">Erro ao carregar candidatos: ${e.message}</p>`;
  }
}

function renderList(){
  const box=document.querySelector('#municipalityList');
  if(!box) return;
  box.innerHTML=municipalities.slice().sort((a,b)=>b.votos-a.votos).map(m=>`<div class="item" onclick='openMunicipio(${JSON.stringify(m)})'><b>${m.nome}</b><span>${fmt(m.votos)} votos</span></div>`).join('');
}

const searchEl=document.querySelector('#search');
if(searchEl){
  searchEl.addEventListener('input',e=>{
    const q=e.target.value.toLowerCase();
    document.querySelectorAll('.item').forEach(el=>el.style.display=el.innerText.toLowerCase().includes(q)?'block':'none');
  });
}

const backEl=document.querySelector('#back');
if(backEl){
  backEl.onclick=()=>{
    if(geoLayer && geoLayer.getBounds().isValid()) map.fitBounds(geoLayer.getBounds());
  };
}

async function init(){
  map=L.map('map').setView([-5.1,-45],6.5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors'}).addTo(map);
  
  await loadCandidateSelector();
  
  try {
    const c=await api('/api/candidato');
    selectedCandidate={numero:c.numero,nome:c.nome};
    const selector=document.querySelector('#candidateSelector');
    if(selector) selector.value=c.numero;
    await loadCandidateData();
  } catch(e) {
    console.log('Nenhum candidato configurado, selecione um na lista');
    document.querySelector('#detailSub').textContent='Selecione um candidato no seletor acima para começar';
  }
}

document.addEventListener('DOMContentLoaded',()=>{
  init().catch(e=>{
    console.error('Erro na inicialização:',e);
    document.querySelector('#candidate').textContent='Erro ao inicializar';
    document.querySelector('#detailSub').textContent=e.message;
  });
});
