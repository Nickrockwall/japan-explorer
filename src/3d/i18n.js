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
    'help': "说明", 'h3.h': "怎么用", 'h3.first': "单指拖动平移，双指缩放与旋转；右上角「?」有完整说明。", 'h3.move.mouse.h': "移动镜头", 'h3.move.mouse': "拖动平移，滚轮缩放（对准哪里就往哪里拉近），右键拖动旋转。右边一列按钮：拉近、拉远、回到全国、朝北、俯视 / 斜看。", 'h3.move.touch.h': "移动镜头", 'h3.move.touch': "单指拖动平移，双指张合缩放、双指转动旋转。右边一列按钮：拉近、拉远、回到全国、朝北、俯视 / 斜看。", 'h3.time.h': "时代与年份", 'h3.time': "顶上一行选时代（古代、镰仓、室町、战国、江户、明治），旁边选年份。▶ 从当前年份一直播到 1888 年，每到一个年份先讲这期间发生的事；底部「这期间」列出两个年份之间的事，点开能飞过去。", 'h3.pick.h': "点地图", 'h3.pick': "点一块（国、藩、府县）看它在各个年份归谁；点图例里的一家，看它的领地、推算石高与代表人物。点城、社寺、宿场、浮世绘或「京」印，看各自的卡片；城的卡片列出它历年的主人，还能「登上天守」看四周。「京」的卡片里能展开历代实权，点一段跳到那时的年份。", 'h3.battle.h': "合战", 'h3.battle': "「合战」重演十场合战：行军路线一段段长出来，小旗按兵力插在主力所在的地方；面板里有每一段的经过、名将的话和「众说纷纭」。", 'h3.search.h': "搜索", 'h3.search': "🔍 能搜国、藩、府县、城和家；这一年没有的，会换到有它的年份。", 'h3.more.h': "设置与回平面图", 'h3.more': "⚙ 里调地形起伏、画质、屏风风格、要显示的东西、动态效果与声音，还能存图。左上角的链接与右下角的「平面」开关回平面地图，带着时代与地方。", 'h3.keys.h': "键盘", 'h3.keys': "方向键平移，+ / - 缩放，1–6 换这个时代的年份，[ ] 换时代，空格播放，N 朝北，T 俯视，Esc 关掉卡片与面板。",
  credit: '地形：国土地理院 標高タイル · 湖河与土地覆盖：地球地図日本 · 城：Wikidata / 日文维基百科 · 渲染：three.js',
    loading: '正在加载…', noWebgl: '这台设备的浏览器不支持 WebGL，立体地图打不开。', dl: '正在下载地形…', build: '正在搭建地形…', fail: '加载失败：{m}',
    close: '关闭', split: '分治', part: '（{p}内的分区）', koku: ' · 1598 年石高约 {n} 万石', flat: '在平面战国图里看',
    castle: '城', built: '筑城 {y} 年', ba: '约 {y} 年筑城（信息框写的是一段年号）', gone: ' · 废城 {y} 年',
    h100: '日本 100 名城 · 第 {n} 号', z100: '续日本 100 名城 · 第 {n} 号', 'tenshu.genzon': '现存天守：江户时代或更早建成、保存到今天的 12 座天守之一', 'tenshu.kokuho': '现存天守 · 国宝：现存 12 座天守里被定为国宝的 5 座之一', meijoNote: '100 名城、续 100 名城由日本城郭协会选定；名单与现存天守取自日文维基百科。',
    late: '1576 年安土城之后统一画成天守，', early: '1576 年安土城之前统一画成土垒与望楼，', castleNote: '只是示意，不代表这座城当年的样子。年份取自日文维基百科。',
    jawiki: '日文维基百科', ichi: '一宫', fu: '国府', ji: '国分寺', muni: ' · 位置只到市町村',
    siteNote: '古国三迹：律令时代各国的一宫、国府与国分寺，与平面地图「古国巡礼」相同。战国时多数国府与国分寺已经荒废。',
    bt: '合战', 'bt.title': '在立体地形上重演十场合战', 'bt.pick': '选一场合战', 'bt.note': '与平面地图「合战演武」同一份资料；战国以外的两场不着势力色。',
    'bt.prev': '上一段', 'bt.next': '下一段', 'bt.auto': '自动推演', 'bt.stop': '停止', 'bt.exit': '退出合战',
    search: '搜索', searchPh: '国名、城名或家名', 'k.prov': '国', 'k.castle': '城', 'k.clan': '家', none: '没有找到',
    north: '朝北', tilt: '俯视 / 斜看', 'o.sound': '声音', save: '把这个画面存成图片', back2d: '回到平面地图',
    play: '从 1467 播到 1600', dlN: '正在下载… {n} / {m}',
    'c.provs': '{n} 国', 'c.split': '另有 {n} 国分治', 'c.koku': '推算石高约 {n} 万石', 'c.kokuGe': '推算石高 ≥{n} 万石（奥羽按郡的分区没有石高）', 'c.rank': '当年第 {n}', 'c.head': '代表人物', 'c.note': '石高按 1598 年太阁检地的各国国高推算，分治的国按家数平分。',
    'here.go': '看此地千年', 'h3.here.h': '此地千年', 'h3.here': '长按（手机）或右键单击（电脑）地面，或点开一块后按「看此地千年」：镜头停在那里，从 712 年一年年播到 1888 年，列出这里归哪一国、归谁。', 'pw.all': '历代实权（20 段）', 'pw.allNote': '与平面图年表「实权」页同一份资料；点一段换到落在这一段里的第一个年份，没有立体年份的段不能点。', 'pw.early': '古代', 'here.h': '此地千年 · {name}', 'here.here': '这里', 'here.note': '镜头停在这个地方，从 712 年一年年播到 1888 年；写的是这里在各个年份属于哪一国（藩、府县）、归谁。点一行回到那一年。', 'look.tenshu': '登上天守远望', 'look.yagura': '登上望楼远望', 'look.tip': '拖动环顾四周', 'look.back': '回到地图', 'life.h': '这一带历年归谁', 'life.none': '没有记录', 'life.loading': '江户、明治的年份正在下载……', 'life.note': '写的是城所在的这一块在各个年份归哪一家（藩、府县），不一定是城主本人；点一行换到那一年。', 'p.life': '{a}–{b}', 'p.back': '‹ 返回', 'p.img': '肖像：{l}', holder: '{y} 年这里属于', bc: '约 {c} 世纪筑城（信息框只写了世纪或时代）',
    'save.title': '立体战国图 · {y} 年',
    'st.between': '{a} → {b} 之间', 'st.open': '开场', 'st.n': '{n} 件事', 'st.replay': '重演这场合战',
    'cap.kyo': '京', 'cap.tenka': '天下', 'cap.title': '{y} 年的天下', 'cap.sub': '京都 · 名义上与实际上谁说了算', 'cap.emp': '天皇', 'cap.shogun': '将军', 'cap.nominal': '名义上', 'cap.real': '实际掌权', 'cap.seat': '政权所在', 'cap.more': '在年表里看各时期的实权',
    heian: '平安京（条坊示意）', heianNote: '地图上京都的方格是平安京的条坊（示意）：战国时京都已缩成上京、下京两块，街道大多还在。', 'o.motion': '动态（海浪、旗、雾、炊烟）', slowMotion: '画面有点卡，已关掉动态效果（海浪、旗、炊烟）。想要的话可以在设置 ⚙ 里再打开。',
    more: '其余 {n} 家', ryukyu: '琉球', view: '平面或立体', flat2d: '平面', flat3d: '立体',
  },
  en: {
    title: '3D Sengoku Map · Japan, Then and Now', brand: '3D Sengoku Map', back: '← 2D map', backTitle: 'Back to the 2D Sengoku map',
    scene: '3D Sengoku map: drag to pan, scroll or pinch to zoom, right-drag or two fingers to rotate', years: 'Year',
    in: 'Zoom in', out: 'Zoom out', home: 'Whole country', settings: 'Settings',
    exag: 'Terrain relief', real: 'Actual', quality: 'Quality', high: 'High', low: 'Saver', show: 'Show',
    'o.style': 'Folding-screen style (waves, gold, ink)', 'o.tint': 'Colour by power', 'o.castles': 'Castles', 'o.sites': 'Ichinomiya · kokufu · kokubunji', 'o.trees': 'Forests (close up)',
    hint: 'Drag to pan · scroll to zoom · right-drag to rotate · click a province for all six years',
    'help': "Help", 'h3.h': "How to use", 'h3.first': "Drag with one finger to move; pinch and twist with two to zoom and rotate. Full help is under \"?\" at the top right.", 'h3.move.mouse.h': "Moving around", 'h3.move.mouse': "Drag to pan, scroll to zoom (towards the pointer), right-drag to rotate. The buttons on the right zoom in and out, go back to the whole country, face north and switch between top-down and angled views.", 'h3.move.touch.h': "Moving around", 'h3.move.touch': "Drag with one finger to pan; pinch to zoom and twist with two fingers to rotate. The buttons on the right zoom in and out, go back to the whole country, face north and switch between top-down and angled views.", 'h3.time.h': "Periods and years", 'h3.time': "Pick a period in the top row (Ancient, Kamakura, Muromachi, Sengoku, Edo, Meiji) and a year beside it. ▶ plays from the current year to 1888, telling what happened in between before each year; \"In between\" at the bottom lists those events and flies to each.", 'h3.pick.h': "Tapping the map", 'h3.pick': "Tap an area (province, domain or prefecture) to see who held it in each year; tap a family in the legend for its lands, estimated koku and leading figure. Castles, shrines and temples, post towns, prints and the capital seal each have a card; a castle card lists its holders over the years and lets you climb the keep to look around. The capital card can expand every period of who held power; tap one to jump to a year in it.", 'h3.battle.h': "Battles", 'h3.battle': "\"Battles\" replays ten battles: the march routes grow phase by phase and small banners show each side's strength where its main army stands; the panel tells each phase, quotes the commander and explains what historians still argue about.", 'h3.search.h': "Search", 'h3.search': "🔍 finds provinces, domains, prefectures, castles and families; if one is not there this year, the map moves to a year when it was.", 'h3.more.h': "Settings and the 2D map", 'h3.more': "⚙ sets terrain height, quality, the folding-screen style, what to show, motion and sound, and saves an image. The link at the top left and the \"2D\" switch at the bottom right go back to the 2D map with the same period and place.", 'h3.keys.h': "Keyboard", 'h3.keys': "Arrow keys pan, + / - zoom, 1–6 pick a year in this period, [ ] change period, Space plays, N faces north, T toggles top-down, Esc closes cards and panels.",
  credit: 'Terrain: GSI elevation tiles · Lakes, rivers, land cover: Global Map Japan · Castles: Wikidata / Japanese Wikipedia · Rendering: three.js',
    loading: 'Loading…', noWebgl: "This browser doesn't support WebGL, so the 3D map can't open.", dl: 'Downloading terrain…', build: 'Building terrain…', fail: 'Failed to load: {m}',
    close: 'Close', split: 'split', part: ' (part of {p})', koku: ' · about {n} koku in 1598', flat: 'View on the 2D Sengoku map',
    castle: 'Castle', built: 'Built {y}', ba: 'Built c. {y} (the infobox gives an era range)', gone: ' · abandoned {y}',
    h100: 'Japan’s 100 Fine Castles · No. {n}', z100: 'Next 100 Fine Castles · No. {n}', 'tenshu.genzon': 'Original keep: one of the 12 keeps built in the Edo period or earlier that still stand', 'tenshu.kokuho': 'Original keep · National Treasure: one of the 5 of the 12 surviving keeps listed as National Treasures', meijoNote: 'The 100 and Next 100 Fine Castles were chosen by the Japan Castle Foundation; lists and surviving keeps from Japanese Wikipedia.',
    late: 'After Azuchi Castle (1576) every castle is drawn with a keep; ', early: 'Before Azuchi Castle (1576) every castle is drawn as earthworks and a watchtower; ', castleNote: "it's a symbol, not how this castle looked. Years from Japanese Wikipedia.",
    jawiki: 'Japanese Wikipedia', ichi: 'Ichinomiya', fu: 'Kokufu', ji: 'Kokubunji', muni: ' · located to the municipality only',
    siteNote: "Ancient sites: each province's chief shrine (ichinomiya), capital (kokufu) and provincial temple (kokubunji), as in the 2D map's Ancient sites layer. By the Sengoku period most capitals and temples were long abandoned.",
    bt: 'Battles', 'bt.title': 'Replay ten battles on the 3D terrain', 'bt.pick': 'Pick a battle', 'bt.note': "Same material as the 2D map's battle mode; the two outside the Sengoku period are shown without clan colours.",
    'bt.prev': 'Back', 'bt.next': 'Next', 'bt.auto': 'Play', 'bt.stop': 'Stop', 'bt.exit': 'Leave the battle',
    search: 'Search', searchPh: 'Province, castle or clan', 'k.prov': 'Province', 'k.castle': 'Castle', 'k.clan': 'Clan', none: 'Nothing found',
    north: 'Face north', tilt: 'Top-down / tilted', 'o.sound': 'Sound', save: 'Save this view as an image', back2d: 'Back to the 2D map',
    play: 'Play 1467 to 1600', dlN: 'Downloading… {n} / {m}',
    'c.provs': '{n} provinces', 'c.split': 'plus {n} shared', 'c.koku': 'about {n} koku (estimated)', 'c.kokuGe': 'at least {n} koku (the Ōu district units have no koku figures)', 'c.rank': 'No. {n} that year', 'c.head': 'Leading figure', 'c.note': 'Koku estimated from the 1598 Taikō land survey, province by province; shared provinces are split evenly.',
    'here.go': 'A thousand years here', 'h3.here.h': 'A thousand years here', 'h3.here': 'Long-press (phone) or right-click (computer) the ground, or open an area and press "A thousand years here": the camera stays on that spot and plays from 712 to 1888, listing which province it was in and who held it.', 'pw.all': 'Who held power, all 20 periods', 'pw.allNote': 'The same data as the "Power" page of the year tables on the flat map. Tap a period to jump to the first 3D year in it; periods without a 3D year are not clickable.', 'pw.early': 'Ancient', 'here.h': 'A thousand years here · {name}', 'here.here': 'Here', 'here.note': 'The camera stays on this spot and plays from 712 to 1888, noting which province (domain, prefecture) it was in and who held it. Tap a row to go back to that year.', 'look.tenshu': 'Climb the keep and look around', 'look.yagura': 'Climb the watchtower and look around', 'look.tip': 'Drag to look around', 'look.back': 'Back to the map', 'life.h': 'Who held this area', 'life.none': 'not recorded', 'life.loading': 'Loading the Edo and Meiji years…', 'life.note': 'Who held the area around the castle in each map year (family, domain or prefecture) — not necessarily the castle’s own lord. Tap a row to go to that year.', 'p.life': '{a}–{b}', 'p.back': '‹ Back', 'p.img': 'Portrait: {l}', holder: 'In {y} this was held by', bc: 'built around the {c}th century (the infobox gives only the century or period)',
    'save.title': '3D Sengoku Map · {y}',
    'st.between': 'Between {a} and {b}', 'st.open': 'Opening', 'st.n': '{n} events', 'st.replay': 'Replay this battle',
    'cap.kyo': 'Kyō', 'cap.tenka': 'The realm', 'cap.title': 'Who held the realm in {y}', 'cap.sub': 'Kyoto · who was in charge, in name and in fact', 'cap.emp': 'Emperor', 'cap.shogun': 'Shogun', 'cap.nominal': 'In name', 'cap.real': 'In fact', 'cap.seat': 'Seat of power', 'cap.more': 'See who held power in each period',
    heian: 'Heian-kyō street grid (schematic)', heianNote: 'The grid drawn at Kyoto is the street plan of Heian-kyō (schematic). By the Sengoku period the city had shrunk to two parts, Kamigyō and Shimogyō, though most streets survived.', 'o.motion': 'Motion (waves, banners, mist, smoke)', slowMotion: 'The view was running slowly, so motion (waves, banners, smoke) has been turned off. You can turn it back on in Settings ⚙.',
    more: '{n} more', ryukyu: 'Ryūkyū', view: '2D or 3D', flat2d: '2D', flat3d: '3D',
  },
  ja: {
    title: '立体戦国図 · 古今日本地図', brand: '立体戦国図', back: '← 平面地図', backTitle: '平面の戦国図に戻る',
    scene: '立体戦国図：ドラッグで移動、ホイールかピンチで拡大縮小、右ドラッグか二本指で回転', years: '年',
    in: '近づく', out: '遠ざかる', home: '全国を表示', settings: '設定',
    exag: '起伏の強調', real: '実寸', quality: '画質', high: '高', low: '省電力', show: '表示',
    'o.style': '屏風風（青海波・金泥・墨）', 'o.tint': '勢力で色分け', 'o.castles': '城', 'o.sites': '一宮・国府・国分寺', 'o.trees': '森（近づいたとき）',
    hint: 'ドラッグで移動 · ホイールで拡大縮小 · 右ドラッグで回転 · 国をクリックで六つの年',
    'help': "使い方", 'h3.h': "使い方", 'h3.first': "1本指でドラッグして移動、2本指で拡大縮小と回転。右上の「?」に詳しい使い方があります。", 'h3.move.mouse.h': "視点の移動", 'h3.move.mouse': "ドラッグで移動、ホイールで拡大縮小（ポインタの方へ寄ります）、右ドラッグで回転。右側のボタンは拡大・縮小・全国に戻る・北を上に・真上から / 斜めから。", 'h3.move.touch.h': "視点の移動", 'h3.move.touch': "1本指のドラッグで移動、2本指のピンチで拡大縮小、ひねって回転。右側のボタンは拡大・縮小・全国に戻る・北を上に・真上から / 斜めから。", 'h3.time.h': "時代と年", 'h3.time': "上の列で時代（古代・鎌倉・室町・戦国・江戸・明治）を選び、隣で年を選びます。▶ で今の年から1888年まで、年ごとにそのあいだの出来事を語りながら再生。下の「このあいだ」には年と年のあいだの出来事が並び、開くとその場所へ飛びます。", 'h3.pick.h': "地図をタップ", 'h3.pick': "国・藩・府県をタップすると各年に誰のものだったか。凡例の家をタップするとその領地・推定石高・代表人物。城・社寺・宿場・浮世絵・「京」の印にもそれぞれカードがあり、城のカードには歴代の持ち主と「天守に登る」があります。「京」のカードでは歴代の実権を開き、時期をタップするとその年に移れます。", 'h3.battle.h': "合戦", 'h3.battle': "「合戦」で十の合戦を再現：進軍路が段階ごとにのび、兵力に応じた小旗が主力のいる所に立ちます。パネルには各段階の経過、武将の言葉、「諸説あり」の解説。", 'h3.search.h': "検索", 'h3.search': "🔍 で国・藩・府県・城・家を探せます。その年にないものは、あった年に切り替えます。", 'h3.more.h': "設定と平面地図", 'h3.more': "⚙ で地形の起伏・画質・屏風風・表示するもの・動き・音を設定、画像の保存も。左上のリンクと右下の「平面」スイッチで、同じ時代と場所のまま平面地図に戻ります。", 'h3.keys.h': "キーボード", 'h3.keys': "矢印キーで移動、+ / - で拡大縮小、1–6 でこの時代の年、[ ] で時代、スペースで再生、N で北を上、T で真上から、Esc でカードやパネルを閉じます。",
    credit: '地形：国土地理院 標高タイル · 湖沼・河川・土地被覆：地球地図日本 · 城：Wikidata / 日本語版ウィキペディア · 描画：three.js',
    loading: '読み込み中…', noWebgl: 'このブラウザは WebGL に対応していないため、立体地図を開けません。', dl: '地形をダウンロード中…', build: '地形を組み立て中…', fail: '読み込みに失敗しました：{m}',
    close: '閉じる', split: '分割', part: '（{p}内の区分）', koku: ' · 1598年の石高 約{n}万石', flat: '平面の戦国図で見る',
    castle: '城', built: '築城 {y}年', ba: '{y}年ごろ築城（情報欄は年号の期間）', gone: ' · 廃城 {y}年',
    h100: '日本100名城 · {n}番', z100: '続日本100名城 · {n}番', 'tenshu.genzon': '現存天守：江戸時代以前に建てられ今に残る12の天守の一つ', 'tenshu.kokuho': '現存天守・国宝：現存12天守のうち国宝の5城の一つ', meijoNote: '100名城・続100名城は日本城郭協会の選定。名簿と現存天守は日本語版ウィキペディアによります。',
    late: '1576年の安土城以降はすべて天守で描いています。', early: '1576年の安土城以前はすべて土塁と櫓で描いています。', castleNote: '模式図で、その城の当時の姿ではありません。年は日本語版ウィキペディアによります。',
    jawiki: 'ウィキペディア', ichi: '一宮', fu: '国府', ji: '国分寺', muni: ' · 位置は市町村まで',
    siteNote: '旧国の三つの跡：律令時代の各国の一宮・国府・国分寺（平面地図の「古国めぐり」と同じ）。戦国時代には多くの国府・国分寺がすでに廃れていました。',
    bt: '合戦', 'bt.title': '立体の地形で十の合戦を再現', 'bt.pick': '合戦を選ぶ', 'bt.note': '平面地図の「合戦演武」と同じ資料。戦国以外の二つは勢力の色を付けません。',
    'bt.prev': '前へ', 'bt.next': '次へ', 'bt.auto': '自動で進む', 'bt.stop': '止める', 'bt.exit': '合戦を終える',
    search: '検索', searchPh: '国名・城名・家名', 'k.prov': '国', 'k.castle': '城', 'k.clan': '家', none: '見つかりません',
    north: '北を上に', tilt: '真上から / 斜めから', 'o.sound': '音', save: 'この画面を画像で保存', back2d: '平面地図に戻る',
    play: '1467年から1600年まで再生', dlN: 'ダウンロード中… {n} / {m}',
    'c.provs': '{n} か国', 'c.split': 'ほかに分割 {n} か国', 'c.koku': '推定石高 約{n}万石', 'c.kokuGe': '推定石高 {n}万石以上（奥羽の郡単位の区分は石高なし）', 'c.rank': 'その年の第 {n} 位', 'c.head': '代表的な人物', 'c.note': '石高は1598年の太閤検地の国高から推定。分割の国は家の数で等分。',
    'here.go': 'この地の千年を見る', 'h3.here.h': 'この地の千年', 'h3.here': '地面を長押し（スマホ）か右クリック（パソコン）、または区域を開いて「この地の千年を見る」：その場所に視点をとめ、712年から1888年まで、どの国に属し誰のものだったかを並べます。', 'pw.all': '歴代の実権（20期）', 'pw.allNote': '平面地図の年表「実権」と同じ資料。時期をタップするとその時期に入る最初の年に移ります（立体地図の年がない時期は押せません）。', 'pw.early': '古代', 'here.h': 'この地の千年 · {name}', 'here.here': 'ここ', 'here.note': 'この場所に視点をとめ、712年から1888年まで年ごとに、どの国（藩・府県）に属し誰のものだったかを記します。行をタップするとその年に戻ります。', 'look.tenshu': '天守に登って見渡す', 'look.yagura': '櫓に登って見渡す', 'look.tip': 'ドラッグで見回す', 'look.back': '地図に戻る', 'life.h': 'この一帯の歴代の持ち主', 'life.none': '記録なし', 'life.loading': '江戸・明治の年を読み込み中……', 'life.note': '城のある一帯が各年にどの家（藩・府県）のものだったか。城主本人とは限りません。行をタップするとその年へ。', 'p.life': '{a}–{b}', 'p.back': '‹ 戻る', 'p.img': '肖像：{l}', holder: '{y}年にここを治めていたのは', bc: '{c}世紀ごろの築城（情報欄は世紀・時代のみ）',
    'save.title': '立体戦国図 · {y}年',
    'st.between': '{a}→{b}のあいだ', 'st.open': 'はじまり', 'st.n': '{n} の出来事', 'st.replay': 'この合戦を再現',
    'cap.kyo': '京', 'cap.tenka': '天下', 'cap.title': '{y}年の天下', 'cap.sub': '京都 · 名目上と実際に誰が治めていたか', 'cap.emp': '天皇', 'cap.shogun': '将軍', 'cap.nominal': '名目上', 'cap.real': '実権', 'cap.seat': '政権の所在', 'cap.more': '年表で各時期の実権を見る',
    heian: '平安京（条坊・模式）', heianNote: '京都に描いた碁盤目は平安京の条坊（模式図）。戦国時代の京都は上京・下京の二つに縮んでいたが、通りの多くは残っていた。', 'o.motion': '動き（波・旗・霧・炊煙）', slowMotion: '動作が重いため、動き（波・旗・炊煙）を止めました。設定 ⚙ からまたオンにできます。',
    more: 'ほか {n} 家', ryukyu: '琉球', view: '平面か立体か', flat2d: '平面', flat3d: '立体',
  },
};
// 3.35：五个时代（古代、镰仓、战国、江户、明治），3.38 加室町
Object.assign(S.zh, {
  'k.gap': '名单这几年空着，前后都是这一家',
  title: '立体古今图 · 古今日本地图', brand: '立体古今图', scene: '立体古今图：拖动平移，滚轮或双指缩放，右键或双指旋转', backTitle: '回到平面地图', hint: '拖动平移 · 滚轮缩放 · 右键拖动旋转 · 点一块看各个年份',
  play: '从这一年一直播到 1888', 'save.title': '立体古今图 · {y} 年', eras: '时代',
  'era.kodai': '古代', 'era.kamakura': '镰仓', 'era.muromachi': '室町', 'era.sengoku': '战国', 'era.edo': '江户', 'era.meiji': '明治',
  'era.kodai.span': '律令国家：712 / 757 / 824 年的国界与五畿七道', 'era.kamakura.span': '镰仓幕府：各国守护（1200 / 1250 / 1300）', 'era.muromachi.span': '室町幕府：各国守护（1350 / 1400 / 1440）', 'era.sengoku.span': '战国大名（1467–1600）', 'era.edo.span': '幕末的藩领（1867）', 'era.meiji.span': '废藩置县到府县定型（1871 / 1876 / 1888）',
  eraLoading: '正在下载这个时代的资料…', eraFail: '这个时代的资料没下载下来，稍后再试',
  'cap.seal.kyo': '京', 'cap.seal.heijo': '京', 'cap.seal.tokyo': '東', 'cap.name.kyo': '京都', 'cap.name.heijo': '平城京', 'cap.name.tokyo': '东京',
  'bak.seal': '幕', 'bak.kamakura': '镰仓幕府', 'bak.edo': '江户幕府', 'cap.sub2': '天皇所在 · 名义上与实际上谁说了算', 'cap.shikken': '执权',
  heijo: '平城京（条坊示意）', heijoNote: '奈良的方格是平城京的条坊（示意：东西 8 坊约 4.3 km、南北 9 条），宫在北端正中。',
  heianNote: '京都的方格是平安京的条坊（示意）；后来的京都并不总是填满这些方格，战国时只剩上京、下京两块。', tokyoNote: '1868 年江户改称东京，明治天皇移居旧江户城，东京成为首都。',
  siteNote: '古国三迹：律令时代各国的一宫、国府与国分寺，与平面地图「古国巡礼」相同。古代只画国府与国分寺（741 年国分寺之诏以后），一宫是平安后期才有的叫法。',
  fort: '城柵', fortNote: '古代朝廷经营东北与守卫九州的城柵、大宰府（示意）。年份取自日文维基百科。',
  inn: '宿场', innNote: '江户五街道的宿场（示意：路线是宿场之间的直线，坐标取自日文维基各宿场条目）。',
  'pr.series': '歌川广重《六十余州名所图会》（1853–1856）', 'pr.note': '画中地点与平面地图「古国」图层的浮世绘相同；图为公有领域。',
  'k.han': '藩', 'k.pref': '府县', 'k.provs': '{n} 国的守护', 'k.who': '守护', 'k.from': '{y} 年起', 'k.sub': '各年份的守护', 'k.none': '日文维基的名单里没有这一国。',
  'k.note': '守护取自日文维基各国条目的「鎌倉幕府」守护名单；名单没写到的年份记「不详」，北条一门各流不细分。',
  'mu.note': '守护取自日文维基各国条目的「室町幕府」守护名单（南北朝时两朝各有任命，只按名单写）；名单写在正文里的国按原文，没写到的年份记「不详」。', 'mu.looseNote': '「其他守护家」是名单里几家大族以外的守护；「不详」是名单没写到这一年。', 'mu.prose': '条目正文写明这一家世袭守护（没有逐年名单）', 'k.looseNote': '「其他御家人」是名单里北条与几家大族以外的守护；「不详」是名单没写到这一年。',
  'kd.circuitNote': '五畿七道：律令时代把全国分成畿内与七条「道」，各道有同名的官道。地图上的官道是国府之间的连线（示意）。',
  'kd.musashi': '武藏国 771 年以前属东山道（从上野国有一条支路），771 年改属东海道。', 'kd.note': '国界按 {y} 年（各国的分合按日文维基，沿今天的市区町村界画，是近似）。',
  'e.sub': '幕末（1868 年前后）', 'e.koku': '旧高约 {n} 万石（全国各村合计）', 'e.seat': '藩厅', 'e.lord': '最后一位藩主', 'e.ken': '1871 年改为',
  'e.note': '领地按今天的市区町村取石高最多的领主画，是近似；飞地、一村几方共管都看不出来。资料：国立历史民俗博物馆《旧高旧領取調帳》。',
  'e.kind.han': '藩', 'e.kind.bakufu': '幕府领（天领，含代官所、预地）', 'e.kind.hatamoto': '旗本领', 'e.kind.jisha': '寺社领', 'e.kind.mixed': '相给（几方共管）', 'e.kind.sankyo': '御三卿领', 'e.kind.ezo': '虾夷地', 'e.kind.ryukyu': '琉球王国（萨摩控制下）', 'e.kind.none': '没有记录',
  'm.ken': '县', 'm.exBakufu': '旧幕府领的府县', 'm.haihan': '废藩置县', 'm.from': '原来是 {h}', 'm.kenNote': '1871 年 7 月废藩置县，藩原样改为县（3 府 302 县）；县名取自日文维基的藩条目。年底就合并成 3 府 72 县。', 'm.noKen': '1871 年 7 月废藩置县，藩原样改为县；这一块的县名在条目里没找到确切写法，没有写。',
  'm.today': '今天的', 'm.note': '府县界按今天的都道府县与市区町村拼出（合并、分立按日文维基），是近似。', 'm.cap.1876': '3 府 35 县（1876 年 8 月以后）', 'm.cap.1888': '3 府 43 县与北海道厅（1888 年 12 月以后）',
  'lg.kodai': '五畿七道 · {y} 年的国界', 'lg.kamakura': '各国守护的家（日文维基各国条目）', 'lg.muromachi': '各国守护的家（日文维基各国条目）', 'lg.sengoku': '战国大名', 'lg.edo': '幕末的领主 · 藩 {n} 家（按市区町村，近似）', 'lg.1871': '废藩置县：藩改为县', 'lg.1876': '3 府 35 县', 'lg.1888': '3 府 43 县 · 北海道厅',
  moreBlk: '其余 {n} 块', 'bt.note': '与平面地图「合战演武」同一份资料；离最近的地图年份差十年以上的（一之谷、坛之浦）不着势力色。',
  'bt.debate': '众说纷纭', 'bt.per': '地图上每面小旗约代表 {n} 人（按上面写的兵力数字，诸说不一）', 'bt.perShip': '地图上每面小旗约代表 {n} 艘船（按上面写的数字，诸说不一）',
  credit: '地形：国土地理院 標高タイル · 湖河与土地覆盖：地球地図日本 · 城、守护、街道：Wikidata / 日文维基百科 · 藩领：歴博《旧高旧領取調帳》 · 渲染：three.js',
});
Object.assign(S.en, {
  'k.gap': 'gap in the list; the same family before and after',
  title: '3D Japan Through Time · Japan, Then and Now', brand: '3D Through Time', scene: '3D map of Japan through time: drag to pan, scroll or pinch to zoom, right-drag or two fingers to rotate', backTitle: 'Back to the 2D map', hint: 'Drag to pan · scroll to zoom · right-drag to rotate · click an area for every year',
  play: 'Play from this year to 1888', 'save.title': '3D Japan Through Time · {y}', eras: 'Period',
  'era.kodai': 'Ancient', 'era.kamakura': 'Kamakura', 'era.muromachi': 'Muromachi', 'era.sengoku': 'Sengoku', 'era.edo': 'Edo', 'era.meiji': 'Meiji',
  'era.kodai.span': 'The law-code state: provinces and circuits in 712 / 757 / 824', 'era.kamakura.span': 'Kamakura shogunate: provincial constables (1200 / 1250 / 1300)', 'era.muromachi.span': 'Muromachi shogunate: provincial constables (1350 / 1400 / 1440)', 'era.sengoku.span': 'Sengoku warlords (1467–1600)', 'era.edo.span': 'Domains at the end of the Edo period (1867)', 'era.meiji.span': 'From domains to prefectures (1871 / 1876 / 1888)',
  eraLoading: 'Downloading this period…', eraFail: "Couldn't download this period. Try again later.",
  'cap.seal.kyo': '京', 'cap.seal.heijo': '京', 'cap.seal.tokyo': '東', 'cap.name.kyo': 'Kyoto', 'cap.name.heijo': 'Heijō-kyō', 'cap.name.tokyo': 'Tokyo',
  'bak.seal': '幕', 'bak.kamakura': 'Kamakura shogunate', 'bak.edo': 'Edo shogunate', 'cap.sub2': 'Seat of the emperor · who was in charge, in name and in fact', 'cap.shikken': 'Regent',
  heijo: 'Heijō-kyō street grid (schematic)', heijoNote: 'The grid at Nara is the street plan of Heijō-kyō (schematic: 8 blocks east–west, about 4.3 km, and 9 north–south), with the palace at the top centre.',
  heianNote: 'The grid at Kyoto is the street plan of Heian-kyō (schematic); the later city did not always fill it — in the Sengoku period it had shrunk to Kamigyō and Shimogyō.', tokyoNote: 'In 1868 Edo was renamed Tokyo; Emperor Meiji moved into the old Edo Castle and Tokyo became the capital.',
  siteNote: "Ancient sites: each province's chief shrine (ichinomiya), capital (kokufu) and provincial temple (kokubunji), as in the 2D map's Ancient sites layer. The ancient years show only capitals and temples (temples after the edict of 741); 'ichinomiya' is a late-Heian title.",
  fort: 'Fort', fortNote: 'Forts from which the ancient court ran the northeast and guarded Kyushu, and Dazaifu (schematic). Years from Japanese Wikipedia.',
  inn: 'Post town', innNote: 'A post town on the five Edo highways (schematic: the road is drawn straight from town to town; positions from the Japanese Wikipedia article on each town).',
  'pr.series': 'Hiroshige, Famous Views of the Sixty-odd Provinces (1853–1856)', 'pr.note': "Same prints as on the 2D map's province layer; public domain.",
  'k.han': 'Domain', 'k.pref': 'Prefecture', 'k.provs': 'Constable of {n} provinces', 'k.who': 'Constables', 'k.from': 'from {y}', 'k.sub': 'constable by year', 'k.none': 'Not in the Japanese Wikipedia list.',
  'mu.note': "Constables from the Muromachi-shogunate lists in each province's Japanese Wikipedia article (in the Northern and Southern Courts period both courts appointed constables; this follows the list). Provinces whose article gives it in prose follow that text; years not covered are 'Not recorded'.", 'mu.looseNote': "'Other constables' are those outside the major families; 'Not recorded' means the list doesn't reach that year.", 'mu.prose': 'the article says this family held the post hereditarily (no year-by-year list)', 'k.note': "Constables from the Kamakura-shogunate lists in each province's Japanese Wikipedia article; years the list doesn't cover are 'Not recorded'. Hōjō branch families are not told apart.",
  'k.looseNote': "'Other vassals' are constables outside the Hōjō and a few great families; 'Not recorded' means the list doesn't cover that year.",
  'kd.circuitNote': 'The law codes divided the country into the Home Provinces and seven circuits, each with a highway of the same name. The roads on the map just join the provincial capitals (schematic).',
  'kd.musashi': 'Musashi belonged to the Tōsandō until 771 (reached by a branch road from Kōzuke), then to the Tōkaidō.', 'kd.note': 'Borders as of {y} (splits and mergers per Japanese Wikipedia, drawn along today’s municipal borders, so approximate).',
  'e.sub': 'End of the Edo period (around 1868)', 'e.koku': 'about {n} koku (all its villages nationwide)', 'e.seat': 'Seat', 'e.lord': 'Last lord', 'e.ken': 'In 1871 became',
  'e.note': "Each of today's municipalities is coloured by the lord with the most koku there, so this is approximate; enclaves and shared villages don't show. Data: National Museum of Japanese History, Kyūdaka Kyūryō Torishirabechō.",
  'e.kind.han': 'Domain', 'e.kind.bakufu': 'Shogunate land (tenryō)', 'e.kind.hatamoto': 'Hatamoto fiefs', 'e.kind.jisha': 'Temple & shrine land', 'e.kind.mixed': 'Shared by several lords', 'e.kind.sankyo': 'Gosankyō lands', 'e.kind.ezo': 'Ezo', 'e.kind.ryukyu': 'Ryūkyū Kingdom (under Satsuma)', 'e.kind.none': 'No record',
  'm.ken': 'prefecture', 'm.exBakufu': 'Former shogunate land', 'm.haihan': 'Domains abolished', 'm.from': 'Formerly {h}', 'm.kenNote': 'In July 1871 the domains became prefectures as they were (3 + 302); names from the domain articles on Japanese Wikipedia. By year’s end they were merged into 3 + 72.', 'm.noKen': 'In July 1871 the domains became prefectures as they were; no reliable name for this one was found.',
  'm.today': 'Today', 'm.note': "Borders built from today's prefectures and municipalities (mergers and splits per Japanese Wikipedia), so approximate.", 'm.cap.1876': '3 + 35 prefectures (from August 1876)', 'm.cap.1888': '3 + 43 prefectures and the Hokkaidō Agency (from December 1888)',
  'lg.kodai': 'Circuits · provinces as of {y}', 'lg.kamakura': "Constables' families (Japanese Wikipedia)", 'lg.muromachi': "Constables' families (Japanese Wikipedia)", 'lg.sengoku': 'Sengoku warlords', 'lg.edo': 'Lords at the end of the Edo period · {n} domains (by municipality, approx.)', 'lg.1871': 'Domains become prefectures', 'lg.1876': '3 + 35 prefectures', 'lg.1888': '3 + 43 prefectures · Hokkaidō',
  moreBlk: '{n} more', 'bt.note': "Same material as the 2D map's battle mode; battles more than ten years from the nearest map year (Ichi-no-Tani, Dan-no-ura) are shown without clan colours.",
  'bt.debate': 'Still debated', 'bt.per': 'Each small banner on the map stands for about {n} men (from the figures above; accounts vary)', 'bt.perShip': 'Each small banner on the map stands for about {n} ships (from the figures above; accounts vary)',
  credit: 'Terrain: GSI elevation tiles · Lakes, rivers, land cover: Global Map Japan · Castles, constables, highways: Wikidata / Japanese Wikipedia · Domains: NMJH Kyūdaka Kyūryō Torishirabechō · Rendering: three.js',
});
Object.assign(S.ja, {
  'k.gap': '一覧にこの年がない（前後とも同じ家）',
  title: '立体古今図 · 古今日本地図', brand: '立体古今図', scene: '立体古今図：ドラッグで移動、ホイールかピンチで拡大縮小、右ドラッグか二本指で回転', backTitle: '平面地図に戻る', hint: 'ドラッグで移動 · ホイールで拡大縮小 · 右ドラッグで回転 · クリックで各年を表示',
  play: 'この年から1888年まで再生', 'save.title': '立体古今図 · {y}年', eras: '時代',
  'era.kodai': '古代', 'era.kamakura': '鎌倉', 'era.muromachi': '室町', 'era.sengoku': '戦国', 'era.edo': '江戸', 'era.meiji': '明治',
  'era.kodai.span': '律令国家：712 / 757 / 824年の国境と五畿七道', 'era.kamakura.span': '鎌倉幕府：諸国の守護（1200 / 1250 / 1300）', 'era.muromachi.span': '室町幕府：諸国の守護（1350 / 1400 / 1440）', 'era.sengoku.span': '戦国大名（1467–1600）', 'era.edo.span': '幕末の藩領（1867）', 'era.meiji.span': '廃藩置県から府県の確定まで（1871 / 1876 / 1888）',
  eraLoading: 'この時代のデータをダウンロード中…', eraFail: 'この時代のデータを読み込めませんでした。あとでもう一度どうぞ',
  'cap.seal.kyo': '京', 'cap.seal.heijo': '京', 'cap.seal.tokyo': '東', 'cap.name.kyo': '京都', 'cap.name.heijo': '平城京', 'cap.name.tokyo': '東京',
  'bak.seal': '幕', 'bak.kamakura': '鎌倉幕府', 'bak.edo': '江戸幕府', 'cap.sub2': '天皇の所在 · 名目上と実際に誰が治めていたか', 'cap.shikken': '執権',
  heijo: '平城京（条坊・模式）', heijoNote: '奈良の碁盤目は平城京の条坊（模式図：東西8坊約4.3km・南北9条）。宮は北端中央。',
  heianNote: '京都の碁盤目は平安京の条坊（模式図）。後の京都はこれを埋め尽くしてはおらず、戦国時代には上京・下京の二つに縮んでいた。', tokyoNote: '1868年に江戸は東京と改められ、明治天皇が旧江戸城に移って東京が首都となった。',
  siteNote: '旧国の三つの跡：律令時代の各国の一宮・国府・国分寺（平面地図の「古国めぐり」と同じ）。古代の年は国府と国分寺（741年の詔以後）だけを描く。一宮は平安後期からの呼び名。',
  fort: '城柵', fortNote: '古代の朝廷が東北経営と九州の守りに置いた城柵と大宰府（模式図）。年は日本語版ウィキペディアによる。',
  inn: '宿場', innNote: '江戸五街道の宿場（模式図：道は宿場どうしを直線で結んだもの。位置は各宿場の記事による）。',
  'pr.series': '歌川広重『六十余州名所図会』（1853–1856）', 'pr.note': '平面地図の旧国レイヤーの浮世絵と同じ。パブリックドメイン。',
  'k.han': '藩', 'k.pref': '府県', 'k.provs': '{n} か国の守護', 'k.who': '守護', 'k.from': '{y}年から', 'k.sub': '年ごとの守護', 'k.none': 'ウィキペディアの一覧にこの国はありません。',
  'mu.note': '守護は日本語版ウィキペディア各国記事の「室町幕府」守護一覧による（南北朝期は両朝がそれぞれ任命、一覧のとおり）。一覧が本文に書かれている国はその記述により、書かれていない年は「不詳」。', 'mu.looseNote': '「その他の守護」は主な家以外の守護、「不詳」は一覧がその年に及ばないもの。', 'mu.prose': '記事本文に、この家が守護を世襲したとある（年ごとの一覧なし）',
  'k.note': '守護は日本語版ウィキペディア各国記事の「鎌倉幕府」守護一覧による。一覧にない年は「不詳」。北条一門の各流は分けていない。',
  'k.looseNote': '「その他の御家人」は北条と主な数家以外の守護、「不詳」は一覧にその年がないもの。',
  'kd.circuitNote': '五畿七道：律令で全国を畿内と七つの道に分け、道ごとに同名の官道があった。地図の官道は国府どうしを結んだだけの模式図。',
  'kd.musashi': '武蔵国は771年まで東山道（上野国から支路）、以後は東海道に属した。', 'kd.note': '国境は{y}年のもの（分立・合併は日本語版ウィキペディアによる。今の市区町村界に沿うので概略）。',
  'e.sub': '幕末（1868年ごろ）', 'e.koku': '旧高 約{n}万石（全国の村の合計）', 'e.seat': '藩庁', 'e.lord': '最後の藩主', 'e.ken': '1871年に',
  'e.note': '今の市区町村ごとに石高が最も多い領主で塗った概略図。飛び地や相給は表れない。資料：国立歴史民俗博物館『旧高旧領取調帳』。',
  'e.kind.han': '藩', 'e.kind.bakufu': '幕府領（天領・代官所・預地）', 'e.kind.hatamoto': '旗本領', 'e.kind.jisha': '寺社領', 'e.kind.mixed': '相給', 'e.kind.sankyo': '御三卿領', 'e.kind.ezo': '蝦夷地', 'e.kind.ryukyu': '琉球王国（薩摩の支配下）', 'e.kind.none': '記録なし',
  'm.ken': '県', 'm.exBakufu': '旧幕府領の府県', 'm.haihan': '廃藩置県', 'm.from': 'もとは{h}', 'm.kenNote': '1871年7月の廃藩置県で藩はそのまま県になった（3府302県）。県名は日本語版ウィキペディアの藩の記事による。同年末には3府72県に統合。', 'm.noKen': '1871年7月の廃藩置県で藩はそのまま県になった。この地域の県名は記事に確かな記述がなく、書いていない。',
  'm.today': '今の', 'm.note': '府県境は今の都道府県と市区町村から組み立てた概略（合併・分立は日本語版ウィキペディアによる）。', 'm.cap.1876': '3府35県（1876年8月以後）', 'm.cap.1888': '3府43県と北海道庁（1888年12月以後）',
  'lg.kodai': '五畿七道 · {y}年の国境', 'lg.kamakura': '諸国の守護の家（日本語版ウィキペディア）', 'lg.muromachi': '諸国の守護の家（日本語版ウィキペディア）', 'lg.sengoku': '戦国大名', 'lg.edo': '幕末の領主 · 藩{n}家（市区町村単位の概略）', 'lg.1871': '廃藩置県：藩が県に', 'lg.1876': '3府35県', 'lg.1888': '3府43県 · 北海道庁',
  moreBlk: 'ほか{n}', 'bt.note': '平面地図の「合戦演武」と同じ資料。地図の年から十年以上離れた合戦（一ノ谷・壇ノ浦）は勢力の色を付けません。',
  'bt.debate': '諸説あり', 'bt.per': '地図の小旗1本がおよそ{n}人（上の兵力の数字による。諸説あり）', 'bt.perShip': '地図の小旗1本がおよそ{n}艘（上の数字による。諸説あり）',
  credit: '地形：国土地理院 標高タイル · 湖沼・河川・土地被覆：地球地図日本 · 城・守護・街道：Wikidata / 日本語版ウィキペディア · 藩領：歴博『旧高旧領取調帳』 · 描画：three.js',
});

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
