// 数据加载与浏览器本地存储（路径与键名按当前地图，见 country.js；日本即原来的路径与键名）
import { MAP } from './country.js';

const VISITED_KEY = `${MAP.store}visited`;
const API_KEY = 'je.api';

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${url}`);
  return res.json();
}

// 令制国真实边界（五畿七道滤镜用到时才下载）
export const loadProvinces = () => fetchJSON(`${MAP.data}/provinces.json`);
// 古国演变时间轴（用到时才下载）
export const loadProvinceEras = () => fetchJSON(`${MAP.data}/province_eras.json`);
// 战国势力图（68 国 × 6 个年份，用到时才下载）
// 彼时今日（几百年前的今天；读不到就不显示这一节）
// 江户诸藩的历代藩主（详卡用，用到时才下载）
export const loadHan = () => fetchJSON(`${MAP.data}/han.json`).catch(() => null);
export const loadKako = () => fetchJSON(`${MAP.data}/kako.json`).catch(() => null);
export const loadSengoku = () => fetchJSON(`${MAP.data}/sengoku.json`);
// 天皇 · 将军 · 执权年表与人物详写（人物卡用；读不到时人物卡只有基本信息）
export const loadRulers = () => fetchJSON(`${MAP.data}/rulers.json`).catch(() => null);
export const loadBios = () => fetchJSON(`${MAP.data}/people.json`).catch(() => ({}));

// 优先读取 tools/build_bundle.py 生成的单文件包（每种语言 1 个请求）；
// 包不存在时回退为逐个文件加载
export async function loadAll(lang = 'zh', merge = (b) => b) {
  const geoP = fetchJSON(MAP.geo);
  try {
    const b = await fetchJSON(`${MAP.data}/bundle/${lang}.json`);
    return { index: b.index, geo: await geoP, events: b.events, prefs: new Map(b.prefs.map((p) => [p.id, p])), pilgrimage: b.pilgrimage, hiroshige: b.hiroshige || [], provinceNames: b.province_names || [], koku: b.koku || [], kokuryoku: b.kokuryoku || null, domains: b.domains || null, emblems: b.emblems || {} };
  } catch {
    return loadFiles(lang, merge);
  }
}

// lang 不是中文时，按 src/data/i18n/manifest.json 载入已翻译的覆盖层并合并；
// 未翻译的县保持中文，并标记 _translated = false
async function loadFiles(lang, merge) {
  const [index, geo, events, manifest] = await Promise.all([
    fetchJSON(`${MAP.data}/index.json`),
    fetchJSON(MAP.geo),
    fetchJSON(`${MAP.data}/historical_events.json`),
    lang === 'zh' ? null : fetchJSON(`${MAP.data}/i18n/manifest.json`),
  ]);
  const done = new Set(manifest?.[lang]?.prefectures || []);
  const dir = `${MAP.data}/i18n/${lang}`;
  const prefs = await Promise.all(index.map(async (e) => {
    const base = await fetchJSON(`${MAP.data}/prefectures/${e.file}`);
    if (lang === 'zh') return { ...base, _translated: true };
    if (!done.has(e.id)) return { ...base, _translated: false };
    return { ...merge(base, await fetchJSON(`${dir}/prefectures/${e.file}`)), _translated: true };
  }));
  const ev = manifest?.[lang]?.events ? merge(events, await fetchJSON(`${dir}/historical_events.json`)) : events;
  // 圣地巡礼：译文按 id 叠加（与 tools/build_bundle.py 的 pilgrimage() 一致）
  const pil = await fetchJSON(`${MAP.data}/pilgrimage.json`);
  const over = lang === 'zh' ? {} : await fetchJSON(`${dir}/pilgrimage.json`).catch(() => ({}));
  const pilgrimage = { done: pil.done, spots: pil.spots.map((s) => ({ ...s, ...(over[s.id] || {}) })) };
  // 广重浮世绘只随数据包发布（题名译文、市区町村名由 build_bundle.py 拼好）；回退加载时不显示
  const kokuryoku = await fetchJSON(`${MAP.data}/kokuryoku.json`).catch(() => null);
  const emblems = Object.fromEntries(Object.entries(await fetchJSON(`${MAP.data}/emblems.json`).catch(() => ({}))).map(([k, v]) => [k, v.file]));
  return { index, geo, events: ev, prefs: new Map(prefs.map((p) => [p.id, p])), pilgrimage, hiroshige: [], provinceNames: [], koku: [], kokuryoku, emblems };
}

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    if (value == null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch { /* 隐私模式等情况下忽略 */ }
}

export const visited = {
  get: () => new Set(read(VISITED_KEY, [])),
  add(id) {
    const s = this.get();
    s.add(id);
    write(VISITED_KEY, [...s]);
    return s;
  },
  clear: () => write(VISITED_KEY, null),
};

// 御朱印：{ [id]: 盖印时间 ISO 字符串 }
const GOSHUIN_KEY = `${MAP.store}goshuin`;
export const goshuinBook = {
  get: () => read(GOSHUIN_KEY, {}),
  stamp(id) {
    const book = this.get();
    if (!book[id]) book[id] = new Date().toISOString();
    write(GOSHUIN_KEY, book);
    return book;
  },
  clear: () => write(GOSHUIN_KEY, null),
};

// 诸国一宫：{ [旧国]: { at 参拜时间, site 神社 id, real 是否亲临, realAt 亲临时间 } }
const ICHI_KEY = `${MAP.store}ichinomiya`;
export const ichinomiya = {
  get: () => read(ICHI_KEY, {}),
  pray(prov, site) {
    const book = this.get();
    if (!book[prov]) book[prov] = { at: new Date().toISOString(), site };
    write(ICHI_KEY, book);
    return book;
  },
  // 实地打卡：没参拜过的顺带记上参拜
  checkin(prov, site) {
    const book = this.get();
    const now = new Date().toISOString();
    book[prov] = { at: book[prov]?.at || now, site, real: true, realAt: now };
    write(ICHI_KEY, book);
    return book;
  },
  clear: () => write(ICHI_KEY, null),
};

// 半岛乡校：{ [Wikidata id]: { at 到访时间, real 是否亲临, realAt 亲临时间 } }
const HY_KEY = `${MAP.store}hyanggyo`;
export const hyanggyoBook = {
  get: () => read(HY_KEY, {}),
  visit(id) {
    const book = this.get();
    if (!book[id]) book[id] = { at: new Date().toISOString() };
    write(HY_KEY, book);
    return book;
  },
  // 实地打卡：没记过到访的顺带记上
  checkin(id) {
    const book = this.get();
    const now = new Date().toISOString();
    book[id] = { at: book[id]?.at || now, real: true, realAt: now };
    write(HY_KEY, book);
    return book;
  },
  clear: () => write(HY_KEY, null),
};

// 界面偏好：滤镜模式、向导模式、右侧上下比例。滤镜与图层每张地图各记各的，其余全站共用
const PER_MAP = new Set(['filter', 'layer']);
const prefKey = (name) => `${PER_MAP.has(name) ? MAP.store : 'je.'}ui.${name}`;
export const uiPref = {
  get: (name, fallback) => read(prefKey(name), fallback),
  set: (name, value) => write(prefKey(name), value),
};

export const DEFAULT_API = {
  claude: { baseUrl: 'https://api.anthropic.com/v1', model: 'claude-sonnet-5-5' },
  openai: { baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  gemini: { baseUrl: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-flash-lite-latest' },
};

export const apiConfig = {
  get: () => read(API_KEY, null),
  set: (cfg) => write(API_KEY, cfg),
  clear: () => write(API_KEY, null),
};
