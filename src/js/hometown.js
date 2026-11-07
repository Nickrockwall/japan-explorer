// 此地年表（古代户籍对话框末尾）：把一个市区町村在各时代的归属按年份串成一条线——
// 古代的国 → 战国 6 个年份（相邻年份同一家的合并）→ 江户领有本郡的藩各家（在位年份来自 han.json）→ 废藩置县 → 今天，
// 中间按年份插入彼时今日里坐标落在这个市区町村里的事件、诞生与去世。只用已核验的数据，不补写
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { findHan } from './han.js';

const SG_YEARS = ['1467', '1560', '1573', '1582', '1590', '1600'];
const MAX_KAKO = 20; // 大城市的区能有几十条：事件优先，其余按年份取前面的
const pick = (o) => o?.[lang] || o?.zh || o?.ja || '';
const nm = (o) => (lang === 'en' ? o.en || o.ja : lang === 'ja' ? o.ja : o.zh);

// 点是否在多边形里（射线法；只看外环，岛与飞地各是一块 Polygon）
function inRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
export function inGeometry(pt, g) {
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  return polys.some((poly) => inRing(pt, poly[0]));
}

// 彼时今日里落在这块地方的条目（每条带上日期键）；同一件事记在几个日子里的（承久之乱）只算一次
export function kakoIn(all, geometry) {
  const out = new Map();
  for (const [key, list] of Object.entries(all || {})) {
    for (const e of list) if (e.c && !out.has(`${e.q}|${e.t}`) && inGeometry(e.c, geometry)) out.set(`${e.q}|${e.t}`, { ...e, key });
  }
  return [...out.values()];
}

// 一个藩各家的起止：第一位有在位年份的就任 → 最后一位的退任（都不详时为 null）；
// 头一位或末一位不详时那一头不写（open），免得把第二代的就任年当成这一家的开始
function famSpan(rows) {
  const ys = rows.map((r) => r[5]).filter(Boolean);
  if (!ys.length) return null;
  const last = ys[ys.length - 1];
  return [ys[0][0], last[last.length - 1], !rows[0][5], !rows[rows.length - 1][5]];
}
const spanText = ([a, b, openA, openB]) => `${openA ? '…' : a}–${openB ? '…' : b}`;

// ctx 与古代户籍相同，再加 geometry（这个市区町村的边界）与 kako（彼时今日全部数据，没有时为 null）
export function hometownItems({ pref, props, provNames, sengoku, domains, han, prefLabel, geometry, kako }) {
  const items = [];
  const key = props.province;
  const pn = (ja) => provNames?.[ja]?.[lang] || ja;
  if (key && key !== '-') items.push({ y: -1, yl: t('ht.anc'), main: t('ht.prov', { prov: pn(key) }), kind: 'anc' });

  // 战国：相邻年份同一家的并成一段（1600 年是东西两军，单列）
  const unit = sengoku?.muni_units?.[props.code] || (sengoku?.units?.[key] ? key : null);
  const sg = sengoku?.units?.[unit] || sengoku?.provinces?.[key];
  if (sg && key !== '-') {
    let run = null;
    for (const y of SG_YEARS) {
      const c = sg[y]?.c;
      if (!c) continue;
      const g = (y === '1600' ? sengoku.sides : sengoku.clans)[c];
      const name = g?.[lang] || g?.zh || c;
      if (run && run.c === c && y !== '1600') { run.to = y; continue; }
      run = { c, from: y, to: y, name, side: y === '1600' };
      items.push(run);
    }
    for (const r of items.filter((x) => x.c)) {
      Object.assign(r, { y: +r.from, yl: r.from === r.to ? r.from : `${r.from}–${r.to}`, main: r.side ? t('ht.side', { name: r.name }) : r.name, kind: 'sg' });
    }
  }

  // 江户：幕末领有本郡最多町村的那一方；是藩就列出这个藩的各家（年份按在位），是天领等就写一行。
  // 主要的郡没有记录时（会津若松的北会津郡），只在其余几个郡的领主都相同时才用它，不一致就不写
  const gunList = props.old_districts || [];
  const gun = (gunList.find(([, part]) => !part) || gunList[0])?.[0];
  const topOf = (g) => domains?.[pref.id]?.[g]?.r?.[0]?.[0];
  const others = [...new Set(gunList.map(([g]) => topOf(g)).filter(Boolean))];
  const top = gun && topOf(gun) || (others.length === 1 ? others[0] : null);
  const h = top && !top.startsWith('@') ? findHan(han, top, pref.id) : null;
  if (h) {
    let prev = h.y?.[0] ?? 1603;
    h.f.forEach(([ja, zh, rows]) => {
      const span = famSpan(rows);
      const y = span ? span[0] : prev;
      prev = span ? span[1] : prev;
      const enSur = rows.find((r) => r[3])?.[3].split(' ')[0];
      const fam = !ja ? nm(h.n) : lang === 'zh' ? zh : lang === 'en' && enSur ? t('hn.fam', { name: enSur }) : ja;
      const who = (r) => (lang === 'en' ? r[3] || r[1] : lang === 'ja' ? r[1] : r[2]);
      const sub = rows.length > 1 ? `${who(rows[0])} → ${who(rows[rows.length - 1])}` : who(rows[0]);
      items.push({ y, yl: span ? spanText(span) : '', main: t('ht.fam', { han: nm(h.n), fam, n: rows.length }), sub, kind: 'edo' });
    });
    if (h.k) items.push({ y: 1871, yl: '1871', main: t('ht.haihan'), kind: 'edo' });
  } else if (top) {
    items.push({ y: 1700, yl: t('ht.edo'), main: top.startsWith('@') ? t(`ks.lord.${top.slice(1)}`) : top, kind: 'edo' });
  }

  // 彼时今日：落在这里的事件 / 诞生 / 去世
  const here = kakoIn(kako, geometry);
  const chosen = [...here.filter((e) => !e.t), ...here.filter((e) => e.t).sort((a, b) => a.y - b.y)].slice(0, MAX_KAKO);
  for (const e of chosen) {
    items.push({ y: e.y, yl: String(e.y), main: pick(e.n), tag: e.t, q: e.q, kind: 'kako' });
  }
  items.sort((a, b) => a.y - b.y); // 同一年：数组里的先后不变
  items.push({ y: 9999, yl: t('ht.now'), main: `${prefLabel} ${lang === 'en' && props.en ? props.en : props.name}`, kind: 'now' });
  return { items, more: Math.max(0, here.length - chosen.length), people: here.length };
}

export function hometownHTML({ items, more, people }) {
  const li = items.map((x) => {
    const tag = x.tag ? `<em class="kk-t kk-${x.tag}">${esc(t(`kk.t.${x.tag}`))}</em>` : '';
    const body = `<span class="ht-y">${esc(x.yl)}</span><span class="ht-m"><b>${esc(x.main)}${tag}</b>${x.sub ? `<span>${esc(x.sub)}</span>` : ''}</span>`;
    return `<li class="ht-${x.kind}">${x.q ? `<button type="button" class="ht-r ht-kk" data-kako="${esc(x.q)}" data-kt="${x.tag || ''}">${body}</button>` : `<div class="ht-r">${body}</div>`}</li>`;
  }).join('');
  return `<section class="ht" aria-labelledby="ht-h">
    <div class="ht-h" id="ht-h">${esc(t('ht.h'))}</div>
    <ol class="ht-list">${li}</ol>
    ${more ? `<p class="ht-more">${esc(t('ht.more', { n: more }))}</p>` : ''}
    <p class="ks-note">${esc(t(people ? 'ht.note' : 'ht.note0'))}</p></section>`;
}
