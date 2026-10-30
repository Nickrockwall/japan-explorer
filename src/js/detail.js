// 右上：地区风土与历史详卡
import { crestSVG } from './crests.js';

export const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const CIRCUITS = ['畿内', '东海道', '东山道', '北陆道', '山阴道', '山阳道', '南海道', '西海道'];

export function renderWelcome(el) {
  el.innerHTML = `
    <div class="welcome">
      <div class="badge-title">五畿七道 · 六十八国</div>
      <h2>今日的 47 都道府县，<br>曾是怎样的古国版图？</h2>
      <p>公元 7 世纪，律令国家把列岛划分为“五畿七道”与六十八个令制国。千年之后，明治政府废藩置县，又拼出了今天的都道府县——有的县恰好等于一国，有的县却由五国拼成，有的古国被一分为二。</p>
      <p>在左侧地图上点选任意地区，查看它的<b>古今双名</b>、<b>律令→战国→江户→近现代</b>沿革、名胜物产与方言，并和随地区更换身份的<b>时空案内人</b>聊聊。</p>
      <div class="circuits">${CIRCUITS.map((c) => `<span class="circuit-tag">${c}</span>`).join('')}<span class="circuit-tag">令制外：虾夷地 · 琉球</span></div>
    </div>`;
}

const list = (items) => items.map((x) => `<span class="pill">${esc(x)}</span>`).join('');

const fmtDate = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
};

function stampButton(p, stampedAt) {
  return stampedAt
    ? `<button class="stamp-btn done" type="button" disabled>${crestSVG(p.goshuin.crest_icon, 'crest crest-mini')}已盖印 · ${fmtDate(stampedAt)}</button>`
    : `<button class="stamp-btn" type="button" data-act="stamp">${crestSVG(p.goshuin.crest_icon, 'crest crest-mini')}打卡盖印</button>`;
}

// 盖印动效：朱印落下 + 面板微震 + 设备振动
export function playStamp(el, p, stampedAt) {
  const seal = document.createElement('div');
  seal.className = 'seal-drop';
  seal.innerHTML = `
    <div class="seal-face">
      ${crestSVG(p.goshuin.crest_icon, 'crest seal-crest')}
      <div class="seal-title">${esc(p.goshuin.title)}</div>
      <div class="seal-meta">奉拝 · ${esc(p.name.kanji)}</div>
    </div>`;
  // 详卡可滚动，浮层按其可视区域定位
  const r = el.getBoundingClientRect();
  Object.assign(seal.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${r.height}px` });
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
  nojun_karakuchi: { label: '浓醇辛口', x: 0.78, y: 0.22 }, tanrei_karakuchi: { label: '淡丽辛口', x: 0.78, y: 0.78 },
  nojun_amakuchi: { label: '浓醇甘口', x: 0.22, y: 0.22 }, tanrei_amakuchi: { label: '淡丽甘口', x: 0.22, y: 0.78 },
  shochu: { label: '烧酎·泡盛', x: null, y: null },
};

// 拉面构造解构图：碗的剖面 + 三层标注
function ramenFocus(p) {
  const r = p.ramen;
  const [soup, soupDeep] = RAMEN_BROTH[r.category] || RAMEN_BROTH.other;
  const noodles = Array.from({ length: 5 }, (_, i) =>
    `<path d="M40 ${92 + i * 6} q10 -5 20 0 t20 0 t20 0 t20 0 t20 0 t20 0 t20 0" fill="none" stroke="#f3d98a" stroke-width="2.6" stroke-linecap="round" opacity="${0.95 - i * 0.1}"/>`).join('');
  return `
    <section class="focus focus-ramen" aria-label="拉面构造解构">
      <div class="focus-h"><span class="focus-tag">拉面流派图鉴</span><b>${esc(r.style_name)}</b></div>
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
          <div><dt><i style="background:#c9925c"></i>浇头</dt><dd>${esc(r.toppings)}</dd></div>
          <div><dt><i style="background:#f3d98a"></i>面体</dt><dd>${esc(r.noodles)}</dd></div>
          <div><dt><i style="background:${soup}"></i>汤头</dt><dd>${esc(r.broth)}</dd></div>
        </dl>
      </div>
      <p class="focus-note">${esc(r.highlight)}</p>
    </section>`;
}

// 地酒酒标：竖排铭柄 + 风味象限
function sakeFocus(p) {
  const s = p.sake;
  const q = SAKE_QUAD[s.quadrant] || SAKE_QUAD.shochu;
  const chart = q.x == null
    ? '<div class="quad-none">烧酎·泡盛<br><small>不按清酒甘辛象限计</small></div>'
    : `<div class="quad">
        <span class="ax ax-t">浓醇</span><span class="ax ax-b">淡丽</span><span class="ax ax-l">甘口</span><span class="ax ax-r">辛口</span>
        <i class="quad-dot" style="left:${q.x * 100}%;top:${q.y * 100}%"></i>
      </div>`;
  return `
    <section class="focus focus-sake" aria-label="代表地酒">
      <div class="focus-h"><span class="focus-tag">地酒名酿地图</span><b>${esc(q.label)}</b>${s.famous ? '<span class="famous">全国名酿</span>' : ''}</div>
      <div class="sake-wrap">
        <div class="sake-label"><span class="brand">${esc(s.brand)}</span><span class="brewery">${esc(s.brewery)}</span></div>
        ${chart}
      </div>
      <p class="focus-note">${esc(s.taste_profile)}</p>
    </section>`;
}

function fudoSection(p) {
  return `
    <div class="section-h">风土 <small>Ramen & Sake</small></div>
    <div class="fudo">
      <div class="fudo-card"><span class="fudo-ico" aria-hidden="true">🍜</span><div>
        <div class="fudo-k">在地拉面</div><b>${esc(p.ramen.style_name)}</b><p>${esc(p.ramen.highlight)}</p></div></div>
      <div class="fudo-card"><span class="fudo-ico" aria-hidden="true">🍶</span><div>
        <div class="fudo-k">代表地酒</div><b>${esc(p.sake.brand)}</b><small>${esc(p.sake.brewery)}</small><p>${esc(p.sake.taste_profile)}</p></div></div>
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
    tl.insertAdjacentHTML('afterbegin', `<div class="era-note">⏳ ${esc(era.short)}：本县时间轴未单列此时代，可在地图上看该时代的全国格局。</div>`);
  }
}

export function renderDetail(el, p, { stampedAt, focus } = {}) {
  const L = p.historical_lineage;
  const provs = L.ritsuryo_provinces;
  const ancient = provs.map((x) => esc(x.name)).join(' · ');
  const fmtPop = p.stats.population_k >= 1000
    ? `${(p.stats.population_k / 1000).toFixed(2)}百万`
    : `${(p.stats.population_k / 10).toFixed(1)}万`;

  el.innerHTML = `
    <div class="hero">
      <div class="hero-badge" aria-hidden="true">${esc(p.badge.icon)}</div>
      <div class="hero-main">
        <div class="ancient-title">${ancient}<span class="arrow">→</span>${esc(p.name.zh)}</div>
        <div class="modern-title">
          <span class="kanji">${esc(p.name.kanji)}</span>
          <span class="kana">${esc(p.name.kana)}</span>
          <span class="romaji">${esc(p.name.romaji)}</span>
        </div>
        <div class="badge-title">「${esc(p.badge.title)}」</div>
      </div>
      ${stampButton(p, stampedAt)}
    </div>

    <div class="stats">
      <div class="stat"><div class="k">地方</div><div class="v">${esc(p.region)}</div></div>
      <div class="stat"><div class="k">厅所在地</div><div class="v" title="${esc(p.capital)}">${esc(p.capital)}</div></div>
      <div class="stat"><div class="k">人口</div><div class="v" title="${esc(p.stats.source)}">${fmtPop}</div></div>
      <div class="stat"><div class="k">面积</div><div class="v">${p.stats.area_km2.toLocaleString()} km²</div></div>
    </div>

    ${focus === 'ramen' ? ramenFocus(p) : focus === 'sake' ? sakeFocus(p) : ''}

    <details class="meme" ${focus ? '' : 'open'}>
      <summary><span class="meme-h">地域修罗场</span><small>地缘梗速览 · 玩笑话，别当真</small></summary>
      ${p.regional_meme.map((m) => `
        <div class="meme-item"><b>${esc(m.title)}</b><p>${esc(m.text)}</p></div>`).join('')}
    </details>

    <div class="section-h">令制国对照 <small>Ritsuryō Provinces</small></div>
    <div class="provinces">
      ${provs.map((x) => `
        <div class="prov ${x.circuit === '令制外' ? 'outside' : ''}">
          <span class="n">${esc(x.name)}</span><span class="kana">${esc(x.kana)}</span>
          <span class="meta"><span class="circ">${esc(x.circuit)}</span> · ${esc(x.portion)}</span>
          ${x.cross_prefectures?.length ? `<span class="cross" title="该国古地今分属多县">跨界 · 亦属 ${x.cross_prefectures.map(esc).join('、')}</span>` : ''}
        </div>`).join('')}
    </div>

    <div class="section-h">历代统治者 <small>Lineage</small></div>
    <div class="lineage">
      <div class="lineage-row"><span class="k">战国</span><div class="pills">${list(L.sengoku_daimyo)}</div></div>
      <div class="lineage-row"><span class="k">江户</span><div class="pills">${list(L.edo_domains)}</div></div>
      <div class="lineage-row"><span class="k">明治</span><div>${esc(L.meiji_transition.summary)}</div></div>
    </div>
    <div class="note"><b>古界线 vs 今县界：</b>${esc(L.meiji_transition.boundary_note)}</div>

    <div class="section-h">历史时间轴 <small>点击展开</small></div>
    <div class="timeline">
      ${p.history_timeline.map((t, i) => `
        <details class="tl" data-stage="${esc(t.era)}" ${i === 0 ? 'open' : ''}>
          <summary><span class="era">${esc(t.era)}</span><span class="t">${esc(t.title)}</span><span class="period">${esc(t.period)}</span></summary>
          <div class="body">${esc(t.summary)}</div>
        </details>`).join('')}
    </div>

    <div class="two-col">
      <div>
        <div class="section-h">名胜 <small>Landmarks</small></div>
        <ul class="items">${p.landmarks.map((x) => `<li><span class="n">${esc(x.name)}</span><span class="d">${esc(x.note)}</span></li>`).join('')}</ul>
      </div>
      <div>
        <div class="section-h">物产 <small>Specialties</small></div>
        <ul class="items">${p.specialties.map((x) => `<li><span class="n">${esc(x.name)}</span><span class="d">${esc(x.note)}</span></li>`).join('')}</ul>
      </div>
    </div>

    ${fudoSection(p)}

    <div class="section-h">方言速览 <small>${esc(p.dialect.name)}</small></div>
    <div class="dialect-box">
      <p class="feat">${esc(p.dialect.features)}</p>
      ${p.dialect.phrases.map((x) => `
        <div class="phrase">
          <span class="p">${esc(x.phrase)}</span><span class="m">${esc(x.meaning)}</span>
          ${x.note ? `<span class="x">${esc(x.note)}</span>` : ''}
        </div>`).join('')}
    </div>`;
  el.scrollTop = 0;
}
