// 古国国力：68 国的今日人口 / 江户人口 / 密度 / 石高 / 三百年逆袭（排名升降），着色、提示、榜单、宿敌 PK。
// 数据由 tools/build_kokuryoku.py 生成（data.kokuryoku）；旧国名取自 provinces.json 的 properties
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export const METRICS = ['pop', 'pop1721', 'density', 'koku', 'rise'];
// 五档：少 → 多（淡黄土 → 赭 → 深朱）；逆袭：大跌 → 大涨（藍 → 纸色 → 朱）
const RAMP = ['#ece2c8', '#dcc48a', '#c9975a', '#b3664a', '#94402f'];
const RISE = [[10, '#a8392e'], [3, '#d99a7a'], [-2, '#e4dccb'], [-9, '#8fb0c4'], [-Infinity, '#3e6a8a']];
const DOME = 43500; // 东京巨蛋棒球赛时约 43,500 席（日文维基「東京ドーム」）
// 宿敌 PK：一方可以是几个国合起来（长州 = 周防 + 长门），也可以是一个郡（按市区町村的明治旧郡汇总）
export const PK = [
  { id: 'iga-koka', sides: [{ provs: ['伊賀国'] }, { district: '近江国/甲賀郡' }] },
  { id: 'kai-echigo', sides: [{ provs: ['甲斐国'] }, { provs: ['越後国'] }] },
  { id: 'owari-mikawa', sides: [{ provs: ['尾張国'] }, { provs: ['三河国'] }] },
  { id: 'satsuma-choshu', sides: [{ provs: ['薩摩国'] }, { provs: ['周防国', '長門国'], name: 'choshu' }] },
  { id: 'osaka3', sides: [{ provs: ['摂津国'] }, { provs: ['河内国'] }, { provs: ['和泉国'] }] },
  { id: 'bi3', sides: [{ provs: ['備前国'] }, { provs: ['備中国'] }, { provs: ['備後国'] }] },
];

const fmt = (n, d = 0) => n.toLocaleString(lang === 'zh' ? 'zh-CN' : lang, { maximumFractionDigits: d });
export function fmtPeople(n) {
  if (n == null) return '—';
  if (lang === 'en') return n >= 1e6 ? `${fmt(n / 1e6, n < 1e7 ? 2 : 1)}M` : n >= 1e4 ? `${fmt(n / 1e3)}K` : fmt(n);
  return n >= 1e4 ? t('kr.wan', { n: fmt(n / 1e4, n < 1e5 ? 1 : 0) }) : fmt(n);
}
const fmtKoku = (n) => (n == null ? '—' : lang === 'en' ? `${fmt(n / 1e6, 2)}M koku` : t('kr.koku.v', { n: fmt(n / 1e4, n < 1e5 ? 1 : 0) }));

export function createPower(data, provinces) {
  const P = data.provinces;
  const props = new Map(provinces.features.map((f) => [f.properties.key, f.properties]));
  const outside = (k) => props.get(k)?.circuit === '令制外';
  const name = (k) => {
    const p = props.get(k);
    return lang === 'en' ? p.en.replace(/ Province$/, '') : (lang === 'ja' ? p.ja : p.zh).replace(/国$/, '');
  };
  // 令制外（虾夷地、琉球）不在幕府的国别调查之内，江户的指标留空
  const raw = {
    pop: (k) => P[k].pop,
    pop1721: (k) => (outside(k) ? null : P[k].pop1721),
    density: (k) => P[k].pop / P[k].area,
    koku: (k) => (outside(k) ? null : P[k].koku1834 || null),
  };
  const keys = Object.keys(P);
  const rankOf = {};
  for (const m of Object.keys(raw)) {
    const list = keys.filter((k) => raw[m](k) != null).sort((a, b) => raw[m](b) - raw[m](a));
    rankOf[m] = new Map(list.map((k, i) => [k, i + 1]));
  }
  // 逆袭：只在两边都有排名的国之间重排，避免令制外把名次挤乱
  const both = keys.filter((k) => rankOf.pop1721.has(k));
  const rEdo = new Map([...both].sort((a, b) => P[b].pop1721 - P[a].pop1721).map((k, i) => [k, i + 1]));
  const rNow = new Map([...both].sort((a, b) => P[b].pop - P[a].pop).map((k, i) => [k, i + 1]));
  const rise = (k) => (rEdo.has(k) ? rEdo.get(k) - rNow.get(k) : null);
  const value = (m, k) => (m === 'rise' ? rise(k) : raw[m](k));

  let metric = 'pop';
  let focus = null;

  function color(k) {
    if (!P[k]) return null; // 奄美、小笠原等令制外的小块没有统计
    const v = value(metric, k);
    if (v == null) return null;
    if (metric === 'rise') return RISE.find(([min]) => v >= min)[1];
    const r = rankOf[metric].get(k);
    return RAMP[RAMP.length - 1 - Math.min(RAMP.length - 1, Math.floor(((r - 1) * RAMP.length) / rankOf[metric].size))];
  }

  function show(m, v) {
    if (v == null) return '—';
    if (m === 'pop' || m === 'pop1721') return fmtPeople(v);
    if (m === 'density') return t('kr.density.v', { n: fmt(v) });
    if (m === 'koku') return fmtKoku(v);
    return v > 0 ? `▲${v}` : v < 0 ? `▼${-v}` : '—';
  }

  function legend() {
    const items = metric === 'rise'
      ? [['kr.rise.up2', 0], ['kr.rise.up', 1], ['kr.rise.flat', 2], ['kr.rise.down', 3], ['kr.rise.down2', 4]]
        .map(([key, i]) => [t(key), RISE[i][1], both.filter((k) => color(k) === RISE[i][1]).length])
      : RAMP.map((c, i) => {
        const inBin = keys.filter((k) => color(k) === c).map((k) => value(metric, k));
        return inBin.length ? [`${show(metric, Math.min(...inBin))} – ${show(metric, Math.max(...inBin))}`, c, inBin.length] : null;
      }).filter(Boolean).reverse();
    return { caption: t(`kr.cap.${metric}`, { year: data.pop_year }), items };
  }

  function tip(k) {
    const v = P[k];
    if (!v) return '';
    const row = (m, val) => `${t(`kr.m.${m}`)}：${show(m, val)}${rankOf[m]?.get(k) ? ` <span style="color:#6b6155">${t('kr.rank', { n: rankOf[m].get(k) })}</span>` : ''}`;
    const r = rise(k);
    return [row('pop', v.pop), row('pop1721', value('pop1721', k)), row('koku', value('koku', k)),
      `${t('kr.area')}：${fmt(v.area)} km² · ${row('density', value('density', k))}`,
      r != null ? `${t('kr.m.rise')}：${t('kr.rise.v', { a: rEdo.get(k), b: rNow.get(k) })}` : ''].filter(Boolean).join('<br>');
  }

  // ── 反常识头条：全部由数字算出，算不出来的那条就不出 ──
  function headlines() {
    const out = [];
    const byPop = keys.slice().sort((a, b) => P[b].pop - P[a].pop);
    const total = keys.reduce((s, k) => s + P[k].pop, 0);
    const top = byPop[0];
    let n = 0;
    for (let s = 0, i = byPop.length - 1; i > 0 && s + P[byPop[i]].pop < P[top].pop; i--) { s += P[byPop[i]].pop; n += 1; }
    out.push(t('kr.h.top', { a: name(top), pct: Math.round((P[top].pop / total) * 100), pop: fmtPeople(P[top].pop), n }));
    const low = byPop[byPop.length - 1];
    if (P[low].pop * 2 < DOME) out.push(t('kr.h.dome', { a: name(low), pop: fmtPeople(P[low].pop) }));
    const order = both.slice().sort((a, b) => rise(b) - rise(a));
    const up = order[0];
    const down = order[order.length - 1];
    out.push(t('kr.h.up', { a: name(up), x: rEdo.get(up), y: rNow.get(up) }));
    out.push(t('kr.h.down', { a: name(down), x: rEdo.get(down), y: rNow.get(down) }));
    const shrink = both.filter((k) => P[k].pop < P[k].pop1721).sort((a, b) => P[a].pop / P[a].pop1721 - P[b].pop / P[b].pop1721);
    if (shrink.length) {
      const k = shrink[0];
      out.push(t('kr.h.shrink', { list: shrink.map(name).join(t('list.sep')), a: name(k), pct: Math.round((P[k].pop / P[k].pop1721) * 100) }));
    }
    const grow = both.slice().sort((a, b) => P[b].pop / P[b].pop1721 - P[a].pop / P[a].pop1721)[0];
    out.push(t('kr.h.grow', { a: name(grow), x: fmt(P[grow].pop / P[grow].pop1721, 1) }));
    const rich = [...rankOf.koku.keys()][0];
    out.push(t('kr.h.koku', { a: name(rich), koku: fmtKoku(P[rich].koku1834), y: rankOf.pop.get(rich) }));
    return out;
  }
  const facts = headlines();
  let factIdx = 0;

  // ── 宿敌 PK ──
  function side(s) {
    if (s.district) {
      const d = data.districts[s.district];
      return { label: t(`kr.d.${s.district.split('/')[1]}`), pop: d.pop, area: d.area, munis: d.munis, pop1721: null, koku: null };
    }
    const sum = (f) => (s.provs.every((k) => f(k) != null) ? s.provs.reduce((a, k) => a + f(k), 0) : null);
    return {
      label: s.name ? t(`kr.pk.${s.name}`) : name(s.provs[0]),
      pop: sum((k) => P[k].pop), area: sum((k) => P[k].area), munis: sum((k) => P[k].munis),
      pop1721: sum((k) => value('pop1721', k)), koku: sum((k) => value('koku', k)),
    };
  }
  const PK_ROWS = [
    ['pop', (x) => x.pop, fmtPeople], ['pop1721', (x) => x.pop1721, fmtPeople],
    ['grow', (x) => (x.pop1721 ? x.pop / x.pop1721 : null), (v) => (v == null ? '—' : `×${fmt(v, 1)}`)],
    ['koku', (x) => x.koku, fmtKoku], ['area', (x) => x.area, (v) => (v == null ? '—' : `${fmt(v)} km²`)],
    ['density', (x) => x.pop / x.area, (v) => t('kr.density.v', { n: fmt(v) })], ['munis', (x) => x.munis, (v) => (v == null ? '—' : fmt(v))],
  ];
  function pkTable(sides) {
    const cols = sides.map(side);
    const head = `<tr><th></th>${cols.map((c) => `<th>${esc(c.label)}</th>`).join('')}</tr>`;
    const rows = PK_ROWS.map(([key, get, f]) => {
      const vals = cols.map(get);
      const best = Math.max(...vals.filter((v) => v != null));
      return `<tr><th>${t(`kr.pk.row.${key}`)}</th>${vals.map((v) => `<td class="${v === best && vals.filter((x) => x != null).length > 1 ? 'win' : ''}">${f(v)}</td>`).join('')}</tr>`;
    }).join('');
    return `<table class="pk-table">${head}${rows}</table>`;
  }
  let pkId = PK[0].id;
  let pkCustom = null; // [key, key]

  // ── 卡片：头条 + 榜单 / PK ──
  let tab = 'rank';
  function card() {
    const tabs = ['rank', 'pk'].map((x) => `<button type="button" role="tab" data-kr-tab="${x}" aria-selected="${x === tab}" class="${x === tab ? 'on' : ''}">${t(`kr.tab.${x}`)}</button>`).join('');
    return `<button class="muni-card-x" type="button" data-act="kr-close" aria-label="${esc(t('close'))}">×</button>
      <div class="muni-name">${t('kr.title')}</div>
      <div class="kr-fact"><span>${facts[factIdx]}</span><button type="button" data-act="kr-fact" title="${esc(t('kr.next'))}">${t('kr.next')} ›</button></div>
      <div class="kr-tabs" role="tablist">${tabs}</div>
      <div class="kr-body">${tab === 'rank' ? rankList() : pkView()}
      <p class="kr-note">${t('kr.note', { year: data.pop_year })}</p></div>`;
  }
  function rankList() {
    const list = (metric === 'rise' ? both.slice().sort((a, b) => rise(b) - rise(a) || rNow.get(a) - rNow.get(b))
      : [...rankOf[metric].keys()]);
    const max = Math.max(...list.map((k) => Math.abs(value(metric, k))));
    return `<ol class="kr-list">${list.map((k, i) => {
      const v = value(metric, k);
      const w = Math.max(2, Math.round((Math.abs(v) / max) * 100));
      const val = metric === 'rise' ? `${t('kr.rise.v', { a: rEdo.get(k), b: rNow.get(k) })} <b class="${v > 0 ? 'up' : v < 0 ? 'down' : ''}">${show('rise', v)}</b>` : show(metric, v);
      return `<li data-k="${esc(k)}" class="${k === focus ? 'on' : ''}"><span class="no">${i + 1}</span><span class="nm">${esc(name(k))}</span>
        <span class="bar"><i style="width:${w}%;background:${color(k)}"></i></span><span class="val">${val}</span></li>`;
    }).join('')}</ol>`;
  }
  function pkView() {
    const chips = PK.map((p) => `<button type="button" data-pk="${p.id}" class="${!pkCustom && p.id === pkId ? 'on' : ''}">${t(`kr.pk.${p.id}`)}</button>`).join('');
    const opts = (sel) => keys.filter((k) => !outside(k)).sort((a, b) => (props.get(a).kana || '').localeCompare(props.get(b).kana || ''))
      .map((k) => `<option value="${esc(k)}" ${k === sel ? 'selected' : ''}>${esc(name(k))}</option>`).join('');
    const [a, b] = pkCustom || ['武蔵国', '摂津国'];
    const sides = pkCustom ? pkCustom.map((k) => ({ provs: [k] })) : PK.find((p) => p.id === pkId).sides;
    return `<div class="kr-pk-chips">${chips}</div>
      <div class="kr-pk-pick"><select data-pk-side="0" aria-label="${esc(t('kr.pk.a'))}">${opts(a)}</select><span>VS</span><select data-pk-side="1" aria-label="${esc(t('kr.pk.b'))}">${opts(b)}</select></div>
      ${pkTable(sides)}`;
  }

  return {
    get metric() { return metric; },
    setMetric(m) { metric = METRICS.includes(m) ? m : 'pop'; },
    get focus() { return focus; },
    setFocus(k) { focus = k; },
    color, legend, tip, card, name,
    // 卡片里的点击；返回 true 表示需要重绘卡片
    handle(e) {
      const tb = e.target.closest('[data-kr-tab]');
      if (tb) { tab = tb.dataset.krTab; return true; }
      if (e.target.closest('[data-act="kr-fact"]')) { factIdx = (factIdx + 1) % facts.length; return true; }
      const pk = e.target.closest('[data-pk]');
      if (pk) { pkId = pk.dataset.pk; pkCustom = null; return true; }
      return false;
    },
    pick(sel) {
      const cur = pkCustom || ['武蔵国', '摂津国'];
      cur[+sel.dataset.pkSide] = sel.value;
      pkCustom = [...cur];
    },
  };
}
