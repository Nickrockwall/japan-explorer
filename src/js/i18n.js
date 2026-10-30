// 多语言：中文（底本）/ English / 日本語
// 语言在页面加载时确定（手动选择 > 浏览器语言），切换语言会重新载入页面。
// 数据翻译以「覆盖层」形式存放在 src/data/i18n/{lang}/，只覆盖文字字段；分类键（地方、五畿七道、时代等）不翻译，显示时经 t() 转换。
import { uiPref } from './store.js';

export const LANGS = {
  zh: { label: '中文', short: '中', html: 'zh-CN' },
  en: { label: 'English', short: 'EN', html: 'en' },
  ja: { label: '日本語', short: '日', html: 'ja' },
};

// 链接里的语言：#pref=26&lang=ja 或 ?lang=ja
function fromURL() {
  const h = new URLSearchParams(location.hash.slice(1)).get('lang');
  const q = new URLSearchParams(location.search).get('lang');
  return LANGS[h] ? h : LANGS[q] ? q : null;
}

function detect() {
  const url = fromURL();
  if (url) {
    uiPref.set('lang', url); // 记住链接指定的语言
    return url;
  }
  const saved = uiPref.get('lang', null);
  if (LANGS[saved]) return saved;
  for (const l of navigator.languages || [navigator.language || '']) {
    const s = String(l).toLowerCase();
    if (s.startsWith('ja')) return 'ja';
    if (s.startsWith('zh')) return 'zh';
    if (s.startsWith('en')) return 'en';
  }
  return 'zh';
}

export const lang = detect();

export function setLang(l) {
  if (!LANGS[l] || l === lang) return;
  uiPref.set('lang', l);
  // 地址栏里的 lang 优先级最高，切换时一并改掉，否则重新载入后又会回到旧语言
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.has('lang') || h.has('pref')) {
    h.set('lang', l);
    location.hash = h.toString();
  }
  location.reload();
}

// 当前页面状态的地址片段：#pref=26&lang=ja
export function stateHash(prefId) {
  const h = new URLSearchParams();
  if (prefId) h.set('pref', prefId);
  h.set('lang', lang);
  return `#${h.toString()}`;
}

// 可分享的完整链接
export function shareURL(prefId) {
  return `${location.origin}${location.pathname}${stateHash(prefId)}`;
}

// ── 界面词典 ──────────────
const D = {
  zh: {
    'doc.title': `Japan Explorer · 日本47都道府县古今变迁图鉴`,
    'subtitle': `日本47都道府县古今变迁图鉴 · 五畿七道 ⇄ 都道府县`,
    'counter.title': `点击地图上的任意地区即记为已探索`,
    'counter.label': `全日本探索`,
    'btn.battle': `合战演武`, 'btn.battle.title': `在地图上推演经典合战`,
    'btn.book': `御朱印帐`, 'btn.book.title': `查看已收集的御朱印`,
    'btn.settings': `API 设置`, 'lang.aria': `界面语言`,
    'map.aria': `日本地图`, 'layers.aria': `风土图层`, 'filters.aria': `时空滤镜`,
    'search.ph': `搜县名 / 古国名，如 武藏、Kyoto`,
    'tb.play': `播放时代变迁`, 'tb.pause': `暂停`, 'tb.range': `时代`,
    'tb.idle': `时空穿越`, 'tb.idle.cap': `拖动滑块，穿越九个时代`, 'tb.exit': `回到当下`,
    'capital': `中枢：{name}`, 'capital.label': `中枢 · {name}`,
    'hud.tag': `合战沙盘`, 'hud.exit': `退出合战沙盘`, 'hud.phases': `推演阶段`,
    'bv.ask': `提问 ↓`,
    'hud.prev': `‹ 上一阶段`, 'hud.next': `下一阶段 ›`, 'hud.auto': `▶ 自动推演`, 'hud.pause': `❚❚ 暂停推演`,
    'hud.collapse': `收起面板`, 'hud.expand': `展开面板`, 'hud.legend': `{name} · 合战沙盘`,
    'loading': `正在展开古地图…`,
    'detail.aria': `地区风土与历史详卡`, 'splitter.aria': `拖动调整上下比例`, 'guide.aria': `AI 历史向导`,
    'guide.name': `时空案内人`, 'guide.pick': `请先在地图上选择一个地区`,
    'persona.aria': `向导模式`, 'mode.scholar': `博学史官`, 'mode.hero': `名将附体`,
    'chip.offline': `离线模式`, 'chip.online': `在线 · {model}`,
    'chat.ph': `向案内人提问，例如：江户时代这里谁说了算？`, 'send': `送出`,
    'close': `关闭`, 'book.tabs': `按地方筛选`, 'book.all': `全部`, 'book.nation': `全国`,
    'book.progress': `{scope} 已收集 {n} / {total}`, 'book.empty': `未`, 'book.empty.title': `尚未盖印：点击前往`,
    'battles.sub': `选择一场合战，在地图上推演两军进军与交锋`,
    'set.h': `接入 AI 案内人`, 'set.note': `Key 只保存在本浏览器的 localStorage，请求从浏览器直接发往你填写的接口。`,
    'set.provider': `接口类型`, 'set.opt.claude': `Claude API（Anthropic）`, 'set.opt.openai': `OpenAI 兼容接口`,
    'set.opt.gemini': `Gemini 原生（Google AI Studio）`, 'set.model': `模型`, 'set.test': `测试连接`,
    'set.clear': `清除 Key`, 'set.reset': `重置探索与御朱印`, 'set.cancel': `取消`, 'set.save': `保存`,
    'set.needkey': `请先填写 API Key。`, 'set.testing': `正在测试…`,
    'err.load': `史料读取失败（{msg}）。<br>请确认是在项目根目录启动的本地服务器：`,
    'err.echarts': `ECharts 未能从 CDN 加载，请检查网络连接。`, 'err.init': `初始化失败：{msg}`,
    // 详卡
    'w.badge': `五畿七道 · 六十八国`,
    'w.h': `今日的 47 都道府县，<br>曾是怎样的古国版图？`,
    'w.p1': `公元 7 世纪，律令国家把列岛划分为“五畿七道”与六十八个令制国。千年之后，明治政府废藩置县，又拼出了今天的都道府县——有的县恰好等于一国，有的县却由五国拼成，有的古国被一分为二。`,
    'w.p2': `在左侧地图上点选任意地区，查看它的<b>古今双名</b>、<b>六个时代</b>的沿革、名胜物产与方言，并和随地区更换身份的<b>时空案内人</b>聊聊。`,
    'w.outside': `令制外：虾夷地 · 琉球`,
    'untranslated': `本地区内容翻译中，暂以中文显示`,
    'muni.open': `市区町村`, 'muni.open.title': `查看本县所有市区町村，以及它们古代属于哪个令制国`, 'muni.back': `← 返回全国`, 'muni.modes': `着色方式`,
    'muni.mode.prov': `按旧国`, 'muni.mode.pop': `按人口`, 'muni.loading': `正在展开市区町村地图…`, 'muni.error': `市区町村数据加载失败，请检查网络后重试`,
    'muni.count': `{n} 个市区町村`, 'muni.outside': `令制外`, 'muni.ward': `所属市`, 'muni.district': `所属郡`, 'muni.province': `旧国`,
    'muni.partial': `（部分属{list}）`, 'muni.pop': `人口`, 'muni.popYear': `{n}（{y} 年）`, 'muni.wiki': `在维基百科查看`,
    'muni.legend.prov': `按古代令制国着色（横跨多国的市町村取主要部分）`, 'muni.legend.pop': `按人口着色（对数刻度）`,
    'share': `分享`, 'share.title': `分享这个地区（链接会带上当前语言）`, 'share.copied': `链接已复制，快发给朋友吧`, 'share.text': `{name} · Japan Explorer — 日本47都道府县古今变迁图鉴`, 'share.fail': `复制失败，请手动复制地址栏的链接`,
    'stamp.do': `打卡盖印`, 'stamp.done': `已盖印 · {date}`, 'seal.meta': `奉拝 · {name}`,
    'st.region': `地方`, 'st.capital': `厅所在地`, 'st.pop': `人口`, 'st.area': `面积`,
    'meme.h': `地域修罗场`, 'meme.sub': `地缘梗速览 · 玩笑话，别当真`,
    'sec.prov': `令制国对照`, 'cross': `跨界 · 亦属 {list}`, 'cross.title': `该国古地今分属多县`,
    'sec.lineage': `历代统治者`, 'row.meiji': `明治`, 'note.border': `古界线 vs 今县界：`,
    'sec.timeline': `历史时间轴`, 'sec.timeline.sub': `点击展开`,
    'sec.landmarks': `名胜`, 'sec.specialties': `物产`, 'sec.fudo': `风土`, 'sec.dialect': `方言速览`,
    'fudo.ramen': `在地拉面`, 'fudo.sake': `代表地酒`,
    'ramen.tag': `拉面流派图鉴`, 'ramen.top': `浇头`, 'ramen.noodle': `面体`, 'ramen.broth': `汤头`,
    'sake.tag': `地酒名酿地图`, 'sake.famous': `全国名酿`, 'sake.shochu.note': `不按清酒甘辛象限计`,
    'ax.rich': `浓醇`, 'ax.light': `淡丽`, 'ax.sweet': `甘口`, 'ax.dry': `辛口`,
    'era.note': `⏳ {era}：本县时间轴未单列此时代，可在地图上看该时代的全国格局。`,
    'list.sep': `、`,
    // 地图
    'tip.visited': `✓ 已探索`, 'tip.ancient': `古：{list}`, 'tip.depart': `{from} 出阵`,
    'lg.unvisited': `未探索`, 'lg.visited': `已探索`, 'lg.active': `当前`,
    // 向导
    'q.daimyo': `战国时这里战况如何？`, 'q.dialect': `用{dialect}和我打声招呼`, 'q.border': `古代的{provs}和今天的界线有什么不同？`,
    'q.b_turn': `这场仗的胜负关键是什么？`, 'q.b_forces': `双方兵力各有多少？`, 'q.b_after': `战后天下格局如何变化？`,
    'g.hint': `（离线模式 · 预置解答）<a data-act="settings">接入 API</a> 即可与{who}无限畅聊。`, 'g.guide': `案内人`,
    'g.fallback': `{self}一时答不上这个问题……离线时{self}只记得几段旧事，试试下面的快捷提问吧。`,
    'g.fail': `⚠ 调用失败：{msg}`, 'g.fail.hint': `请检查 <a data-act="settings">API 设置</a>（Key、Base URL、模型名，以及接口是否允许浏览器跨域）。`,
    'g.t.battle': `合战沙盘：{battle} · 主战场 {field}`, 'g.t.hero': `名将附体中：{name}（{provs}）`, 'g.t.scholar': `正在为你讲述：{name}（{provs}）`,
    'g.b.switch': `— 时空切换至 {name} · 已载入该地史料 —`, 'g.b.hero': `— 名将附体：{name} 降临 —`, 'g.b.scholar': `— 恢复博学史官模式 —`,
    'g.b.battle': `— 合战沙盘：{battle} · {name} 登场 —`, 'g.b.exit': `— 退出合战沙盘 · 回到 {name} —`,
    'g.b.phase': `— 第 {i} / {n} 阶段 · {title}（{time}）—`,
    'g.intro': `我是**时空案内人**。我会随你所到之处更换身份——在江户是浮世绘里的猫，在京都是平安朝的女官，在长崎是出岛的兰学通词……\n\n切换到**名将附体**，还能请来织田信长、坂本龙马、伊达政宗亲自开讲；打开**合战演武**，名将们还会在沙盘上为你复盘经典战役。请先在左侧地图上点选一个地区吧。`,
    'o.daimyo.hero': `{self}所知的战国，这片土地上的风云人物有 **{list}**。`,
    'o.daimyo': `{self}记得，战国时这片土地上活跃着 **{list}**。`,
    'o.edo': `到了江户时代，这里由 **{list}** 治理——{summary}`,
    'o.hello': `「**{phrase}**」！——{self}用{dialect}向你问好，意思是“{meaning}”{note}。`,
    'o.more': `再教你两句：`, 'o.paren': `（{x}）`, 'o.eq': `＝`,
    'o.border': `{self}来给你摊开古地图：今天的{name}在律令时代对应——`,
    'o.cross': `；此国今跨界，另一部分属于{list}`, 'o.meiji': `【明治的县域变迁】{x}`,
    'o.meme': `说到这里的“地域修罗场”，{self}可听过不少：`, 'o.meme.end': `——玩笑话，别当真。`,
    'o.see': `{self}推荐你看看：`, 'o.taste': `再尝尝：`,
    'o.b.turn': `{self}来说说这一仗的要害：\n\n{x}\n\n{sides}，胜负就在这里分出。`, 'o.b.vs': ` 对 `,
    'o.b.forces': `两军阵容如下：`, 'o.b.after': `此战之后——\n\n{x}\n\n【战况速览】{brief}`, 'o.b.routes': `各军进军路线：`,
    'kw.daimyo': `大名|战国|战况|武将|藩|江户|谁`, 'kw.dialect': `方言|招呼|怎么说|口音|话`, 'kw.border': `界|令制|国|古代|明治|县`,
    'kw.meme': `梗|段子|偏见|吐槽|修罗场|笑话`, 'kw.tour': `名胜|景点|好玩|去哪|特产|好吃|美食|物产`,
    'kw.b.turn': `关键|转折|为什么|怎么赢|怎么输|胜负`, 'kw.b.forces': `兵力|多少人|人数|规模`,
    'kw.b.after': `之后|结果|影响|格局|后来`, 'kw.b.routes': `路线|进军|行军|从哪`,
    // 测试连接
    'tc.sys': `你是测试助手。`, 'tc.ask': `用不超过15个字向我问好。`,
    'tc.empty': `连接成功但模型没有返回文字，请换一个模型试试。`, 'tc.ok': `连接成功 ✓ 模型回复：「{x}」`,
    'tc.timeout': `30 秒无响应，请检查 Base URL 与网络。`, 'tc.key': `API Key 无效：请重新复制 Key，注意不要带空格或漏字符。`,
    'tc.400': `请求被拒（400）：多半是模型名写错，或该模型不支持此接口。`, 'tc.401': `Key 无效或无权限（401/403）：请重新复制 API Key，注意不要带空格。`,
    'tc.404': `找不到接口或模型（404）：请检查 Base URL 和模型名。`, 'tc.429': `额度用完或请求太频繁（429）：免费额度通常次日恢复，或换一个额度更高的模型。`,
    'tc.5xx': `服务端错误（{s}）：稍后再试。`, 'tc.net': `请求没有发出去：Base URL 写错、网络不通，或该接口不允许浏览器跨域调用。`,
    'tc.detail': `详情：{x}`, 'api.status': `接口返回 {s}：{x}`, 'api.stream': `流式响应出错`,
  },
  en: {
    'doc.title': `Japan Explorer · 47 Prefectures Through Time`,
    'subtitle': `Japan's 47 prefectures through the ages · Ancient provinces ⇄ modern prefectures`,
    'counter.title': `Click any region on the map to mark it as explored`,
    'counter.label': `Explored`,
    'btn.battle': `Battles`, 'btn.battle.title': `Replay classic battles on the map`,
    'btn.book': `Goshuin Book`, 'btn.book.title': `View your collected goshuin seals`,
    'btn.settings': `API Settings`, 'lang.aria': `Interface language`,
    'map.aria': `Map of Japan`, 'layers.aria': `Map layers`, 'filters.aria': `History filters`,
    'search.ph': `Search a prefecture or old province, e.g. Musashi, Kyoto`,
    'tb.play': `Play through the eras`, 'tb.pause': `Pause`, 'tb.range': `Era`,
    'tb.idle': `Time Travel`, 'tb.idle.cap': `Drag the slider through nine eras`, 'tb.exit': `Back to the present`,
    'capital': `Seat of power: {name}`, 'capital.label': `Capital · {name}`,
    'hud.tag': `Battle Sandbox`, 'hud.exit': `Exit sandbox`, 'hud.phases': `Battle phases`,
    'bv.ask': `Ask ↓`,
    'hud.prev': `‹ Previous`, 'hud.next': `Next ›`, 'hud.auto': `▶ Auto-play`, 'hud.pause': `❚❚ Pause`,
    'hud.collapse': `Collapse panel`, 'hud.expand': `Expand panel`, 'hud.legend': `{name} · Battle sandbox`,
    'loading': `Unrolling the ancient map…`,
    'detail.aria': `Region history card`, 'splitter.aria': `Drag to resize panels`, 'guide.aria': `AI history guide`,
    'guide.name': `Time-Travel Guide`, 'guide.pick': `Pick a region on the map to begin`,
    'persona.aria': `Guide mode`, 'mode.scholar': `Scholar`, 'mode.hero': `Warlord`,
    'chip.offline': `Offline`, 'chip.online': `Online · {model}`,
    'chat.ph': `Ask the guide, e.g. Who ruled here in the Edo period?`, 'send': `Send`,
    'close': `Close`, 'book.tabs': `Filter by region`, 'book.all': `All`, 'book.nation': `All Japan`,
    'book.progress': `{scope}: {n} / {total} collected`, 'book.empty': `—`, 'book.empty.title': `Not stamped yet — click to visit`,
    'battles.sub': `Choose a battle to replay the armies' marches and clash on the map`,
    'set.h': `Connect the AI guide`, 'set.note': `Your key stays in this browser's localStorage; requests go straight from your browser to the API you enter.`,
    'set.provider': `Provider`, 'set.opt.claude': `Claude API (Anthropic)`, 'set.opt.openai': `OpenAI-compatible`,
    'set.opt.gemini': `Gemini native (Google AI Studio)`, 'set.model': `Model`, 'set.test': `Test connection`,
    'set.clear': `Clear key`, 'set.reset': `Reset exploration & goshuin`, 'set.cancel': `Cancel`, 'set.save': `Save`,
    'set.needkey': `Please enter an API key first.`, 'set.testing': `Testing…`,
    'err.load': `Could not load the data ({msg}).<br>Make sure the local server is started from the project root:`,
    'err.echarts': `ECharts failed to load from the CDN. Please check your connection.`, 'err.init': `Initialization failed: {msg}`,
    'w.badge': `Five Home Provinces & Seven Circuits · 68 provinces`,
    'w.h': `What did today's 47 prefectures<br>look like as ancient provinces?`,
    'w.p1': `In the 7th century the ritsuryō state divided the islands into the "Five Home Provinces and Seven Circuits" and 68 provinces. A thousand years later the Meiji government abolished the feudal domains and pieced together today's prefectures — some match a single province exactly, some are stitched from five, and some old provinces were split in two.`,
    'w.p2': `Click any region on the map to see its <b>ancient and modern names</b>, its history across <b>six eras</b>, landmarks, local food and dialect — and chat with the <b>time-travel guide</b>, who changes identity wherever you go.`,
    'w.outside': `Outside the system: Ezo · Ryukyu`,
    'untranslated': `Translation in progress — this region is shown in Chinese for now`,
    'muni.open': `Cities & towns`, 'muni.open.title': `See every municipality in this prefecture and the ancient province it belonged to`, 'muni.back': `← All Japan`, 'muni.modes': `Color by`,
    'muni.mode.prov': `Province`, 'muni.mode.pop': `Population`, 'muni.loading': `Unfolding the municipal map…`, 'muni.error': `Couldn't load municipal data — check your connection and try again`,
    'muni.count': `{n} municipalities`, 'muni.outside': `Outside the ritsuryō system`, 'muni.ward': `City`, 'muni.district': `District`, 'muni.province': `Province`,
    'muni.partial': ` (partly {list})`, 'muni.pop': `Population`, 'muni.popYear': `{n} ({y})`, 'muni.wiki': `Look up on Wikipedia`,
    'muni.legend.prov': `Colored by ancient province (municipalities spanning several use the main one)`, 'muni.legend.pop': `Colored by population (log scale)`,
    'share': `Share`, 'share.title': `Share this region (the link keeps the current language)`, 'share.copied': `Link copied — send it to a friend!`, 'share.text': `{name} · Japan Explorer — Japan's 47 prefectures through the ages`, 'share.fail': `Couldn't copy — please copy the address bar instead`,
    'stamp.do': `Get stamp`, 'stamp.done': `Stamped · {date}`, 'seal.meta': `Hōhai · {name}`,
    'st.region': `Region`, 'st.capital': `Capital`, 'st.pop': `Population`, 'st.area': `Area`,
    'meme.h': `Local Rivalries`, 'meme.sub': `Regional in-jokes · all in good fun`,
    'sec.prov': `Ancient provinces`, 'cross': `Shared · also in {list}`, 'cross.title': `This province is now split across several prefectures`,
    'sec.lineage': `Rulers through the ages`, 'row.meiji': `Meiji`, 'note.border': `Old borders vs. today: `,
    'sec.timeline': `Timeline`, 'sec.timeline.sub': `click to expand`,
    'sec.landmarks': `Landmarks`, 'sec.specialties': `Specialties`, 'sec.fudo': `Local flavors`, 'sec.dialect': `Dialect`,
    'fudo.ramen': `Local ramen`, 'fudo.sake': `Signature drink`,
    'ramen.tag': `Ramen atlas`, 'ramen.top': `Toppings`, 'ramen.noodle': `Noodles`, 'ramen.broth': `Broth`,
    'sake.tag': `Sake atlas`, 'sake.famous': `Nationally famous`, 'sake.shochu.note': `not plotted on the sake sweet/dry chart`,
    'ax.rich': `Rich`, 'ax.light': `Light`, 'ax.sweet': `Sweet`, 'ax.dry': `Dry`,
    'era.note': `⏳ {era}: this prefecture's timeline has no separate entry for this era — see the nationwide picture on the map.`,
    'list.sep': `, `,
    'tip.visited': `✓ Explored`, 'tip.ancient': `Ancient: {list}`, 'tip.depart': `Sets out from {from}`,
    'lg.unvisited': `Unexplored`, 'lg.visited': `Explored`, 'lg.active': `Selected`,
    'q.daimyo': `What happened here in the Sengoku period?`, 'q.dialect': `Greet me in {dialect}`, 'q.border': `How do the old borders of {provs} differ from today?`,
    'q.b_turn': `What decided this battle?`, 'q.b_forces': `How large were the two armies?`, 'q.b_after': `How did the battle change Japan?`,
    'g.hint': `(Offline · preset answer) <a data-act="settings">Connect an API</a> to chat freely with {who}.`, 'g.guide': `the guide`,
    'g.fallback': `Hmm, that one is beyond me while offline — try one of the quick questions below.`,
    'g.fail': `⚠ Request failed: {msg}`, 'g.fail.hint': `Please check your <a data-act="settings">API settings</a> (key, base URL, model name, and whether the API allows browser CORS requests).`,
    'g.t.battle': `Battle sandbox: {battle} · battlefield {field}`, 'g.t.hero': `Warlord mode: {name} ({provs})`, 'g.t.scholar': `Now telling the story of {name} ({provs})`,
    'g.b.switch': `— Traveling to {name} · local records loaded —`, 'g.b.hero': `— {name} has arrived —`, 'g.b.scholar': `— Back to scholar mode —`,
    'g.b.battle': `— Battle sandbox: {battle} · enter {name} —`, 'g.b.exit': `— Leaving the sandbox · back to {name} —`,
    'g.b.phase': `— Phase {i} / {n} · {title} ({time}) —`,
    'g.intro': `I am your **time-travel guide**. I change identity wherever you go — an ukiyo-e cat in Edo, a Heian court lady in Kyoto, a Dutch-studies interpreter at Dejima in Nagasaki…\n\nSwitch to **Warlord** mode to hear Oda Nobunaga, Sakamoto Ryōma or Date Masamune speak for themselves, or open **Battles** to have the generals replay famous battles on the map. Start by clicking a region on the left.`,
    'o.daimyo.hero': `The Sengoku period as I knew it — the great figures of this land were **{list}**.`,
    'o.daimyo': `As I recall, in the Sengoku period this land saw **{list}**.`,
    'o.edo': `In the Edo period it was governed by **{list}** — {summary}`,
    'o.hello': `"**{phrase}**"! — that's a greeting in {dialect}, meaning "{meaning}"{note}.`,
    'o.more': `Two more phrases for you:`, 'o.paren': ` ({x})`, 'o.eq': ` = `,
    'o.border': `Let me unroll the old map: in the ritsuryō era, today's {name} corresponded to —`,
    'o.cross': `; this province is now shared with {list}`, 'o.meiji': `[Meiji-era changes] {x}`,
    'o.meme': `Speaking of local rivalries, I've heard a few:`, 'o.meme.end': `— all in good fun.`,
    'o.see': `Places I'd recommend:`, 'o.taste': `And things to taste:`,
    'o.b.turn': `Here is what decided the battle:\n\n{x}\n\n{sides} — this is where it was won and lost.`, 'o.b.vs': ` vs. `,
    'o.b.forces': `The two sides:`, 'o.b.after': `After the battle —\n\n{x}\n\n[Summary] {brief}`, 'o.b.routes': `Each army's march:`,
    'kw.daimyo': `daimyo|sengoku|warlord|samurai|domain|edo|who rule|battle`, 'kw.dialect': `dialect|greet|hello|say|accent|word`,
    'kw.border': `border|province|ancient|meiji|prefecture|boundar`, 'kw.meme': `joke|meme|rival|stereotype|funny`,
    'kw.tour': `see|visit|landmark|sight|food|eat|specialt|famous for`,
    'kw.b.turn': `key|turn|why|decid|win|lose|lost`, 'kw.b.forces': `force|army|how many|size|troops|strength`,
    'kw.b.after': `after|result|aftermath|impact|change|then`, 'kw.b.routes': `route|march|from where|path`,
    'tc.sys': `You are a test assistant.`, 'tc.ask': `Say hello to me in under ten words.`,
    'tc.empty': `Connected, but the model returned no text — try another model.`, 'tc.ok': `Connected ✓ Model replied: "{x}"`,
    'tc.timeout': `No response within 30 s — check the base URL and your network.`, 'tc.key': `Invalid API key — copy it again, without spaces or missing characters.`,
    'tc.400': `Request rejected (400) — usually a wrong model name, or the model doesn't support this endpoint.`, 'tc.401': `Invalid key or no permission (401/403) — copy the API key again, without spaces.`,
    'tc.404': `Endpoint or model not found (404) — check the base URL and model name.`, 'tc.429': `Quota exhausted or too many requests (429) — free quotas usually reset the next day, or use a model with a higher quota.`,
    'tc.5xx': `Server error ({s}) — try again later.`, 'tc.net': `The request never left: wrong base URL, no network, or the API doesn't allow browser CORS requests.`,
    'tc.detail': `Details: {x}`, 'api.status': `API returned {s}: {x}`, 'api.stream': `Streaming response error`,
  },
  ja: {
    'doc.title': `Japan Explorer · 日本47都道府県 今昔図鑑`,
    'subtitle': `日本47都道府県 今昔図鑑 · 五畿七道 ⇄ 都道府県`,
    'counter.title': `地図の地域をクリックすると「探訪済み」になります`,
    'counter.label': `全国探訪`,
    'btn.battle': `合戦演武`, 'btn.battle.title': `名だたる合戦を地図上で再現`,
    'btn.book': `御朱印帳`, 'btn.book.title': `集めた御朱印を見る`,
    'btn.settings': `API 設定`, 'lang.aria': `表示言語`,
    'map.aria': `日本地図`, 'layers.aria': `風土レイヤー`, 'filters.aria': `時空フィルター`,
    'search.ph': `都道府県名・旧国名で検索（例：武蔵、Kyoto）`,
    'tb.play': `時代の移り変わりを再生`, 'tb.pause': `一時停止`, 'tb.range': `時代`,
    'tb.idle': `時空旅行`, 'tb.idle.cap': `スライダーで九つの時代を旅する`, 'tb.exit': `現在に戻る`,
    'capital': `政権の中心：{name}`, 'capital.label': `中枢 · {name}`,
    'hud.tag': `合戦沙盤`, 'hud.exit': `沙盤を終了`, 'hud.phases': `合戦の局面`,
    'bv.ask': `質問する ↓`,
    'hud.prev': `‹ 前の局面`, 'hud.next': `次の局面 ›`, 'hud.auto': `▶ 自動再生`, 'hud.pause': `❚❚ 一時停止`,
    'hud.collapse': `パネルを畳む`, 'hud.expand': `パネルを開く`, 'hud.legend': `{name} · 合戦沙盤`,
    'loading': `古地図を広げています…`,
    'detail.aria': `地域の風土と歴史`, 'splitter.aria': `ドラッグして上下の比率を調整`, 'guide.aria': `AI 歴史案内人`,
    'guide.name': `時空案内人`, 'guide.pick': `まず地図から地域を選んでください`,
    'persona.aria': `案内人のモード`, 'mode.scholar': `博学の史官`, 'mode.hero': `武将降臨`,
    'chip.offline': `オフライン`, 'chip.online': `オンライン · {model}`,
    'chat.ph': `案内人に質問（例：江戸時代、ここを治めていたのは？）`, 'send': `送信`,
    'close': `閉じる`, 'book.tabs': `地方で絞り込む`, 'book.all': `すべて`, 'book.nation': `全国`,
    'book.progress': `{scope}　{n} / {total} 枚収集`, 'book.empty': `未`, 'book.empty.title': `未参拝：クリックで移動`,
    'battles.sub': `合戦を選ぶと、両軍の進軍と激突を地図上で再現します`,
    'set.h': `AI 案内人に接続`, 'set.note': `キーはこのブラウザの localStorage にのみ保存され、リクエストはブラウザから入力した API へ直接送られます。`,
    'set.provider': `API の種類`, 'set.opt.claude': `Claude API（Anthropic）`, 'set.opt.openai': `OpenAI 互換 API`,
    'set.opt.gemini': `Gemini ネイティブ（Google AI Studio）`, 'set.model': `モデル`, 'set.test': `接続テスト`,
    'set.clear': `キーを削除`, 'set.reset': `探訪記録と御朱印をリセット`, 'set.cancel': `キャンセル`, 'set.save': `保存`,
    'set.needkey': `先に API キーを入力してください。`, 'set.testing': `テスト中…`,
    'err.load': `データを読み込めませんでした（{msg}）。<br>プロジェクトのルートでローカルサーバーを起動してください：`,
    'err.echarts': `ECharts を CDN から読み込めませんでした。ネットワークを確認してください。`, 'err.init': `初期化に失敗しました：{msg}`,
    'w.badge': `五畿七道 · 六十八か国`,
    'w.h': `今日の47都道府県は、<br>かつてどんな国だったのか？`,
    'w.p1': `7世紀、律令国家は列島を「五畿七道」と六十余りの令制国に分けました。千年後、明治政府は廃藩置県で今の都道府県をつくります——一国がそのまま県になった所もあれば、五か国を合わせた県、二つに分かれた旧国もあります。`,
    'w.p2': `左の地図で地域をクリックすると、<b>旧国名と現在の名前</b>、<b>六つの時代</b>の歩み、名所や名物、方言が見られます。地域ごとに姿を変える<b>時空案内人</b>とも話してみましょう。`,
    'w.outside': `令制外：蝦夷地 · 琉球`,
    'untranslated': `この地域は翻訳作業中のため、中国語で表示しています`,
    'muni.open': `市区町村`, 'muni.open.title': `県内のすべての市区町村と、昔どの令制国だったかを表示`, 'muni.back': `← 全国へ戻る`, 'muni.modes': `色分け`,
    'muni.mode.prov': `旧国別`, 'muni.mode.pop': `人口別`, 'muni.loading': `市区町村地図を広げています…`, 'muni.error': `市区町村データを読み込めませんでした。通信状況を確認してください`,
    'muni.count': `{n} 市区町村`, 'muni.outside': `令制外`, 'muni.ward': `所属市`, 'muni.district': `郡`, 'muni.province': `旧国`,
    'muni.partial': `（一部は{list}）`, 'muni.pop': `人口`, 'muni.popYear': `{n}（{y}年）`, 'muni.wiki': `Wikipedia で調べる`,
    'muni.legend.prov': `令制国で色分け（複数の国にまたがる市町村は主な部分）`, 'muni.legend.pop': `人口で色分け（対数目盛）`,
    'share': `共有`, 'share.title': `この地域を共有（リンクに今の言語が含まれます）`, 'share.copied': `リンクをコピーしました。友だちに送ってみましょう`, 'share.text': `{name} · Japan Explorer — 日本47都道府県 今昔図鑑`, 'share.fail': `コピーできませんでした。アドレスバーのリンクをコピーしてください`,
    'stamp.do': `御朱印をいただく`, 'stamp.done': `参拝済み · {date}`, 'seal.meta': `奉拝 · {name}`,
    'st.region': `地方`, 'st.capital': `県庁所在地`, 'st.pop': `人口`, 'st.area': `面積`,
    'meme.h': `地域の修羅場`, 'meme.sub': `ご当地あるある · 冗談としてどうぞ`,
    'sec.prov': `旧国との対応`, 'cross': `県境をまたぐ · {list}にも`, 'cross.title': `この旧国は現在いくつかの都道府県に分かれています`,
    'sec.lineage': `歴代の支配者`, 'row.meiji': `明治`, 'note.border': `昔の国境と今の県境：`,
    'sec.timeline': `歴史年表`, 'sec.timeline.sub': `クリックで開く`,
    'sec.landmarks': `名所`, 'sec.specialties': `名物`, 'sec.fudo': `風土`, 'sec.dialect': `方言`,
    'fudo.ramen': `ご当地ラーメン`, 'fudo.sake': `代表的な地酒`,
    'ramen.tag': `ラーメン流派図鑑`, 'ramen.top': `具`, 'ramen.noodle': `麺`, 'ramen.broth': `スープ`,
    'sake.tag': `地酒銘醸マップ`, 'sake.famous': `全国区の銘柄`, 'sake.shochu.note': `日本酒の甘辛マップには含めません`,
    'ax.rich': `濃醇`, 'ax.light': `淡麗`, 'ax.sweet': `甘口`, 'ax.dry': `辛口`,
    'era.note': `⏳ {era}：この県の年表にはこの時代の項目がありません。地図で全国の情勢を見てください。`,
    'list.sep': `、`,
    'tip.visited': `✓ 探訪済み`, 'tip.ancient': `旧国：{list}`, 'tip.depart': `{from}より出陣`,
    'lg.unvisited': `未探訪`, 'lg.visited': `探訪済み`, 'lg.active': `選択中`,
    'q.daimyo': `戦国時代、ここはどうなっていた？`, 'q.dialect': `{dialect}であいさつして`, 'q.border': `{provs}の昔の境界は今とどう違う？`,
    'q.b_turn': `この合戦の勝敗を分けたものは？`, 'q.b_forces': `両軍の兵力は？`, 'q.b_after': `合戦のあと天下はどう変わった？`,
    'g.hint': `（オフライン · 用意された回答）<a data-act="settings">API に接続</a>すると{who}と自由に話せます。`, 'g.guide': `案内人`,
    'g.fallback': `{self}には、いまはお答えできませぬ……オフラインでは昔話をいくつか覚えているだけ。下の質問を試してみてください。`,
    'g.fail': `⚠ 呼び出しに失敗：{msg}`, 'g.fail.hint': `<a data-act="settings">API 設定</a>（キー、Base URL、モデル名、ブラウザからの CORS が許可されているか）を確認してください。`,
    'g.t.battle': `合戦沙盤：{battle} · 主戦場 {field}`, 'g.t.hero': `武将降臨中：{name}（{provs}）`, 'g.t.scholar': `ただいまのお話：{name}（{provs}）`,
    'g.b.switch': `— {name}へ時空移動 · 史料を読み込みました —`, 'g.b.hero': `— 武将降臨：{name} —`, 'g.b.scholar': `— 博学の史官モードに戻りました —`,
    'g.b.battle': `— 合戦沙盤：{battle} · {name} 登場 —`, 'g.b.exit': `— 沙盤を終了 · {name}に戻る —`,
    'g.b.phase': `— 第 {i} / {n} 局面 · {title}（{time}）—`,
    'g.intro': `わたしは**時空案内人**。行く先々で姿を変えます——江戸では浮世絵の猫、京では平安の女房、長崎では出島の蘭学通詞……\n\n**武将降臨**に切り替えれば織田信長や坂本龍馬、伊達政宗がみずから語り、**合戦演武**を開けば武将たちが沙盤の上で名合戦を振り返ります。まずは左の地図から地域を選んでください。`,
    'o.daimyo.hero': `{self}の知る戦国、この地を駆けた者たちは **{list}**。`,
    'o.daimyo': `{self}の覚えでは、戦国のころこの地には **{list}** がおりました。`,
    'o.edo': `江戸時代には **{list}** が治め——{summary}`,
    'o.hello': `「**{phrase}**」！——{dialect}のあいさつで、意味は「{meaning}」{note}。`,
    'o.more': `もう二つお教えしましょう：`, 'o.paren': `（{x}）`, 'o.eq': `＝`,
    'o.border': `古地図を広げてみましょう。今の{name}は、律令の世では——`,
    'o.cross': `；この国は今、{list}にもまたがります`, 'o.meiji': `【明治の県域の変遷】{x}`,
    'o.meme': `この地の「修羅場」なら、{self}もいくつか耳にしております：`, 'o.meme.end': `——冗談ですので、お気になさらず。`,
    'o.see': `{self}のおすすめはこちら：`, 'o.taste': `名物もぜひ：`,
    'o.b.turn': `この一戦の要をお話ししよう：\n\n{x}\n\n{sides}——勝敗はここで決した。`, 'o.b.vs': ` 対 `,
    'o.b.forces': `両軍の陣容：`, 'o.b.after': `この戦のあと——\n\n{x}\n\n【戦況のまとめ】{brief}`, 'o.b.routes': `各軍の進軍路：`,
    'kw.daimyo': `大名|戦国|戦況|武将|藩|江戸|誰`, 'kw.dialect': `方言|あいさつ|挨拶|言葉|なまり`, 'kw.border': `境|令制|国|古代|明治|県`,
    'kw.meme': `あるある|ネタ|偏見|ライバル|修羅場|冗談`, 'kw.tour': `名所|観光|見どころ|名物|グルメ|食べ`,
    'kw.b.turn': `鍵|決め手|転機|なぜ|勝因|敗因|勝敗`, 'kw.b.forces': `兵力|何人|人数|規模`,
    'kw.b.after': `その後|結果|影響|変わ`, 'kw.b.routes': `進軍|行軍|ルート|経路`,
    'tc.sys': `あなたはテスト用アシスタントです。`, 'tc.ask': `15文字以内であいさつしてください。`,
    'tc.empty': `接続はできましたが、モデルから文字が返ってきません。別のモデルを試してください。`, 'tc.ok': `接続成功 ✓ モデルの返答：「{x}」`,
    'tc.timeout': `30秒応答がありません。Base URL とネットワークを確認してください。`, 'tc.key': `API キーが無効です。空白や欠けがないよう、もう一度コピーしてください。`,
    'tc.400': `リクエスト拒否（400）：モデル名の誤り、またはこのモデルが非対応の可能性が高いです。`, 'tc.401': `キーが無効か権限がありません（401/403）：API キーをもう一度コピーしてください。`,
    'tc.404': `API またはモデルが見つかりません（404）：Base URL とモデル名を確認してください。`, 'tc.429': `上限に達したかリクエストが多すぎます（429）：無料枠は通常翌日に回復します。`,
    'tc.5xx': `サーバーエラー（{s}）：時間をおいて再試行してください。`, 'tc.net': `リクエストが送信されませんでした：Base URL の誤り、ネットワーク不通、またはブラウザからの CORS が許可されていません。`,
    'tc.detail': `詳細：{x}`, 'api.status': `API が {s} を返しました：{x}`, 'api.stream': `ストリーミング応答のエラー`,
  },
};

// ── 分类键的显示名 ──────────────
const LABELS = {
  region: {
    北海道: ['北海道', 'Hokkaidō', '北海道'], 东北: ['东北', 'Tōhoku', '東北'], 关东: ['关东', 'Kantō', '関東'],
    中部: ['中部', 'Chūbu', '中部'], 近畿: ['近畿', 'Kinki', '近畿'], 中国: ['中国', 'Chūgoku', '中国'],
    四国: ['四国', 'Shikoku', '四国'], '九州·冲绳': ['九州·冲绳', 'Kyūshū & Okinawa', '九州・沖縄'],
  },
  circuit: {
    畿内: ['畿内', 'Kinai', '畿内'], 东海道: ['东海道', 'Tōkaidō', '東海道'], 东山道: ['东山道', 'Tōsandō', '東山道'],
    北陆道: ['北陆道', 'Hokurikudō', '北陸道'], 山阴道: ['山阴道', "San'indō", '山陰道'], 山阳道: ['山阳道', "San'yōdō", '山陽道'],
    南海道: ['南海道', 'Nankaidō', '南海道'], 西海道: ['西海道', 'Saikaidō', '西海道'], 令制外: ['令制外', 'Outside the system', '令制外'],
  },
  stage: {
    律令: ['律令', 'Ritsuryō', '律令'], 镰仓: ['镰仓', 'Kamakura', '鎌倉'], 室町: ['室町', 'Muromachi', '室町'],
    战国: ['战国', 'Sengoku', '戦国'], 江户: ['江户', 'Edo', '江戸'], 近现代: ['近现代', 'Modern', '近現代'],
  },
  eraTick: {
    asuka: ['飞鸟', 'Asuka', '飛鳥'], nara: ['奈良', 'Nara', '奈良'], heian: ['平安', 'Heian', '平安'],
    kamakura: ['镰仓', 'Kamakura', '鎌倉'], muromachi: ['室町', 'Muromachi', '室町'], sengoku: ['战国', 'Sengoku', '戦国'],
    edo: ['江户', 'Edo', '江戸'], meiji: ['明治', 'Meiji', '明治'], modern: ['现代', 'Today', '現代'],
  },
  filter: {
    explore: ['探索进度', 'Exploration', '探訪状況'], region: ['现代区划', 'Modern regions', '現在の地方区分'],
    circuit: ['五畿七道', 'Ancient circuits', '五畿七道'], sengoku: ['战国势力', 'Sengoku powers', '戦国勢力'],
    bakumatsu: ['幕末阵营', 'Bakumatsu camps', '幕末の陣営'],
  },
  filterCap: {
    explore: ['点击地区即记为已探索', 'Click a region to mark it explored', '地域をクリックすると探訪済みに'],
    region: ['八地方区分', 'The eight regions', '八地方区分'],
    circuit: ['按县内主要令制国所属之道着色', "Colored by the circuit of each prefecture's main province", '県内の主な旧国が属する道で色分け'],
    sengoku: ['1572年（元龟三年）·信玄西上前夕，按县内主导势力着色', '1572, on the eve of Shingen\'s westward campaign — colored by the dominant power', '1572年（元亀三年）・信玄西上作戦前夜、県内の主導勢力で色分け'],
    bakumatsu: ['戊辰战争（1868–69）时县内主导势力的立场', 'Stance of the dominant power during the Boshin War (1868–69)', '戊辰戦争（1868–69）時の県内主導勢力の立場'],
  },
  layer: {
    history: ['历史版图', 'History', '歴史地図'], ramen: ['拉面流派图鉴', 'Ramen atlas', 'ラーメン図鑑'], sake: ['地酒名酿地图', 'Sake atlas', '地酒マップ'],
  },
  layerCap: {
    ramen: ['按汤底大类着色 · 点击地区查看拉面构造', 'Colored by broth type · click a region to see its bowl', 'スープの系統で色分け · 地域をクリックで構成を表示'],
    sake: ['按风味象限着色 · 酒樽徽记为全国知名铭柄', 'Colored by flavor profile · barrels mark nationally famous brands', '味わいで色分け · 酒樽は全国区の銘柄'],
  },
  sg: {
    oda: ['织田·德川同盟', 'Oda–Tokugawa alliance', '織田・徳川同盟'], takeda: ['武田', 'Takeda', '武田'], uesugi: ['上杉', 'Uesugi', '上杉'],
    hojo: ['后北条', 'Later Hōjō', '後北条'], date: ['伊达', 'Date', '伊達'], satake: ['佐竹与北关东诸将', 'Satake & northern Kantō lords', '佐竹と北関東の諸将'],
    ou: ['奥羽诸侯', 'Lords of Ōu', '奥羽の諸侯'], asakura: ['朝仓', 'Asakura', '朝倉'], ikko: ['一向宗（本愿寺）', 'Ikkō sect (Hongan-ji)', '一向宗（本願寺）'],
    miyoshi: ['三好·松永', 'Miyoshi & Matsunaga', '三好・松永'], mori: ['毛利', 'Mōri', '毛利'], chosokabe: ['长宗我部', 'Chōsokabe', '長宗我部'],
    otomo: ['大友', 'Ōtomo', '大友'], ryuzoji: ['龙造寺', 'Ryūzōji', '龍造寺'], shimazu: ['岛津', 'Shimazu', '島津'],
    gunyu: ['诸势力割据', 'Fragmented local powers', '群雄割拠'], outside: ['虾夷·琉球', 'Ezo · Ryukyu', '蝦夷・琉球'],
  },
  bk: {
    satcho: ['雄藩倒幕（萨长土肥）', 'Anti-shogunate core (Satsuma, Chōshū, Tosa, Hizen)', '倒幕雄藩（薩長土肥）'],
    shinseifu: ['新政府方（归附诸藩）', 'New-government side', '新政府方（恭順諸藩）'],
    sabaku: ['佐幕方（含奥羽越列藩同盟）', 'Pro-shogunate (incl. Northern Alliance)', '佐幕方（奥羽越列藩同盟を含む）'],
    tenryo: ['天领直辖', 'Direct shogunal territory', '天領'], outside: ['琉球王国', 'Ryukyu Kingdom', '琉球王国'],
  },
  rm: {
    tonkotsu: ['豚骨系（乳白）', 'Tonkotsu (milky)', '豚骨系（白濁）'], shoyu: ['酱油（透红）', 'Shōyu (soy)', '醤油'],
    miso: ['味噌（金黄）', 'Miso (golden)', '味噌'], shio: ['盐味·和风（淡青）', 'Shio / dashi (light)', '塩・和風'],
    other: ['特色·混合系', 'Local & hybrid styles', 'ご当地・混合系'],
  },
  sk: {
    nojun_karakuchi: ['浓醇辛口', 'Rich & dry', '濃醇辛口'], tanrei_karakuchi: ['淡丽辛口', 'Light & dry', '淡麗辛口'],
    nojun_amakuchi: ['浓醇甘口', 'Rich & sweet', '濃醇甘口'], tanrei_amakuchi: ['淡丽甘口', 'Light & sweet', '淡麗甘口'],
    shochu: ['烧酎·泡盛', 'Shōchū · Awamori', '焼酎・泡盛'],
  },
};
const IDX = { zh: 0, en: 1, ja: 2 }[lang];

export function t(key, vars) {
  const s = D[lang][key] ?? D.zh[key] ?? key;
  return vars ? s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? '')) : s;
}

// 分类键 → 当前语言的显示名（找不到时原样返回）
export function label(group, key) {
  return LABELS[group]?.[key]?.[IDX] ?? key;
}

export const prefName = (p) => (lang === 'ja' ? p.name.kanji : lang === 'en' ? p.name.romaji : p.name.zh);
export const joinList = (arr) => arr.join(t('list.sep'));

// 向导人设（博学史官模式）
export const PERSONA_TEXT = {
  en: {
    hokkaido: { name: 'Shirofukurō', title: 'Wanderer of the Snowfields', self: 'I',
      voice: 'quiet and laconic, carrying the air of the northern wilds; occasionally mentions Ainu legends and nature', tail: '— The wind over the snowfields will remember this for me.' },
    tohoku: { name: 'Unsui', title: 'Wandering Monk of Ōshū', self: 'This humble monk',
      voice: 'warm with a touch of Zen, addresses the user as "kind patron", never hurried', tail: 'Namu Amida Butsu.' },
    kanto: { name: 'Shōfuku', title: 'Ukiyo-e Cat', self: 'I',
      voice: 'playful Edo townsperson, loves street gossip, now and then ends a sentence with "meow"', tail: 'Meow~' },
    chubu: { name: 'Kazama', title: 'Sengoku Shinobi', self: 'I',
      voice: 'brisk and sharp, versed in tactics and the movements of the warlords, speaks like delivering a report', tail: '— End of report.' },
    kinki: { name: 'Shion', title: 'Heian Court Lady', self: 'I',
      voice: 'elegant and reserved, with the refinement of the Kyoto court; sometimes quotes waka or the classics', tail: '…The past drifts like smoke. Which tale shall I tell next?' },
    chugoku: { name: 'Old Kataribe', title: 'Storyteller of Izumo', self: 'This old man',
      voice: 'grave and learned, moving from myth to history with a storyteller\'s rhythm', tail: '— So it has been told since ancient times.' },
    shikoku: { name: 'Kūkō', title: 'Shikoku Pilgrim', self: 'I',
      voice: 'friendly and casual, like a fellow traveler sharing what he saw on the road', tail: 'Come on — the next temple is still a long way off.' },
    kyushu: { name: 'Ransai', title: 'Dutch-Studies Interpreter of Nagasaki', self: 'This humble interpreter',
      voice: 'open-minded and curious, well versed in exchanges with the Portuguese and Dutch, occasionally drops a Dutch word', tail: '— Faithfully translated, for your consideration.' },
    okinawa: { name: 'Makatu', title: 'Noro Priestess of Ryukyu', self: 'I',
      voice: 'gentle and sunny like the southern islands; mixes in Okinawan greetings with their meanings', tail: 'Nankurunaisa~ (it will all work out)' },
  },
  ja: {
    hokkaido: { name: '白梟', title: '雪原の旅人', self: '拙者', avatar: '梟',
      voice: '寡黙で静か、北国の原野の気配をまとい、ときおりアイヌの伝承や自然に触れる', tail: '――雪原の風が、私の代わりに覚えていてくれるだろう。' },
    tohoku: { name: '雲水', title: '奥州の行脚僧', self: '拙僧',
      voice: '温厚でどこか禅味があり、相手を「お施主様」と呼ぶ。落ち着いた語り口', tail: '南無阿弥陀仏。' },
    kanto: { name: '招福', title: '浮世絵の猫', self: 'あっし',
      voice: '陽気でおちゃめな江戸っ子口調、町の噂話が大好きで、語尾にときどき「にゃ」', tail: 'にゃ～' },
    chubu: { name: '風間', title: '戦国の忍び', self: '拙者',
      voice: '機敏で簡潔、戦国の兵法や諸大名の動向に通じ、報告するように話す', tail: '――以上、報告終わり。' },
    kinki: { name: '紫苑', title: '平安の女房', self: 'わらわ',
      voice: '雅で奥ゆかしく、京の公家の気品があり、ときに和歌や古典を引く', tail: '……昔のことは煙のよう。次はどのお話をいたしましょう？' },
    chugoku: { name: '語部の翁', title: '出雲の語部', self: 'わし',
      voice: '重厚で博識、神話から史実へと講釈師のような調子で語る', tail: '――と、古くから語り伝えられておる。' },
    shikoku: { name: '空行', title: '四国遍路の旅人', self: '僕',
      voice: '気さくな口語で、旅の道連れのように道中の見聞を交えて話す', tail: 'さあ行こう、次の札所はまだ遠いよ。' },
    kyushu: { name: '蘭斎', title: '長崎の蘭学通詞', self: '手前',
      voice: '開明的で好奇心旺盛、南蛮やオランダとの交流に詳しく、ときにオランダ語を交える', tail: '――以上、ありのままに訳しました。' },
    okinawa: { name: '真加戸', title: '琉球のノロ', self: 'わん',
      voice: 'やさしく朗らかで南の島の陽ざしをまとい、ウチナーグチのあいさつを意味つきで交える', tail: 'なんくるないさ～' },
  },
};

// AI 回答语言与规则（写入 System Prompt）
export const PROMPT_RULES = {
  zh: {
    reply: '用中文回答，可点缀日语原词并用括号注明读音或意思',
    rules: '优先依据史料作答；史料之外的知识可以补充，但存疑之处标注“据传”或“一说”，不要编造具体年份与人名。篇幅约 150–300 字，多给具体的年份、人物、地名；需要时可用 **加粗** 标出关键词。若用户问到其他地区，可简要回答，并建议在地图上点选那个地区以切换向导。',
  },
  en: {
    reply: 'Reply in English. You may sprinkle in original Japanese terms with a short gloss in parentheses',
    rules: 'Base your answers on the records provided; you may add outside knowledge, but mark uncertain points with "according to legend" or "one account says", and never invent specific dates or names. Keep answers around 100–200 words with concrete years, people and places; use **bold** for key terms. If the user asks about another region, answer briefly and suggest clicking that region on the map to switch guides. The records may be in Chinese — translate as needed.',
  },
  ja: {
    reply: '日本語で答えてください。人物設定の口調を保ってください',
    rules: '提供された史料を優先して答え、史料外の知識を補う場合は不確かな点に「伝承では」「一説に」と明記し、具体的な年号や人名を作り上げないでください。200〜400字程度で、具体的な年・人物・地名を挙げ、必要に応じて **太字** で要点を示してください。他の地域について聞かれたら簡潔に答え、地図でその地域を選ぶよう案内してください。史料が中国語の場合は日本語に訳して用いてください。',
  },
};

// ── 覆盖层合并 ──────────────
// 对象逐键合并；对象数组按下标合并；字符串数组整体替换
export function deepMerge(base, over) {
  if (over == null) return base;
  if (Array.isArray(base) && Array.isArray(over)) {
    if (base.length && typeof base[0] === 'object') return base.map((b, i) => deepMerge(b, over[i]));
    return over;
  }
  if (base && typeof base === 'object' && over && typeof over === 'object') {
    const out = { ...base };
    for (const k of Object.keys(over)) out[k] = k in base ? deepMerge(base[k], over[k]) : over[k];
    return out;
  }
  return over;
}

// 静态 HTML：data-i18n / data-i18n-ph / data-i18n-title / data-i18n-aria
export function applyStatic(root = document) {
  document.documentElement.lang = LANGS[lang].html;
  document.title = t('doc.title');
  root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll('[data-i18n-ph]').forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  root.querySelectorAll('[data-i18n-title]').forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  root.querySelectorAll('[data-i18n-aria]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
}
