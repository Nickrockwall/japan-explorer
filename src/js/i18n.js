// 多语言：中文（底本）/ English / 日本語
// 语言在页面加载时确定（手动选择 > 浏览器语言），切换语言会重新载入页面。
// 数据翻译以「覆盖层」形式存放在 src/data/i18n/{lang}/，只覆盖文字字段；分类键（地方、五畿七道、时代等）不翻译，显示时经 t() 转换。
import { uiPref } from './store.js';
import { mapKey } from './country.js';

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

// 衬线字体栈（CSS 的 --serif，按 <html lang> 取日文或中文字形），给画在 canvas 上的地图标签用
export const serifFont = () => getComputedStyle(document.documentElement).getPropertyValue('--serif').trim() || 'serif';

export function setLang(l) {
  if (!LANGS[l] || l === lang) return;
  uiPref.set('lang', l);
  // 地址栏里的 lang 优先级最高，切换时一并改掉，否则重新载入后又会回到旧语言
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.has('lang') || h.has('pref') || h.has('map')) {
    h.set('lang', l);
    location.hash = h.toString();
  }
  location.reload();
}

// 当前页面状态的地址片段：#pref=26&lang=ja（日本以外的地图在最前面加 map=）
export function stateHash(prefId) {
  const h = new URLSearchParams();
  if (mapKey !== 'japan') h.set('map', mapKey);
  if (prefId) h.set('pref', prefId);
  h.set('lang', lang);
  return `#${h.toString()}`;
}

// 可分享的完整链接
export function shareURL(prefId) {
  return `${location.origin}${location.pathname}${stateHash(prefId)}`;
}

// ── 界面词典 ──────────────
const D = (await import(`./lang/${lang}.js`)).default; // 只下载当前语言的词典（src/js/lang/）

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
    南海道: ['南海道', 'Nankaidō', '南海道'], 西海道: ['西海道', 'Saikaidō', '西海道'], 北海道: ['北海道（1869）', 'Hokkaidō (1869)', '北海道（1869）'],
    令制外: ['令制外', 'Outside the system', '令制外'],
  },
  stage: {
    律令: ['律令', 'Ritsuryō', '律令'], 镰仓: ['镰仓', 'Kamakura', '鎌倉'], 室町: ['室町', 'Muromachi', '室町'],
    战国: ['战国', 'Sengoku', '戦国'], 江户: ['江户', 'Edo', '江戸'], 近现代: ['近现代', 'Modern', '近現代'],
  },
  eraTick: {
    asuka: ['飞鸟', 'Asuka', '飛鳥'], nara: ['奈良', 'Nara', '奈良'], heian: ['平安', 'Heian', '平安'],
    kamakura: ['镰仓', 'Kamakura', '鎌倉'], muromachi: ['室町', 'Muromachi', '室町'], sengoku: ['战国', 'Sengoku', '戦国'],
    edo: ['江户', 'Edo', '江戸'], meiji: ['明治', 'Meiji', '明治'], taisho: ['大正', 'Taishō', '大正'], modern: ['现代', 'Today', '現代'],
  },
  filter: {
    explore: ['探索进度', 'Exploration', '探訪状況'], region: ['现代区划', 'Modern regions', '現在の地方区分'],
    circuit: ['五畿七道', 'Ancient circuits', '五畿七道'], sengoku: ['战国势力', 'Sengoku powers', '戦国勢力'],
    bakumatsu: ['幕末阵营', 'Bakumatsu camps', '幕末の陣営'], power: ['古国国力', 'Rankings', '旧国の国力'],
  },
  filterCap: {
    explore: ['点击地区即记为已探索', 'Click a region to mark it explored', '地域をクリックすると探訪済みに'],
    region: ['八地方区分', 'The eight regions', '八地方区分'],
    circuit: ['按县内主要令制国所属之道着色', "Colored by the circuit of each prefecture's main province", '県内の主な旧国が属する道で色分け'],
    sengoku: ['1572年（元龟三年）·信玄西上前夕，按县内主导势力着色', '1572, on the eve of Shingen\'s westward campaign — colored by the dominant power', '1572年（元亀三年）・信玄西上作戦前夜、県内の主導勢力で色分け'],
    bakumatsu: ['戊辰战争（1868–69）时县内主导势力的立场', 'Stance of the dominant power during the Boshin War (1868–69)', '戊辰戦争（1868–69）時の県内主導勢力の立場'],
    power: ['68 国的今日人口与江户国力', 'Population today and Edo-period strength of the 68 provinces', '68か国の現在の人口と江戸の国力'],
  },
  layer: {
    history: ['历史版图', 'History', '歴史地図'], ramen: ['拉面流派图鉴', 'Ramen atlas', 'ラーメン図鑑'], sake: ['地酒名酿地图', 'Sake atlas', '地酒マップ'],
    pilgrimage: ['圣地巡礼', 'Pilgrimage', '聖地巡礼'], koku: ['古国巡礼', 'Ancient sites', '古国めぐり'],
  },
  pil: {
    all: ['全部巡礼', 'All', 'すべて'], anime: ['动漫圣地', 'Anime', 'アニメ聖地'], taiga: ['大河剧名所', 'Taiga drama', '大河ドラマ'],
  },
  layerCap: {
    koku: ['诸国一宫 · 国府 · 国分寺 · 点图钉参拜（放大地图显示国府与国分寺；空心 = 只定位到市区町村）', 'Ichinomiya shrines, provincial capitals and kokubunji temples · tap a pin (zoom in to see capitals and temples; hollow = located to the municipality only)', '諸国一宮・国府・国分寺 · ピンをタップ（拡大すると国府と国分寺も表示。白抜き＝市区町村までの位置）'],
    pilgrimage: ['动漫圣地与大河剧名所 · 点图钉查看作品与巡礼贴士', 'Anime and taiga-drama locations · tap a pin for the scene and tips', 'アニメ聖地と大河ドラマゆかりの地 · ピンをタップで作品と巡礼のコツ'],
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
  const s = D[key] ?? key;
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
