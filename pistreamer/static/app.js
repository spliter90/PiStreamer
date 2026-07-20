const fmt=s=>new Date(s*1000).toISOString().slice(11,19);
let statusData={streaming:false,paused:false};
const healthLabels={good:'STABIL',warning:'WARNUNG',critical:'KRITISCH',offline:'OFFLINE'};
async function refresh(){
  const r=await fetch('/api/status');
  if(r.status===401){location='/login';return}
  const d=await r.json();statusData=d;
  document.querySelector('#state').textContent=d.streaming?(d.paused?'PAUSE':'LIVE'):'OFFLINE';
  document.querySelector('#dot').classList.toggle('live',d.streaming);
  document.querySelector('#uptime').textContent=fmt(d.uptime);
  document.querySelector('#cpu').textContent=d.cpu+' %';
  document.querySelector('#ram').textContent=d.ram+' %';
  document.querySelector('#temp').textContent=d.temperature===null?'–':d.temperature+' °C';
  const p=document.querySelector('#pause-button');p.disabled=!d.streaming;p.textContent=d.paused?'▶ Fortsetzen':'⏸ Pause';
  try{
    const n=await fetch('/api/network/status',{cache:'no-store'}).then(x=>x.json());
    document.querySelector('#health').textContent=healthLabels[n.health]||n.health;
    document.querySelector('#health-message').textContent=n.message||'';
    document.querySelector('#upload').textContent=(n.upload_mbps||0).toFixed(2)+' Mbit/s';
    document.querySelector('#profile').textContent=(n.profile||'custom').replaceAll('_',' ')+(n.auto_quality?' · AUTO':'');
    document.querySelector('#stream-errors').textContent=(n.reconnects||0)+' / '+(n.dropped_frames||0);
  }catch(e){document.querySelector('#health').textContent='UNBEKANNT'}
  const l=await fetch('/api/logs').then(x=>x.json());
  document.querySelector('#logs').textContent=l.lines.slice(-80).join('\n')||'Noch keine Meldungen.';
}
async function action(name){const r=await fetch('/api/'+name,{method:'POST'});const d=await r.json();if(!r.ok)alert(d.error||'Fehler');setTimeout(refresh,500)}
async function togglePause(){await action(statusData.paused?'resume':'pause')}
refresh();setInterval(refresh,3000);
