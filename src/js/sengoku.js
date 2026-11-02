// 战国势力图：68 国 × 6 个年份（1467 / 1560 / 1573 / 1582 / 1590 / 1600），着色、提示、图例、国别卡片与人物简卡。
// 数据 src/data/sengoku.json 由 tools/sengoku_tool.py 生成并核对；1600 年按关原之战的站队（sides）着色。
// 人物：sengoku.json 的 people（各年份代表人物）+ rulers.json（天皇 · 将军 · 执权）+ people.json（详写：简介、肖像、家纹、相关人物）
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { crestSVG } from './crests.js';

const OUTSIDE = '#33333a';

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

  const entry = (k, y = year) => data.provinces[k]?.[y];
  const group = (y, c) => (y === '1600' ? data.sides[c] : data.clans[c]);
  const isOutside = (k) => !props.get(k)?.zh;
  function color(k) {
    if (isOutside(k)) return OUTSIDE;
    const e = entry(k);
    return e ? group(year, e.c)?.color || OUTSIDE : OUTSIDE;
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
      items: [...big.map(([c, n]) => [clanName(year, c), group(year, c).color, n]),
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
        <span class="sg-c"><i style="background:${g.color}"></i>${esc(pick(g))}${withs}</span><span class="sg-h">${who}</span></li>`;
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
    return `<button type="button" class="sg-back" data-act="sg-back">‹ ${esc(focus ? provName(focus) : t('sg.back'))}</button>
      <div class="sg-head">${face}<div><div class="muni-name">${esc(personName(title))}${crest}</div>
      <div class="muni-meta">${esc(sub)}</div></div></div>
      <div class="kr-body">${bio ? `<p class="sg-bio">${esc(pick(bio.bio))}</p>` : ''}
      <ol class="sg-rows sg-roles">${roles}</ol>
      ${rel ? `<div class="sg-rels"><span>${esc(t('sg.related'))}</span>${rel}</div>` : ''}
      <a class="sg-wiki" href="${wikiLink(title, p.qid)}" target="_blank" rel="noopener">${esc(t('sg.wiki'))} ↗</a>
      ${bio?.img ? `<p class="kr-note">${esc(bio.author ? t('sg.img.by', { author: bio.author, license: bio.license }) : t('sg.img'))}</p>` : ''}</div>`;
  }

  function card() {
    const x = `<button class="muni-card-x" type="button" data-act="sg-close" aria-label="${esc(t('close'))}">×</button>`;
    return x + (person ? personCard(person) : provCard(focus));
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

  return {
    years: data.years,
    get year() { return year; },
    setYear(y) { if (data.years.includes(y)) year = y; },
    get focus() { return focus; },
    setFocus(k) { focus = k; person = null; },
    color, legend, tip, card, entry, showPerson, guideInfo,
    // 卡片里的点击；返回 true 表示需要重绘卡片
    handle(e) {
      const who = e.target.closest('[data-person]');
      if (who) { person = who.dataset.person; return true; }
      if (e.target.closest('[data-act="sg-back"]')) { person = null; return focus ? true : { rulers: true }; } // 从年表打开的回到年表
      const row = e.target.closest('.sg-rows li[data-y]');
      if (row && !person) return { year: row.dataset.y };
      return false;
    },
  };
}
