// 当前地图（日本 / 以后的朝鲜半岛）：与语言一样在页面加载时确定，切换地图走整页重载。
// 规则（pickMap）：链接里的 map= 是已登记的地图 → 用它；否则链接里有 pref=（老链接都是日本）→ 日本；
// 否则上次看的地图；都没有 → 日本。日本模式的数据路径与存储键保持原样，老用户的进度不受影响。
// 不 import store.js（store.js 要用这里的配置），本地存储直接读写。

export const MAPS = {
  japan: { key: 'japan', geo: 'src/assets/geojson/japan.json', data: 'src/data', units: 47, store: 'je.' },
  korea: { key: 'korea', geo: 'src/data/korea/regions.json', data: 'src/data/korea', units: 29, store: 'je.korea.' },
};

const SAVED_KEY = 'je.ui.map';

export function pickMap(hash, saved) {
  const h = new URLSearchParams(String(hash || '').replace(/^#/, ''));
  const want = h.get('map');
  if (MAPS[want]) return want;
  if (h.has('pref')) return 'japan';
  if (MAPS[saved]) return saved;
  return 'japan';
}

function readSaved() {
  try { return JSON.parse(localStorage.getItem(SAVED_KEY)); } catch { return null; }
}

export const mapKey = pickMap(location.hash, readSaved());
try { localStorage.setItem(SAVED_KEY, JSON.stringify(mapKey)); } catch { /* 隐私模式等情况下忽略 */ }

export const MAP = MAPS[mapKey];

// 换地图：地址栏只留语言和 map=，整页重载
export function setMap(key) {
  if (!MAPS[key] || key === mapKey) return;
  const old = new URLSearchParams(location.hash.slice(1));
  const h = new URLSearchParams();
  h.set('map', key);
  if (old.has('lang')) h.set('lang', old.get('lang'));
  location.hash = h.toString();
  location.reload();
}
