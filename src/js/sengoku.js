// 战国势力图：68 国 × 6 个年份（1467 / 1560 / 1573 / 1582 / 1590 / 1600），着色、提示、图例、国别卡片与人物简卡。
// 数据 src/data/sengoku.json 由 tools/sengoku_tool.py 生成并核对；1600 年按关原之战的站队（sides）着色。
// 人物：sengoku.json 的 people（各年份代表人物）+ rulers.json（天皇 · 将军 · 执权）+ people.json（详写：简介、肖像、家纹、相关人物）
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { crestSVG } from './crests.js';

const OUTSIDE = '#33333a';
const DIM = [24, 24, 28]; // 聚光时压暗到底色 #18181c
// 总称（国人割据、多方争夺、丰臣直辖与中小大名、奥羽诸氏；1600 年的倒戈 / 分裂 / 观望）不是一家：不合并国界、不出势力总览
const LOOSE = new Set(['gunyu', 'contest', 'toyo_small', 'ou', 'outside', 'turn', 'split', 'neutral']);
const mix = (hex, f) => {
  const n = parseInt(hex.slice(1), 16);
  const ch = [n >> 16, (n >> 8) & 255, n & 255].map((v, i) => Math.round(v + (DIM[i] - v) * f));
  return `rgb(${ch.join(',')})`;
};

// 维基百科链接：日文直接用条目名，其他语言经 Wikidata 跳到该语言的条目
export function wikiLink(title, qid) {
  if (lang === 'ja' || !qid) return `https://ja.wikipedia.org/wiki/${encodeURIComponent(title)}`;
  return `https://www.wikidata.org/wiki/Special:GoToLinkedPage/${lang}wiki/${qid}`;
}

// 天皇 · 将军 · 执权按条目名索引：{ ja, zh, en, qid, roles: [[职位键, 代数, 起, 止]] }
function rulerIndex(rulers) {
  const out = {};
  const add = (r, role) => {
    const p = (out[r.wiki] ??= { ja: r.ja, zh: r.zh, en: r.en, qid: r.qid, roles: [] });
    p.roles.push([role, r.n, r.from, r.to]);
  };
  for (const r of rulers?.emperors || []) add(r, 'emperor');
  for (const r of rulers?.shoguns || []) add(r, `shogun.${r.bakufu}`);
  for (const r of rulers?.shikken || []) add(r, 'shikken');
  return out;
}

export function createSengoku(data, provinces, year = '1560', { rulers = null, bios = {} } = {}) {
  const rulerBy = rulerIndex(rulers);
  const props = new Map(provinces.features.map((f) => [f.properties.key, f.properties]));
  const keys = Object.keys(data.provinces).filter((k) => props.has(k));
  const pick = (o) => o[lang] || o.zh;
  const provName = (k) => {
    const p = props.get(k);
    if (!p?.zh) return t('prov.outside');
    return lang === 'en' ? p.en.replace(/ Province$/, '') : (lang === 'ja' ? p.ja : p.zh);
  };
  let focus = null;
  let person = null; // 卡片里正在看的人物（条目名）
  let clan = null; // 势力总览：所选年份里的一家（CLANS / SIDES 的键）
  let near = new Map(); // 旧国 → 陆上相邻的旧国（map.js 由国界算出后 setAdjacency 传入）

  const entry = (k, y = year) => data.provinces[k]?.[y];
  const group = (y, c) => (y === '1600' ? data.sides[c] : data.clans[c]);
  const isOutside = (k) => !props.get(k)?.zh;
  function baseColor(k) {
    if (isOutside(k)) return OUTSIDE;
    const e = entry(k);
    return e ? group(year, e.c)?.color || OUTSIDE : OUTSIDE;
  }
  // 看某一家的势力总览时：它的国（含分治）原色，相邻的国半暗，其余压暗
  function color(k) {
    const c = baseColor(k);
    if (!clan || share(k, clan) || !c.startsWith('#')) return c;
    return mix(c, [...(near.get(k) || [])].some((n) => share(n, clan)) ? 0.45 : 0.78);
  }
  // 某家在某国占的份额：独占 1，分治按家数平分
  function share(k, c, y = year) {
    const e = entry(k, y);
    if (!e || isOutside(k)) return 0;
    const all = [e.c, ...(e.with || [])];
    return all.includes(c) ? 1 / all.length : 0;
  }
  const clanName = (y, c) => pick(group(y, c));
  const headOf = (y, c) => data.heads[y]?.[c];
  const base = (title) => data.people[title] || rulerBy[title];
  const personName = (title) => (base(title) ? pick(base(title)) : title.replace(/ \(.*\)$/, ''));
  const life = (p) => t('sg.life', { a: p.born ?? '?', b: p.died ?? '?' });

  function legend() {
    const counts = new Map();
    for (const k of keys) {
      if (isOutside(k)) continue;
      const c = entry(k).c;
      counts.set(c, (counts.get(c) || 0) + 1);
    }
    // 只占一国的家太多（1560 年有二十来家），图例里合成一项，地图提示里仍有各家的名字
    const sorted = [...counts].sort((a, b) => b[1] - a[1]);
    const big = sorted.length > 12 ? sorted.filter(([, n]) => n > 1) : sorted;
    const rest = sorted.length - big.length;
    return {
      caption: t(`sg.cap.${year}`),
      items: [...big.map(([c, n]) => [clanName(year, c), group(year, c).color, n, LOOSE.has(c) ? null : c]),
        ...(rest ? [[t('sg.rest', { n: rest }), 'linear-gradient(90deg,#b07a9a,#8a9a5a,#6f9fb8)']] : [])],
    };
  }

  function tip(k) {
    const e = entry(k);
    if (!e || isOutside(k)) return '';
    const head = headOf(year, e.c);
    const withs = e.with?.length ? `<div style="color:#b4ada3;margin-top:2px">${esc(t('sg.split', { list: e.with.map((c) => clanName(year, c)).join(' · ') }))}</div>` : '';
    return `<div style="margin-top:3px"><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color(k)};margin-right:6px"></span>${esc(t('sg.y', { y: year }))} · <b>${esc(clanName(year, e.c))}</b>${head ? ` · ${esc(personName(head))}` : ''}</div>${withs}`;
  }

  // ── 卡片：一国的六个年份；点人名看人物简卡 ──
  function provCard(k) {
    const rows = data.years.map((y) => {
      const e = entry(k, y);
      if (!e) return '';
      const g = group(y, e.c);
      const head = headOf(y, e.c);
      const who = head ? `<button type="button" class="sg-who" data-person="${esc(head)}">${esc(personName(head))}</button>` : '';
      const withs = e.with?.length ? `<div class="sg-with">${esc(t('sg.split', { list: e.with.map((c) => clanName(y, c)).join(' · ') }))}</div>` : '';
      return `<li class="${y === year ? 'on' : ''}" data-y="${y}"><span class="sg-y">${y}</span>
        <span class="sg-c"><i style="background:${g.color}"></i>${LOOSE.has(e.c) ? esc(pick(g)) : `<button type="button" class="sg-clan" data-clan="${e.c}" data-cy="${y}">${esc(pick(g))}</button>`}${withs}</span><span class="sg-h">${who}</span></li>`;
    }).join('');
    return `<div class="muni-name">${esc(provName(k))}</div>
      <div class="muni-meta">${esc(t('sg.card.sub'))}</div>
      <div class="kr-body"><ol class="sg-rows">${rows}</ol><p class="kr-note">${esc(t('sg.note'))}</p></div>`;
  }

  const roleText = (role, n) => {
    const [kind, bakufu] = role.split('.');
    return t(`sg.r.${kind}`, { n, b: bakufu ? t(`sg.bakufu.${bakufu}`) : '' });
  };
  const yr = (y) => (y == null ? '?' : y < 0 ? t('sg.bc', { y: -y }) : y);
  function personCard(title) {
    const p = base(title) || {};
    const bio = bios[title];
    const roles = [
      ...(rulerBy[title]?.roles || []).map(([role, n, a, b]) => `<li><span class="sg-y sg-span">${yr(a)}–${b == null ? '' : yr(b)}</span><span>${esc(roleText(role, n))}</span></li>`),
      ...data.years.flatMap((y) => Object.entries(data.heads[y] || {}).filter(([, v]) => v === title).map(([c]) => {
        // 1590 年秀吉是整个丰臣政权的代表，按全国计
        const all = c === 'toyo_small';
        const n = keys.filter((k) => !isOutside(k) && (all || entry(k, y).c === c)).length;
        return `<li><span class="sg-y">${y}</span><span>${esc(t(y === '1600' ? 'sg.role.side' : 'sg.role', { clan: clanName(y, all ? 'toyotomi' : c), n }))}</span></li>`;
      })),
    ].join('');
    const sub = [lang === 'ja' ? p.en : p.ja, data.people[title] ? life(p) : ''].filter(Boolean).join(' · ');
    const face = bio?.img ? `<img class="sg-face" src="${bio.img}" alt="" loading="lazy">`
      : bio?.crest ? `<span class="sg-face sg-crest">${crestSVG(bio.crest)}</span>` : '';
    const crest = bio?.img && bio.crest ? `<span class="sg-mon">${crestSVG(bio.crest)}</span>` : '';
    const rel = (bio?.related || []).filter(base).map((r) => `<button type="button" class="sg-rel" data-person="${esc(r)}">${esc(personName(r))}</button>`).join('');
    return `<button type="button" class="sg-back" data-act="sg-back">‹ ${esc(clan ? clanName(year, clan) : focus ? provName(focus) : t('sg.back'))}</button>
      <div class="sg-head">${face}<div><div class="muni-name">${esc(personName(title))}${crest}</div>
      <div class="muni-meta">${esc(sub)}</div></div></div>
      <div class="kr-body">${bio ? `<p class="sg-bio">${esc(pick(bio.bio))}</p>` : ''}
      <ol class="sg-rows sg-roles">${roles}</ol>
      ${rel ? `<div class="sg-rels"><span>${esc(t('sg.related'))}</span>${rel}</div>` : ''}
      <a class="sg-wiki" href="${wikiLink(title, p.qid)}" target="_blank" rel="noopener">${esc(t('sg.wiki'))} ↗</a>
      ${bio?.img ? `<p class="kr-note">${esc(bio.author ? t('sg.img.by', { author: bio.author, license: bio.license }) : t('sg.img'))}</p>` : ''}</div>`;
  }

  // ── 势力总览：一家在所选年份的领国、按 1598 年太阁检地国高折算的石高、名次、各年份的消长、接壤的势力 ──
  const KOKU = data.koku || {};
  const kokuOf = (k) => KOKU[k] ?? null;
  const total = keys.reduce((a, k) => a + (isOutside(k) ? 0 : kokuOf(k) || 0), 0);
  function clanStats(c, y = year) {
    const held = keys.map((k) => [k, share(k, c, y)]).filter(([, s]) => s > 0);
    const koku = held.reduce((a, [k, s]) => a + (kokuOf(k) || 0) * s, 0);
    return { held, koku, n: held.filter(([, s]) => s === 1).length, part: held.filter(([, s]) => s < 1).length };
  }
  function rankOf(c) {
    const owners = new Set(keys.flatMap((k) => (isOutside(k) ? [] : [entry(k).c, ...(entry(k).with || [])])).filter((x) => !LOOSE.has(x)));
    const list = [...owners].map((x) => [x, clanStats(x).koku]).sort((a, b) => b[1] - a[1]);
    const i = list.findIndex(([x]) => x === c);
    return i < 0 ? null : { n: i + 1, of: list.length };
  }
  const man = (v) => t('sg.c.man', { v: v >= 1e6 ? Math.round(v / 1e4) : (v / 1e4).toFixed(1).replace(/\.0$/, ''), k: v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : `${Math.round(v / 1e3)}k` });
  // 接壤：本家任一国（含分治）陆上相邻、归别家（不算总称）的国，按别家归并
  function neighbours(c) {
    const out = new Map();
    for (const [k] of clanStats(c).held) {
      for (const n of near.get(k) || []) {
        if (share(n, c) === 1 || isOutside(n)) continue;
        for (const o of [entry(n).c, ...(entry(n).with || [])]) {
          if (o === c || LOOSE.has(o)) continue;
          (out.get(o) || out.set(o, new Set()).get(o)).add(n);
        }
      }
    }
    return [...out].sort((a, b) => b[1].size - a[1].size);
  }
  function trend(c) {
    // 1600 年按东西两军站队，与家族不是一回事：看家族时画 1467–1590，看两军时不画
    const ys = data.years.filter((y) => y !== '1600');
    if (year === '1600') return '';
    const pts = ys.map((y) => ({ y, ...clanStats(c, y) }));
    const max = Math.max(...pts.map((p) => p.koku), 1);
    const bars = pts.map((p) => `<li class="${p.y === year ? 'on' : ''}" data-y="${p.y}" title="${esc(p.koku ? `${p.y} · ${man(p.koku)}` : p.y)}">
      <span class="sg-bar"><b style="height:${Math.max(p.koku ? 3 : 0, Math.round((p.koku / max) * 40))}px;background:${group(year, c).color}"></b></span>
      <span class="sg-bn">${p.n + p.part || '–'}</span><small>${p.y}</small></li>`).join('');
    return `<div class="sg-sub">${esc(t('sg.c.trend'))}</div><ol class="sg-trend">${bars}</ol>`;
  }
  function clanCard(c) {
    const g = group(year, c);
    const st = clanStats(c);
    const head = headOf(year, c);
    const back = focus ? `<button type="button" class="sg-back" data-act="sg-back">‹ ${esc(provName(focus))}</button>` : '';
    const mon = data.clans[c]?.mon;
    const title = `<div class="muni-name">${mon ? `<span class="sg-mon-big" style="--c:${g.color}"><i style="-webkit-mask-image:url(src/assets/crests/${c}.png);mask-image:url(src/assets/crests/${c}.png)"></i></span>` : `<i class="sg-dot" style="background:${g.color}"></i>`}${esc(pick(g))}</div>`;
    const credit = mon ? `<p class="kr-note sg-credit">${esc(t('sg.c.mon', { name: mon.name }))} · <a href="${esc(mon.page)}" target="_blank" rel="noopener">${esc([mon.license, mon.author].filter(Boolean).join(' · '))}</a></p>` : '';
    if (!st.held.length) {
      return `${back}${title}<div class="muni-meta">${esc(t('sg.c.sub', { y: year }))}</div>
        <div class="kr-body"><p class="sg-none">${esc(t('sg.c.none', { y: year }))}</p>${trend(c)}</div>`;
    }
    const rk = rankOf(c);
    const pct = total ? (st.koku / total) * 100 : 0;
    const provs = st.held.map(([k, s]) => `<button type="button" class="sg-pv${s < 1 ? ' part' : ''}" data-prov="${esc(k)}">${esc(provName(k))}${s < 1 ? `<small>${esc(t('sg.c.part'))}</small>` : ''}</button>`).join('');
    const nb = neighbours(c).map(([o, ks]) => `<li><i style="background:${group(year, o).color}"></i><button type="button" class="sg-clan" data-clan="${o}" data-cy="${year}">${esc(clanName(year, o))}</button>
      <span>${esc([...ks].map(provName).join(' · '))}</span></li>`).join('');
    const notes = [t('sg.c.note'),
      st.held.some(([k]) => k === '出羽国' || k === '陸奥国') ? t('sg.c.dewa') : '',
      st.held.some(([k]) => kokuOf(k) == null) ? t('sg.c.nokoku') : ''].filter(Boolean).join(' ');
    return `${back}${title}
      <div class="muni-meta">${esc(t('sg.c.sub', { y: year }))}${head ? ` · <button type="button" class="sg-who" data-person="${esc(head)}">${esc(personName(head))}</button>` : ''}</div>
      <div class="kr-body">
        <div class="sg-stats">
          <div><b>${st.n}${st.part ? `<small>+${st.part}</small>` : ''}</b><span>${esc(t('sg.c.provs'))}</span></div>
          <div><b>${esc(man(st.koku))}</b><span>${esc(t('sg.c.koku'))}</span></div>
          <div><b>${pct.toFixed(1)}%</b><span>${esc(t('sg.c.pct'))}</span></div>
          ${rk ? `<div><b>${esc(t('sg.c.rank', { n: rk.n }))}</b><span>${esc(t('sg.c.of', { n: rk.of }))}</span></div>` : ''}
        </div>
        <div class="sg-pvs">${provs}</div>
        ${trend(c)}
        ${nb ? `<div class="sg-sub">${esc(t('sg.c.near'))}</div><ul class="sg-near">${nb}</ul>` : ''}
        <p class="kr-note">${esc(notes)}</p>${credit}
      </div>`;
  }

  function card() {
    if (!person && !clan && !focus) return ''; // 没有可看的（如换到 1600 年后势力总览关掉了）
    const x = `<button class="muni-card-x" type="button" data-act="sg-close" aria-label="${esc(t('close'))}">×</button>`;
    return x + (person ? personCard(person) : clan ? clanCard(clan) : provCard(focus));
  }
  // 两国交界怎么画：0 = 同一家的领国，不画（合成一片）；2 = 两家各自的领国，势力前线；1 = 其余（照常画国界）。
  // 总称（LOOSE）不是一家，不合并；分治的国也不合并
  function edgeKind(a, b) {
    if (isOutside(a) || isOutside(b)) return 1;
    const x = entry(a), y = entry(b);
    if (!x || !y || x.with?.length || y.with?.length || LOOSE.has(x.c) || LOOSE.has(y.c)) return 1;
    return x.c === y.c ? 0 : 2;
  }
  // 交给向导的：当前年份与这一国 6 个年份的归属（名字已按界面语言）
  function guideInfo(k) {
    if (!k || isOutside(k)) return null;
    const rows = data.years.map((y) => {
      const e = entry(k, y);
      const head = headOf(y, e.c);
      return { year: y, clan: clanName(y, e.c), head: head ? personName(head) : '', with: e.with?.map((c) => clanName(y, c)).join(' · ') || '' };
    });
    return { prov: provName(k), year, rows };
  }
  // 从外部（年表等）直接打开某人的卡片
  function showPerson(title) { person = base(title) ? title : null; return !!person; }

  // ── 家纹旗：深色方牌 + 代表色描边 + 金色家纹（没有家纹的写家名两个字），canvas 画好转成图给地图用 ──
  const icons = new Map();
  let iconsLoad = null;
  function drawIcon(c, img) {
    const S = 128;
    const cv = document.createElement('canvas');
    cv.width = cv.height = S;
    const g = cv.getContext('2d');
    g.beginPath();
    if (g.roundRect) g.roundRect(7, 7, S - 14, S - 14, 20); else g.rect(7, 7, S - 14, S - 14); // 旧版 Safari 没有 roundRect
    g.fillStyle = 'rgba(20,20,24,.94)';
    g.fill();
    g.lineWidth = 9;
    g.strokeStyle = data.clans[c].color;
    g.stroke();
    if (img) {
      const n = 74;
      const t2 = document.createElement('canvas');
      t2.width = t2.height = n;
      const h = t2.getContext('2d');
      h.drawImage(img, 0, 0, n, n);
      h.globalCompositeOperation = 'source-in';
      h.fillStyle = '#f2dcae';
      h.fillRect(0, 0, n, n);
      g.drawImage(t2, (S - n) / 2, (S - n) / 2);
    } else {
      // 「姉小路（三木）」取括号里的；其余取前两个字
      const name = data.clans[c].ja.match(/（(.+)）/)?.[1] || data.clans[c].ja;
      const text = [...name].slice(0, 2).join('');
      g.fillStyle = '#f2dcae';
      g.font = `700 ${text.length > 1 ? 44 : 60}px "Noto Serif JP", "Noto Serif SC", serif`;
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText(text, S / 2, S / 2 + 3);
    }
    return cv.toDataURL();
  }
  // 家纹图全部到齐（或失败）后画好所有旗，然后 done() 让地图重画
  function loadIcons(done) {
    iconsLoad ??= Promise.all(Object.entries(data.clans).filter(([c]) => !LOOSE.has(c)).map(([c, v]) => new Promise((ok) => {
      if (!v.mon) { icons.set(c, drawIcon(c, null)); ok(); return; }
      const img = new Image();
      img.onload = () => { icons.set(c, drawIcon(c, img)); ok(); };
      img.onerror = () => { icons.set(c, drawIcon(c, null)); ok(); };
      img.src = `src/assets/crests/${c}.png`;
    }))).then(done);
    return iconsLoad;
  }
  // 当年各家（不含总称；1600 年按东西军，不插家纹旗）独占的国，地图据此定旗的位置
  function banners() {
    if (year === '1600') return [];
    const by = new Map();
    for (const k of keys) {
      const e = entry(k);
      if (isOutside(k) || LOOSE.has(e.c) || !data.clans[e.c] || e.with?.length) continue;
      (by.get(e.c) || by.set(e.c, []).get(e.c)).push(k);
    }
    return [...by].map(([c, provs]) => ({ c, provs, name: clanName(year, c), icon: icons.get(c) || null }));
  }

  return {
    years: data.years,
    get year() { return year; },
    banners, loadIcons,
    monOf: (c) => data.clans[c]?.mon || null,
    setYear(y) {
      if (!data.years.includes(y)) return;
      year = y;
      if (clan && !group(y, clan)) clan = null; // 家族与 1600 年的东西军不互通
    },
    get focus() { return focus; },
    setFocus(k) { focus = k; person = null; clan = null; },
    get clan() { return clan; },
    // 打开某家的势力总览（总称与不存在的键不打开）；null 关掉
    setClan(c) {
      clan = c && !LOOSE.has(c) && (data.clans[c] || data.sides[c]) ? c : null;
      person = null;
      return !!clan;
    },
    setAdjacency(pairs) {
      near = new Map();
      for (const [a, b] of pairs) {
        (near.get(a) || near.set(a, new Set()).get(a)).add(b);
        (near.get(b) || near.set(b, new Set()).get(b)).add(a);
      }
    },
    // 交给向导的势力总览（名字已按界面语言）
    clanGuide() {
      if (!clan) return null;
      const st = clanStats(clan);
      const head = headOf(year, clan);
      return { year, clan: clanName(year, clan), head: head ? personName(head) : '',
        provs: st.held.map(([k, s]) => provName(k) + (s < 1 ? `(${t('sg.c.part')})` : '')),
        koku: st.held.length ? man(st.koku) : '', rank: rankOf(clan)?.n || null, near: neighbours(clan).map(([o]) => clanName(year, o)) };
    },
    color, legend, tip, card, entry, showPerson, guideInfo, edgeKind,
    // 卡片里的点击；返回 true 表示需要重绘卡片
    handle(e) {
      const who = e.target.closest('[data-person]');
      if (who) { person = who.dataset.person; return true; }
      const cl = e.target.closest('[data-clan]');
      if (cl) { person = null; clan = cl.dataset.clan; return cl.dataset.cy !== year ? { year: cl.dataset.cy, clan: true } : { clan: true }; }
      const pv = e.target.closest('[data-prov]');
      if (pv) return { prov: pv.dataset.prov };
      const bar = e.target.closest('.sg-trend li[data-y]');
      if (bar) return { year: bar.dataset.y };
      if (e.target.closest('[data-act="sg-back"]')) {
        if (person) { person = null; return clan || focus ? { clan: true } : { rulers: true }; } // 从年表打开的回到年表
        clan = null;
        return focus ? { clan: true } : { close: true };
      }
      const row = e.target.closest('.sg-rows li[data-y]');
      if (row && !person) return { year: row.dataset.y };
      return false;
    },
  };
}
