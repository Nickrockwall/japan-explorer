// 古代户籍《古今人别帐》：选一个市区町村（或「我在哪」的定位点），按时代列出这里归谁管。
// 每一栏注明精确到哪一级（市区町村 / 郡 / 县 / 国），只用已核验的数据计算，不编故事。
// 同一份 rows 既画成对话框里的卷轴（kosekiHTML），也画到 canvas 上存成图片（kosekiImage）
import { t, lang, label } from './i18n.js';
import { esc } from './detail.js';
import { distanceKm } from './koku.js';
import { fmtPeople } from './kokuryoku.js';
import { findHan, kosekiHanHTML } from './han.js';

const WALK_KM = 30; // 估算步行天数：一天约 30 公里
const DIRS = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];

function bearing([x1, y1], [x2, y2]) {
  const r = Math.PI / 180;
  const y = Math.sin((x2 - x1) * r) * Math.cos(y2 * r);
  const x = Math.cos(y1 * r) * Math.sin(y2 * r) - Math.sin(y1 * r) * Math.cos(y2 * r) * Math.cos((x2 - x1) * r);
  const deg = (Math.atan2(y, x) / r + 360) % 360;
  return t(`ks.dir.${DIRS[Math.round(deg / 45) % 8]}`);
}

// 多边形面积加权质心（取最大的那块）：市区町村地图里选中的地方用它量距离
export function centroidOf(geometry) {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  let best = null;
  let bestA = 0;
  for (const poly of polys) {
    const ring = poly[0];
    let a = 0, cx = 0, cy = 0;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const f = ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
      a += f;
      cx += (ring[j][0] + ring[i][0]) * f;
      cy += (ring[j][1] + ring[i][1]) * f;
    }
    if (Math.abs(a) > bestA) { bestA = Math.abs(a); best = [cx / (3 * a), cy / (3 * a)]; }
  }
  return best;
}

function nearest(sites, pt) {
  return sites.filter((s) => s.coords)
    .map((s) => ({ s, km: distanceKm(pt, s.coords) }))
    .sort((a, b) => a.km - b.km)[0] || null;
}

const km = (d) => (d < 10 ? d.toFixed(1) : Math.round(d));
const walk = (d) => (d < 12 ? t('ks.walk.day') : t('ks.walk.n', { n: Math.ceil(d / WALK_KM) }));

// ctx：{ pref, props, provNames, pt, sites, domains, power, prints, prefLabel, sengoku, han }
export function kosekiRows({ pref, props, provNames, pt, sites, domains, power, prints, prefLabel, sengoku, han }) {
  const pn = (ja) => provNames?.[ja]?.[lang] || ja;
  const key = props.province;
  const short = key?.replace(/国$/, '');
  const mine = sites.filter((s) => s.prov === key);
  const circuit = mine[0]?.circuit;
  const gunList = props.old_districts || [];
  const gun = (gunList.find(([, part]) => !part) || gunList[0])?.[0];
  const muniName = lang === 'en' && props.en ? props.en : props.name;
  const rows = [];

  // 本贯：道 · 国 · 郡；今属
  const home = [circuit ? label('circuit', circuit) : null, key ? pn(key) : t('muni.outside'), gun].filter(Boolean).join(' · ');
  const partial = props.partial?.length ? t('muni.partial', { list: props.partial.map(pn).join(' · ') }) : '';
  rows.push({ k: 'home', seal: 'muni', main: home, sub: [t('ks.now', { place: `${prefLabel} ${muniName}` }), partial].filter(Boolean).join(' · ') });

  if (mine.length && pt) {
    const ichi = nearest(mine.filter((s) => s.kind === 'ichi'), pt);
    if (ichi) rows.push({ k: 'kami', seal: 'muni', main: ichi.s.name, sub: t('ks.far', { dir: bearing(pt, ichi.s.coords), km: km(ichi.km) }) });
    const fu = nearest(mine.filter((s) => s.kind === 'fu'), pt);
    const ji = nearest(mine.filter((s) => s.kind === 'ji'), pt);
    if (fu || ji) {
      const part = [];
      if (fu) part.push(t('ks.fu', { dir: bearing(pt, fu.s.coords), km: km(fu.km), walk: walk(fu.km) }));
      if (ji) part.push(t('ks.ji', { name: ji.s.name, km: km(ji.km) }));
      rows.push({ k: 'ritsuryo', seal: 'muni', main: part[0], sub: part.slice(1).join(' · ') });
    }
  } else if (!mine.length) {
    rows.push({ k: 'ritsuryo', seal: 'pref', main: t('ks.outside'), sub: '' });
  }

  const f = pref.map_filters;
  // 战国：有 sengoku.json 时按旧国列出 6 个年份（主行 1560 → 1582 → 1600，副行其余三年）；没有时退回县的 1572
  const sg = sengoku?.provinces?.[key];
  if (sg && props.province !== '-') {
    const at = (y) => {
      const g = (y === '1600' ? sengoku.sides : sengoku.clans)[sg[y].c];
      return `${y} ${g[lang] || g.zh}`;
    };
    rows.push({ k: 'sengoku6', seal: 'prov', main: ['1560', '1582', '1600'].map(at).join(' → '), sub: ['1467', '1573', '1590'].map(at).join(' · ') });
  } else {
    rows.push({ k: 'sengoku', seal: 'pref', main: label('sg', f.sengoku_1572), sub: '' });
  }

  const d = gun && domains?.[pref.id]?.[gun];
  if (d) {
    const lord = (name) => (name.startsWith('@') ? t(`ks.lord.${name.slice(1)}`) : name);
    const hans = d.r.map(([n]) => !n.startsWith('@') && findHan(han, n, pref.id)).filter(Boolean);  // 点开看历代藩主
    rows.push({ k: 'edo', seal: 'gun', main: lord(d.r[0][0]), sub: t('ks.edo.of', { gun, n: d.t, list: d.r.map(([n, c]) => `${lord(n)} ${c}`).join(t('list.sep')) }), hans });
  } else {
    const list = pref.historical_lineage.edo_domains || [];
    rows.push({ k: 'edo', seal: 'pref', main: list.slice(0, 3).join(t('list.sep')) || '—', sub: list.length > 3 ? t('ks.more', { n: list.length - 3 }) : '' });
  }
  rows.push({ k: 'boshin', seal: 'pref', main: label('bk', f.bakumatsu), sub: '' });

  const P = power?.provinces?.[key];
  if (P) {
    const rank = Object.values(power.provinces).filter((v) => v.pop > P.pop).length + 1;
    rows.push({ k: 'power', seal: 'prov', main: t('ks.power', { prov: pn(key), pop: fmtPeople(P.pop), rank }), sub: '' });
  }
  const ph = pref.dialect?.phrases?.[0];
  if (ph) rows.push({ k: 'voice', seal: 'pref', main: `「${ph.phrase}」`, sub: ph.meaning, voice: true });
  return { rows, short, print: prints?.[0] || null };
}

export function kosekiHTML(ctx, data, name) {
  const { rows, print } = data;
  const title = `${ctx.prefLabel} ${lang === 'en' && ctx.props.en ? ctx.props.en : ctx.props.name}`;
  const body = rows.map((r) => `
    <div class="ks-row">
      <div class="ks-k">${esc(t(`ks.r.${r.k}`))}<i class="ks-seal" title="${esc(t(`ks.p.${r.seal}.t`))}">${esc(t(`ks.p.${r.seal}`))}</i></div>
      <div class="ks-v"><b>${esc(r.main)}</b>${r.sub ? `<span>${esc(r.sub)}</span>` : ''}${r.hans?.length ? kosekiHanHTML(r.hans) : ''}
        ${r.voice ? `<button type="button" class="ks-voice" data-act="ks-voice">${esc(t('ks.voice'))}</button>` : ''}</div>
    </div>`).join('');
  const art = print ? `<button type="button" class="ks-art" data-act="art" data-no="${print.no}"><img src="${esc(print.img)}" alt="" loading="lazy"><span>${esc(t('ks.art', { title: print.title_t || print.title }))}</span></button>` : '';
  return `
    <button type="button" class="book-close" data-act="ks-close" aria-label="${esc(t('close'))}">×</button>
    <header class="ks-head">
      <div class="ks-kicker">${esc(t('ks.kicker'))}</div>
      <h2 id="koseki-h">${esc(t('ks.title'))}</h2>
      <div class="ks-place">${esc(title)}</div>
      <label class="ks-name">${esc(t('ks.name'))}<input type="text" maxlength="16" data-ks-name value="${esc(name)}" placeholder="${esc(t('ks.name.ph'))}"></label>
    </header>
    <div class="ks-rows">${body}</div>
    ${art}
    <p class="ks-note">${esc(t('ks.note'))}</p>
    <div class="ks-actions">
      <button type="button" class="btn" data-act="ks-image">${esc(t('ks.image'))}</button>
      <button type="button" class="btn btn-ghost" data-act="ks-link">${esc(t('ks.link'))}</button>
    </div>`;
}

// ── 存成图片：竖版 1080 宽，和纸底、朱印，文字自动折行 ──
// 按词折行：连续的字母数字（含 . , ' - 等）不拆开，汉字假名逐字
function wrap(ctx, text, max) {
  const out = [];
  let line = '';
  for (const tok of text.match(/[\w.,'’()\-–]+\s*|\s+|./gu) || []) {
    if (ctx.measureText(line + tok).width > max && line.trim()) { out.push(line.trimEnd()); line = tok.trimStart(); } else line += tok;
  }
  if (line) out.push(line);
  return out;
}

export async function kosekiImage(ctxInfo, data, name) {
  const W = 1080;
  const PAD = 80;
  const serif = getComputedStyle(document.documentElement).getPropertyValue('--serif') || 'serif';
  const sans = getComputedStyle(document.documentElement).getPropertyValue('--sans') || 'sans-serif';
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  // 先量高度，再画
  const layout = () => {
    let y = 300;
    const items = data.rows.map((r) => {
      g.font = `700 40px ${serif}`;
      const main = wrap(g, r.main, W - PAD * 2 - 230);
      g.font = `400 28px ${sans}`;
      const sub = r.sub ? wrap(g, r.sub, W - PAD * 2 - 230) : [];
      const h = Math.max(70, main.length * 52 + sub.length * 40) + 34;
      const it = { r, main, sub, y, h };
      y += h;
      return it;
    });
    return { items, H: y + 170 };
  };
  let { items, H } = layout();
  c.width = W;
  c.height = H;
  ({ items, H } = layout());
  // 和纸底 + 深色边框
  const grad = g.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, '#f3ead9');
  grad.addColorStop(1, '#e6d9bf');
  g.fillStyle = grad;
  g.fillRect(0, 0, W, H);
  g.strokeStyle = '#3a1f1c';
  g.lineWidth = 24;
  g.strokeRect(12, 12, W - 24, H - 24);
  g.textBaseline = 'top';
  g.fillStyle = '#8a3b33';
  g.font = `400 28px ${sans}`;
  g.fillText(t('ks.kicker'), PAD, 70);
  g.fillStyle = '#2b2420';
  g.font = `900 76px ${serif}`;
  g.fillText(t('ks.title'), PAD, 110);
  g.font = `400 32px ${sans}`;
  g.fillStyle = '#5a4a3e';
  const head = `${ctxInfo.prefLabel} ${lang === 'en' && ctxInfo.props.en ? ctxInfo.props.en : ctxInfo.props.name}${name ? ` · ${t('ks.name')}${name}` : ''}`;
  g.fillText(head, PAD, 210);
  for (const { r, main, sub, y } of items) {
    g.strokeStyle = 'rgba(58,31,28,.25)';
    g.lineWidth = 2;
    g.beginPath();
    g.moveTo(PAD, y);
    g.lineTo(W - PAD, y);
    g.stroke();
    g.fillStyle = '#8a3b33';
    g.font = `700 30px ${serif}`;
    g.fillText(t(`ks.r.${r.k}`), PAD, y + 22);
    // 精确度朱印
    const sx = PAD + 150;
    g.fillStyle = '#b83a30';
    g.fillRect(sx, y + 20, 44, 44);
    g.fillStyle = '#f3ead9';
    g.font = `700 ${lang === 'en' ? 15 : 26}px ${serif}`;
    g.textAlign = 'center';
    g.fillText(t(`ks.p.${r.seal}`), sx + 22, y + (lang === 'en' ? 34 : 29));
    g.textAlign = 'left';
    g.fillStyle = '#2b2420';
    g.font = `700 40px ${serif}`;
    main.forEach((l, i) => g.fillText(l, PAD + 230, y + 20 + i * 52));
    g.fillStyle = '#5a4a3e';
    g.font = `400 28px ${sans}`;
    sub.forEach((l, i) => g.fillText(l, PAD + 230, y + 26 + main.length * 52 + i * 40));
  }
  g.fillStyle = '#8a7a68';
  g.font = `400 24px ${sans}`;
  g.fillText('Japan Explorer · nickrockwall.github.io/japan-explorer', PAD, H - 100);
  return new Promise((res) => c.toBlob(res, 'image/png'));
}
