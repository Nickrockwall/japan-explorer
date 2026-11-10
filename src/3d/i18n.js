// 立体战国图的三种语言（中文 / English / 日本語）。不加载主站的词典（src/js/lang/ 每种约 60 KB），只放这一页用到的字。
// 语言与主站相同：链接 #lang= / ?lang= > 主站记住的语言（je.ui.lang）> 浏览器语言 > 中文
const LANGS = { zh: 'zh-CN', en: 'en', ja: 'ja' };

function detect() {
  const h = new URLSearchParams(location.hash.slice(1)).get('lang') || new URLSearchParams(location.search).get('lang');
  if (LANGS[h]) return h;
  try {
    const saved = JSON.parse(localStorage.getItem('je.ui.lang') || 'null');
    if (LANGS[saved]) return saved;
  } catch { /* 无痕模式 */ }
  for (const l of navigator.languages || [navigator.language || '']) {
    const s = String(l).toLowerCase();
    if (s.startsWith('ja')) return 'ja';
    if (s.startsWith('zh')) return 'zh';
    if (s.startsWith('en')) return 'en';
  }
  return 'zh';
}

export const lang = detect();

const S = {
  zh: {
    title: '立体战国图 · 古今日本地图', brand: '立体战国图', back: '← 平面地图', backTitle: '回到平面战国图',
    scene: '立体战国图：拖动平移，滚轮或双指缩放，右键或双指旋转', years: '年份',
    in: '拉近', out: '拉远', home: '回到全国', settings: '设置',
    exag: '地形起伏', real: '实际', quality: '画质', high: '高', low: '省电', show: '显示',
    'o.style': '屏风风格（青海波、描金、墨色）', 'o.tint': '势力着色', 'o.castles': '城', 'o.sites': '一宫·国府·国分寺', 'o.trees': '树林（拉近时）',
    hint: '拖动平移 · 滚轮缩放 · 右键拖动旋转 · 点一国看六个年份',
    credit: '地形：国土地理院 標高タイル · 湖河与土地覆盖：地球地図日本 · 城：Wikidata / 日文维基百科 · 渲染：three.js',
    loading: '正在加载…', noWebgl: '这台设备的浏览器不支持 WebGL，立体地图打不开。', dl: '正在下载地形…', build: '正在搭建地形…', fail: '加载失败：{m}',
    close: '关闭', split: '分治', part: '（{p}内的分区）', koku: ' · 1598 年石高约 {n} 万石', flat: '在平面战国图里看',
    castle: '城', built: '筑城 {y} 年', gone: ' · 废城 {y} 年',
    late: '1576 年安土城之后统一画成天守，', early: '1576 年安土城之前统一画成土垒与望楼，', castleNote: '只是示意，不代表这座城当年的样子。年份取自日文维基百科。',
    jawiki: '日文维基百科', ichi: '一宫', fu: '国府', ji: '国分寺', muni: ' · 位置只到市町村',
    siteNote: '古国三迹：律令时代各国的一宫、国府与国分寺，与平面地图「古国巡礼」相同。战国时多数国府与国分寺已经荒废。',
    more: '其余 {n} 家', ryukyu: '琉球',
  },
  en: {
    title: '3D Sengoku Map · Japan, Then and Now', brand: '3D Sengoku Map', back: '← 2D map', backTitle: 'Back to the 2D Sengoku map',
    scene: '3D Sengoku map: drag to pan, scroll or pinch to zoom, right-drag or two fingers to rotate', years: 'Year',
    in: 'Zoom in', out: 'Zoom out', home: 'Whole country', settings: 'Settings',
    exag: 'Terrain relief', real: 'Actual', quality: 'Quality', high: 'High', low: 'Saver', show: 'Show',
    'o.style': 'Folding-screen style (waves, gold, ink)', 'o.tint': 'Colour by power', 'o.castles': 'Castles', 'o.sites': 'Ichinomiya · kokufu · kokubunji', 'o.trees': 'Forests (close up)',
    hint: 'Drag to pan · scroll to zoom · right-drag to rotate · click a province for all six years',
    credit: 'Terrain: GSI elevation tiles · Lakes, rivers, land cover: Global Map Japan · Castles: Wikidata / Japanese Wikipedia · Rendering: three.js',
    loading: 'Loading…', noWebgl: "This browser doesn't support WebGL, so the 3D map can't open.", dl: 'Downloading terrain…', build: 'Building terrain…', fail: 'Failed to load: {m}',
    close: 'Close', split: 'split', part: ' (part of {p})', koku: ' · about {n} koku in 1598', flat: 'View on the 2D Sengoku map',
    castle: 'Castle', built: 'Built {y}', gone: ' · abandoned {y}',
    late: 'After Azuchi Castle (1576) every castle is drawn with a keep; ', early: 'Before Azuchi Castle (1576) every castle is drawn as earthworks and a watchtower; ', castleNote: "it's a symbol, not how this castle looked. Years from Japanese Wikipedia.",
    jawiki: 'Japanese Wikipedia', ichi: 'Ichinomiya', fu: 'Kokufu', ji: 'Kokubunji', muni: ' · located to the municipality only',
    siteNote: "Ancient sites: each province's chief shrine (ichinomiya), capital (kokufu) and provincial temple (kokubunji), as in the 2D map's Ancient sites layer. By the Sengoku period most capitals and temples were long abandoned.",
    more: '{n} more', ryukyu: 'Ryūkyū',
  },
  ja: {
    title: '立体戦国図 · 古今日本地図', brand: '立体戦国図', back: '← 平面地図', backTitle: '平面の戦国図に戻る',
    scene: '立体戦国図：ドラッグで移動、ホイールかピンチで拡大縮小、右ドラッグか二本指で回転', years: '年',
    in: '近づく', out: '遠ざかる', home: '全国を表示', settings: '設定',
    exag: '起伏の強調', real: '実寸', quality: '画質', high: '高', low: '省電力', show: '表示',
    'o.style': '屏風風（青海波・金泥・墨）', 'o.tint': '勢力で色分け', 'o.castles': '城', 'o.sites': '一宮・国府・国分寺', 'o.trees': '森（近づいたとき）',
    hint: 'ドラッグで移動 · ホイールで拡大縮小 · 右ドラッグで回転 · 国をクリックで六つの年',
    credit: '地形：国土地理院 標高タイル · 湖沼・河川・土地被覆：地球地図日本 · 城：Wikidata / 日本語版ウィキペディア · 描画：three.js',
    loading: '読み込み中…', noWebgl: 'このブラウザは WebGL に対応していないため、立体地図を開けません。', dl: '地形をダウンロード中…', build: '地形を組み立て中…', fail: '読み込みに失敗しました：{m}',
    close: '閉じる', split: '分割', part: '（{p}内の区分）', koku: ' · 1598年の石高 約{n}万石', flat: '平面の戦国図で見る',
    castle: '城', built: '築城 {y}年', gone: ' · 廃城 {y}年',
    late: '1576年の安土城以降はすべて天守で描いています。', early: '1576年の安土城以前はすべて土塁と櫓で描いています。', castleNote: '模式図で、その城の当時の姿ではありません。年は日本語版ウィキペディアによります。',
    jawiki: 'ウィキペディア', ichi: '一宮', fu: '国府', ji: '国分寺', muni: ' · 位置は市町村まで',
    siteNote: '旧国の三つの跡：律令時代の各国の一宮・国府・国分寺（平面地図の「古国めぐり」と同じ）。戦国時代には多くの国府・国分寺がすでに廃れていました。',
    more: 'ほか {n} 家', ryukyu: '琉球',
  },
};
export const t = (k, v = {}) => (S[lang][k] ?? S.zh[k] ?? k).replace(/\{(\w+)\}/g, (_, n) => v[n]);

// 带 {zh, en, ja} 的数据取当前语言，缺了退回中文 / 日文
export const nm = (o) => (o ? o[lang] || o.zh || o.ja || '' : '');

// 五畿七道（与主站 i18n.js 的 circuit 表相同）
const CIRCUIT = {
  畿内: ['畿内', 'Kinai', '畿内'], 东海道: ['东海道', 'Tōkaidō', '東海道'], 东山道: ['东山道', 'Tōsandō', '東山道'],
  北陆道: ['北陆道', 'Hokurikudō', '北陸道'], 山阴道: ['山阴道', "San'indō", '山陰道'], 山阳道: ['山阳道', "San'yōdō", '山陽道'],
  南海道: ['南海道', 'Nankaidō', '南海道'], 西海道: ['西海道', 'Saikaidō', '西海道'], 北海道: ['北海道（1869）', 'Hokkaidō (1869)', '北海道（1869）'],
  令制外: ['令制外', 'Outside the system', '令制外'],
};
export const circuit = (c) => CIRCUIT[c]?.[['zh', 'en', 'ja'].indexOf(lang)] ?? c;

// 静态文字：data-t（文字）、data-t-title、data-t-aria
export function applyStatic() {
  document.documentElement.lang = LANGS[lang];
  document.title = t('title');
  document.querySelectorAll('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll('[data-t-title]').forEach((el) => { el.title = t(el.dataset.tTitle); });
  document.querySelectorAll('[data-t-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.tAria)); });
}
