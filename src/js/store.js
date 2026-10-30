// 数据加载与浏览器本地存储
const VISITED_KEY = 'je.visited';
const API_KEY = 'je.api';

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${url}`);
  return res.json();
}

export async function loadAll() {
  const [index, geo, events] = await Promise.all([
    fetchJSON('src/data/index.json'),
    fetchJSON('src/assets/geojson/japan.json'),
    fetchJSON('src/data/historical_events.json'),
  ]);
  const prefs = await Promise.all(index.map((e) => fetchJSON(`src/data/prefectures/${e.file}`)));
  return { index, geo, events, prefs: new Map(prefs.map((p) => [p.id, p])) };
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
