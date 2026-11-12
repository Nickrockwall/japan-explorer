// 生日帖：选一个日子（比如生日），把彼时今日里这一天的诞生 / 忌日 / 事件全部列出来，再算几个数：
// 这一天在全年 366 天里排第几「热闹」、最早的一件距今多少年、和哪个县缘分最深。同一份 data 既画成对话框，也画成图片
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { wrap } from './koseki.js';
import { fixLink } from './report.js';

const pick = (o) => o?.[lang] || o?.zh || '';

export function bdayData(all, key, now = new Date()) {
  const list = all[key] || [];
  const kind = (k) => list.filter((e) => (e.t || 'ev') === k);
  // 比这一天条目多的日子有几天 → 名次（并列取最好）
  const rank = 1 + Object.values(all).filter((v) => v.length > list.length).length;
  const tally = new Map();
  for (const e of list) tally.set(e.p, (tally.get(e.p) || 0) + 1);
  const [topP, topN] = [...tally].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0] || [];
  const oldest = list.reduce((a, e) => (a == null || e.y < a.y ? e : a), null);
  return { key, born: kind('born'), died: kind('died'), ev: kind('ev'), total: list.length, rank, days: Object.keys(all).length || 366, top: topP ? { p: topP, n: topN } : null, oldest, year: now.getFullYear() };
}

// 一条的副标题：县（· 某藩主）
const subOf = (e, prefName, lordOf) => [prefName(e.p), lordOf(e)].filter(Boolean).join(' · ');

function facts(d, prefName) {
  const out = [{ k: t('bd.f.rank'), v: t('bd.f.rankv', { n: d.rank, all: d.days }) }];
  if (d.oldest) out.push({ k: t('bd.f.oldest'), v: t('bd.f.oldestv', { y: d.oldest.y }), sub: [t('kk.ago', { n: d.year - d.oldest.y }), pick(d.oldest.n)] });
  if (d.top) out.push({ k: t('bd.f.pref'), v: prefName(d.top.p), sub: [t('bd.f.prefv', { n: d.top.n })] });
  return out;
}

const GROUPS = ['born', 'died', 'ev'];

// ── 出生年（3.40，只存本机）：年号、干支、今年几岁、同龄的他们 ──
// 年号按公历日期换（1873 年改用公历以后才准，输入框最早 1873）；干支按公历年，立春（2 月 4 日前后）以前出生的另注一句
const GENGO = [['meiji', 1868, '01-01'], ['taisho', 1912, '07-30'], ['showa', 1926, '12-25'], ['heisei', 1989, '01-08'], ['reiwa', 2019, '05-01']];
export function wareki(y, md) {
  let g = null;
  for (const e of GENGO) if (y > e[1] || (y === e[1] && md >= e[2])) g = e;
  return g ? { key: g[0], n: y - g[1] + 1 } : null;
}
const STEM = '甲乙丙丁戊己庚辛壬癸';
const BRANCH = '子丑寅卯辰巳午未申酉戌亥';
const STEM_EN = ['kinoe', 'kinoto', 'hinoe', 'hinoto', 'tsuchinoe', 'tsuchinoto', 'kanoe', 'kanoto', 'mizunoe', 'mizunoto'];
const BRANCH_EN = ['ne', 'ushi', 'tora', 'u', 'tatsu', 'mi', 'uma', 'hitsuji', 'saru', 'tori', 'inu', 'i'];
export function eto(y) {
  const i = (((y - 4) % 60) + 60) % 60;
  return { kan: STEM[i % 10] + BRANCH[i % 12], en: `${STEM_EN[i % 10]}-${BRANCH_EN[i % 12]}`, b: i % 12 };
}
export function ageOn(y, md, now = new Date()) {
  const today = `${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  return now.getFullYear() - y - (today < md ? 1 : 0);
}
// 同龄的他们：ages.json（tools/age_tool.py）里「那一年 − 生年」正好等于这个岁数的事；没有就取最近的岁数
const KIND_ORDER = { bat: 0, sho: 1, shk: 2, emp: 3, die: 4 };
export function sameAge(ages, age, max = 8) {
  if (!ages?.e?.length) return { age, list: [] };
  let a = age;
  let hit = ages.e.filter((e) => e[2] === a);
  for (let d = 1; !hit.length && d < 40; d++) {
    for (const x of [age - d, age + d]) {
      if (!hit.length) { hit = ages.e.filter((e) => e[2] === x); if (hit.length) a = x; }
    }
  }
  hit = hit.slice().sort((p, q) => KIND_ORDER[p[3]] - KIND_ORDER[q[3]] || p[1] - q[1]);
  return { age: a, list: hit.slice(0, max), more: Math.max(0, hit.length - max) };
}
const pname = (p) => (lang === 'ja' ? p[0] : lang === 'en' ? p[2] || p[0] : p[1] || p[0]);
export function youHTML(you, ages, battles) {
  if (!you) return '';
  const w = wareki(you.y, you.md);
  const e = eto(you.y);
  const age = ageOn(you.y, you.md);
  const gengo = w ? t('bd.y.gengo', { g: t(`bd.gg.${w.key}`), n: w.n === 1 ? t('bd.y.gan') : w.n }) : '';
  const etoTxt = lang === 'en' ? t('bd.y.eto', { animal: t(`bd.an.${e.b}`), kan: e.kan, rd: e.en }) : t('bd.y.eto', { kan: e.kan, animal: t(`bd.an.${e.b}`) });
  const early = you.md < '02-05' ? `<small>${esc(t('bd.y.risshun', { kan: eto(you.y - 1).kan }))}</small>` : '';
  const sa = sameAge(ages, age);
  const what = (x) => {
    if (x[3] === 'bat') return t('bd.age.bat', { b: (battles.find((b) => b.key === x[4])?.name || '').replace(/\s*[（(]\d+[)）]$/, '') });
    return t(`bd.age.${x[3]}`);
  };
  const items = sa.list.map((x) => `<li><b>${esc(pname(ages.p[x[0]]))}</b>${esc(t('bd.age.item', { age: x[2], y: x[1], what: what(x) }))}</li>`).join('');
  const head = sa.age === age ? t('bd.age.h', { age }) : t('bd.age.near', { age, a: sa.age });
  return `<section class="bd-you">
    <div class="bd-facts"><div class="bd-fact"><span>${esc(t('bd.y.k'))}</span><b>${esc(gengo || String(you.y))}</b><small>${esc(etoTxt)}</small>${early}</div>
    <div class="bd-fact"><span>${esc(t('bd.y.age'))}</span><b>${esc(t('bd.y.agev', { n: age }))}</b></div></div>
    ${ages ? `<h3>${esc(head)}</h3>${items ? `<ul class="bd-age">${items}</ul>` : ''}<p class="ks-note">${esc(t('bd.age.note'))}</p>` : ''}
  </section>`;
}

export function bdayHTML(d, { prefName, lordOf, name, you, ages, battles }) {
  const [m, day] = d.key.split('-').map(Number);
  const fact = facts(d, prefName).map((f) => `<div class="bd-fact"><span>${esc(f.k)}</span><b>${esc(f.v)}</b>${f.sub ? `<small>${esc(f.sub.join(' · '))}</small>` : ''}</div>`).join('');
  const group = (g) => {
    const rows = d[g];
    if (!rows.length) return '';
    const items = rows.map((e) => `<li><button type="button" class="bd-item" data-kako="${esc(e.q)}" data-kt="${e.t || ''}">
      <span class="bd-y">${e.y}<small>${esc(t('kk.ago', { n: d.year - e.y }))}</small></span>
      <span class="bd-main"><b>${esc(pick(e.n))}</b><span>${esc(subOf(e, prefName, lordOf))}</span></span></button></li>`).join('');
    return `<section class="bd-group"><h3>${esc(t(`bd.g.${g}`, { n: rows.length }))}</h3><ol>${items}</ol></section>`;
  };
  return `
    <button type="button" class="book-close" data-act="bd-close" aria-label="${esc(t('close'))}">×</button>
    <header class="ks-head">
      <div class="ks-kicker">${esc(t('bd.kicker'))}</div>
      <h2 id="bday-h">${esc(t('bd.title', { m, d: day }))}</h2>
      <label class="ks-name">${esc(t('bd.name'))}<input type="text" maxlength="16" data-bd-name value="${esc(name)}" placeholder="${esc(t('ks.name.ph'))}"></label>
      <label class="bd-date">${esc(t('kk.pick'))}<input type="date" data-bd-date value="${d.year}-${d.key}"></label>
      <label class="bd-date">${esc(t('bd.y.in'))}<input type="number" inputmode="numeric" min="1873" max="${d.year}" placeholder="${esc(t('bd.y.ph'))}" data-bd-year value="${you?.y || ''}"></label>
    </header>
    ${youHTML(you, ages, battles || [])}
    <div class="bd-facts">${fact}</div>
    ${d.total ? GROUPS.map(group).join('') : `<p class="kk-none">${esc(t('kk.none'))}</p>`}
    <p class="ks-note">${esc(t('bd.note'))}</p>
    <div class="ks-actions">
      <button type="button" class="btn" data-act="bd-image">${esc(t('ks.image'))}</button>
      <button type="button" class="btn btn-ghost" data-act="bd-link">${esc(t('ks.link'))}</button>
    </div>
    <p class="fix-row">${fixLink(t('fix.w.bd', { m, d: day }))}</p>`;
}

// ── 存成图片：与古代户籍同一套和纸底，竖版 1080 宽；每组最多画 6 条，其余写「另有 N 条」 ──
const MAX_ROWS = 6;
// 放不下一行的截短加省略号
const oneLine = (g, text, max) => {
  const lines = wrap(g, text, max);
  return lines.length > 1 ? `${lines[0].replace(/\s+$/, '').slice(0, -1)}…` : lines[0] || '';
};

export async function bdayImage(d, { prefName, lordOf, name }) {
  const W = 1080;
  const PAD = 80;
  const css = getComputedStyle(document.documentElement);
  const serif = css.getPropertyValue('--serif') || 'serif';
  const sans = css.getPropertyValue('--sans') || 'sans-serif';
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  const [m, day] = d.key.split('-').map(Number);
  const fs = facts(d, prefName);
  const layout = () => {
    let y = 330 + 190; // 标题 + 三格数字
    const blocks = GROUPS.filter((k) => d[k].length).map((k) => {
      const top = y;
      y += 70;
      const rows = d[k].slice(0, MAX_ROWS).map((e) => {
        g.font = `700 36px ${serif}`;
        const main = wrap(g, pick(e.n), W - PAD * 2 - 170);
        const h = main.length * 46 + 60;
        const r = { e, main, y, h };
        y += h;
        return r;
      });
      const more = d[k].length - rows.length;
      const moreY = y;
      if (more > 0) y += 44;
      y += 20;
      return { k, top, rows, more, moreY };
    });
    return { blocks, H: y + 130 };
  };
  let { blocks, H } = layout();
  c.width = W;
  c.height = H;
  ({ blocks, H } = layout());
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
  g.fillText(t('bd.kicker'), PAD, 70);
  g.fillStyle = '#2b2420';
  g.font = `900 76px ${serif}`;
  g.fillText(t('bd.title', { m, d: day }), PAD, 110);
  if (name) {
    g.font = `700 34px ${serif}`;
    g.fillStyle = '#5a4a3e';
    g.fillText(`${t('bd.name')}${name}`, PAD, 210);
  }
  // 三格数字
  const cw = (W - PAD * 2 - 40) / 3;
  fs.forEach((f, i) => {
    const x = PAD + i * (cw + 20);
    g.fillStyle = 'rgba(255,255,255,.4)';
    g.fillRect(x, 290, cw, 200);
    g.fillStyle = '#8a3b33';
    g.font = `400 24px ${sans}`;
    g.fillText(f.k, x + 18, 306);
    g.fillStyle = '#2b2420';
    g.font = `700 36px ${serif}`;
    g.fillText(oneLine(g, f.v, cw - 36), x + 18, 346);
    if (f.sub) {
      g.fillStyle = '#5a4a3e';
      g.font = `400 24px ${sans}`;
      f.sub.forEach((l, j) => g.fillText(oneLine(g, l, cw - 36), x + 18, 400 + j * 34));
    }
  });
  for (const { k, top, rows, more, moreY } of blocks) {
    g.fillStyle = '#8a3b33';
    g.font = `700 32px ${serif}`;
    g.fillText(t(`bd.g.${k}`, { n: d[k].length }), PAD, top + 20);
    g.strokeStyle = 'rgba(58,31,28,.5)';
    g.lineWidth = 3;
    g.beginPath();
    g.moveTo(PAD, top + 64);
    g.lineTo(W - PAD, top + 64);
    g.stroke();
    for (const { e, main, y } of rows) {
      g.fillStyle = '#8a5a2b';
      g.font = `700 34px ${serif}`;
      g.fillText(String(e.y), PAD, y + 14);
      g.fillStyle = '#2b2420';
      g.font = `700 36px ${serif}`;
      main.forEach((l, i) => g.fillText(l, PAD + 170, y + 12 + i * 46));
      g.fillStyle = '#5a4a3e';
      g.font = `400 26px ${sans}`;
      g.fillText(oneLine(g, subOf(e, prefName, lordOf), W - PAD * 2 - 170), PAD + 170, y + 16 + main.length * 46);
    }
    if (more > 0) {
      g.fillStyle = '#8a7a68';
      g.font = `400 26px ${sans}`;
      g.fillText(t('bd.more', { n: more }), PAD + 170, moreY);
    }
  }
  g.fillStyle = '#8a7a68';
  g.font = `400 24px ${sans}`;
  g.fillText('Japan Explorer · nickrockwall.github.io/japan-explorer', PAD, H - 90);
  return new Promise((res) => c.toBlob(res, 'image/png'));
}
