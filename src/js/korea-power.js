// 半岛国力：今天的 29 区 × 1432 年《世宗实录·地理志》的户、口、垦田（tools/fetch_sejong.py 汇总成 power.json）。
// 与日本的古国国力（kokuryoku.js）同一套玩法：指标着色、由数字算出的头条、榜单、对决；文字键用 kp.*。
// 1432 年的数字是当时的户籍登记：口数漏记很多（官方自己也说「十不录一二」），户数相对可比；汉城府只记户数。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export const KP_METRICS = ['pop', 'hh', 'kyol', 'density', 'rise'];
const RAMP = ['#2a3a3a', '#3f6b5f', '#8f8a62', '#d4a373', '#e2573a'];
const RISE = [[8, '#e2573a'], [3, '#d99a6c'], [-2, '#56605c'], [-7, '#6f8fb8'], [-Infinity, '#3f63b0']];
// 对决预设：同一个道分成南北两半的，两个江原道，两座首都
export const KP_PK = [
  ['gyeongsang', 14, 15], ['jeolla', 12, 13], ['chungcheong', 10, 11], ['gangwon', 9, 26],
  ['hwanghae', 24, 25], ['pyeongan', 21, 22], ['hamgyeong', 27, 28], ['capitals', 1, 17],
];

const fmt = (n, d = 0) => n.toLocaleString(lang === 'zh' ? 'zh-CN' : lang, { maximumFractionDigits: d });
function people(n) {
  if (n == null) return '—';
  if (lang === 'en') return n >= 1e6 ? `${fmt(n / 1e6, n < 1e7 ? 2 : 1)}M` : n >= 1e4 ? `${fmt(n / 1e3)}K` : fmt(n);
  return n >= 1e4 ? t('kp.wan', { n: fmt(n / 1e4, n < 1e5 ? 1 : 0) }) : fmt(n);
}
const hhs = (n) => (n == null ? '—' : t('kp.hh.v', { n: fmt(n) }));
const kyols = (n) => (n == null ? '—' : t('kp.kyol.v', { n: fmt(n) }));

// regions：Map(id → regions.json 的 properties)；nameOf：当前语言的区名
export function createKoreaPower(data, regions, nameOf) {
  const R = data.regions;
  const keys = [...regions.keys()].filter((id) => R[id]);
  const P = (id) => regions.get(id);
  const raw = {
    pop: (id) => P(id).pop,
    hh: (id) => R[id].hh,
    kyol: (id) => R[id].kyol,
    density: (id) => P(id).pop / P(id).area,
  };
  const rankOf = {};
  for (const m of Object.keys(raw)) {
    const list = keys.filter((id) => raw[m](id) != null).sort((a, b) => raw[m](b) - raw[m](a));
    rankOf[m] = new Map(list.map((id, i) => [id, i + 1]));
  }
  // 逆袭：1432 年户数排名 → 今天人口排名
  const rise = (id) => rankOf.hh.get(id) - rankOf.pop.get(id);
  const value = (m, id) => (m === 'rise' ? rise(id) : raw[m](id));
  const name = (id) => nameOf(P(id));

  let metric = 'hh';
  let focus = null;
  let tab = 'rank';
  let pk = KP_PK[0][0];
  let custom = null;

  function color(id) {
    if (!R[id]) return null; // 罗先：1432 年没有郡县落在这里
    const v = value(metric, id);
    if (v == null) return null;
    if (metric === 'rise') return RISE.find(([min]) => v >= min)[1];
    const r = rankOf[metric].get(id);
    return RAMP[RAMP.length - 1 - Math.min(RAMP.length - 1, Math.floor(((r - 1) * RAMP.length) / rankOf[metric].size))];
  }
  function show(m, v) {
    if (v == null) return '—';
    if (m === 'pop') return people(v);
    if (m === 'hh') return hhs(v);
    if (m === 'kyol') return kyols(v);
    if (m === 'density') return t('kp.density.v', { n: fmt(v) });
    return v > 0 ? `▲${v}` : v < 0 ? `▼${-v}` : '—';
  }
  function legend() {
    const items = metric === 'rise'
      ? [['kp.rise.up2', 0], ['kp.rise.up', 1], ['kp.rise.flat', 2], ['kp.rise.down', 3], ['kp.rise.down2', 4]]
        .map(([k, i]) => [t(k), RISE[i][1], keys.filter((id) => color(id) === RISE[i][1]).length]).filter((x) => x[2])
      : RAMP.map((c) => {
        const vals = keys.filter((id) => color(id) === c).map((id) => value(metric, id));
        return vals.length ? [`${show(metric, Math.min(...vals))} – ${show(metric, Math.max(...vals))}`, c, vals.length] : null;
      }).filter(Boolean).reverse();
    return { caption: t(`kp.cap.${metric}`), items };
  }
  function tip(id) {
    const r = R[id];
    if (!r) return '';
    const row = (m) => `${t(`kp.m.${m}`)}：${show(m, value(m, id))}${rankOf[m]?.get(id) ? ` <span style="color:#8a847a">${t('kp.rank', { n: rankOf[m].get(id) })}</span>` : ''}`;
    return [row('pop'), row('hh'), `${t('kp.m.kou')}：${r.pop == null ? t('kp.kou.none') : people(r.pop)}`, row('kyol'),
      `${t('kp.m.rise')}：${t('kp.rise.v', { a: rankOf.hh.get(id), b: rankOf.pop.get(id) })}`].join('<br>');
  }

  // ── 头条：全部由数字算出 ──
  function headlines() {
    const out = [];
    const byPop = keys.slice().sort((a, b) => P(b).pop - P(a).pop);
    const total = keys.reduce((s, id) => s + P(id).pop, 0);
    const top = byPop[0];
    let n = 0;
    for (let s = 0, i = byPop.length - 1; i > 0 && s + P(byPop[i]).pop < P(top).pop; i--) { s += P(byPop[i]).pop; n += 1; }
    out.push(t('kp.h.top', { a: name(top), pct: Math.round((P(top).pop / total) * 100), n }));
    const hhTop = [...rankOf.hh.keys()][0];
    const hhTotal = keys.reduce((s, id) => s + R[id].hh, 0);
    out.push(t('kp.h.hh', { a: name(hhTop), hh: hhs(R[hhTop].hh), pct: Math.round((R[hhTop].hh / hhTotal) * 100), y: rankOf.pop.get(hhTop) }));
    const order = keys.slice().sort((a, b) => rise(b) - rise(a));
    const up = order[0];
    const down = order[order.length - 1];
    out.push(t('kp.h.up', { a: name(up), x: rankOf.hh.get(up), y: rankOf.pop.get(up) }));
    out.push(t('kp.h.down', { a: name(down), x: rankOf.hh.get(down), y: rankOf.pop.get(down) }));
    const kyolTop = [...rankOf.kyol.keys()][0];
    out.push(t('kp.h.kyol', { a: name(kyolTop), k: kyols(R[kyolTop].kyol), y: rankOf.pop.get(kyolTop) }));
    if (R[1]) out.push(t('kp.h.capital', { hh: hhs(R[1].hh), pop: people(P(1).pop) }));
    const per = keys.slice().sort((a, b) => P(b).pop / R[b].hh - P(a).pop / R[a].hh);
    out.push(t('kp.h.per', { a: name(per[0]), x: fmt(P(per[0]).pop / R[per[0]].hh), b: name(per[per.length - 1]), y: fmt(P(per[per.length - 1]).pop / R[per[per.length - 1]].hh) }));
    return out;
  }
  const facts = headlines();
  let factIdx = 0;

  // ── 对决 ──
  const PK_ROWS = [
    ['pop', (id) => P(id).pop, people], ['hh', (id) => R[id].hh, hhs], ['kou', (id) => R[id].pop, people],
    ['per', (id) => P(id).pop / R[id].hh, (v) => (v == null ? '—' : `×${fmt(v)}`)], ['kyol', (id) => R[id].kyol, kyols],
    ['area', (id) => P(id).area, (v) => `${fmt(v)} km²`], ['density', (id) => P(id).pop / P(id).area, (v) => t('kp.density.v', { n: fmt(v) })],
    ['n', (id) => R[id].n, (v) => fmt(v)],
  ];
  function pkTable(ids) {
    const head = `<tr><th></th>${ids.map((id) => `<th>${esc(name(id))}</th>`).join('')}</tr>`;
    const rows = PK_ROWS.map(([k, get, f]) => {
      const vals = ids.map((id) => get(id) ?? null);
      const real = vals.filter((v) => v != null);
      const best = Math.max(...real);
      return `<tr><th>${t(`kp.pk.row.${k}`)}</th>${vals.map((v) => `<td class="${real.length > 1 && v === best ? 'win' : ''}">${v == null ? '—' : f(v)}</td>`).join('')}</tr>`;
    }).join('');
    return `<table class="pk-table">${head}${rows}</table>`;
  }
  function pkView() {
    const chips = KP_PK.map(([k]) => `<button type="button" data-pk="${k}" class="${!custom && k === pk ? 'on' : ''}">${t(`kp.pk.${k}`)}</button>`).join('');
    const ids = custom || KP_PK.find(([k]) => k === pk).slice(1);
    const opts = (sel) => keys.map((id) => `<option value="${id}" ${id === sel ? 'selected' : ''}>${esc(name(id))}</option>`).join('');
    return `<div class="kr-pk-chips">${chips}</div>
      <div class="kr-pk-pick"><select data-pk-side="0" aria-label="${esc(t('kr.pk.a'))}">${opts(ids[0])}</select><span>VS</span><select data-pk-side="1" aria-label="${esc(t('kr.pk.b'))}">${opts(ids[1])}</select></div>
      ${pkTable(ids)}`;
  }
  function rankList() {
    const list = metric === 'rise' ? keys.slice().sort((a, b) => rise(b) - rise(a) || rankOf.pop.get(a) - rankOf.pop.get(b)) : [...rankOf[metric].keys()];
    const max = Math.max(...list.map((id) => Math.abs(value(metric, id))));
    return `<ol class="kr-list">${list.map((id, i) => {
      const v = value(metric, id);
      const w = Math.max(2, Math.round((Math.abs(v) / max) * 100));
      const val = metric === 'rise' ? `${t('kp.rise.v', { a: rankOf.hh.get(id), b: rankOf.pop.get(id) })} <b class="${v > 0 ? 'up' : v < 0 ? 'down' : ''}">${show('rise', v)}</b>` : show(metric, v);
      return `<li data-k="${id}" class="${id === focus ? 'on' : ''}"><span class="no">${i + 1}</span><span class="nm">${esc(name(id))}</span>
        <span class="bar"><i style="width:${w}%;background:${color(id)}"></i></span><span class="val">${val}</span></li>`;
    }).join('')}</ol>`;
  }
  function card() {
    const tabs = ['rank', 'pk'].map((x) => `<button type="button" role="tab" data-kr-tab="${x}" aria-selected="${x === tab}" class="${x === tab ? 'on' : ''}">${t(`kp.tab.${x}`)}</button>`).join('');
    const metrics = KP_METRICS.map((m) => `<button type="button" data-kp-metric="${m}" class="${m === metric ? 'on' : ''}">${t(`kp.m.${m}`)}</button>`).join('');
    return `<button class="muni-card-x" type="button" data-act="kp-close" aria-label="${esc(t('close'))}">×</button>
      <div class="muni-name">${t('kp.title')}</div>
      <div class="kr-fact"><span>${facts[factIdx]}</span><button type="button" data-act="kr-fact">${t('kr.next')} ›</button></div>
      <div class="kp-metrics" role="group" aria-label="${esc(t('kr.metrics'))}">${metrics}</div>
      <div class="kr-tabs" role="tablist">${tabs}</div>
      <div class="kr-body">${tab === 'rank' ? rankList() : pkView()}
      <p class="kr-note">${t('kp.note')}</p></div>`;
  }

  return {
    get metric() { return metric; },
    get focus() { return focus; },
    setFocus(id) { focus = id; },
    color, legend, tip, card,
    // 卡片里的点击；返回 true 表示要重画卡片（换了指标还要重新着色：metricChanged）
    handle(e) {
      const m = e.target.closest('[data-kp-metric]');
      if (m) { metric = m.dataset.kpMetric; return true; }
      const tb = e.target.closest('[data-kr-tab]');
      if (tb) { tab = tb.dataset.krTab; return true; }
      if (e.target.closest('[data-act="kr-fact"]')) { factIdx = (factIdx + 1) % facts.length; return true; }
      const p = e.target.closest('[data-pk]');
      if (p) { pk = p.dataset.pk; custom = null; return true; }
      return false;
    },
    pick(sel) {
      const cur = custom || KP_PK.find(([k]) => k === pk).slice(1);
      cur[+sel.dataset.pkSide] = Number(sel.value);
      custom = [...cur];
    },
  };
}
