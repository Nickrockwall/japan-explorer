// 此地年表（古代户籍对话框末尾）：把一个市区町村在各时代的归属按年份串成一条线——
// 古代的国 → 战国 6 个年份（相邻年份同一家的合并）→ 江户领有本郡的藩各家（在位年份来自 han.json）→ 废藩置县 → 今天，
// 中间按年份插入彼时今日里坐标落在这个市区町村里的事件、诞生与去世。只用已核验的数据，不补写。
// 冲绳、北海道与奄美群岛不在令制国：另按地区写（region_eras.json，tools/region_eras_tool.py），北海道分和人地与蝦夷地
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

// 彼时今日里落在这块地方的条目（每条带上日期键）；同一件事记在几个日子里的（承久之乱）只算一次。
// 地点只写到县、政令市、江户这类大范围的（g）坐标只是代表点，不算进代表点所在的那个市区町村
export function kakoIn(all, geometry) {
  const out = new Map();
  for (const [key, list] of Object.entries(all || {})) {
    for (const e of list) if (e.c && !e.g && !out.has(`${e.q}|${e.t}`) && inGeometry(e.c, geometry)) out.set(`${e.q}|${e.t}`, { ...e, key });
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

// ctx 与古代户籍相同，再加 geometry（这个市区町村的边界）、kako（彼时今日全部数据）、region（冲绳、北海道、奄美的地区年表）
// 与 ken（废藩置县后各郡归哪个县，bundle/ken-<lang>.json）、town（明治町村与地名来历，bundle/town-<lang>.json），没有的为 null
export function hometownItems({ pref, props, provNames, sengoku, domains, mainGun, han, prefLabel, geometry, kako, region, ken, town }) {
  const items = [];
  const key = props.province;
  const pn = (ja) => provNames?.[ja]?.[lang] || ja;
  // 古代：本国；和名抄对得上古郡的写上郡与郷数
  const wg = town?.wamyo?.muni?.[props.code];
  const gous = wg && town.wamyo.gou?.[key]?.[wg];
  if (key && key !== '-') items.push({ y: -1, yl: t('ht.anc'), main: t('ht.prov', { prov: pn(key) }), sub: gous?.length ? t('ht.wamyo', { gun: wg, n: gous.length }) : '', kind: 'anc' });

  // 战国：相邻年份同一家的并成一段（1600 年是东西两军，单列）
  const unit = sengoku?.muni_units?.[props.code] || (sengoku?.units?.[key] ? key : null);
  const sg = sengoku?.units?.[unit] || sengoku?.provinces?.[key];
  if (sg && key !== '-') {
    let run = null;
    for (const y of SG_YEARS) {
      const c = sg[y]?.c;
      // 令制外（冲绳、和人地以外的北海道在战国图上的总称）不写；关原之战与阿伊努的土地无关，1600 年也不写
      if (!c || c === 'outside' || (y === '1600' && c === 'ainu')) continue;
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
  // 主要郡（main_gun）：城下町（藩厅所在）直接是那个藩，江户 / 京都的市街直接是幕府领；其次旧高旧领数据库里本市区町村石高最多的一方（town.kyu）；
  // 再次中心市街所在的郡；整市一级的只在别的办法都没有时用
  const mg = mainGun?.[props.code];
  const kyuTop = town?.kyu?.[props.code]?.r?.[0]?.[0];
  const top = mg?.seat || mg?.town ? mg.lord : kyuTop || (mg?.g && topOf(mg.g)) || gun && topOf(gun) || (others.length === 1 ? others[0] : null) || mg?.lord || null;
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
  } else if (top) {
    items.push({ y: 1700, yl: t('ht.edo'), main: top.startsWith('@') ? t(`ks.lord.${top.slice(1)}`) : top, kind: 'edo' });
  }
  // 废藩置县之后：本郡（没有就取有记录的第一个郡）先后归哪个县。废藩置县那一行列了几个县时按藩名挑（上田藩 → 上田县），挑不出就不写
  const chain = (mg?.g && ken?.[pref.id]?.[mg.g]) || ken?.[pref.id]?.[gun] || gunList.map(([g]) => ken?.[pref.id]?.[g]).find(Boolean);
  if (chain) {
    const want = h && nm(h.n).replace(/藩$/, lang === 'ja' ? '県' : '县').replace(/ Domain$/, ' Prefecture');
    let shown = false;
    let cur = null; // 本地当前所属的县：「某县的辖区改归某县」这种行只在来源县就是它时才算
    for (const [y, names, haihan, src] of chain) {
      const name = names.length === 1 ? names[0] : haihan ? names.find((n) => n === want) : null;
      if (!name || (src && src !== cur)) continue;
      items.push({ y, yl: String(y), main: t(haihan ? 'ht.haihan.to' : 'ht.ken', { name }), kind: 'edo' });
      shown ||= haihan;
      cur = name;
    }
    if (!shown && h?.k) items.push({ y: 1871, yl: '1871', main: t('ht.haihan'), kind: 'edo' });
  } else if (h?.k) {
    items.push({ y: 1871, yl: '1871', main: t('ht.haihan'), kind: 'edo' });
  }

  // 明治町村制：今属这里的町村（town.mura，郡条目里写明的），列前 8 个
  const mura = town?.mura?.[props.code];
  if (mura?.length) {
    const ys = mura.map((x) => x[2]).sort((a, b) => a - b);
    const y = ys[Math.floor(ys.length / 2)];
    const names = mura.slice(0, 8).map(([n]) => n).join(t('list.sep'));
    items.push({ y, yl: String(y), main: t('ht.mura', { n: mura.length }), sub: mura.length > 8 ? `${names} ${t('ks.mura.more', { n: mura.length })}` : names, kind: 'mura' });
  }

  // 冲绳 / 北海道 / 奄美群岛（鹿儿岛县里不属于令制国的市町村）：地区年表（北海道按市町村在不在和人地挑 wajin / ezo 的条目）
  const amami = pref.id === 46 && (!key || key === '-');
  const reg = pref.id === 47 ? region?.okinawa : pref.id === 1 ? region?.hokkaido : amami ? region?.amami : null;
  if (reg) {
    const wajin = sengoku?.muni_units?.[props.code] === '和人地';
    for (const r of reg) {
      if (r.scope === (wajin ? 'ezo' : 'wajin')) continue;
      items.push({ y: r.y, yl: pick(r.yl), main: pick(r.main), sub: r.sub ? pick(r.sub) : '', kind: 'reg' });
    }
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
