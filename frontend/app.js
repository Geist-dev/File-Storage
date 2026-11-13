'use strict';

const $ = (selector) => document.querySelector(selector);
let token = sessionStorage.getItem('fileStorageToken') || '';
let page = 1;
const pageSize = 10;
const tags = new Set();
let thumbUrls = [];
let previewUrl = '';
let listRequest = 0;
let authGeneration = 0;

function show(selector, visible) {
  $(selector).classList.toggle('hidden', !visible);
}
function toast(message, type = 'success') {
  const element = $('#toast');
  element.textContent = message;
  element.className = `toast ${type}`;
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => element.classList.add('hidden'), 4000);
}
function humanSize(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
}
async function request(path, options = {}, binary = false) {
  const requestToken = token;
  const headers = new Headers(options.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let message = `Ошибка запроса (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : 'Проверьте введённые данные';
    } catch { /* Non-JSON errors keep the status message. */ }
    const translations = {
      'Invalid credentials': 'Неверный email или пароль',
      'Email already registered': 'Этот email уже зарегистрирован. Войдите в аккаунт.',
      'File too large': 'Файл превышает допустимый размер',
      'Invalid token': 'Сессия истекла. Войдите снова.',
      'User not found': 'Войдите в аккаунт снова',
    };
    if (response.status === 401 && token === requestToken) setToken('');
    throw new Error(translations[message] || message);
  }
  return binary ? response.blob() : response.json();
}
function releaseThumbnails() {
  thumbUrls.forEach((url) => URL.revokeObjectURL(url));
  thumbUrls = [];
}
function closePreview() {
  $('#previewDialog').close();
  $('#previewImage').removeAttribute('src');
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = '';
}
function setToken(value) {
  token = value;
  authGeneration += 1;
  listRequest += 1;
  if (value) sessionStorage.setItem('fileStorageToken', value);
  else sessionStorage.removeItem('fileStorageToken');
  // Remove credentials saved by older versions of the app.
  localStorage.removeItem('token');
  show('#auth', !value);
  show('#workspace', Boolean(value));
  show('#logout', Boolean(value));
  if (!value) {
    releaseThumbnails();
    closePreview();
    $('#filesTable tbody').replaceChildren();
    $('#me').textContent = 'Локальное хранилище';
    $('#password').value = '';
    $('#file').value = '';
    $('#folder').value = '';
    $('#search').value = '';
    $('#tagFilter').value = '';
    $('#stateFilter').value = 'active';
    tags.clear();
    renderTags();
    updateSelection();
    page = 1;
  }
}
async function authenticate(register = false) {
  const form = $('#authForm');
  if (!form.reportValidity()) return;
  const password = $('#password').value;
  if (register && (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password) || new TextEncoder().encode(password).length > 72)) {
    toast('Пароль: от 8 символов, латинская буква и цифра; не более 72 байт UTF-8.', 'error');
    return;
  }
  $('#login').disabled = $('#register').disabled = true;
  try {
    const result = await request(`/auth/${register ? 'register' : 'login'}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: $('#email').value.trim(), password }),
    });
    setToken(result.token);
    $('#password').value = '';
    page = 1;
    await loadAccount();
    await reload();
    toast(register ? 'Аккаунт создан' : 'Вы вошли в хранилище');
  } catch (error) { toast(error.message, 'error'); }
  finally { $('#login').disabled = $('#register').disabled = false; }
}
async function loadAccount() {
  const generation = authGeneration;
  const user = await request('/me');
  if (generation === authGeneration) $('#me').textContent = user.email;
}
function renderTags() {
  $('#tagsChips').replaceChildren();
  for (const tag of tags) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    const label = document.createElement('span');
    label.textContent = tag;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = '×';
    remove.setAttribute('aria-label', `Удалить тег ${tag}`);
    remove.addEventListener('click', () => { tags.delete(tag); renderTags(); });
    chip.append(label, remove);
    $('#tagsChips').append(chip);
  }
}
function updateSelection() {
  const files = [...$('#file').files];
  $('#selectedFiles').textContent = files.length
    ? `Выбрано: ${files.length} · ${files.map((file) => file.name).join(', ')}`
    : 'Документы и изображения';
  $('#uploadBtn').disabled = !files.length;
}
async function upload() {
  const files = [...$('#file').files];
  if (!files.length) return;
  $('#uploadBtn').disabled = true;
  $('#uploadBtn').textContent = 'Загрузка…';
  let uploaded = 0;
  try {
    for (const file of files) {
      const body = new FormData();
      body.append('file', file);
      body.append('folder', $('#folder').value.trim());
      body.append('tags', JSON.stringify([...tags]));
      await request('/files/upload', { method: 'POST', body });
      uploaded += 1;
    }
    toast(`Загружено файлов: ${uploaded}`);
  } catch (error) {
    toast(`Загружено ${uploaded} из ${files.length}. ${error.message}`, 'error');
  } finally {
    $('#file').value = '';
    $('#uploadBtn').textContent = 'Загрузить файлы ↑';
    updateSelection();
    if (token) { page = 1; await reload(); }
  }
}
function action(label, handler, className = 'secondary') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.textContent = label;
  button.addEventListener('click', async () => {
    button.disabled = true;
    try { await handler(); }
    catch (error) { toast(error.message, 'error'); }
    finally { button.disabled = false; }
  });
  return button;
}
async function loadThumbnail(item, image, revision) {
  try {
    const blob = await request(`/files/${item.id}/thumb`, {}, true);
    if (revision !== listRequest) return;
    const url = URL.createObjectURL(blob);
    thumbUrls.push(url);
    image.src = url;
  } catch { image.remove(); }
}
function fileRow(item, revision) {
  const row = document.createElement('tr');
  const nameCell = document.createElement('td');
  const info = document.createElement('div');
  info.className = 'file-info';
  if (item.thumb_available) {
    const image = document.createElement('img');
    image.className = 'thumb';
    image.alt = '';
    info.append(image);
    loadThumbnail(item, image, revision);
  } else {
    const icon = document.createElement('span');
    icon.className = 'file-symbol';
    icon.textContent = item.name.split('.').pop().slice(0, 4).toUpperCase();
    info.append(icon);
  }
  const details = document.createElement('div');
  const title = document.createElement('div');
  title.className = 'file-title';
  title.textContent = item.name;
  title.title = item.name;
  const meta = document.createElement('div');
  meta.className = 'file-meta';
  meta.textContent = [item.path || 'Без папки', ...item.tags.map((tag) => `#${tag}`)].join(' · ');
  details.append(title, meta);
  info.append(details);
  nameCell.append(info);
  const size = document.createElement('td');
  size.textContent = humanSize(item.size);
  const status = document.createElement('td');
  const badge = document.createElement('span');
  badge.className = `status-badge${item.state === 'deleted' ? ' deleted' : ''}`;
  badge.textContent = item.state === 'deleted' ? 'В корзине' : 'Приватный';
  status.append(badge);
  const buttons = document.createElement('td');
  buttons.className = 'file-actions';
  if (item.state === 'deleted') {
    buttons.append(action('Восстановить', async () => {
      await request(`/files/${item.id}/restore`, { method: 'POST' });
      await reload();
      toast('Файл восстановлен');
    }));
  } else {
    if (item.mime.startsWith('image/')) buttons.append(action('Просмотр', async () => {
      const blob = await request(`/files/${item.id}/preview`, {}, true);
      closePreview();
      previewUrl = URL.createObjectURL(blob);
      $('#previewImage').src = previewUrl;
      $('#previewImage').alt = item.name;
      $('#previewTitle').textContent = item.name;
      $('#previewDialog').showModal();
    }));
    buttons.append(action('Скачать', async () => {
      const blob = await request(`/files/${item.id}/download`, {}, true);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = item.name;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }));
    buttons.append(action('Удалить', async () => {
      await request(`/files/${item.id}`, { method: 'DELETE' });
      await reload();
      toast('Файл перемещён в корзину');
    }, 'delete-button'));
  }
  row.append(nameCell, size, status, buttons);
  return row;
}
async function reload() {
  const revision = ++listRequest;
  const params = new URLSearchParams({
    q: $('#search').value.trim(), tag: $('#tagFilter').value.trim(),
    state: $('#stateFilter').value, page: String(page), page_size: String(pageSize),
  });
  try {
    const data = await request(`/files?${params}`);
    if (revision !== listRequest) return;
    const pages = Math.max(1, Math.ceil(data.total / pageSize));
    if (page > pages) { page = pages; return reload(); }
    releaseThumbnails();
    $('#filesTable tbody').replaceChildren(...data.items.map((item) => fileRow(item, revision)));
    $('#fileCount').textContent = data.total;
    $('#pageInfo').textContent = `Страница ${page} из ${pages} · Файлов: ${data.total}`;
    $('#prevPage').disabled = page <= 1;
    $('#nextPage').disabled = page >= pages;
    show('#emptyState', !data.items.length);
  } catch (error) { if (revision === listRequest || !token) toast(error.message, 'error'); }
}
async function init() {
  $('#authForm').addEventListener('submit', (event) => { event.preventDefault(); authenticate(); });
  $('#register').addEventListener('click', () => authenticate(true));
  $('#logout').addEventListener('click', () => { setToken(''); toast('Вы вышли из аккаунта', 'info'); });
  $('#file').addEventListener('change', updateSelection);
  $('#dropzone').addEventListener('click', () => $('#file').click());
  for (const event of ['dragenter', 'dragover']) $('#dropzone').addEventListener(event, (ev) => {
    ev.preventDefault(); $('#dropzone').classList.add('dragover');
  });
  for (const event of ['dragleave', 'drop']) $('#dropzone').addEventListener(event, (ev) => {
    ev.preventDefault(); $('#dropzone').classList.remove('dragover');
  });
  $('#dropzone').addEventListener('drop', (event) => {
    $('#file').files = event.dataTransfer.files;
    updateSelection();
  });
  $('#tagInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      const value = event.target.value.trim();
      if (value) { tags.add(value); renderTags(); }
      event.target.value = '';
    }
  });
  $('#uploadBtn').addEventListener('click', upload);
  $('#filterForm').addEventListener('submit', (event) => { event.preventDefault(); page = 1; reload(); });
  $('#stateFilter').addEventListener('change', () => { page = 1; reload(); });
  $('#reload').addEventListener('click', reload);
  $('#prevPage').addEventListener('click', () => { if (page > 1) { page -= 1; reload(); } });
  $('#nextPage').addEventListener('click', () => { page += 1; reload(); });
  $('#closePreview').addEventListener('click', closePreview);
  $('#previewDialog').addEventListener('cancel', (event) => { event.preventDefault(); closePreview(); });
  updateSelection();
  setToken(token);
  try {
    const config = await request('/api/config');
    $('#uploadLimit').textContent = `До ${config.max_upload_mb} MB на файл`;
  } catch { $('#uploadLimit').textContent = 'Лимит задаётся на сервере'; }
  if (token) {
    try { await loadAccount(); await reload(); }
    catch (error) { toast(error.message, 'error'); }
  }
}
document.addEventListener('DOMContentLoaded', init);
