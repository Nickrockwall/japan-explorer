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
    bt: '合战', 'bt.title': '在立体地形上重演五场合战', 'bt.pick': '选一场合战', 'bt.note': '与平面地图「合战演武」同一份资料；战国以外的两场不着势力色。',
    'bt.prev': '上一段', 'bt.next': '下一段', 'bt.auto': '自动推演', 'bt.stop': '停止', 'bt.exit': '退出合战',
    search: '搜索', searchPh: '国名、城名或家名', 'k.prov': '国', 'k.castle': '城', 'k.clan': '家', none: '没有找到',
    north: '朝北', tilt: '俯视 / 斜看', 'o.sound': '声音', save: '把这个画面存成图片', back2d: '回到平面地图',
    play: '从 1467 播到 1600', dlN: '正在下载… {n} / {m}',
    'c.provs': '{n} 国', 'c.split': '另有 {n} 国分治', 'c.koku': '推算石高约 {n} 万石', 'c.kokuGe': '推算石高 ≥{n} 万石（奥羽按郡的分区没有石高）', 'c.rank': '当年第 {n}', 'c.head': '代表人物', 'c.note': '石高按 1598 年太阁检地的各国国高推算，分治的国按家数平分。',
    'p.life': '{a}–{b}', 'p.back': '‹ 返回', 'p.img': '肖像：{l}', holder: '{y} 年这里属于', bc: '约 {c} 世纪筑城（信息框只写到世纪）',
    'save.title': '立体战国图 · {y} 年',
    'st.between': '{a} → {b} 之间', 'st.open': '开场', 'st.n': '{n} 件事', 'st.replay': '重演这场合战',
    'cap.kyo': '京', 'cap.tenka': '天下', 'cap.title': '{y} 年的天下', 'cap.sub': '京都 · 名义上与实际上谁说了算', 'cap.emp': '天皇', 'cap.shogun': '将军', 'cap.nominal': '名义上', 'cap.real': '实际掌权', 'cap.seat': '政权所在', 'cap.more': '在年表里看各时期的实权',
    heian: '平安京（条坊示意）', heianNote: '地图上京都的方格是平安京的条坊（示意）：战国时京都已缩成上京、下京两块，街道大多还在。', 'o.motion': '动态（海浪、旗、雾、炊烟）',
    more: '其余 {n} 家', ryukyu: '琉球', view: '平面或立体', flat2d: '平面', flat3d: '立体',
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
    bt: 'Battles', 'bt.title': 'Replay five battles on the 3D terrain', 'bt.pick': 'Pick a battle', 'bt.note': "Same material as the 2D map's battle mode; the two outside the Sengoku period are shown without clan colours.",
    'bt.prev': 'Back', 'bt.next': 'Next', 'bt.auto': 'Play', 'bt.stop': 'Stop', 'bt.exit': 'Leave the battle',
    search: 'Search', searchPh: 'Province, castle or clan', 'k.prov': 'Province', 'k.castle': 'Castle', 'k.clan': 'Clan', none: 'Nothing found',
    north: 'Face north', tilt: 'Top-down / tilted', 'o.sound': 'Sound', save: 'Save this view as an image', back2d: 'Back to the 2D map',
    play: 'Play 1467 to 1600', dlN: 'Downloading… {n} / {m}',
    'c.provs': '{n} provinces', 'c.split': 'plus {n} shared', 'c.koku': 'about {n} koku (estimated)', 'c.kokuGe': 'at least {n} koku (the Ōu district units have no koku figures)', 'c.rank': 'No. {n} that year', 'c.head': 'Leading figure', 'c.note': 'Koku estimated from the 1598 Taikō land survey, province by province; shared provinces are split evenly.',
    'p.life': '{a}–{b}', 'p.back': '‹ Back', 'p.img': 'Portrait: {l}', holder: 'In {y} this was held by', bc: 'built around the {c}th century (the infobox gives only the century)',
    'save.title': '3D Sengoku Map · {y}',
    'st.between': 'Between {a} and {b}', 'st.open': 'Opening', 'st.n': '{n} events', 'st.replay': 'Replay this battle',
    'cap.kyo': 'Kyō', 'cap.tenka': 'The realm', 'cap.title': 'Who held the realm in {y}', 'cap.sub': 'Kyoto · who was in charge, in name and in fact', 'cap.emp': 'Emperor', 'cap.shogun': 'Shogun', 'cap.nominal': 'In name', 'cap.real': 'In fact', 'cap.seat': 'Seat of power', 'cap.more': 'See who held power in each period',
    heian: 'Heian-kyō street grid (schematic)', heianNote: 'The grid drawn at Kyoto is the street plan of Heian-kyō (schematic). By the Sengoku period the city had shrunk to two parts, Kamigyō and Shimogyō, though most streets survived.', 'o.motion': 'Motion (waves, banners, mist, smoke)',
    more: '{n} more', ryukyu: 'Ryūkyū', view: '2D or 3D', flat2d: '2D', flat3d: '3D',
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
    bt: '合戦', 'bt.title': '立体の地形で五つの合戦を再現', 'bt.pick': '合戦を選ぶ', 'bt.note': '平面地図の「合戦演武」と同じ資料。戦国以外の二つは勢力の色を付けません。',
    'bt.prev': '前へ', 'bt.next': '次へ', 'bt.auto': '自動で進む', 'bt.stop': '止める', 'bt.exit': '合戦を終える',
    search: '検索', searchPh: '国名・城名・家名', 'k.prov': '国', 'k.castle': '城', 'k.clan': '家', none: '見つかりません',
    north: '北を上に', tilt: '真上から / 斜めから', 'o.sound': '音', save: 'この画面を画像で保存', back2d: '平面地図に戻る',
    play: '1467年から1600年まで再生', dlN: 'ダウンロード中… {n} / {m}',
    'c.provs': '{n} か国', 'c.split': 'ほかに分割 {n} か国', 'c.koku': '推定石高 約{n}万石', 'c.kokuGe': '推定石高 {n}万石以上（奥羽の郡単位の区分は石高なし）', 'c.rank': 'その年の第 {n} 位', 'c.head': '代表的な人物', 'c.note': '石高は1598年の太閤検地の国高から推定。分割の国は家の数で等分。',
    'p.life': '{a}–{b}', 'p.back': '‹ 戻る', 'p.img': '肖像：{l}', holder: '{y}年にここを治めていたのは', bc: '{c}世紀ごろの築城（情報欄は世紀のみ）',
    'save.title': '立体戦国図 · {y}年',
    'st.between': '{a}→{b}のあいだ', 'st.open': 'はじまり', 'st.n': '{n} の出来事', 'st.replay': 'この合戦を再現',
    'cap.kyo': '京', 'cap.tenka': '天下', 'cap.title': '{y}年の天下', 'cap.sub': '京都 · 名目上と実際に誰が治めていたか', 'cap.emp': '天皇', 'cap.shogun': '将軍', 'cap.nominal': '名目上', 'cap.real': '実権', 'cap.seat': '政権の所在', 'cap.more': '年表で各時期の実権を見る',
    heian: '平安京（条坊・模式）', heianNote: '京都に描いた碁盤目は平安京の条坊（模式図）。戦国時代の京都は上京・下京の二つに縮んでいたが、通りの多くは残っていた。', 'o.motion': '動き（波・旗・霧・炊煙）',
    more: 'ほか {n} 家', ryukyu: '琉球', view: '平面か立体か', flat2d: '平面', flat3d: '立体',
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
  document.querySelectorAll('[data-t-ph]').forEach((el) => { el.placeholder = t(el.dataset.tPh); });
  document.querySelectorAll('[data-t-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.tAria)); });
}
