// 古代户籍《古今人别帐》：选一个市区町村（或「我在哪」的定位点），按时代列出这里归谁管。
// 每一栏注明精确到哪一级（市区町村 / 郡 / 县 / 国），只用已核验的数据计算，不编故事。
// 同一份 rows 既画成对话框里的卷轴（kosekiHTML），也画到 canvas 上存成图片（kosekiImage）
import { t, lang, label } from './i18n.js';
import { esc } from './detail.js';
import { distanceKm } from './koku.js';
import { fmtPeople } from './kokuryoku.js';
import { findHan, kosekiHanHTML } from './han.js';
import { fixLink } from './report.js';
import { fold } from './search.js';

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

// 此地天灾（3.41，town.saigai ← tools/saigai_tool.py）：震中离这里够近的大地震、火山在 40 公里内的大喷发。
// 半径与 build_bundle.quake_r 相同：M7 30 km、M8 95 km、M9 300 km，M7 以下（死者 ≥100 才收的）25 km
const QUAKE_R = (m, tsu) => Math.max(m < 7 ? 25 : 30 * 10 ** (0.5 * (m - 7)), tsu >= 10 ? 300 : 0); // 海啸 ≥10 米的至少 300 km（3.43）
const VOLC_R = 40;
export function saigaiRow(list, pt) {
  if (!list?.length || !pt) return null;
  const near = list.map(([kind, name, y, mOrMt, dead, flag, lon, lat, tsu, tsuAt]) => {
    const d = distanceKm(pt, [lon, lat]);
    return { kind, name, y, m: mOrMt, dead, flag, d, dir: bearing(pt, [lon, lat]), tsu, tsuAt };
  }).filter((e) => e.d <= (e.kind === 'e' ? QUAKE_R(e.m, e.tsu) : VOLC_R));
  if (!near.length) return null;
  const deadTxt = (e) => (e.dead == null ? '' : t(e.flag & 2 ? 'ks.saigai.dead.m' : e.flag & 1 ? 'ks.saigai.dead.r' : 'ks.saigai.dead', { n: e.dead.toLocaleString(lang) }));
  const line = (e) => (e.kind === 'e'
    ? t('ks.saigai.eq', { y: e.y, name: e.name, m: e.m, dir: e.dir, km: km(e.d) })
    : t('ks.saigai.vol', { y: e.y, name: e.name, mt: e.m, dir: e.dir, km: km(e.d) })) + deadTxt(e)
    + (e.tsu ? (e.tsuAt ? t('ks.saigai.tsu.at', { m: e.tsu, at: e.tsuAt }) : t('ks.saigai.tsu', { m: e.tsu })) : '');
  // 最重的一次（按死者，没有死者数的按规模）写在上面，其余按年份
  // 3.43：按「死者数 / 距离」挑（海啸大的地震半径放宽到 300 km 以后，神户的第一行变成了 179 km 外的宝永地震）；没有死者数的按 100 人算
  const sev = (e) => (e.dead ?? 100) / Math.max(e.d, 10) + (e.kind === 'e' ? e.m : 7) / 1000;
  const top = near.reduce((a, b) => (sev(b) > sev(a) ? b : a));
  const rest = near.filter((e) => e !== top).sort((a, b) => a.y - b.y);
  const more = rest.length > 6 ? ` ${t('ks.saigai.more', { n: rest.length - 6 })}` : '';
  return { k: 'saigai', seal: 'muni', main: line(top),
    sub: [rest.slice(0, 6).map(line).join(t('list.sep')) + more, t('ks.saigai.note')].filter(Boolean).join(' · ') };
}

// 3.43 户籍新栏（数据在 town 包，build_bundle 的 place_extras）：绳文的海、附近的古战场、古坟、此地的国宝、人口的变化
const KASSEN_R = 15, KOFUN_R = 20; // 与 build_bundle 的 KASSEN_R / KOFUN_R 相同
const POP_YEARS = [1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
export function placeRows(town, code, pt) {
  const out = [];
  if (!town) return out;
  const near = (list, lonI, r) => (pt ? (list || []).map((x) => ({ x, d: distanceKm(pt, [x[lonI], x[lonI + 1]]), dir: bearing(pt, [x[lonI], x[lonI + 1]]) }))
    .filter((e) => e.d <= r).sort((a, b) => a.d - b.d) : []);
  // 绳文的海：本市海拔 5 米以下的陆地占几成（tools/jomon_tool.py）；不到 5% 不写
  const jp = town.jomon?.[code];
  if (jp >= 5) out.push({ k: 'jomon', seal: 'muni', main: t(jp >= 50 ? 'ks.jomon.most' : 'ks.jomon', { pct: jp }), sub: t('ks.jomon.note') });
  // 古坟：最近的一座前方后圆坟；20 公里内更大的另写一句（宫内厅治定的陵墓写被葬者）
  const kf = near(town.kofun, 3, KOFUN_R);
  if (kf.length) {
    const desc = (e) => t('ks.kofun.item', { name: e.x[0], dir: e.dir, km: km(e.d) })
      + (e.x[1] ? t('ks.kofun.len', { m: e.x[1] }) : '') + (e.x[2] ? t('ks.kofun.ryo', { who: e.x[2] }) : '');
    const big = kf.reduce((a, b) => ((b.x[1] || 0) > (a.x[1] || 0) ? b : a));
    const n5 = kf.filter((e) => e.d <= 5).length;
    out.push({ k: 'kofun', seal: 'muni', main: desc(kf[0]),
      sub: [big !== kf[0] && big.x[1] ? t('ks.kofun.big', { item: desc(big) }) : '', n5 > 1 ? t('ks.kofun.n5', { n: n5 }) : '', t('ks.kofun.note')].filter(Boolean).join(' · ') });
  }
  // 附近的古战场：15 公里内最近的三场
  const ks = near(town.kassen, 2, KASSEN_R);
  if (ks.length) {
    const item = (e) => t('ks.kassen.item', { y: e.x[1], name: e.x[0], dir: e.dir, km: km(e.d) });
    out.push({ k: 'battles', seal: 'muni', main: item(ks[0]),
      sub: [ks.slice(1, 3).map(item).join(t('list.sep')), ks.length > 3 ? t('ks.kassen.more', { n: ks.length }) : '', t('ks.kassen.note')].filter(Boolean).join(' · ') });
  }
  // 人口的变化：1970 → 2020 年（2025 年的数照条目画进小图，文字只写国势调查确定的 2020 年）
  const own = town.pop?.[code];
  const series = own || town.pop?.[town.popCity?.[code]];
  if (series?.length === POP_YEARS.length) {
    const a = series[0], b = series[10];
    const pi = series.slice(0, 11).indexOf(Math.max(...series.slice(0, 11)));
    const pct = Math.round((b / a - 1) * 100);
    out.push({ k: 'pop', seal: own ? 'muni' : 'city', spark: series,
      main: t('ks.pop', { a: fmtPeople(a), b: fmtPeople(b), pct: `${pct > 0 ? '+' : ''}${pct}%` }),
      sub: [pi > 0 && pi < 10 ? t('ks.pop.peak', { y: POP_YEARS[pi], n: fmtPeople(series[pi]) }) : '', t('ks.pop.note')].filter(Boolean).join(' · ') });
  }
  // 此地的国宝：按 Wikidata 的位置落在这个市区町村的（收藏品写的是收藏处）
  const kh = town.kokuho?.[code];
  if (kh?.length) {
    out.push({ k: 'kokuho', seal: 'muni', main: t('ks.kokuho', { n: kh.length }),
      sub: [kh.slice(0, 8).map(([n]) => n).join(t('list.sep')) + (kh.length > 8 ? ` ${t('ks.mura.more', { n: kh.length })}` : ''), t('ks.kokuho.note')].join(' · ') });
  }
  return out;
}

// 户籍里人口那一栏的小折线（12 个点，1970–2025）
function sparkSVG(v) {
  const w = 160, h = 34, max = Math.max(...v), min = Math.min(...v), sx = w / (v.length - 1);
  const y = (n) => (max === min ? h / 2 : h - 3 - ((n - min) / (max - min)) * (h - 6));
  const pts = v.map((n, i) => `${(i * sx).toFixed(1)},${y(n).toFixed(1)}`).join(' ');
  return `<svg class="ks-spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="#8a3b33" stroke-width="2"/>`
    + `<circle cx="${(10 * sx).toFixed(1)}" cy="${y(v[10]).toFixed(1)}" r="2.6" fill="#8a3b33"/></svg>`;
}

// 同姓的氏族（3.43，bundle/myoji-<lang>.json）：户主名开头的姓（最长的那个，按 fold 统一字形）有出身地的氏族
let myojiIdx = null;
export function myojiLine(myoji, name) {
  if (!myoji || !name) return '';
  myojiIdx ||= Object.fromEntries(Object.keys(myoji).map((k) => [fold(k), k]));
  const f = fold(name.trim());
  for (let n = Math.min(3, f.length); n >= 1; n--) {
    const k = myojiIdx[f.slice(0, n)];
    if (k) return t('ks.myoji', { list: myoji[k].slice(0, 3).map(([c, o]) => t('ks.myoji.item', { clan: c, from: o })).join(t('list.sep')) });
  }
  return '';
}

// 同名地名的键 → 对应的古代设施（量这里到本国那一处的距离）
const DOU_SITE = { fuchu: 'fu', kofu: 'fu', soja: 'fu', kokubu: 'ji', ichi: 'ichi' };

// ctx：{ pref, props, provNames, pt, sites, domains, mainGun, power, prints, prefLabel, prefOf, sengoku, han, town }（prefOf：县 id → 县名）（town：bundle/town/<lang>/NN.json 的明治町村与地名来历，可能为 null）
// 家乡站在哪一边（3.37）：只取战国势力图的年份与合战同年或只差一两年的四场（桶狭间 1560、川中岛 1561 → 1560、长篠 1575 → 1573、
// 关原 1600），那一年这块地归的家正是合战的一方才写（值是合战数据里的 faction 键）；关原按 1600 年的东西两军，观望、倒戈也照写
const SIDES = [
  { key: 'okehazama', y: '1560', side: { oda: 'oda', imagawa: 'imagawa' } },
  { key: 'kawanakajima', y: '1560', side: { takeda: 'takeda', uesugi: 'uesugi' } },
  { key: 'nagashino', y: '1573', side: { oda: 'oda', tokugawa: 'oda', takeda: 'takeda' } },
  { key: 'sekigahara', y: '1600', sides: true },
];
function sidesRow(sg, sengoku, battles, code) {
  const out = [];
  const colon = lang === 'en' ? ': ' : '：';
  for (const s of SIDES) {
    const b = battles?.find((x) => x.key === s.key);
    const e = sg?.[s.y];
    if (!b || !e) continue;
    const cs = [e.c, ...(e.with || [])];
    const title = b.name.replace(/\s*[（(]\d+[)）]$/, '');
    if (s.sides) {
      // 3.38：城主站在与本国不同一边的城下（sengoku.towns，如上田的真田昌幸）按城主写
      const tw = sengoku.towns?.[code];
      const g = sengoku.sides[tw ? tw.c : e.c];
      const nm = (o) => o[lang] || o.zh;
      if (tw && g) out.push(`${title}${colon}${t('ks.sides.town', { side: nm(g), who: nm(tw.who), castle: nm(tw.castle) })}`);
      else if (g) out.push(`${title}${colon}${g[lang] || g.zh}${e.with ? t('ks.sides.split') : ''}`);
      continue;
    }
    const fs = [...new Set(cs.map((c) => s.side[c]).filter(Boolean))].map((k) => b.factions.find((f) => f.key === k)?.name).filter(Boolean);
    if (fs.length) out.push(`${title}${colon}${fs.join(t('list.sep'))}`);
  }
  return out;
}

export function kosekiRows({ pref, props, provNames, pt, sites, domains, mainGun, power, prints, prefLabel, prefOf, sengoku, han, town, battles }) {
  const pn = (ja) => provNames?.[ja]?.[lang] || ja;
  const key = props.province;
  const short = key?.replace(/国$/, '');
  const mine = sites.filter((s) => s.prov === key);
  const circuit = mine[0]?.circuit;
  const gunList = props.old_districts || [];
  const gun = (gunList.find(([, part]) => !part) || gunList[0])?.[0];
  const homeGun = mainGun?.[props.code]?.g || gun; // 本贯也用中心市街所在的郡（笠间市：西茨城郡，而不是 1878 年前的茨城郡）
  const muniName = lang === 'en' && props.en ? props.en : props.name;
  const rows = [];

  // 本贯：道 · 国 · 郡；今属
  const home = [circuit ? label('circuit', circuit) : null, key ? pn(key) : t('muni.outside'), homeGun].filter(Boolean).join(' · ');
  const partial = props.partial?.length ? t('muni.partial', { list: props.partial.map(pn).join(' · ') }) : '';
  rows.push({ k: 'home', seal: 'muni', main: home, sub: [t('ks.now', { place: `${prefLabel} ${muniName}` }), partial].filter(Boolean).join(' · ') });
  const kr = kuniRow(town?.kuni, key, pref.id, pn, prefOf);
  if (kr) rows.push(kr);

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
  // 古代郷名（town.wamyo）：《和名类聚抄》所载本郡的郷；今天的市区町村经明治旧郡对应到古郡（只整体属于一郡的才有），郷的位置不细分
  const wg = town?.wamyo?.muni?.[props.code];
  const gous = wg && town.wamyo.gou?.[key]?.[wg];
  if (gous?.length) {
    const names = gous.slice(0, 14).map(([n, k]) => (!k || k === '-' ? n : lang === 'en' ? `${n} (${k})` : `${n}（${k}）`)).join(t('list.sep'));
    rows.push({ k: 'wamyo', seal: 'gun', main: t('ks.wamyo', { gun: wg, n: gous.length }), sub: gous.length > 14 ? `${names} ${t('ks.mura.more', { n: gous.length })}` : names });
  }
  // 千年地名（town.sennen，3.40）：今天、平成合并前或明治町村的名字（去掉市町村区）正是同一古郡的《和名抄》郷名
  const sn = town?.sennen?.[props.code];
  if (sn?.length) {
    const q = (n) => (lang === 'en' ? `“${n}”` : `「${n}」`);
    rows.push({ k: 'sennen', seal: 'gun', main: t('ks.sennen', { list: sn.map(([, , g]) => q(g)).join(t('list.sep')) }),
      sub: [sn.map(([n, w]) => t(`ks.sennen.w${w}`, { name: n })).join(t('list.sep')), t('ks.sennen.note')].join(' · ') });
  }

  const f = pref.map_filters;
  // 战国：有 sengoku.json 时按旧国列出 6 个年份（主行 1560 → 1582 → 1600，副行其余三年）；没有时退回县的 1572。
  // 奥羽按郡、虾夷地按和人地 / 阿伊努的土地（muni_units，与战国势力图的分区一致），精度印为「郡」
  const unit = sengoku?.muni_units?.[props.code] || (sengoku?.units?.[key] ? key : null);
  const sg = sengoku?.units?.[unit] || sengoku?.provinces?.[key];
  if (sg && props.province !== '-') {
    const at = (y) => {
      const g = (y === '1600' ? sengoku.sides : sengoku.clans)[sg[y].c];
      return `${y} ${g[lang] || g.zh}`;
    };
    rows.push({ k: 'sengoku6', seal: unit ? 'gun' : 'prov', main: ['1560', '1582', '1600'].map(at).join(' → '), sub: ['1467', '1573', '1590'].map(at).join(' · ') });
    const sides = sidesRow(sg, sengoku, battles, props.code);
    if (sides.length) rows.push({ k: 'sides', seal: unit ? 'gun' : 'prov', main: sides.join(' · '), sub: t('ks.sides.note') });
  } else {
    rows.push({ k: 'sengoku', seal: 'pref', main: label('sg', f.sengoku_1572), sub: '' });
  }

  // 主要郡（main_gun）：横跨几郡时按中心市街所在的郡；江户 / 京都的市街（优先于郡的记录）与整市一级的直接给出领主
  const mg = mainGun?.[props.code];
  const edoGun = mg?.g || gun;
  const d = edoGun && domains?.[pref.id]?.[edoGun];
  const lord = (name) => (name.startsWith('@') ? t(`ks.lord.${name.slice(1)}`) : name);
  // 旧高旧领数据库（town.kyu）：今天这个市区町村里各村的领主按石高合计，前 4 位 + 其余，写百分比
  const kyu = town?.kyu?.[props.code];
  const pct = (v) => { const x = (v / kyu.k) * 100; return x < 1 ? '<1%' : `${Math.round(x)}%`; };
  const kyuSub = kyu ? t('ks.edo.kyu', { n: kyu.t, koku: Math.round(kyu.k).toLocaleString(lang), list: kyu.r.map(([n, v]) => `${lord(n)} ${pct(v)}`).join(t('list.sep')) }) + (kyu.p ? t('ks.edo.kyu.part') : '') : '';
  const hansOf = (names) => names.map((n) => !n.startsWith('@') && findHan(han, n, pref.id)).filter(Boolean);
  if (mg?.seat) {
    // 城下町：藩厅所在，直接写这个藩；本市（没有就本郡）的统计接在后面
    const h = findHan(han, mg.lord, pref.id);
    const of = kyuSub || (d?.r?.length && d.t ? t('ks.edo.of', { gun: edoGun, n: d.t, list: d.r.map(([n, c]) => `${lord(n)} ${c}`).join(t('list.sep')) }) : '');
    rows.push({ k: 'edo', seal: 'muni', main: mg.lord, sub: [t('ks.edo.seat', { han: mg.lord, seat: mg.seat }), of].filter(Boolean).join(' · '), hans: h ? [h] : [] });
  } else if (!mg?.town && kyu?.r?.length) {
    rows.push({ k: 'edo', seal: 'muni', main: lord(kyu.r[0][0]), sub: kyuSub, hans: hansOf(kyu.r.map(([n]) => n)) });
  } else if (mg?.town || (!d?.r?.length && mg?.lord)) {
    const h = !mg.lord.startsWith('@') && findHan(han, mg.lord, pref.id);
    rows.push({ k: 'edo', seal: mg.town ? 'muni' : 'city', main: lord(mg.lord), sub: mg.town ? t(`ks.edo.town.${mg.town}`) : t('ks.edo.city', { city: mg.city }), hans: h ? [h] : [] });
  } else if (d?.r?.length) {
    const gun = edoGun;
    const hans = hansOf(d.r.map(([n]) => n));  // 点开看历代藩主
    // 没有町村数的郡（正文写「全域が仙台藩領」）：写「某郡全域」
    const sub = d.t ? t('ks.edo.of', { gun, n: d.t, list: d.r.map(([n, c]) => `${lord(n)} ${c}`).join(t('list.sep')) }) : t('ks.edo.all', { gun });
    rows.push({ k: 'edo', seal: 'gun', main: lord(d.r[0][0]), sub, hans });
  } else {
    const list = pref.historical_lineage.edo_domains || [];
    rows.push({ k: 'edo', seal: 'pref', main: list.slice(0, 3).join(t('list.sep')) || '—', sub: list.length > 3 ? t('ks.more', { n: list.length - 3 }) : '' });
  }
  // 远方的领主（town.far，3.40）：幕末这里有 5% 以上的石高属于藩厅在 150 公里外的藩
  const far = town?.far?.[props.code];
  if (far?.length) {
    const [h, kmv, pc] = far[0];
    rows.push({ k: 'far', seal: 'muni', main: t('ks.farlord', { han: h, km: kmv, pct: pc }),
      sub: [far.slice(1).map(([h2, k2, p2]) => t('ks.farlord.more', { han: h2, km: k2, pct: p2 })).join(t('list.sep')), t('ks.farlord.note')].filter(Boolean).join(' · ') });
  }
  rows.push({ k: 'boshin', seal: 'pref', main: label('bk', f.bakumatsu), sub: '' });
  // 明治町村（town.mura）：町村制时今属这里的町村（郡条目里写明的，可能不全），最多列 14 个
  const mura = town?.mura?.[props.code];
  if (mura?.length) {
    const ys = mura.map((x) => x[2]).sort((a, b) => a - b);
    const names = mura.slice(0, 14).map(([n, part]) => (part ? `${n}${t('ks.mura.part')}` : n)).join(t('list.sep'));
    rows.push({ k: 'mura', seal: 'muni', main: t('ks.mura', { y: ys[Math.floor(ys.length / 2)], n: mura.length }), sub: mura.length > 14 ? `${names} ${t('ks.mura.more', { n: mura.length })}` : names });
  }
  // 平成大合并前（town.heisei）：1995 年时今属这里的市町村与哪一年起成为今天的样子（只有 1995 年以后变过的才有）
  const hs = heiseiOf(town, props.code);
  if (hs) rows.push({ k: 'heisei', seal: 'muni', main: t('ks.heisei', { list: hs.list }), sub: t(hs.yl.includes('–') ? 'ks.heisei.to2' : 'ks.heisei.to', { y: hs.yl, place: muniName }) });

  const P = power?.provinces?.[key];
  if (P) {
    const rank = Object.values(power.provinces).filter((v) => v.pop > P.pop).length + 1;
    rows.push({ k: 'power', seal: 'prov', main: t('ks.power', { prov: pn(key), pop: fmtPeople(P.pop), rank }), sub: '' });
  }
  // 市区町村的逆袭（town.rise，3.40）：幕末石高的全国名次 → 今天人口的名次
  const rr = town?.rise?.r?.[props.code];
  if (rr) {
    const [a, b] = rr;
    const n = town.rise.n;
    // 名次相差三倍以上才算逆袭 / 没落（83 → 322 算没落，16 → 45 算差不多）
    rows.push({ k: 'rise', seal: 'muni', main: t('ks.rise', { a, b, n }), sub: t(a >= b * 3 ? 'ks.rise.up' : b >= a * 3 ? 'ks.rise.down' : 'ks.rise.flat') });
  }
  rows.push(...placeRows(town, props.code, pt));
  const disaster = saigaiRow(town?.saigai, pt);
  if (disaster) rows.push(disaster);
  const ph = pref.dialect?.phrases?.[0];
  if (ph) rows.push({ k: 'voice', seal: 'pref', main: `「${ph.phrase}」`, sub: ph.meaning, voice: true });
  // 同乡名人（town.famous，3.37）：Wikidata 出生地落在这里的已故人物，按语言条目数排（tools/famous_tool.py）
  // 政令市的区没有自己的（出生地多记在市上）：用市的（town.famousCity：区 → 市的代码），印「全市」
  const famCity = !town?.famous?.[props.code] && props.city ? town?.famous?.[town.famousCity?.[props.code]] : null;
  const fam = town?.famous?.[props.code] || famCity;
  if (fam?.length) {
    const life = (b, d) => (lang === 'en' ? ` (${b ?? '?'}–${d ?? '?'})` : `（${b ?? '?'}–${d ?? '?'}）`);
    rows.push({ k: 'famous', seal: famCity ? 'city' : 'muni', main: fam.slice(0, 3).map(([, n, b, d]) => `${n}${life(b, d)}`).join(t('list.sep')), sub: [fam.length > 3 ? fam.slice(3).map(([, n]) => n).join(t('list.sep')) : '', t('ks.famous.note')].filter(Boolean).join(' · ') });
  }
  // 地名来历（town.yurai）：政令市的区用市名的来历（印「全市」），其余按本市区町村
  const yd = town?.yurai?.[pref.id];
  const own = yd?.[props.name];
  const yr = own || (props.city && yd?.[props.city]);
  if (yr) rows.push({ k: 'yurai', seal: own ? 'muni' : 'city', main: own ? muniName : props.city, sub: yr });
  // 同名地名（town.dou）：这里今天、1995 年或明治町村制时的名字带「府中」「国府」「国分」「一宫」「总社」的，
  // 写这类名字的由来、本国那一处设施离这里多远，并列出全国其他同名的地方（取最近的那个名字，一个键一栏）
  const dou = town?.dou || [];
  for (const k of [...new Set(dou.filter((x) => x[4] === props.code).map((x) => x[0]))]) {
    const mineK = dou.find((x) => x[0] === k && x[4] === props.code);
    const others = dou.filter((x) => x[0] === k && x[4] !== props.code);
    if (!others.length) continue;
    const site = mine.length && pt ? nearest(mine.filter((s) => s.kind === DOU_SITE[k]), pt) : null;
    // 其他地方写今天的市区町村，以前的名字写在括号里（兵库县有两个 1995 年的一宫町，今天分属宍粟市与淡路市）
    const list = others.slice(0, 10).map(([, name, pid, y, , cur]) => {
      const pref = prefOf ? prefOf(pid) : '';
      return y ? t('ks.dou.old', { pref, now: cur, name, y }) : t('ks.dou.item', { pref, name });
    }).join(t('list.sep'));
    const sub = [t(`ks.dou.why.${k}`), site ? t('ks.dou.far', { site: t(`ks.dou.s.${DOU_SITE[k]}`), km: km(site.km) }) : '',
      t('ks.dou.list', { list: others.length > 10 ? `${list} ${t('ks.mura.more', { n: others.length })}` : list })].filter(Boolean).join(t('ks.dou.sep'));
    rows.push({ k: 'dou', seal: 'muni', main: t('ks.dou', { name: mineK[1], y: mineK[3] ? t('ks.dou.y0', { y: mineK[3] }) : '', kw: t(`ks.dou.kw.${k}`), n: others.length }), sub });
  }
  return { rows: groupRows(rows), short, print: prints?.[0] || null };
}

// 3.43：户籍一长（上田 20 栏上下），按五组排：古代 / 战乱 / 江户 / 近现代 / 这片土地；组内保持原来的先后。
// 对话框里每组有小标题，顶上一行跳转按钮（data-act="ks-jump"）；存图也按这个顺序
export const KS_GROUPS = ['ancient', 'war', 'edo', 'modern', 'place'];
const KS_GROUP_OF = {
  jomon: 'ancient', kofun: 'ancient', home: 'ancient', kami: 'ancient', ritsuryo: 'ancient', wamyo: 'ancient', sennen: 'ancient', kuni: 'ancient',
  sengoku6: 'war', sengoku: 'war', sides: 'war', battles: 'war',
  edo: 'edo', far: 'edo', boshin: 'edo',
  mura: 'modern', heisei: 'modern', pop: 'modern', power: 'modern', rise: 'modern',
};
function groupRows(rows) {
  const gi = (r) => KS_GROUPS.indexOf(KS_GROUP_OF[r.k] || 'place');
  return rows.map((r, i) => ({ ...r, g: KS_GROUPS[gi(r)], i })).sort((a, b) => gi(a) - gi(b) || a.i - b.i);
}

// 你其实是别国人（3.40，town.kuni：按今天的人口，旧国的大半在哪个县、本县的大半是哪个国）：
// 这里的旧国大半在别县 → 写出来；或本县大半是另一个国、这个国只占本县不到四成 → 写出来；都不是就不出这一栏
function kuniRow(kuni, key, pid, pn, prefOf) {
  const share = kuni?.prov?.[key];
  if (!share?.length || !prefOf) return null;
  const here = share.find(([p]) => p === pid)?.[1];
  const [mp, mpct] = share[0];
  if (mp !== pid) {
    return { k: 'kuni', seal: 'prov', main: t('ks.kuni.away', { prov: pn(key), pref: prefOf(mp), pct: mpct }), sub: t('ks.kuni.here', { prov: pn(key), pct: here ?? '<1' }) };
  }
  const top = kuni.pref?.[0];
  const mine = kuni.pref?.find(([k]) => k === key)?.[1];
  if (top && top[0] !== key && mine != null && mine < 40) {
    return { k: 'kuni', seal: 'prov', main: t('ks.kuni.minor', { prov: pn(key), main: pn(top[0]), pct: top[1] }), sub: t('ks.kuni.minor.sub', { prov: pn(key), pct: mine }) };
  }
  return null;
}

// 1995 年的市町村（一部的加注）与变动年份（几年的写成「2004–2006」）；max 个以后写「等 n 个」
export function heiseiOf(town, code, max = 14) {
  const hs = town?.heisei?.[code];
  if (!hs?.length) return null;
  const ys = [...new Set(hs.map((x) => x[2]).filter(Boolean))].sort((a, b) => a - b);
  const names = hs.slice(0, max).map(([n, part]) => (part ? `${n}${t('ks.mura.part')}` : n)).join(t('list.sep'));
  return { y: ys[0], yl: ys.length > 1 ? `${ys[0]}–${ys.at(-1)}` : String(ys[0]), list: hs.length > max ? `${names} ${t('ks.mura.more', { n: hs.length })}` : names };
}

export function kosekiHTML(ctx, data, name, extra = '') {
  const { rows, print } = data;
  const title = `${ctx.prefLabel} ${lang === 'en' && ctx.props.en ? ctx.props.en : ctx.props.name}`;
  const groups = KS_GROUPS.filter((g) => rows.some((r) => r.g === g));
  const toc = groups.length > 2 ? `<nav class="ks-toc" aria-label="${esc(t('ks.toc'))}">${groups.map((g) =>
    `<button type="button" data-act="ks-jump" data-g="${g}">${esc(t(`ks.g.${g}`))}</button>`).join('')}</nav>` : '';
  const body = rows.map((r, i) => `${r.g && r.g !== rows[i - 1]?.g ? `<h3 class="ks-grp" data-ks-grp="${r.g}">${esc(t(`ks.g.${r.g}`))}</h3>` : ''}
    <div class="ks-row" data-k="${r.k}">
      <div class="ks-k">${esc(t(`ks.r.${r.k}`))}<i class="ks-seal" title="${esc(t(`ks.p.${r.seal}.t`))}">${esc(t(`ks.p.${r.seal}`))}</i></div>
      <div class="ks-v"><b>${esc(r.main)}</b>${r.spark ? sparkSVG(r.spark) : ''}${r.sub ? `<span>${esc(r.sub)}</span>` : ''}${r.hans?.length ? kosekiHanHTML(r.hans) : ''}
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
      <p class="ks-myoji" data-ks-myoji>${esc(myojiLine(ctx.myoji, name))}</p>
    </header>
    ${toc}
    <div class="ks-rows">${body}</div>
    ${art}
    <p class="ks-note">${esc(t('ks.note'))}</p>
    ${extra}
    <div class="ks-actions">
      <button type="button" class="btn" data-act="ks-image">${esc(t('ks.image'))}</button>
      <button type="button" class="btn btn-ghost" data-act="ks-link">${esc(t('ks.link'))}</button>
      ${ctx.pt ? `<a class="btn btn-ghost ks-3d" href="3d.html#here=${ctx.pt[0].toFixed(4)},${ctx.pt[1].toFixed(4)}&hn=${encodeURIComponent(lang === 'en' && ctx.props.en ? ctx.props.en : ctx.props.name)}&lang=${lang}">${esc(t('ks.3d'))}</a>
      <a class="btn btn-ghost ks-look" href="3d.html#look=${ctx.pt[0].toFixed(4)},${ctx.pt[1].toFixed(4)}&hn=${encodeURIComponent(lang === 'en' && ctx.props.en ? ctx.props.en : ctx.props.name)}&lang=${lang}">${esc(t('ks.look'))}</a>` : ''}
    </div>
    <p class="fix-row">${fixLink(t('fix.w.ks', { name: title }))}</p>`;
}

// ── 存成图片：竖版 1080 宽，和纸底、朱印，文字自动折行 ──
// 按词折行：连续的字母数字（含 . , ' - 等）不拆开，汉字假名逐字
export function wrap(ctx, text, max) {
  const out = [];
  let line = '';
  for (const tok of text.match(/[\w.,'’()\-–]+\s*|\s+|./gu) || []) {
    if (ctx.measureText(line + tok).width > max && line.trim()) { out.push(line.trimEnd()); line = tok.trimStart(); } else line += tok;
  }
  if (line) out.push(line);
  return out;
}

// town：此地年表（hometownItems 的结果），画在各栏之后；彼时今日条目带诞生 / 忌日字样
export async function kosekiImage(ctxInfo, data, name, town = null) {
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
    const tl = [];
    if (town?.items.length) {
      y += 40;
      const head = y;
      y += 70;
      for (const x of town.items) {
        g.font = `700 30px ${serif}`;
        const text = `${x.main}${x.tag ? ` · ${t(`kk.t.${x.tag}`)}` : ''}`;
        const main = wrap(g, text, W - PAD * 2 - 200);
        g.font = `400 24px ${sans}`;
        const sub = x.sub ? wrap(g, x.sub, W - PAD * 2 - 200) : [];
        tl.push({ x, main, sub, y });
        y += main.length * 40 + sub.length * 32 + 14;
      }
      tl.head = head;
    }
    return { items, tl, H: y + 170 };
  };
  let { items, tl, H } = layout();
  c.width = W;
  c.height = H;
  ({ items, tl, H } = layout());
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
  if (tl.length) {
    g.fillStyle = '#3a1f1c';
    g.fillRect(PAD, tl.head, W - PAD * 2, 3);
    g.font = `900 40px ${serif}`;
    g.fillStyle = '#2b2420';
    g.fillText(t('ht.h'), PAD, tl.head + 18);
    // 左边一条竖线串起年份
    g.fillStyle = '#c9a67a';
    g.fillRect(PAD + 6, tl[0].y + 6, 3, tl.at(-1).y - tl[0].y + 20);
    for (const { x, main, sub, y } of tl) {
      g.fillStyle = x.kind === 'kako' ? '#8a5a2b' : x.kind === 'anc' || x.kind === 'now' ? '#c9a67a' : '#8a3b33';
      g.beginPath();
      g.arc(PAD + 7.5, y + 16, 8, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = '#8a3b33';
      g.font = `700 26px ${serif}`;
      g.fillText(x.yl, PAD + 30, y + 2);
      g.fillStyle = '#2b2420';
      g.font = `${x.kind === 'kako' ? 600 : 700} 30px ${serif}`;
      main.forEach((l, i) => g.fillText(l, PAD + 200, y + i * 40));
      g.fillStyle = '#5a4a3e';
      g.font = `400 24px ${sans}`;
      sub.forEach((l, i) => g.fillText(l, PAD + 200, y + 4 + main.length * 40 + i * 32));
    }
  }
  g.fillStyle = '#8a7a68';
  g.font = `400 24px ${sans}`;
  g.fillText('Japan Explorer · nickrockwall.github.io/japan-explorer', PAD, H - 100);
  return new Promise((res) => c.toBlob(res, 'image/png'));
}
