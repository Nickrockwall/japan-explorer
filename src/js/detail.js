// 右上：地区风土与历史详卡
import { crestSVG } from './crests.js';
import { t, label, lang, prefName, joinList } from './i18n.js';
import { mapKey } from './country.js';
import { sharedButtons } from './shared.js';

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const CIRCUITS = ['畿内', '东海道', '东山道', '北陆道', '山阴道', '山阳道', '南海道', '西海道'];

export function renderWelcome(el) {
  el.innerHTML = `
    <div class="welcome">
      <div class="badge-title">${t('w.badge')}</div>
      <h2>${t('w.h')}</h2>
      <p>${t('w.p1')}</p>
      <p>${t('w.p2')}</p>
      <p><button type="button" class="btn tour-again" data-act="tour">📖 ${t('tour.again')}</button></p>
      <div class="circuits">${CIRCUITS.map((c) => `<span class="circuit-tag">${esc(label('circuit', c))}</span>`).join('')}<span class="circuit-tag">${t('w.outside')}</span></div>
      <div class="section-h">${t('sh.h')}</div>${sharedButtons()}
      <p class="legal">${legalHTML()}</p>
    </div>`;
}

// 版权与许可：代码 MIT、内容 CC BY-NC 4.0；全国地图须注明出典（地球地図日本）
const REPO = 'https://github.com/Nickrockwall/japan-explorer';
export function legalHTML() {
  return `© 2026 Nickrockwall · ${t('legal.lic')} · <a href="${REPO}/blob/main/LICENSE-CONTENT.md" target="_blank" rel="noopener">${t('legal.more')}</a><br>${t(mapKey === 'korea' ? 'kr.legal.map' : 'legal.map')}`;
}

const list = (items) => items.map((x) => `<span class="pill">${esc(x)}</span>`).join('');

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
};

// 人口：中文“百万/万”，日语“万人”，英语“M/K”
function fmtPop(k) {
  if (lang === 'en') return k >= 1000 ? `${(k / 1000).toFixed(2)}M` : `${k}K`;
  if (lang === 'ja') return `${Math.round(k / 10).toLocaleString()}万人`;
  return k >= 1000 ? `${(k / 1000).toFixed(2)}百万` : `${(k / 10).toFixed(1)}万`;
}

// 全称 + 简称：窄屏（手机）只显示简称，完整文字在 title 里
const twoLabels = (full, short) => `<span class="lbl-full">${esc(full)}</span><span class="lbl-short">${esc(short)}</span>`;

function stampButton(p, stampedAt) {
  const crest = crestSVG(p.goshuin.crest_icon, 'crest crest-mini');
  if (stampedAt) {
    const full = t('stamp.done', { date: fmtDate(stampedAt) });
    return `<button class="stamp-btn done" type="button" disabled title="${esc(full)}">${crest}${twoLabels(full, t('stamp.doneShort'))}</button>`;
  }
  return `<button class="stamp-btn" type="button" data-act="stamp" title="${esc(t('stamp.do'))}">${crest}${twoLabels(t('stamp.do'), t('stamp.doShort'))}</button>`;
}

// 盖印动效：朱印落下 + 面板微震 + 设备振动
export function playStamp(el, p, stampedAt) {
  const seal = document.createElement('div');
  seal.className = 'seal-drop';
  seal.innerHTML = `
    <div class="seal-face">
      ${crestSVG(p.goshuin.crest_icon, 'crest seal-crest')}
      <div class="seal-title">${esc(p.goshuin.title)}</div>
      <div class="seal-meta">${esc(t('seal.meta', { name: p.name.kanji }))}</div>
    </div>`;
  // 浮层只盖住详卡在屏幕内可见的部分：窄屏时详卡随整页展开（高达数千像素），
  // 直接用它的矩形会让印章落在屏幕外
  const r = el.getBoundingClientRect();
  const top = Math.max(r.top, 0), bottom = Math.min(r.bottom, innerHeight);
  const left = Math.max(r.left, 0), right = Math.min(r.right, innerWidth);
  const box = bottom - top > 200 ? { top, height: bottom - top } : { top: 0, height: innerHeight }; // 详卡几乎不可见时用整个屏幕
  Object.assign(seal.style, { left: `${left}px`, top: `${box.top}px`, width: `${right - left}px`, height: `${box.height}px` });
  document.body.appendChild(seal);
  el.classList.remove('shake');
  void el.offsetWidth;
  el.classList.add('shake');
  try { navigator.vibrate?.([30, 40, 60]); } catch { /* 不支持则忽略 */ }
  setTimeout(() => seal.classList.add('out'), 1500);
  setTimeout(() => { seal.remove(); el.classList.remove('shake'); }, 2100);
  const btn = el.querySelector('.stamp-btn');
  if (btn) btn.outerHTML = stampButton(p, stampedAt);
}

// ── 风土：拉面与地酒 ──────────────
const RAMEN_BROTH = {
  tonkotsu: ['#f1e8d6', '#d8c8a8'], shoyu: ['#b5523f', '#7a2e22'], miso: ['#e0ab4a', '#a8762a'],
  shio: ['#cfe7e2', '#9fc8c2'], other: ['#9a86c0', '#5f4f86'],
};
const SAKE_QUAD = {
  nojun_karakuchi: { x: 0.78, y: 0.22 }, tanrei_karakuchi: { x: 0.78, y: 0.78 },
  nojun_amakuchi: { x: 0.22, y: 0.22 }, tanrei_amakuchi: { x: 0.22, y: 0.78 },
  shochu: { x: null, y: null },
};

// 拉面构造解构图：碗的剖面 + 三层标注
function ramenFocus(p) {
  const r = p.ramen;
  const [soup, soupDeep] = RAMEN_BROTH[r.category] || RAMEN_BROTH.other;
  const noodles = Array.from({ length: 5 }, (_, i) =>
    `<path d="M40 ${92 + i * 6} q10 -5 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0" fill="none" stroke="#f3d98a" stroke-width="2.6" stroke-linecap="round" opacity="${0.95 - i * 0.1}"/>`).join('');
  return `
    <section class="focus focus-ramen" aria-label="${t('ramen.tag')}">
      <div class="focus-h"><span class="focus-tag">${t('ramen.tag')}</span><b>${esc(r.style_name)}</b></div>
      <div class="ramen-wrap">
        <svg class="bowl" viewBox="0 0 200 150" aria-hidden="true">
          <defs><linearGradient id="soup-${p.id}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="${soup}"/><stop offset="1" stop-color="${soupDeep}"/></linearGradient></defs>
          <path d="M18 72 h164 c0 44 -36 66 -82 66 s-82 -22 -82 -66z" fill="url(#soup-${p.id})"/>
          ${noodles}
          <ellipse cx="62" cy="70" rx="20" ry="8" fill="#b9714a" stroke="#7e4a2e" stroke-width="1.5"/>
          <circle cx="104" cy="68" r="9" fill="#f6f2e8" stroke="#e86f9a" stroke-width="2"/>
          <path d="M98 68 q6 -6 12 0 q-6 6 -12 0" fill="none" stroke="#e86f9a" stroke-width="1.6"/>
          <rect x="128" y="56" width="22" height="18" rx="2" fill="#1f2a1f" transform="rotate(-12 139 65)"/>
          <path d="M150 66 l14 -10 M155 68 l12 -6" stroke="#7fbf6a" stroke-width="3" stroke-linecap="round"/>
          <path d="M10 72 h180" stroke="#c23531" stroke-width="5" stroke-linecap="round"/>
          <path d="M18 74 c4 40 36 62 82 62 s78 -22 82 -62" fill="none" stroke="#2a2a30" stroke-width="5"/>
          <path d="M70 140 h60 l-6 8 h-48z" fill="#2a2a30"/>
        </svg>
        <dl class="ramen-parts">
          <div><dt><i style="background:#c9925c"></i>${t('ramen.top')}</dt><dd>${esc(r.toppings)}</dd></div>
          <div><dt><i style="background:#f3d98a"></i>${t('ramen.noodle')}</dt><dd>${esc(r.noodles)}</dd></div>
          <div><dt><i style="background:${soup}"></i>${t('ramen.broth')}</dt><dd>${esc(r.broth)}</dd></div>
        </dl>
      </div>
      <p class="focus-note">${esc(r.highlight)}</p>
    </section>`;
}

// 地酒酒标：竖排铭柄 + 风味象限
function sakeFocus(p) {
  const s = p.sake;
  const q = SAKE_QUAD[s.quadrant] || SAKE_QUAD.shochu;
  const quad = label('sk', s.quadrant);
  const chart = q.x == null
    ? `<div class="quad-none">${esc(quad)}<br><small>${t('sake.shochu.note')}</small></div>`
    : `<div class="quad">
        <span class="ax ax-t">${t('ax.rich')}</span><span class="ax ax-b">${t('ax.light')}</span><span class="ax ax-l">${t('ax.sweet')}</span><span class="ax ax-r">${t('ax.dry')}</span>
        <i class="quad-dot" style="left:${q.x * 100}%;top:${q.y * 100}%"></i>
      </div>`;
  return `
    <section class="focus focus-sake" aria-label="${t('fudo.sake')}">
      <div class="focus-h"><span class="focus-tag">${t('sake.tag')}</span><b>${esc(quad)}</b>${s.famous ? `<span class="famous">${t('sake.famous')}</span>` : ''}</div>
      <div class="sake-wrap">
        <div class="sake-label"><span class="brand">${esc(s.brand)}</span><span class="brewery">${esc(s.brewery)}</span></div>
        ${chart}
      </div>
      <p class="focus-note">${esc(s.taste_profile)}</p>
    </section>`;
}

function fudoSection(p) {
  return `
    <div class="section-h">${t('sec.fudo')} <small>Ramen & Sake</small></div>
    <div class="fudo">
      <div class="fudo-card"><span class="fudo-ico" aria-hidden="true">🍜</span><div>
        <div class="fudo-k">${t('fudo.ramen')}</div><b>${esc(p.ramen.style_name)}</b><p>${esc(p.ramen.highlight)}</p></div></div>
      <div class="fudo-card"><span class="fudo-ico" aria-hidden="true">🍶</span><div>
        <div class="fudo-k">${t('fudo.sake')}</div><b>${esc(p.sake.brand)}</b><small>${esc(p.sake.brewery)}</small><p>${esc(p.sake.taste_profile)}</p></div></div>
    </div>`;
}

// 时代滑块联动：高亮对应的时间轴阶段
export function highlightEra(el, era) {
  el.querySelectorAll('.tl').forEach((d) => d.classList.remove('era-hl'));
  el.querySelector('.era-note')?.remove();
  if (!era) return;
  const tl = el.querySelector('.timeline');
  if (!tl) return;
  const hit = era.timeline_stage && el.querySelector(`.tl[data-stage="${era.timeline_stage}"]`);
  if (hit) {
    hit.open = true;
    hit.classList.add('era-hl');
    hit.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  } else {
    tl.insertAdjacentHTML('afterbegin', `<div class="era-note">${esc(t('era.note', { era: era.short }))}</div>`);
  }
}

// 详卡头像：县章（金色遮罩）；没有县章的县用旧国名朱印（最多两国，竖排）
function badge(p, emblem) {
  const name = prefName(p);
  if (emblem) {
    const u = `url('${esc(emblem)}')`;
    return `<span class="emblem" role="img" aria-label="${esc(t('emblem.alt', { name }))}" title="${esc(t('emblem.alt', { name }))}"
      style="-webkit-mask-image:${u};mask-image:${u}"></span>`;
  }
  const provs = p.historical_lineage.ritsuryo_provinces.map((x) => x.name.replace(/国$/, '')).slice(0, 2);
  return `<span class="kuni-seal${provs.length > 1 ? ' two' : ''}" role="img" aria-label="${esc(provs.join(' · '))}">${provs.map((x) => `<b>${esc(x)}</b>`).join('')}</span>`;
}

export function renderDetail(el, p, { stampedAt, focus, extra = '', emblem } = {}) {
  const L = p.historical_lineage;
  const provs = L.ritsuryo_provinces;
  const ancient = provs.map((x) => esc(x.name)).join(' · ');
  const stageRow = (era, html) => `<div class="lineage-row"><span class="k">${esc(label('stage', era))}</span>${html}</div>`;

  el.innerHTML = `
    ${p._translated === false ? `<div class="untranslated">🌐 ${t('untranslated')}</div>` : ''}
    <div class="hero">
      <div class="hero-badge">${badge(p, emblem)}</div>
      <div class="hero-main">
        <div class="ancient-title">${ancient}<span class="arrow">→</span>${esc(prefName(p))}</div>
        <div class="modern-title">
          <span class="kanji">${esc(p.name.kanji)}</span>
          <span class="kana">${esc(p.name.kana)}</span>
          <span class="romaji">${esc(p.name.romaji)}</span>
        </div>
        <div class="badge-title">「${esc(p.badge.title)}」</div>
      </div>
      <div class="hero-actions">
        ${stampButton(p, stampedAt)}
        <button class="share-btn" type="button" data-act="share" title="${esc(t('share.title'))}" aria-label="${esc(t('share'))}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a3 3 0 1 0-2.8-4M6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm12 6a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <span>${t('share')}</span>
        </button>
        <button class="share-btn" type="button" data-act="muni" title="${esc(t('muni.open.title'))}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2zM9 4v14M15 6v14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
          <span>${twoLabels(t('muni.open'), t('muni.openShort'))}</span>
        </button>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="k">${t('st.region')}</div><div class="v">${esc(label('region', p.region))}</div></div>
      <div class="stat"><div class="k">${t('st.capital')}</div><div class="v" title="${esc(p.capital)}">${esc(p.capital)}</div></div>
      <div class="stat"><div class="k">${t('st.pop')}</div><div class="v" title="${esc(p.stats.source)}">${fmtPop(p.stats.population_k)}</div></div>
      <div class="stat"><div class="k">${t('st.area')}</div><div class="v">${p.stats.area_km2.toLocaleString()} km²</div></div>
    </div>

    ${focus === 'ramen' ? ramenFocus(p) : focus === 'sake' ? sakeFocus(p) : ''}

    <details class="meme" ${focus ? '' : 'open'}>
      <summary><span class="meme-h">${t('meme.h')}</span><small>${t('meme.sub')}</small></summary>
      ${p.regional_meme.map((m) => `
        <div class="meme-item"><b>${esc(m.title)}</b><p>${esc(m.text)}</p></div>`).join('')}
    </details>

    <div class="section-h">${t('sec.prov')} <small>Ritsuryō Provinces</small></div>
    <div class="provinces">
      ${provs.map((x) => `
        <div class="prov ${x.circuit === '令制外' ? 'outside' : ''}">
          <span class="n">${esc(x.name)}</span><span class="kana">${esc(x.kana)}</span>
          <span class="meta"><span class="circ">${esc(label('circuit', x.circuit))}</span> · ${esc(x.portion)}</span>
          ${x.cross_prefectures?.length ? `<span class="cross" title="${t('cross.title')}">${esc(t('cross', { list: joinList(x.cross_prefectures) }))}</span>` : ''}
        </div>`).join('')}
    </div>

    <div class="section-h">${t('sec.lineage')} <small>Lineage</small></div>
    <div class="lineage">
      ${stageRow('战国', `<div class="pills">${list(L.sengoku_daimyo)}</div>`)}
      ${stageRow('江户', `<div class="pills">${list(L.edo_domains)}</div>`)}
      <div class="lineage-row"><span class="k">${t('row.meiji')}</span><div>${esc(L.meiji_transition.summary)}</div></div>
    </div>
    <div class="note"><b>${t('note.border')}</b>${esc(L.meiji_transition.boundary_note)}</div>

    <div class="section-h">${t('sec.timeline')} <small>${t('sec.timeline.sub')}</small></div>
    <div class="timeline">
      ${p.history_timeline.map((tl, i) => `
        <details class="tl" data-stage="${esc(tl.era)}" ${i === 0 ? 'open' : ''}>
          <summary><span class="era">${esc(label('stage', tl.era))}</span><span class="t">${esc(tl.title)}</span><span class="period">${esc(tl.period)}</span></summary>
          <div class="body">${esc(tl.summary)}</div>
        </details>`).join('')}
    </div>

    <div class="two-col">
      <div>
        <div class="section-h">${t('sec.landmarks')} <small>Landmarks</small></div>
        <ul class="items">${p.landmarks.map((x) => `<li><span class="n">${esc(x.name)}</span><span class="d">${esc(x.note)}</span></li>`).join('')}</ul>
      </div>
      <div>
        <div class="section-h">${t('sec.specialties')} <small>Specialties</small></div>
        <ul class="items">${p.specialties.map((x) => `<li><span class="n">${esc(x.name)}</span><span class="d">${esc(x.note)}</span></li>`).join('')}</ul>
      </div>
    </div>

    ${fudoSection(p)}

    <div class="section-h">${t('sec.dialect')} <small>${esc(p.dialect.name)}</small></div>
    <div class="dialect-box">
      <p class="feat">${esc(p.dialect.features)}</p>
      ${p.dialect.phrases.map((x) => `
        <div class="phrase">
          <span class="p">${esc(x.phrase)}</span><span class="m">${esc(x.meaning)}</span>
          ${x.note ? `<span class="x">${esc(x.note)}</span>` : ''}
        </div>`).join('')}
    </div>`;
  if (extra) el.insertAdjacentHTML('beforeend', extra); // 详卡底部的附加卡片（如圣地巡礼志）
  el.scrollTop = 0;
}
