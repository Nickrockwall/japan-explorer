// 立体图的卡片（3.36 从 app.js 拆出）：国（战国 / 镰仓 / 古代）、藩与府县、势力总览、人物、城、城柵、宿场、浮世绘、天下
// 会变的状态（当前的块、上色方式、选中的东西、聚光的家）都在 app 的 S 里；其余是 app 给的数据与函数
import * as THREE from 'three';
import { lang, t, nm, circuit } from './i18n.js';
import { YEARS, eraOf, capitalOf } from './eras.js';

export function createCards(S, ctx) {
  const {
    opts, sg, kama, bios, sites, rulers, people, camera, controls, P, LOOSE, KAMA_LOOSE,
    esc, sw, info, entry, provName, regionName, castleName, circuitOf, siteOn, regionAt, prints, regimeOf, rulerOf, shogunOf,
    flatLink, syncBack, syncHash, applyStyle, flyTo, camDist, userYear,
    holderAt, castleOnIn, eraReady, loadEra, lookFrom,
  } = ctx;
  const card = document.querySelector('#card');
  const person = (ja) => nm(people[ja]) || ja;
  function openCard(html) {
    card.innerHTML = `<button class="x" type="button" aria-label="${t('close')}">×</button>${html}`;
    card.hidden = false;
    document.body.classList.add('card-open');
    card.querySelector('.x').onclick = closeCard;
    syncBack();
  }
  function closeCard() {
    card.hidden = true;
    S.focused = null;
    document.body.classList.remove('card-open');
    if (S.spot) { S.spot = null; applyStyle(); }
    syncBack();
    syncHash();
  }
  const wikiOf = (ja, qid) => (qid ? `https://www.wikidata.org/wiki/Special:GoToLinkedPage/jawiki/${qid}` : `https://ja.wikipedia.org/wiki/${encodeURIComponent(ja)}`);
  // 人物卡：sengoku.json 的生卒 + people.json 的自写简介与肖像（有的人才有）；从哪张卡来就能回哪张
  function showPerson(ja, back) {
    const p = people[ja] || {}, b = bios[ja];
    S.focused = { type: 'person', ja };
    openCard(`${back ? `<button class="back" type="button">${t('p.back')}</button>` : ''}
      ${b?.img ? `<img class="portrait" src="${b.img}" alt="">` : ''}
      <h2>${esc(person(ja))}</h2>
      <p class="sub">${esc(t('p.life', { a: p.born ?? '?', b: p.died ?? '?' }))}</p>
      ${b?.bio ? `<p>${esc(b.bio[lang] || b.bio.zh)}</p>` : ''}
      ${b?.img ? `<p class="note">${esc(t('p.img', { l: [b.license, b.author].filter(Boolean).join(' · ') }))}</p>` : ''}
      <p class="links"><a href="${wikiOf(ja, p.qid)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    card.querySelector('.back')?.addEventListener('click', back);
  }
  // 每家当年的推算石高（分治按家数平分）；领有奥羽按郡分区（没有石高）的记 missing
  function clanKoku(year) {
    const sum = new Map(), missing = new Set();
    for (const r of S.regions) {
      const e = entry(r.key, year);
      if (!e) continue;
      const cs = [e.c, ...(e.with || [])];
      const k = sg.koku?.[r.key];
      for (const c of cs) {
        if (k == null) missing.add(c);
        else sum.set(c, (sum.get(c) || 0) + k / cs.length);
      }
    }
    return { sum, missing };
  }
  const flyRegion = (r) => flyTo(r.center[0], r.center[1], THREE.MathUtils.clamp(Math.sqrt(r.area) * 3, 120, 700));
  const provButtons = (rs) => `<div class="provs">${rs.map((r) => `<button type="button" data-k="${esc(r.key)}">${esc(S.mode.blocks ? regionName(r) : provName(r.key, true))}</button>`).join('')}</div>`;
  const bindProvButtons = () => card.querySelectorAll('.provs button').forEach((b) => { b.onclick = () => { const r = S.byKey.get(b.dataset.k); showRegion(r); flyRegion(r); }; });
  // 势力总览：图例里点一家（或搜索）——聚光它的领国，列出国数 / 推算石高 / 名次 / 代表人物 / 各国；镰仓是守护的家、古代是道
  function showClan(c, fly = true) {
    const own = [], shared = [];
    for (const r of S.regions) {
      const e = entry(r.key);
      if (!e) continue;
      const cs = [e.c, ...(e.with || [])];
      if (cs.includes(c)) (cs.length > 1 ? shared : own).push(r);
    }
    if (!own.length && !shared.length) { closeCard(); return; }
    S.spot = c;
    applyStyle();
    S.focused = { type: 'clan', c };
    const ci = info(c);
    const era = eraOf(opts.year);
    if (era === 'sengoku') {
      const { sum, missing } = clanKoku(opts.year);
      const man = (v) => (lang === 'en' ? (Math.round(v / 1000) * 1000).toLocaleString('en') : Math.round(v / 10000));
      const mine = sum.get(c) || 0;
      const rank = missing.has(c) || LOOSE.has(c) ? 0 : 1 + [...sum].filter(([k, v]) => !LOOSE.has(k) && !missing.has(k) && v > mine).length;
      const head = sg.heads[opts.year]?.[c];
      const mon = sg.clans[c]?.mon ? `<img class="mon-img" src="src/assets/crests/${c}.png" alt="">` : sw(c);
      openCard(`<h2>${mon}${esc(nm(ci))}</h2>
        <p class="sub">${opts.year} · ${esc(t('c.provs', { n: own.length }))}${shared.length ? ` · ${esc(t('c.split', { n: shared.length }))}` : ''}</p>
        ${mine ? `<p>${esc(t(missing.has(c) ? 'c.kokuGe' : 'c.koku', { n: man(mine) }))}${rank ? ` · ${esc(t('c.rank', { n: rank }))}` : ''}</p>` : ''}
        ${head ? `<p>${esc(t('c.head'))}：<span class="who" data-person="${esc(head)}">${esc(person(head))}</span></p>` : ''}
        ${provButtons([...own, ...shared])}
        <p class="note">${esc(t('c.note'))}</p>`);
      card.querySelector('[data-person]')?.addEventListener('click', (e) => showPerson(e.target.dataset.person, () => showClan(c, false)));
    } else if (era === 'kamakura') {
      const mon = S.mode.hasMon(c) ? `<img class="mon-img" src="src/assets/crests/${c}.png" alt="">` : sw(c);
      const who = own.map((r) => entry(r.key)?.who).filter(Boolean).map((w) => (lang === 'zh' ? w[1] : w[0]));
      openCard(`<h2>${mon}${esc(nm(ci))}</h2>
        <p class="sub">${opts.year} · ${esc(t('k.provs', { n: own.length }))}</p>
        ${who.length ? `<p>${esc(t('k.who'))}：${esc([...new Set(who)].join(lang === 'en' ? ', ' : '、'))}</p>` : ''}
        ${provButtons(own)}
        <p class="note">${esc(t(KAMA_LOOSE.has(c) ? 'k.looseNote' : 'k.note'))}</p>
        ${ci.wiki ? `<p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(ci.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>` : ''}`);
    } else {
      openCard(`<h2>${sw(c)}${esc(nm(ci))}</h2>
        <p class="sub">${opts.year} · ${esc(t('c.provs', { n: own.length }))}</p>
        ${provButtons(own)}
        <p class="note">${esc(t('kd.circuitNote'))}</p>`);
    }
    bindProvButtons();
    if (fly) {
      const a = S.anchors.find((x) => x.c === c);
      const r = a || { at: (own[0] || shared[0]).center, area: (own[0] || shared[0]).area };
      flyTo(r.at[0], r.at[1], THREE.MathUtils.clamp(Math.sqrt(a ? a.area : r.area) * 2.4, 140, 900));
    }
  }
  const sitesIn = (key) => sites.filter((s) => s.prov === key);
  function showRegion(r) {
    if (!r) return;
    S.focused = { type: 'region', key: r.key };
    const era = eraOf(opts.year);
    if (era === 'sengoku') showSengokuRegion(r);
    else if (era === 'kamakura') showKamakuraRegion(r);
    else if (era === 'kodai') showKodaiRegion(r);
    else showBlock(r);
    syncHash();
  }
  function showSengokuRegion(r) {
    const rows = sg.years.map((y) => {
      const e = (sg.units?.[r.key] || sg.provinces[r.key])?.[y];
      if (!e) return '';
      const cs = [e.c, ...(e.with || [])];
      const head = sg.heads[y]?.[e.c];
      return `<tr class="${y === opts.year ? 'cur' : ''}" data-y="${y}"><th>${y}</th><td>${cs.map((c) => `${sw(c)}${esc(nm(info(c)))}`).join(lang === 'en' ? ', ' : '、')}${e.with ? `<em>${t('split')}</em>` : ''}${head ? `<span class="who" data-person="${esc(head)}">${esc(person(head))}</span>` : ''}</td></tr>`;
    }).join('');
    const koku = sg.koku?.[r.key];
    const parent = r.props.parent ? t('part', { p: provName(r.props.parent) }) : '';
    const n = lang === 'en' ? Math.round(koku / 1000) * 1000 : Math.round(koku / 10000);
    openCard(`<h2>${esc(nm(r.props) || r.key)}${esc(parent)}</h2>
      <p class="sub">${esc(circuit(r.props.circuit || ''))}${koku ? esc(t('koku', { n: n.toLocaleString('en') })) : ''}</p>
      <table class="yrs">${rows}</table>
      <p class="links"><a href="${flatLink(r.key)}">${t('flat')}</a></p>`);
    card.querySelectorAll('tr[data-y]').forEach((tr) => { tr.onclick = (e) => { if (!e.target.closest('[data-person]')) userYear(tr.dataset.y); }; });
    card.querySelectorAll('[data-person]').forEach((el) => { el.onclick = () => showPerson(el.dataset.person, () => showRegion(r)); });
  }
  function showKamakuraRegion(r) {
    const fam = (c) => kama.families[c] || kama.families.unknown;
    const rows = kama.years.map((y) => {
      const e = kama.provinces[r.key]?.[y];
      if (!e) return '';
      const who = e.who ? (lang === 'zh' ? e.who[1] : e.who[0]) : '';
      const sub = who ? `${esc(who)}${e.from ? ` · ${esc(t('k.from', { y: e.from }))}` : ''}` : e.gap ? esc(t('k.gap')) : '';
      return `<tr class="${y === opts.year ? 'cur' : ''}" data-y="${y}"><th>${y}</th><td><i class="sw" style="background:${fam(e.c).color}"></i>${esc(nm(fam(e.c)))}${sub ? `<span class="who">${sub}</span>` : ''}</td></tr>`;
    }).join('');
    openCard(`<h2>${esc(provName(r.key))}</h2>
      <p class="sub">${esc(circuit(r.props.circuit || ''))} · ${esc(t('k.sub'))}</p>
      ${rows ? `<table class="yrs">${rows}</table>` : `<p>${esc(t('k.none'))}</p>`}
      <p class="note">${esc(t('k.note'))}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(r.key)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    card.querySelectorAll('tr[data-y]').forEach((tr) => { tr.onclick = () => userYear(tr.dataset.y); });
  }
  function showKodaiRegion(r) {
    const c = circuitOf(r.key, opts.year);
    const ss = sitesIn(r.key).filter(siteOn);
    const list = ss.map((s) => `<li><small>${esc(t(s.kind))}</small> ${esc(s.name)}</li>`).join('');
    openCard(`<h2>${esc(provName(r.key))}</h2>
      <p class="sub">${opts.year} · ${sw(c)}${esc(circuit(c))}</p>
      ${list ? `<ul class="plain">${list}</ul>` : ''}
      ${r.key === '武蔵国' ? `<p class="note">${esc(t('kd.musashi'))}</p>` : ''}
      <p class="note">${esc(t('kd.note', { y: opts.year }))}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(r.key)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
  }
  // 江户的藩领、明治的府县
  function showBlock(r) {
    const p = r.props, y = opts.year;
    const man = (v) => (lang === 'en' ? `${Math.round(v / 1000).toLocaleString('en')}k` : Math.round(v / 10000).toLocaleString('en'));
    let body = '';
    if (S.base.name === 'edo') {
      const kindName = t(`e.kind.${p.kind}`);
      if (y === '1871') {
        body = `<p class="sub">1871 · ${esc(t('m.haihan'))}</p>
          ${p.kind === 'han' ? `<p>${esc(t('m.from', { h: nm(p) }))}</p>` : `<p>${esc(kindName)}</p>`}
          <p class="note">${esc(t(p.ken ? 'm.kenNote' : 'm.noKen'))}</p>`;
      } else {
        body = `<p class="sub">${esc(t('e.sub'))} · ${esc(kindName)}</p>
          ${p.koku ? `<p>${esc(t('e.koku', { n: man(p.koku) }))}</p>` : ''}
          ${p.seat ? `<p>${esc(t('e.seat'))}：${esc(p.seat)}</p>` : ''}
          ${p.lord ? `<p>${esc(t('e.lord'))}：${esc(lang === 'en' ? p.lord[2] || p.lord[0] : lang === 'zh' ? p.lord[1] : p.lord[0])}</p>` : ''}
          ${p.ken ? `<p>${esc(t('e.ken'))}：${esc(nm({ ja: p.ken[0], zh: p.ken[1], en: p.ken[2] || p.ken[0] }))}</p>` : ''}
          <p class="note">${esc(t('e.note'))}</p>`;
      }
      if (p.kind === 'han') body += `<p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(p.ja)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`;
    } else {
      const today = (p.today || []).map((x) => (lang === 'en' ? x[2] : lang === 'zh' ? x[1] : x[0]));
      body = `<p class="sub">${y} · ${esc(t(`m.cap.${y}`))}</p>
        ${today.length ? `<p>${esc(t('m.today'))}：${esc(today.join(lang === 'en' ? ', ' : '、'))}</p>` : ''}
        <p class="note">${esc(t('m.note'))}</p>
        <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(p.ja)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`;
    }
    openCard(`<h2>${sw(r.key)}${esc(regionName(r))}</h2>${body}`);
  }
  // 城所在的块在当前年份归谁（分治列出各家）
  // 城的一生（3.37）：这座城在立体图的每个年份（古代不画城）所在的那块归谁，前后相同的并成一段；点一段换到那一年。
  // 江户、明治的资料还没下载的先不列，下载完再刷新这张卡片（还开着的话）
  function lifeHTML(c) {
    const ys = YEARS.filter((y) => eraOf(y) !== 'kodai' && castleOnIn(c, y));
    const wait = ys.filter((y) => !eraReady(y));
    if (wait.length) {
      Promise.all(wait.map(loadEra)).then(() => {
        if (S.focused?.type === 'castle' && S.focused.q === c.q && !card.hidden) showCastle(c, false);
      }).catch(() => {});
    }
    const runs = [];
    for (const y of ys) {
      const h = holderAt(c.xz[0], c.xz[1], y);
      if (!h) continue;
      const id = h.map((x) => x.name).join('|');
      const last = runs[runs.length - 1];
      if (last && last.id === id && YEARS.indexOf(y) === YEARS.indexOf(last.ys[last.ys.length - 1]) + 1) last.ys.push(y);
      else runs.push({ id, h, ys: [y] });
    }
    if (!runs.length) return '';
    const rows = runs.map((r) => {
      const span = r.ys.length > 1 ? `${r.ys[0]}–${r.ys[r.ys.length - 1]}` : r.ys[0];
      const who = r.h.length ? r.h.map((x) => `<i class="sw" style="background:${x.color}"></i>${esc(x.name)}`).join(lang === 'en' ? ', ' : '、') : esc(t('life.none'));
      return `<tr class="${r.ys.includes(opts.year) ? 'cur' : ''}" data-y="${r.ys.includes(opts.year) ? opts.year : r.ys[0]}"><th>${span}</th><td>${who}</td></tr>`;
    }).join('');
    return `<h3 class="life-h">${esc(t('life.h'))}</h3><table class="yrs life">${rows}</table>${wait.length ? `<p class="note">${esc(t('life.loading'))}</p>` : ''}<p class="note">${esc(t('life.note'))}</p>`;
  }
  // 100名城 / 续 100 名城的编号、现存天守（castle_extra_tool.py，3.36）
  function meijoHTML(c) {
    const rows = [c.tenshu && `<p class="meijo k">${esc(t(`tenshu.${c.tenshu}`))}</p>`, c.h100 && t('h100', { n: c.h100 }), c.z100 && t('z100', { n: c.z100 })].filter(Boolean);
    if (!rows.length) return '';
    return rows.map((r) => (r.startsWith('<') ? r : `<p class="meijo">${esc(r)}</p>`)).join('') + `<p class="note">${esc(t('meijoNote'))}</p>`;
  }
  function showCastle(c, fly = true) {
    S.focused = { type: 'castle', q: c.q };
    openCard(`<h2>${esc(castleName(c))}</h2>
      <p class="sub">${esc(provName(c.prov))} · ${t('castle')}</p>
      <p>${c.bc ? esc(t('bc', { c: c.bc })) : t(c.ba ? 'ba' : 'built', { y: c.built })}${c.gone ? t('gone', { y: c.gone }) : ''}</p>
      ${meijoHTML(c)}
      <p><button type="button" class="look-btn">${esc(t(+opts.year >= 1576 ? 'look.tenshu' : 'look.yagura'))}</button></p>
      ${lifeHTML(c)}
      <p class="note">${t(+opts.year >= 1576 ? 'late' : 'early')}${t('castleNote')}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(c.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    card.querySelectorAll('.life tr[data-y]').forEach((tr) => { tr.onclick = () => userYear(tr.dataset.y); });
    card.querySelector('.look-btn').onclick = () => lookFrom(c);
    if (fly) flyTo(c.xz[0], c.xz[1], Math.min(camera.position.distanceTo(controls.target), 60));
  }
  function showFort(f) {
    S.focused = { type: 'fort', ja: f.ja };
    openCard(`<h2>${esc(nm(f))}</h2>
      <p class="sub">${esc(t('fort'))}${f.built ? ` · ${esc(t('built', { y: f.built }))}` : ''}${f.gone ? esc(t('gone', { y: f.gone })) : ''}</p>
      <p class="note">${esc(t('fortNote'))}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(f.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    flyTo(f.xz[0], f.xz[1], Math.min(camDist(), 80));
  }
  function showStation(s) {
    S.focused = { type: 'inn', ja: s.ja };
    openCard(`<h2>${esc(nm(s))}</h2>
      <p class="sub">${esc(nm(s.road))} · ${esc(t('inn'))}</p>
      <p class="note">${esc(t('innNote'))}</p>
      <p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(s.ja)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>`);
    flyTo(s.xz[0], s.xz[1], Math.min(camDist(), 40));
  }
  function showPrint(no) {
    const h = prints().find((x) => x.no === +no);
    if (!h) return;
    S.focused = { type: 'print', no: h.no };
    const title = lang === 'zh' ? h.title_zh : lang === 'en' ? h.title_en : h.title;
    openCard(`<h2>${esc(title)}</h2>
      <p class="sub">${esc(provName(h.province))} · ${esc(t('pr.series'))}</p>
      <img class="print-big" src="${h.img}" alt="">
      <p class="note">${esc(t('pr.note'))}</p>
      <p class="links"><a href="${h.source}" target="_blank" rel="noopener">Wikimedia Commons</a></p>`);
    const [x, z] = P(...h.coords);
    flyTo(x, z, Math.min(camDist(), 120));
  }
  function showCapital() {
    const y = opts.year, rg = regimeOf(y);
    const emp = rulerOf(rulers.emperors, y), sho = shogunOf(y);
    const shikken = eraOf(y) === 'kamakura' ? rulerOf(rulers.shikken, y) : null;
    const cap = capitalOf(y);
    S.focused = { type: 'capital' };
    const row = (k, v) => (v ? `<tr><th>${esc(t(k))}</th><td>${esc(v)}</td></tr>` : '');
    openCard(`<h2>${esc(t('cap.title', { y }))}</h2>
      <p class="sub">${esc(t(`cap.name.${cap.key}`))} · ${esc(t('cap.sub2'))}</p>
      <table class="kv">${row('cap.emp', nm(emp))}${row('cap.shogun', sho ? nm(sho) : '')}${row('cap.shikken', shikken ? nm(shikken) : '')}${row('cap.nominal', nm(rg?.nominal))}${row('cap.real', nm(rg?.real))}${row('cap.seat', nm(rg?.seat))}</table>
      ${rg?.note ? `<p class="note">${esc(nm(rg.note))}</p>` : ''}
      <p class="note">${esc(t(+y < 794 ? 'heijoNote' : +y < 1869 ? 'heianNote' : 'tokyoNote'))}</p>
      <p class="links"><a href="index.html#rl=power&lang=${lang}">${esc(t('cap.more'))}</a></p>`);
    const [x, z] = P(...cap.at);
    flyTo(x, z, Math.min(camDist(), 90));
  }

  function showSite(s) {
    S.focused = { type: 'site', id: s.id };
    openCard(`<h2>${esc(s.name)}</h2>
      <p class="sub">${esc(provName(s.prov))} · ${t(s.kind)}${s.precise ? '' : t('muni')}</p>
      <p class="note">${t('siteNote')}</p>
      ${s.wiki ? `<p class="links"><a href="https://ja.wikipedia.org/wiki/${encodeURIComponent(s.wiki)}" target="_blank" rel="noopener">${t('jawiki')}</a></p>` : ''}`);
    flyTo(s.xz[0], s.xz[1], Math.min(camera.position.distanceTo(controls.target), 40));
  }

  return { closeCard, showPerson, showClan, showRegion, showCastle, showFort, showStation, showPrint, showCapital, showSite, flyRegion };
}
