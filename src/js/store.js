// 数据加载与浏览器本地存储
const VISITED_KEY = 'je.visited';
const API_KEY = 'je.api';

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${url}`);
  return res.json();
}

// 令制国真实边界（五畿七道滤镜用到时才下载）
export const loadProvinces = () => fetchJSON('src/data/provinces.json');

// 优先读取 tools/build_bundle.py 生成的单文件包（每种语言 1 个请求）；
// 包不存在时回退为逐个文件加载
export async function loadAll(lang = 'zh', merge = (b) => b) {
  const geoP = fetchJSON('src/assets/geojson/japan.json');
  try {
    const b = await fetchJSON(`src/data/bundle/${lang}.json`);
    return { index: b.index, geo: await geoP, events: b.events, prefs: new Map(b.prefs.map((p) => [p.id, p])), pilgrimage: b.pilgrimage, hiroshige: b.hiroshige || [] };
  } catch {
    return loadFiles(lang, merge);
  }
}

// lang 不是中文时，按 src/data/i18n/manifest.json 载入已翻译的覆盖层并合并；
// 未翻译的县保持中文，并标记 _translated = false
async function loadFiles(lang, merge) {
  const [index, geo, events, manifest] = await Promise.all([
    fetchJSON('src/data/index.json'),
    fetchJSON('src/assets/geojson/japan.json'),
    fetchJSON('src/data/historical_events.json'),
    lang === 'zh' ? null : fetchJSON('src/data/i18n/manifest.json'),
  ]);
  const done = new Set(manifest?.[lang]?.prefectures || []);
  const dir = `src/data/i18n/${lang}`;
  const prefs = await Promise.all(index.map(async (e) => {
    const base = await fetchJSON(`src/data/prefectures/${e.file}`);
    if (lang === 'zh') return { ...base, _translated: true };
    if (!done.has(e.id)) return { ...base, _translated: false };
    return { ...merge(base, await fetchJSON(`${dir}/prefectures/${e.file}`)), _translated: true };
  }));
  const ev = manifest?.[lang]?.events ? merge(events, await fetchJSON(`${dir}/historical_events.json`)) : events;
  // 圣地巡礼：译文按 id 叠加（与 tools/build_bundle.py 的 pilgrimage() 一致）
  const pil = await fetchJSON('src/data/pilgrimage.json');
  const over = lang === 'zh' ? {} : await fetchJSON(`${dir}/pilgrimage.json`).catch(() => ({}));
  const pilgrimage = { done: pil.done, spots: pil.spots.map((s) => ({ ...s, ...(over[s.id] || {}) })) };
  // 广重浮世绘只随数据包发布（题名译文、市区町村名由 build_bundle.py 拼好）；回退加载时不显示
  return { index, geo, events: ev, prefs: new Map(prefs.map((p) => [p.id, p])), pilgrimage, hiroshige: [] };
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
const GOSHUIN_KEY = 'je.goshuin';
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

// 界面偏好：滤镜模式、向导模式、右侧上下比例
export const uiPref = {
  get: (name, fallback) => read(`je.ui.${name}`, fallback),
  set: (name, value) => write(`je.ui.${name}`, value),
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
