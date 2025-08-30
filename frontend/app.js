// --- Helpers ---
const API = 'http://127.0.0.1:8000';
let token = localStorage.getItem('token') || '';
const $ = (s) => document.querySelector(s);
const on = (el, ev, fn) => el && el.addEventListener(ev, fn);
// Глобально, чтобы точно было видно везде
window.humanSize = function (bytes) {
  if (bytes === 0) return '0 B';
  if (!bytes && bytes !== 0) return '';
  const units = ['B','KB','MB','GB','TB'];
  const i = Math.max(0, Math.floor(Math.log(bytes) / Math.log(1024)));
  const num = bytes / Math.pow(1024, i);
  return num.toFixed(1) + ' ' + units[i];
};


function show(sel, onState=true){
  const el = $(sel);
  if(!el) return;
  el.classList[onState ? 'remove' : 'add']('hidden');
}

function showToast(msg, type='info', ms=3500){
  const t = $('#toast'); if(!t) return;
  t.className = `toast ${type}`;
function humanSize(bytes) {
  if (bytes === 0) return '0 B';
  if (!bytes && bytes !== 0) return '';
  const units = ['B','KB','MB','GB','TB'];
  const i = Math.max(0, Math.floor(Math.log(bytes) / Math.log(1024)));
  const num = bytes / Math.pow(1024, i);
  return num.toFixed(1) + ' ' + units[i];
}

  t.textContent = String(msg ?? '');
  t.classList.remove('hidden');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(()=> t.classList.add('hidden'), ms);
}

async function req(path, opts = {}){
  const headers = opts.headers ? {...opts.headers} : {};
  if(token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API + path, {...opts, headers});
  const ct = res.headers.get('content-type') || '';
  let body = null;
  try {
    body = ct.includes('application/json') ? await res.json() : await res.text();
  } catch { body = null; }
  if(!res.ok){
    const detail = body && typeof body === 'object' ? (body.detail || JSON.stringify(body)) : (body || res.statusText);
    const err = new Error(typeof detail === 'string' ? detail : String(detail));
    err.status = res.status;
    throw err;
  }
  return body;
}

function setToken(t){
  token = t || '';
  if(t) localStorage.setItem('token', t); else localStorage.removeItem('token');
  const authed = Boolean(t);
  show('#upload', authed);
  show('#list', authed);
}

// --- Auth ---
async function registerHandler(){
  const email = $('#email')?.value.trim();
  const password = $('#password')?.value ?? '';

  // Client password rules
  const errs = [];
  if(password.length < 8) errs.push('Пароль должен быть не короче 8 символов');
  if(!/[A-Za-z]/.test(password)) errs.push('Пароль должен содержать буквы');
  if(!/[0-9]/.test(password)) errs.push('Пароль должен содержать цифры');
  if(errs.length){ showToast(errs[0], 'error'); return; }

  try{
    const data = await req('/auth/register', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, password})
    });
    const tkn = data?.token;
    if(!tkn) throw new Error('Не удалось получить токен');
    setToken(tkn);
    await me();
    await reload();
    showToast('Регистрация успешна', 'success');
  }catch(e){
    const msg = String(e?.message || e);
    if(/already/i.test(msg) || /зарегистр/i.test(msg)){
      localStorage.setItem('blockedEmail', email || '');
      $('#email')?.classList.add('error');
      $('#register') && ($('#register').disabled = true);
      showToast('Этот email уже зарегистрирован. Введите другой.', 'error');
    }else{
      showToast(msg, 'error');
    }
  }
}

async function loginHandler(){
  const email = $('#email')?.value.trim();
  const password = $('#password')?.value ?? '';
  try{
    const data = await req('/auth/login', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, password})
    });
    const tkn = data?.token;
    if(!tkn) throw new Error('Не удалось получить токен');
    setToken(tkn);
    await me();
    await reload();
    showToast('Вход выполнен', 'success');
  }catch(e){
    showToast(String(e?.message || e), 'error');
  }
}

function logoutHandler(){
  setToken('');
  $('#me') && ($('#me').textContent = 'Не авторизован');
  showToast('Вы вышли из аккаунта', 'info');
}

// --- Tags (chips) ---
const tags = new Set();
function renderChips(){
  const box = $('#tagsChips'); if(!box) return;
  box.innerHTML = '';
  for(const t of tags){
    const div = document.createElement('div');
    div.className = 'chip';
    div.innerHTML = `<span>${t}</span><button title="удалить" data-t="${t}">×</button>`;
    on(div.querySelector('button'), 'click', () => { tags.delete(t); renderChips(); });
    box.appendChild(div);
  }
}

// --- Upload ---
async function handleUpload(fileList){
  if(!fileList || fileList.length === 0) return;
  const folder = $('#folder')?.value.trim() || '';
  const bodyTags = JSON.stringify([...tags]);
  for(const f of fileList){
    const fd = new FormData();
    fd.append('file', f);
    if(bodyTags) fd.append('tags', bodyTags);
    if(folder) fd.append('folder', folder);
    try{
      await req('/files/upload', { method:'POST', body: fd });
    }catch(e){
      showToast(String(e?.message || e), 'error');
      return;
    }
  }
  await reload();
}

async function uploadClick(){ await handleUpload($('#file')?.files); if($('#file')) $('#file').value = ''; }

async function loadThumb(it, imgEl){
  try {
    const res = await fetch(`${API}/files/${it.id}/thumb`, {
      headers: token ? {'Authorization':'Bearer '+token} : {}
    });
    if(!res.ok) throw new Error('thumb error ' + res.status);
    const blob = await res.blob();
    imgEl.src = URL.createObjectURL(blob);
  } catch(e) {
    imgEl.style.display = 'none';
  }
}

// --- List ---
async function reload(){
  try{
    const q = $('#search')?.value.trim() || '';
    const tag = $('#tagFilter')?.value.trim() || '';
    const state = $('#stateFilter')?.value || 'active';
    const params = new URLSearchParams();
    if(q) params.set('q', q);
    if(tag) params.set('tag', tag);
    if(state) params.set('state', state);

    const data = await req('/files?' + params.toString());
    const tbody = document.querySelector('#filesTable tbody');
    if(!tbody) return;
    tbody.innerHTML = '';

    for(const it of data.items){
      const tr = document.createElement('tr');

      const nameTd = document.createElement('td');
      const thumb = document.createElement('img');
      thumb.className = 'thumb'; if(it.thumb_available){ loadThumb(it, thumb); } else { thumb.style.display = 'none'; }
      const nameSpan = document.createElement('span'); nameSpan.textContent = it.name + ' ';
      const pathSpan = document.createElement('span'); pathSpan.className='path'; pathSpan.textContent = it.path ? `(${it.path})` : '';
      nameTd.appendChild(thumb); nameTd.appendChild(nameSpan); nameTd.appendChild(pathSpan);

      const sizeTd = document.createElement('td'); sizeTd.textContent = window.humanSize(it.size);
      const pubTd  = document.createElement('td'); pubTd.innerHTML = `<span class="status-badge">приватный</span>`;
      const actionsTd = document.createElement('td');

      const stateVal = ($('#stateFilter')?.value || 'active');
      if(stateVal !== 'deleted'){
        const prev = document.createElement('button');
        prev.textContent='Просмотр';
        on(prev, 'click', async ()=>{
          try{
            const res = await fetch(`${API}/files/${it.id}/preview`, { headers: token? {'Authorization':'Bearer '+token} : {} });
            if(!res.ok){
              if(res.status === 401){ showToast('Сессия истекла или нет входа. Войдите снова.', 'error'); setToken(''); return; }
              if(res.status === 403){ showToast('Нет доступа к файлу (только владелец).', 'error'); return; }
              if(res.status === 415){ showToast('Предпросмотр недоступен для этого типа файла.', 'info'); return; }
              showToast('Ошибка предпросмотра: '+res.statusText, 'error'); return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const w = window.open(url, '_blank');
            if(!w){ showToast('Разрешите всплывающие окна для предпросмотра', 'info'); }
            setTimeout(()=> URL.revokeObjectURL(url), 30000);
          }catch(err){ showToast(String(err?.message || err), 'error'); }
        });
        actionsTd.appendChild(prev);

        const dl = document.createElement('button');
        dl.textContent='Скачать';
        on(dl, 'click', async ()=>{
          try{
            const blob = await req(`/files/${it.id}/download`);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href=url; a.download=it.name; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
          }catch(err){ showToast(String(err?.message || err), 'error'); }
        });
        actionsTd.appendChild(dl);

        const del = document.createElement('button');
        del.textContent='Удалить';
        on(del, 'click', async ()=>{
          try{ await req(`/files/${it.id}`, { method:'DELETE' }); await reload(); }
          catch(err){ showToast(String(err?.message || err), 'error'); }
        });
        actionsTd.appendChild(del);
      } else {
        const restore = document.createElement('button');
        restore.textContent='Восстановить';
        on(restore, 'click', async ()=>{
          try{ await req(`/files/${it.id}/restore`, { method:'POST' }); await reload(); }
          catch(err){ showToast(String(err?.message || err), 'error'); }
        });
        actionsTd.appendChild(restore);
      }

      tr.appendChild(nameTd);
      tr.appendChild(sizeTd);
      tr.appendChild(pubTd);
      tr.appendChild(actionsTd);
      tbody.appendChild(tr);
    }
  }catch(e){
    if(e.status === 401){ showToast('Сначала войдите в аккаунт', 'error'); setToken(''); }
    else showToast(String(e?.message || e), 'error');
  }
}

async function me(){
  try{
    const data = await req('/me');
    $('#me') && ($('#me').textContent = `Вы вошли: ${data.email}`);
  }catch{
    $('#me') && ($('#me').textContent = 'Не авторизован');
  }
}

// --- Init ---
function init(){
  // Wire buttons
  on($('#register'), 'click', registerHandler);
  on($('#login'), 'click',    loginHandler);
  on($('#logout'), 'click',   logoutHandler);
  on($('#uploadBtn'), 'click', uploadClick);
  on($('#reload'), 'click', reload);
  on($('#stateFilter'), 'change', reload);

  // Email duplicate UX
  on($('#email'), 'input', (e)=>{
    const blocked = localStorage.getItem('blockedEmail');
    if(blocked && e.target.value.trim() === blocked){
      $('#register') && ($('#register').disabled = true);
    }else{
      $('#register') && ($('#register').disabled = false);
      $('#email')?.classList.remove('error');
    }
  });

  // Tag chips input
  on($('#tagInput'), 'keydown', (e)=>{
    if(e.key === 'Enter' || e.key === ','){
      e.preventDefault();
      const v = e.target.value.trim();
      if(v){ tags.add(v); renderChips(); e.target.value=''; }
    }
  });

  // Drag & drop
  const dz = $('#dropzone');
  if(dz){
    ['dragenter','dragover'].forEach(ev => on(dz, ev, (e)=>{ e.preventDefault(); dz.classList.add('dragover'); }));
    ['dragleave','drop'].forEach(ev => on(dz, ev, (e)=>{ e.preventDefault(); dz.classList.remove('dragover'); }));
    on(dz, 'drop', async (e)=>{
      await handleUpload(e.dataTransfer.files);
    });
    on(dz, 'click', ()=> $('#file')?.click());
  }

  // Initial state
  setToken(token);
  me();
  if(token) reload();

  // Global JS errors to toast
  window.addEventListener('error', (ev)=> showToast(ev.message || 'JS error', 'error'));
  window.addEventListener('unhandledrejection', (ev)=> showToast(String(ev.reason?.message || ev.reason || 'Promise rejection'), 'error'));
}

document.addEventListener('DOMContentLoaded', init);
console.log('App JS loaded');
