'use strict';

const TAG_LABELS = {
  shorts: 'Shorts',
  release: 'إصدارات جديدة',
  dart: 'Dart',
  ai: 'AI',
  widget: 'Widgets',
  observable: 'Observable Flutter',
  tutorial: 'شروحات',
  event: 'مؤتمرات وفعاليات',
  community: 'المجتمع',
  performance: 'الأداء',
  web: 'Flutter Web',
  games: 'ألعاب',
};

const WEEK_START_DAY = 6; // Saturday

const dateFmt = new Intl.DateTimeFormat('ar-EG', { day: 'numeric', month: 'long', year: 'numeric' });
const shortDateFmt = new Intl.DateTimeFormat('ar-EG', { day: 'numeric', month: 'long' });
const numberFmt = new Intl.NumberFormat('ar-EG', { notation: 'compact' });

const state = { videos: [], weeks: {}, weekStart: null, tag: 'all', query: '' };

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const child of [].concat(children)) {
    if (child != null) node.append(child);
  }
  return node;
}

// Local-time Saturday 00:00 of the week containing `date`.
function startOfWeek(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const diff = (d.getDay() - WEEK_START_DAY + 7) % 7;
  d.setDate(d.getDate() - diff);
  return d;
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function videosInWeek(weekStart) {
  const end = addDays(weekStart, 7);
  return state.videos.filter((v) => v.date >= weekStart && v.date < end);
}

function renderWeek() {
  const start = state.weekStart;
  const end = addDays(start, 6);
  const videos = videosInWeek(start);
  const currentWeek = startOfWeek(new Date());
  const oldest = state.videos.length ? startOfWeek(state.videos[state.videos.length - 1].date) : currentWeek;

  $('week-title').textContent = start.getTime() === currentWeek.getTime() ? 'ملخص الأسبوع ده' : 'ملخص الأسبوع';
  $('week-range').textContent = `من ${shortDateFmt.format(start)} لحد ${dateFmt.format(end)}`;
  $('prev-week').disabled = start <= oldest;
  $('next-week').disabled = start >= currentWeek;

  const stats = $('week-stats');
  const list = $('week-list');
  stats.replaceChildren();
  list.replaceChildren();
  $('week-digest').replaceChildren();

  if (!videos.length) {
    list.append(el('li', { className: 'week-empty muted', textContent: 'مفيش فيديوهات جديدة في الأسبوع ده لسه.' }));
    return;
  }

  const shorts = videos.filter((v) => v.isShort).length;
  const views = videos.reduce((sum, v) => sum + v.views, 0);
  stats.append(el('span', { className: 'stat', textContent: `${videos.length} فيديو` }));
  if (shorts) stats.append(el('span', { className: 'stat', textContent: `منهم ${shorts} Shorts` }));
  stats.append(el('span', { className: 'stat', textContent: `${numberFmt.format(views)} مشاهدة` }));

  const tagCounts = {};
  for (const v of videos) {
    for (const t of v.tags) if (t !== 'shorts') tagCounts[t] = (tagCounts[t] || 0) + 1;
  }
  const topTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 3);
  if (topTags.length) {
    const names = topTags.map(([t]) => TAG_LABELS[t] || t).join('، ');
    stats.append(el('span', { className: 'stat', textContent: `أكتر مواضيع: ${names}` }));
  }

  const week = state.weeks[dateKey(start)];
  if (week) {
    $('week-digest').append(
      el('p', { className: 'digest-text', textContent: week.digest }),
      el('ul', { className: 'highlights' }, week.highlights.map((h) => el('li', { textContent: h }))),
    );
  }

  for (const v of [...videos].reverse()) {
    const firstSentence = (v.summary.match(/^.*?[.!?](\s|$)/) || [v.summary])[0];
    list.append(el('li', {}, [
      el('a', { href: v.url, target: '_blank', rel: 'noopener', dir: 'auto', textContent: v.title }),
      el('p', {}, [`${shortDateFmt.format(v.date)} · `, el('bdi', { textContent: v.ai ? v.ai.about : firstSentence.trim() })]),
    ]));
  }
}

// Matches the Saturday keys summarize.py writes into data.weeks.
function dateKey(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function summaryBlock(v) {
  if (!v.ai) return el('p', { className: 'summary', dir: 'auto', textContent: v.summary });
  return el('div', { className: 'summary' }, [
    el('p', { className: 'about', textContent: v.ai.about }),
    el('ul', { className: 'points' }, v.ai.points.map((p) => el('li', { textContent: p }))),
    el('p', { className: 'verdict', textContent: `💡 ${v.ai.verdict}` }),
    v.ai.source === 'description'
      ? el('p', { className: 'source-note', textContent: 'الملخص ده من وصف الفيديو، مش من الفيديو نفسه.' })
      : null,
  ]);
}

function searchText(v) {
  const ai = v.ai ? [v.ai.about, v.ai.verdict, ...v.ai.points].join(' ') : '';
  return `${v.title} ${v.summary} ${ai}`.toLowerCase();
}

function renderChips() {
  const used = new Set(state.videos.flatMap((v) => v.tags));
  const tags = ['all', ...Object.keys(TAG_LABELS).filter((t) => used.has(t))];
  $('chips').replaceChildren(...tags.map((t) => {
    const chip = el('button', {
      className: 'chip',
      type: 'button',
      textContent: t === 'all' ? 'الكل' : TAG_LABELS[t],
    });
    chip.setAttribute('aria-pressed', String(state.tag === t));
    chip.addEventListener('click', () => {
      state.tag = t;
      renderChips();
      renderGrid();
    });
    return chip;
  }));
}

function videoCard(v) {
  const thumb = el('a', { className: 'thumb', href: v.url, target: '_blank', rel: 'noopener' }, [
    el('img', { src: v.thumbnail, alt: '', loading: 'lazy' }),
    v.isShort ? el('span', { className: 'badge', textContent: 'Short' }) : null,
  ]);
  return el('article', { className: 'video card' }, [
    thumb,
    el('div', { className: 'video-body' }, [
      el('h3', {}, el('a', { href: v.url, target: '_blank', rel: 'noopener', dir: 'auto', textContent: v.title })),
      el('p', { className: 'meta', textContent: `${dateFmt.format(v.date)} · ${numberFmt.format(v.views)} مشاهدة` }),
      summaryBlock(v),
      el('div', { className: 'tags' }, v.tags.filter((t) => t !== 'shorts').map(
        (t) => el('span', { className: 'tag', textContent: TAG_LABELS[t] || t }),
      )),
      el('a', { className: 'watch', href: v.url, target: '_blank', rel: 'noopener', textContent: 'شوف على يوتيوب ↗' }),
    ]),
  ]);
}

function renderGrid() {
  const q = state.query.trim().toLowerCase();
  const videos = state.videos.filter((v) =>
    (state.tag === 'all' || v.tags.includes(state.tag)) &&
    (!q || searchText(v).includes(q)));
  $('grid').replaceChildren(...videos.map(videoCard));
  $('empty').hidden = videos.length > 0;
}

function shiftWeek(days) {
  state.weekStart = addDays(state.weekStart, days);
  renderWeek();
}

async function init() {
  try {
    const res = await fetch('data/videos.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    state.videos = data.videos
      .map((v) => ({ ...v, date: new Date(v.published) }))
      .sort((a, b) => b.date - a.date);
    state.weeks = data.weeks || {};
    // Open on the latest week that actually has videos.
    state.weekStart = startOfWeek(state.videos.length ? state.videos[0].date : new Date());
    $('footer').textContent = `آخر تحديث: ${dateFmt.format(new Date(data.updatedAt))} · البيانات من RSS قناة Flutter وبتتحدث كل يوم أوتوماتيك`;
  } catch (err) {
    console.error(err);
    state.weekStart = startOfWeek(new Date());
    $('footer').textContent = 'معرفناش نحمّل الفيديوهات دلوقتي. جرّب تعمل refresh كمان شوية.';
  }

  $('prev-week').addEventListener('click', () => shiftWeek(-7));
  $('next-week').addEventListener('click', () => shiftWeek(7));
  $('search').addEventListener('input', (e) => {
    state.query = e.target.value;
    renderGrid();
  });

  renderWeek();
  renderChips();
  renderGrid();
}

init();
