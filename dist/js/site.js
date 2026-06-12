/* ============================================================
   AI 每日速递 - 站点 JavaScript
   ============================================================ */

// Archive index loader
async function loadArchiveIndex() {
  try {
    const resp = await fetch('/data/index.json');
    const data = await resp.json();
    return data.dates || [];
  } catch (e) {
    console.warn('Failed to load archive index:', e);
    return [];
  }
}

// Render archive calendar
async function renderArchiveCalendar(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const dates = await loadArchiveIndex();
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();

  // Generate all days in current month
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const dateSet = new Set(dates.map(d => d.date));

  let html = '';
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${String(month + 1).padStart(2, '0')}${String(d).padStart(2, '0')}`;
    const hasReport = dateSet.has(dateStr);
    const isToday = d === now.getDate();

    if (hasReport) {
      html += `<a href="/archive/${dateStr}.html" class="archive-day">
        <span class="date-num">${d}</span>
        <span class="date-month">${month + 1}月</span>
        <span class="date-dot" style="background:${isToday ? '#3b82f6' : '#22c55e'}"></span>
      </a>`;
    } else {
      html += `<div class="archive-day empty">
        <span class="date-num">${d}</span>
        <span class="date-month">${month + 1}月</span>
        <span class="date-dot"></span>
      </div>`;
    }
  }

  container.innerHTML = html;
}

// Archive list view
async function renderArchiveList(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const dates = await loadArchiveIndex();
  dates.sort((a, b) => b.date.localeCompare(a.date));

  if (dates.length === 0) {
    container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px">暂无历史日报归档</p>';
    return;
  }

  let html = '';
  for (const item of dates) {
    const y = item.date.substring(0, 2);
    const m = item.date.substring(2, 4);
    const d = item.date.substring(4, 6);
    html += `
      <a href="/archive/${item.date}.html" class="archive-day">
        <span class="date-num">${parseInt(d)}</span>
        <span class="date-month">${parseInt(m)}月</span>
        <span class="date-dot"></span>
      </a>`;
  }

  container.innerHTML = `<div class="archive-grid">${html}</div>`;
}

// Simple client-side search
let searchIndex = null;

async function loadSearchIndex() {
  if (searchIndex) return searchIndex;
  try {
    const resp = await fetch('/data/search-index.json');
    searchIndex = await resp.json();
    return searchIndex;
  } catch (e) {
    console.warn('Search index not available');
    return [];
  }
}

async function performSearch(query) {
  const results = document.getElementById('searchResults');
  if (!results) return;

  if (!query || query.trim().length < 2) {
    results.innerHTML = '<p style="color:var(--muted);text-align:center;padding:24px">请输入至少 2 个字符进行搜索</p>';
    return;
  }

  const idx = await loadSearchIndex();
  const q = query.toLowerCase();
  const matched = idx.filter(item =>
    item.title?.toLowerCase().includes(q) ||
    item.summary?.toLowerCase().includes(q) ||
    item.tags?.some(t => t.toLowerCase().includes(q))
  );

  if (matched.length === 0) {
    results.innerHTML = '<p style="color:var(--muted);text-align:center;padding:24px">未找到匹配结果</p>';
    return;
  }

  let html = '';
  for (const item of matched.slice(0, 30)) {
    const title = highlight(item.title || '无标题', q);
    const summary = highlight((item.summary || '').substring(0, 200), q);
    html += `
      <div class="result-item">
        <div class="result-date">${item.date} · ${item.source || 'AI速递'}</div>
        <h3><a href="${item.url || '/archive/' + item.date + '.html'}">${title}</a></h3>
        <p>${summary}</p>
      </div>`;
  }
  results.innerHTML = html;
}

function highlight(text, query) {
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return text.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
}

// Platform tabs
function initPlatformTabs() {
  const tabs = document.querySelectorAll('.platform-tab');
  const panels = document.querySelectorAll('.platform-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.target;
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      panels.forEach(p => {
        p.classList.toggle('active', p.id === target);
      });
    });
  });
}

// Scroll reveal (IntersectionObserver)
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(24px)';
    el.style.transition = 'opacity .6s cubic-bezier(.32,.72,0,1), transform .6s cubic-bezier(.32,.72,0,1)';
    observer.observe(el);
  });
}

// Active nav link
function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
      link.classList.add('active');
    }
  });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  initScrollReveal();
  initPlatformTabs();
  highlightNav();

  // Search handler
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    let timer;
    searchInput.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => performSearch(searchInput.value), 300);
    });
  }

  // Archive calendar
  if (document.getElementById('archiveCalendar')) {
    renderArchiveCalendar('archiveCalendar');
  }
  if (document.getElementById('archiveList')) {
    renderArchiveList('archiveList');
  }
});
