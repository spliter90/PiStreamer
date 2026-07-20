const $ = selector => document.querySelector(selector);
const fmtDuration = seconds => {
  const value = Math.max(0, Number(seconds) || 0);
  const days = Math.floor(value / 86400);
  const clock = new Date((value % 86400) * 1000).toISOString().slice(11, 19);
  return days ? `${days}d ${clock}` : clock;
};

let dashboard = {stream: {streaming: false, paused: false}};
let logFollow = true;
let refreshTimer;
const healthLabels = {good: 'STABIL', warning: 'WARNUNG', critical: 'KRITISCH', offline: 'OFFLINE'};

function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value ?? '–';
}

function setMeter(selector, value) {
  const element = $(selector);
  if (element) element.style.width = `${Math.max(0, Math.min(100, Number(value) || 0))}%`;
}

function formatPlatform(value) {
  return ({youtube: 'YouTube', twitch: 'Twitch', custom: 'RTMP'}[value] || value || '–');
}

function showToast(message, error = false) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.toggle('error', error);
  toast.classList.add('visible');
  window.setTimeout(() => toast.classList.remove('visible'), 3200);
}

function drawNetworkChart(history = []) {
  const canvas = $('#network-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 800;
  const height = canvas.clientHeight || 180;
  if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
    canvas.width = width * ratio;
    canvas.height = height * ratio;
  }
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = 'rgba(148,163,184,.18)';
  ctx.lineWidth = 1;
  for (let y = 20; y < height; y += 40) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
  }
  if (!history.length) return;
  const values = history.map(item => Number(item.upload_mbps) || 0);
  const max = Math.max(1, ...values) * 1.15;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = values.length === 1 ? width : index * width / (values.length - 1);
    const y = height - 16 - (value / max) * (height - 30);
    index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.strokeStyle = '#59a8ff';
  ctx.lineWidth = 3;
  ctx.lineJoin = 'round';
  ctx.stroke();
}

function renderLogs(lines = []) {
  const filter = ($('#log-filter')?.value || '').trim().toLowerCase();
  const visible = filter ? lines.filter(line => line.toLowerCase().includes(filter)) : lines;
  const logBox = $('#logs');
  logBox.textContent = visible.join('\n') || 'Noch keine Meldungen.';
  if (logFollow) logBox.scrollTop = logBox.scrollHeight;
}

function render(data) {
  dashboard = data;
  const stream = data.stream;
  const system = data.system;
  const network = data.network;
  const state = stream.streaming ? (stream.paused ? 'PAUSIERT' : 'LIVE') : 'OFFLINE';

  setText('#state', state);
  setText('#uptime', fmtDuration(stream.uptime));
  setText('#platform', formatPlatform(stream.platform));
  setText('#profile', `${String(stream.profile || 'custom').replaceAll('_', ' ')}${stream.auto_quality ? ' · AUTO' : ''}`);
  setText('#cpu', `${system.cpu.toFixed(1)} %`);
  setText('#ram', `${system.ram.toFixed(1)} %`);
  setText('#disk', `${system.disk.toFixed(1)} %`);
  setText('#temp', system.temperature == null ? '–' : `${system.temperature.toFixed(1)} °C`);
  setText('#temp-note', system.temperature == null ? 'Kein Sensorwert' : system.temperature >= 80 ? 'Kritisch heiß' : system.temperature >= 70 ? 'Erhöht' : 'Normal');
  setText('#upload', `${Number(network.upload_mbps || 0).toFixed(2)} Mbit/s`);
  setText('#speed', stream.ffmpeg_speed == null ? '–' : `${stream.ffmpeg_speed.toFixed(2)}×`);
  setText('#speed-note', stream.ffmpeg_speed == null ? 'Keine FFmpeg-Daten' : stream.ffmpeg_speed < .97 ? 'Unter Echtzeit' : 'Encoder stabil');
  setText('#health', healthLabels[network.health] || network.health);
  setText('#health-message', network.message || 'Keine Statusmeldung');
  setText('#resolution', stream.resolution);
  setText('#fps', stream.fps ? `${stream.fps} FPS` : '–');
  setText('#video-bitrate', stream.video_bitrate);
  setText('#audio-bitrate', stream.audio_bitrate);
  setText('#ffmpeg-pid', stream.ffmpeg_pid || '–');
  setText('#stream-errors', `${stream.reconnects || 0} / ${stream.dropped_frames || 0}`);
  setText('#hostname', system.hostname);
  setText('#system-uptime', fmtDuration(system.system_uptime));
  setText('#video-device', stream.video_device);
  setText('#audio-device', stream.audio_device);
  setText('#updated-at', new Date(data.timestamp * 1000).toLocaleTimeString('de-DE'));

  setMeter('#cpu-bar', system.cpu);
  setMeter('#ram-bar', system.ram);
  setMeter('#disk-bar', system.disk);

  $('#dot').className = `status-dot ${stream.streaming ? (stream.paused ? 'paused' : 'live') : ''}`;
  $('#health').className = `health-badge ${network.health || 'offline'}`;
  $('#api-state').classList.add('online');
  $('#api-state').textContent = 'API online';
  const pause = $('#pause-button');
  pause.disabled = !stream.streaming;
  pause.textContent = stream.paused ? '▶ Fortsetzen' : '⏸ Pause';
  drawNetworkChart(network.history || []);
  renderLogs(data.logs || []);
}

async function refresh() {
  try {
    const response = await fetch('/api/dashboard', {cache: 'no-store'});
    if (response.status === 401) { location = '/login'; return; }
    if (!response.ok) throw new Error(`API ${response.status}`);
    render(await response.json());
  } catch (error) {
    $('#api-state').classList.remove('online');
    $('#api-state').textContent = 'API getrennt';
    setText('#health-message', 'Dashboard-Daten konnten nicht geladen werden.');
  } finally {
    window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(refresh, document.hidden ? 10000 : 3000);
  }
}

async function action(name) {
  try {
    const response = await fetch(`/api/${name}`, {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Aktion fehlgeschlagen');
    showToast('Aktion wurde ausgeführt.');
    window.setTimeout(refresh, 350);
  } catch (error) {
    showToast(error.message, true);
  }
}

function togglePause() {
  return action(dashboard.stream.paused ? 'resume' : 'pause');
}

function toggleLogFollow() {
  logFollow = !logFollow;
  $('#follow-button').textContent = `Auto-Scroll ${logFollow ? 'an' : 'aus'}`;
  renderLogs(dashboard.logs || []);
}

$('#log-filter')?.addEventListener('input', () => renderLogs(dashboard.logs || []));
window.addEventListener('resize', () => drawNetworkChart(dashboard.network?.history || []));
document.addEventListener('visibilitychange', refresh);
refresh();
