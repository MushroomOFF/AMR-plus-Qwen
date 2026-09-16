// ====== КОНСТАНТЫ ======
const JSON_FILE = 'new_releases.json';   // относительно страницы (лежит рядом с ней)
const MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

// ====== КОНФИГ GitHub (для работы в сети) ======
const GH = {
  owner: 'MushroomOFF',
  repo: 'AMR-plus-Qwen',
  branch: 'main',
  file: 'website/new_releases.json'   // путь внутри репозитория
};

// Не localhost → работаем через GitHub API вместо server.py
const USE_GITHUB_API = !['localhost', '127.0.0.1', ''].includes(location.hostname);

function getGenreGroup(cat) {
  if (cat === 'M' || cat === 'MCS') return 'metal';
  if (['HR', 'HRRU', 'CS'].includes(cat)) return 'alternative';
  return null;
}

const GROUP_ORDER = ['metal', 'alternative'];
const GROUP_LABELS = {
  metal: 'Metal',
  alternative: 'Alternative & Hard Rock'
};

// Порядок тегов: всегда первичная сортировка. Пустой тег — в конце.
const TYPE_ORDER = { 'v': 1, 'd': 2, 'o': 3, 'x': 4, '': 5 };

// ====== СОСТОЯНИЕ ======
let allReleases = [];
let adminLogin = null;
let adminPassword = null;
let currentYear = null;      // число или 'all'
let currentMonth = null;     // число (0-11) или 'all'
let activeTypes = new Set(); // Пустой Set = показывать все

// Настройки отображения
let groupByDate = true;      // группировка по датам
let sortMode = 'date_desc';  // 'date_desc' | 'date_asc' | 'artist_asc'

// ====== GitHub-хелперы ======
function ghHeaders() {
  return {
    'Authorization': `Bearer ${adminPassword}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };
}

function b64DecodeUtf8(b64) {
  const bin = atob(b64.replace(/\s/g, ''));
  const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function b64EncodeUtf8(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach(b => bin += String.fromCharCode(b));
  return btoa(bin);
}

// ====== УТИЛИТЫ ======
function cleanData(raw) {
  return raw.map(item => {
    const out = {};
    for (const [k, v] of Object.entries(item)) {
      const key = k.trim();
      out[key] = typeof v === 'string' ? v.trim() : v;
    }
    return out;
  });
}

function parseDate(str) {
  if (!str) return null;
  const d = new Date(str);
  return isNaN(d) ? null : d;
}

function formatDateRu(date) {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth()+1).padStart(2, '0');
  const year = date.getFullYear();
  return `${year}-${month}-${day}`;
}

function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}

// Склонение слова "релиз"
function plural(n) {
  if (n % 10 === 1 && n % 100 !== 11) return '';
  if ([2,3,4].includes(n % 10) && ![12,13,14].includes(n % 100)) return 'а';
  return 'ов';
}

// Описание выбранного периода (для пустого состояния и плоского режима)
function getPeriodLabel() {
  if (currentYear === 'all') return 'во всей базе';
  if (currentMonth === 'all') return `за ${currentYear} год`;
  return `в ${MONTHS_RU[currentMonth].toLowerCase()} ${currentYear}`;
}

function showToast(msg, type = 'info') {
  const c = document.getElementById('toastContainer');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => {
    t.style.transition = 'opacity 0.3s';
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 300);
  }, 3000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

// ====== АУТЕНТИФИКАЦИЯ (двойной режим) ======
function openLoginModal() {
  const modal = document.getElementById('loginModal');
  if (!modal) return;
  modal.classList.add('active');
  const loginInput = document.getElementById('loginInput');
  const passwordInput = document.getElementById('passwordInput');
  const errEl = document.getElementById('modalError');
  if (loginInput) loginInput.value = '';
  if (passwordInput) passwordInput.value = '';
  if (errEl) errEl.textContent = '';
  setTimeout(() => loginInput && loginInput.focus(), 100);
}

function closeLoginModal() {
  const modal = document.getElementById('loginModal');
  if (modal) modal.classList.remove('active');
}

async function submitLogin() {
  const loginInput = document.getElementById('loginInput');
  const passwordInput = document.getElementById('passwordInput');
  const errEl = document.getElementById('modalError');
  if (!loginInput || !passwordInput || !errEl) return;

  const login = loginInput.value.trim();
  const password = passwordInput.value;
  if (!login || !password) { errEl.textContent = 'Введите логин и пароль'; return; }

  try {
    if (!USE_GITHUB_API) {
      // Локально: через server.py
      const r = await fetch('/api/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({login, password})
      });
      const data = await r.json();
      if (!data.success) { errEl.textContent = data.message || 'Неверный логин или пароль'; return; }
    } else {
      // В сети: пароль = fine-grained токен GitHub
      adminPassword = password;
      const r = await fetch('https://api.github.com/user', { headers: ghHeaders() });
      if (!r.ok) { errEl.textContent = 'Неверный токен'; adminPassword = null; return; }
      const me = await r.json();
      if (login && me.login.toLowerCase() !== login.toLowerCase()) {
        errEl.textContent = 'Логин не совпадает с владельцем токена'; adminPassword = null; return;
      }
      const ri = await fetch(`https://api.github.com/repos/${GH.owner}/${GH.repo}`, { headers: ghHeaders() });
      if (ri.ok) {
        const j = await ri.json();
        if (!j.permissions || !j.permissions.push) {
          errEl.textContent = 'У токена нет права записи в репозиторий'; adminPassword = null; return;
        }
      }
    }
    adminLogin = login;
    closeLoginModal();
    updateAdminUI();
    render();
    showToast('✅ Режим редактирования активен', 'success');
  } catch (e) {
    errEl.textContent = 'Ошибка соединения';
  }
}

function logoutAdmin() {
  if (!confirm('Выйти из режима редактирования?')) return;
  adminLogin = null;
  adminPassword = null;
  updateAdminUI();
  render();
  showToast('🔒 Режим редактирования отключён', 'info');
}

function updateAdminUI() {
  const btn = document.getElementById('adminBtn');
  const badge = document.querySelector('.admin-badge');

  if (adminLogin) {
    if (btn) {
      btn.outerHTML = `<div class="admin-badge" onclick="logoutAdmin()" title="Клик — выйти">
        <span class="dot"></span><span>Редактирование</span>
      </div>`;
    }
  } else {
    if (badge) {
      badge.outerHTML = `<button class="admin-btn" id="adminBtn" onclick="openLoginModal()">🔐 Войти</button>`;
    }
  }
}

// ====== ОБНОВЛЕНИЕ MY_TYPE (двойной режим) ======
async function updateMyType(rowId, newType, btnEl) {
  if (!adminLogin || !adminPassword) { showToast('❌ Требуется вход админа', 'error'); return; }
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release) return;
  const oldType = release.my_type;
  if (oldType === newType) return;

  const allBtns = btnEl.parentElement.querySelectorAll('.type-btn');
  allBtns.forEach(b => b.classList.add('saving'));

  try {
    if (!USE_GITHUB_API) {
      const r = await fetch('/api/update_my_type', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({login: adminLogin, password: adminPassword, row_id: rowId, new_type: newType})
      });
      const data = await r.json();
      if (!data.success) throw new Error(data.message);
    } else {
      // Читаем файл из репозитория, меняем, коммитим обратно
      const url = `https://api.github.com/repos/${GH.owner}/${GH.repo}/contents/${GH.file}`;
      const get = await fetch(`${url}?ref=${GH.branch}`, { headers: ghHeaders() });
      if (!get.ok) throw new Error('Не удалось прочитать файл из GitHub');
      const meta = await get.json();
      const data = JSON.parse(b64DecodeUtf8(meta.content));

      let found = false;
      for (const r of data) {
        const rid = ('row_id' in r) ? r.row_id : r['row_id '];
        if (String(rid) === String(rowId)) {
          if ('my_type' in r) r['my_type'] = newType;
          if ('my_type ' in r) r['my_type '] = newType;
          found = true;
        }
      }
      if (!found) throw new Error('row_id не найден в JSON');

      const put = await fetch(url, {
        method: 'PUT',
        headers: { ...ghHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `releases: row_id=${rowId} my_type '${oldType || ''}' -> '${newType}'`,
          content: b64EncodeUtf8(JSON.stringify(data, null, 1) + '\n'),
          sha: meta.sha,
          branch: GH.branch
        })
      });
      if (!put.ok) {
        const e = await put.json().catch(() => ({}));
        throw new Error(e.message || 'Ошибка записи в GitHub');
      }
    }

    release.my_type = newType;
    render();
    showToast(USE_GITHUB_API
      ? `✅ Сохранено в GitHub. На сайте обновится через ~1 мин`
      : `✅ ${release.artist}: ${oldType || '∅'} → ${newType}`, 'success');
  } catch (e) {
    showToast(`❌ ${e.message}`, 'error');
    allBtns.forEach(b => b.classList.remove('saving'));
  }
}

// ====== ФИЛЬТРАЦИЯ ПО ТИПУ ======
function toggleTypeFilter(type) {
  if (activeTypes.has(type)) {
    activeTypes.delete(type);
  } else {
    activeTypes.add(type);
  }
  updateTypeFilterUI();
  applyTypeFilter();
}

function updateTypeFilterUI() {
  document.querySelectorAll('.type-filter-btn').forEach(btn => {
    const type = btn.dataset.type;
    btn.classList.toggle('active', activeTypes.has(type));
  });
}

function applyTypeFilter() {
  const cards = document.querySelectorAll('.release-card');
  cards.forEach(card => {
    const type = card.dataset.myType || 'empty';
    card.style.display = (activeTypes.size === 0 || activeTypes.has(type)) ? '' : 'none';
  });
  updateCounts();
}

function updateCounts() {
  document.querySelectorAll('.date-group').forEach(dateGroup => {
    let dateVisible = 0;
    dateGroup.querySelectorAll('.genre-section').forEach(genreSection => {
      const visibleCards = genreSection.querySelectorAll('.release-card:not([style*="display: none"])');
      const countEl = genreSection.querySelector('.genre-title .count');
      if (countEl) countEl.textContent = visibleCards.length;
      dateVisible += visibleCards.length;
      genreSection.style.display = visibleCards.length === 0 ? 'none' : '';
    });
    const dateCountEl = dateGroup.querySelector('.date-header .date-count');
    if (dateCountEl) {
      dateCountEl.textContent = `${dateVisible} релиз${plural(dateVisible)}`;
    }
    dateGroup.style.display = dateVisible === 0 ? 'none' : '';
  });
}

// ====== ПЛЕЕР ======
function openPlayerModal(rowId) {
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release) return;

  document.getElementById('playerArtist').textContent = release.artist || 'Unknown';
  document.getElementById('playerAlbum').textContent = release.album || '';

  const body = document.getElementById('playerBody');
  const albumLink = release.album_link;
  const albumId = release.album_id;

  if (!albumLink && !albumId) {
    body.innerHTML = `<div class="player-modal-no-link">
      <div class="icon">🎵</div>
      <p>Ссылка на Apple Music отсутствует</p>
    </div>`;
  } else {
    let embedUrl;
    if (albumLink) {
      embedUrl = albumLink
        .replace('music.apple.com', 'embed.music.apple.com')
        .replace(/[?#].*$/, '');
      embedUrl += '?app=music&itsct=music_box_player&itscg=30200&ls=1&theme=light';
    } else {
      embedUrl = `https://embed.music.apple.com/us/album/${albumId}?app=music&itsct=music_box_player&itscg=30200&ls=1&theme=light`;
    }
    body.innerHTML = `<iframe
      src="${embedUrl}"
      allow="autoplay *; encrypted-media *; clipboard-write"
      sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation"
      style="width: 100%; overflow: hidden; border-radius: 10px; background-color: #e4e4e4;"
    ></iframe>`;
  }

  document.getElementById('playerModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closePlayerModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('playerModal').classList.remove('active');
  document.getElementById('playerBody').innerHTML = '';
  document.body.style.overflow = '';
}

// ====== ПРОСМОТР ОБЛОЖКИ ======
function openImageModal(rowId, event) {
  if (event) event.stopPropagation();
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release || !release.cover_link) return;

  const fullUrl = release.cover_link
    .replace('296x296bb.webp', '10000x10000-999.jpg')
    .replace('296x296bf.webp', '10000x10000-999.jpg')
    .replace('296x296bf-60.jpg', '10000x10000-999.jpg');

  document.getElementById('imageModalImg').src = fullUrl;
  document.getElementById('imageModalImg').alt = release.artist || '';
  document.getElementById('imageModalArtist').textContent = release.artist || 'Unknown';
  document.getElementById('imageModalAlbum').textContent = release.album || '';
  document.getElementById('imageModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeImageModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('imageModal').classList.remove('active');
  document.getElementById('imageModalImg').src = '';
  document.body.style.overflow = '';
}

// ====== ФИЛЬТРАЦИЯ И СОРТИРОВКА ======
function getFilteredReleases() {
  return allReleases.filter(r => {
    const d = parseDate(r.update_date);
    if (!d) return false;
    if (currentYear === 'all') return true;          // Вся БД
    if (d.getFullYear() !== currentYear) return false;
    if (currentMonth === 'all') return true;         // Весь год
    return d.getMonth() === currentMonth;
  });
}

// Сортировка: тег — всегда первичный ключ; выбранный режим — вторичный
function sortReleases(list) {
  const sorted = [...list];
  sorted.sort((a, b) => {
    const ta = TYPE_ORDER[a.my_type || ''] ?? 5;
    const tb = TYPE_ORDER[b.my_type || ''] ?? 5;
    if (ta !== tb) return ta - tb;

    if (sortMode === 'artist_asc') {
      return (a.artist || '').localeCompare(b.artist || '', 'ru');
    }
    const da = parseDate(a.update_date) || new Date(0);
    const db = parseDate(b.update_date) || new Date(0);
    if (sortMode === 'date_asc') return da - db;
    return db - da; // date_desc
  });
  return sorted;
}

// ====== РЕНДЕРИНГ ======
function buildYearMonthOptions() {
  const years = new Set();
  const yearMonths = {};

  allReleases.forEach(r => {
    const d = parseDate(r.update_date);
    if (!d) return;
    const y = d.getFullYear();
    const m = d.getMonth();
    years.add(y);
    if (!yearMonths[y]) yearMonths[y] = new Set();
    yearMonths[y].add(m);
  });

  const yearsSorted = [...years].sort((a, b) => b - a);
  const yearSel = document.getElementById('yearSelect');
  const monthSel = document.getElementById('monthSelect');

  // Годы + «Вся БД» последним пунктом
  yearSel.innerHTML = yearsSorted.map(y => `<option value="${y}">${y}</option>`).join('')
    + `<option value="all">Вся БД</option>`;

  function updateMonths() {
    if (yearSel.value === 'all') {
      // Вся БД — выбор месяца недоступен
      monthSel.disabled = true;
      monthSel.innerHTML = `<option>Вся БД</option>`;
      return;
    }
    monthSel.disabled = false;
    const yi = parseInt(yearSel.value);
    const months = yearMonths[yi] ? [...yearMonths[yi]].sort((a, b) => b - a) : [];
    // Месяцы + «Весь год» последним пунктом
    monthSel.innerHTML = months.map(m => `<option value="${m}">${MONTHS_RU[m]}</option>`).join('')
      + `<option value="all">Весь год</option>`;
  }

  yearSel.addEventListener('change', () => {
    updateMonths();
    currentYear = yearSel.value === 'all' ? 'all' : parseInt(yearSel.value);
    currentMonth = monthSel.value === 'all' ? 'all' : parseInt(monthSel.value);
    render();
  });

  monthSel.addEventListener('change', () => {
    currentMonth = monthSel.value === 'all' ? 'all' : parseInt(monthSel.value);
    render();
  });

  if (yearsSorted.length) {
    currentYear = yearsSorted[0];
    yearSel.value = String(currentYear);
    updateMonths();
    currentMonth = parseInt(monthSel.value);
  }
}

function render() {
  const main = document.getElementById('mainContent');
  const releases = sortReleases(getFilteredReleases());

  if (!releases.length) {
    main.innerHTML = `<div class="empty-state">
      <div class="icon">📭</div>
      <h3>Нет релизов</h3>
      <p>Релизы ${getPeriodLabel()} не найдены.</p>
    </div>`;
    return;
  }

  if (groupByDate) {
    renderGroupedByDate(main, releases);
  } else {
    renderFlat(main, releases);
  }

  // Сохраняем состояние фильтров по тегам после перерисовки
  if (activeTypes.size > 0) applyTypeFilter();
}

// Группировка по датам
function renderGroupedByDate(main, releases) {
  const byDate = {};
  releases.forEach(r => {
    const d = parseDate(r.update_date);
    const key = dateKey(d);
    if (!byDate[key]) byDate[key] = {date: d, items: []};
    byDate[key].items.push(r);
  });

  let datesSorted = Object.values(byDate);
  if (sortMode === 'date_asc') {
    datesSorted.sort((a, b) => a.date - b.date);
  } else {
    datesSorted.sort((a, b) => b.date - a.date);
  }

  let html = '';
  datesSorted.forEach(({date, items}) => {
    html += `<div class="date-group">
      <h2 class="date-header">
        <span class="date-text">${formatDateRu(date)}</span>
        <span class="date-count">${items.length} релиз${plural(items.length)}</span>
      </h2>`;
    html += renderGenreSections(items);
    html += `</div>`;
  });

  main.innerHTML = html;
}

// Жанровые секции внутри даты
function renderGenreSections(items) {
  const byGenre = {};
  items.forEach(r => {
    const g = getGenreGroup(r.genre_category);
    if (g) {
      if (!byGenre[g]) byGenre[g] = [];
      byGenre[g].push(r);
    }
  });

  let html = '';
  GROUP_ORDER.forEach(groupKey => {
    const genreItems = byGenre[groupKey];
    if (!genreItems || !genreItems.length) return;
    html += `<section class="genre-section" data-genre="${groupKey}">
      <h3 class="genre-title">${GROUP_LABELS[groupKey]} <span class="count">${genreItems.length}</span></h3>
      <div class="releases-grid">`;
    genreItems.forEach(r => { html += renderCard(r); });
    html += `</div></section>`;
  });
  return html;
}

// Плоский список без дат и жанров (группировка выключена)
function renderFlat(main, releases) {
  let html = `<div class="flat-summary">Найдено: ${releases.length} релиз${plural(releases.length)} ${getPeriodLabel()}</div>`;
  html += `<div class="releases-grid">`;
  releases.forEach(r => { html += renderCard(r); });
  html += `</div>`;
  main.innerHTML = html;
}

function renderCard(r) {
  const name = escapeHtml(r.artist || 'Unknown');
  const album = escapeHtml(r.album || '');
  const cover = r.cover_link || '';

  const coverDisplay = cover
    .replace('296x296bb.webp', '632x632bb.webp')
    .replace('296x296bf.webp', '632x632bf.webp')
    .replace('296x296bf-60.jpg', '632x632bf-60.jpg');

  const currentType = r.my_type || '';
  const rowId = r.row_id;
  const myTypeAttr = currentType || 'empty';

  const TYPE_EMOJI = { 'v': '🔥', 'o': '👌', 'd': '🔍', 'x': '✖️' };

  const linkApple = r.album_link
    ? `<a class="link-btn am-active" href="${r.album_link}" target="_blank" rel="noopener" title="Apple Music" onclick="event.stopPropagation()">🎵</a>`
    : `<span class="link-btn disabled">🎵</span>`;

  const linkYM = r.album_link_ym
    ? `<a class="link-btn ym-active" href="${r.album_link_ym}" target="_blank" rel="noopener" title="Яндекс.Музыка" onclick="event.stopPropagation()">💥</a>`
    : `<span class="link-btn disabled">💥</span>`;

  const linkZV = r.album_link_zv
    ? `<a class="link-btn zv-active" href="${r.album_link_zv}" target="_blank" rel="noopener" title="Звук" onclick="event.stopPropagation()">🔊</a>`
    : `<span class="link-btn disabled">🔊</span>`;

  // Кнопки типов рендерятся ТОЛЬКО в режиме администратора
  let typeBtnsHtml = '';
  if (adminLogin && adminPassword) {
    const types = ['v', 'o', 'd', 'x'];
    const typeBtns = types.map(t => {
      const active = currentType === t ? 'active' : '';
      const emoji = TYPE_EMOJI[t];
      return `<button class="type-btn ${active}" data-type="${t}"
                  onclick="event.stopPropagation(); updateMyType(${rowId}, '${t}', this)"
                  title="Установить тип '${t}'">${emoji}</button>`;
    }).join('');
    typeBtnsHtml = `<div class="type-buttons">${typeBtns}</div>`;
  }

  const imageIndicator = cover ? `<div class="image-indicator" onclick="openImageModal(${rowId}, event)" title="Открыть обложку">
    <svg viewBox="0 0 24 24">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
      <circle cx="8.5" cy="8.5" r="1.5"/>
      <polyline points="21 15 16 10 5 21"/>
    </svg>
  </div>` : '';

  return `<div class="release-card" data-row-id="${rowId}" data-my-type="${myTypeAttr}" onclick="openPlayerModal(${rowId})">
    <div class="cover-wrap">
      ${coverDisplay ? `<img src="${coverDisplay}" alt="${name}" loading="lazy" onerror="this.style.display='none'">` : ''}
      ${imageIndicator}
    </div>
    <div class="card-info">
      <div class="artist-name">${name}</div>
      <div class="album-name">${album}</div>
      <div class="links-row">${linkApple}${linkYM}${linkZV}</div>
      ${typeBtnsHtml}
    </div>
  </div>`;
}

// ====== ЗАГРУЗКА ДАННЫХ ======
async function loadData() {
  try {
    const r = await fetch(JSON_FILE + '?v=' + Date.now());
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const raw = await r.json();
    allReleases = cleanData(raw);

    const statusArea = document.getElementById('statusArea');
    if (statusArea) statusArea.style.display = 'none';

    buildYearMonthOptions();
    render();
  } catch (e) {
    console.error('❌ Ошибка загрузки:', e);
    document.getElementById('mainContent').innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>${e.message}</p>
        <p style="margin-top:10px">
          Локально: запустите <code>python server.py</code> из корня проекта и откройте
          <code>http://localhost:8000/releases.html</code>.<br>
          В сети: проверьте, что страница открыта по адресу
          <code>https://${GH.owner}.github.io/${GH.repo}/releases.html</code>
        </p>
      </div>`;
  }
}

// ====== СОБЫТИЯ ======
document.addEventListener('DOMContentLoaded', () => {
  const passwordInput = document.getElementById('passwordInput');
  if (passwordInput) {
    passwordInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') submitLogin();
    });
  }

  const typeFilters = document.getElementById('typeFilters');
  if (typeFilters) {
    typeFilters.addEventListener('click', e => {
      const btn = e.target.closest('.type-filter-btn');
      if (!btn) return;
      toggleTypeFilter(btn.dataset.type);
    });
  }

  // Группировка по датам
  const groupToggle = document.getElementById('groupByDateToggle');
  if (groupToggle) {
    groupToggle.addEventListener('change', e => {
      groupByDate = e.target.checked;
      render();
    });
  }

  // Режим сортировки
  const sortSelect = document.getElementById('sortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', e => {
      sortMode = e.target.value;
      render();
    });
  }

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeLoginModal();
      closePlayerModal();
      closeImageModal();
    }
  });

  loadData();
});