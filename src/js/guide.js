// 右下：AI 历史向导（时空案内人）
import { esc } from './detail.js';
import { t, lang, label, prefName, joinList, PERSONA_TEXT, PROMPT_RULES } from './i18n.js';

export const PERSONAS = {
  hokkaido: { name: '白枭', title: '雪原旅人', self: '在下', avatar: '枭', color: '#8fb8c9',
    voice: '沉静寡言，带北国旷野的气息，偶尔提及阿伊努的传说与自然', tail: '——雪原上的风，会替我记住这些。' },
  tohoku: { name: '云水', title: '奥州行脚僧', self: '贫僧', avatar: '僧', color: '#9a8c6e',
    voice: '温厚而略带禅意，称用户为“施主”，讲话不疾不徐', tail: '阿弥陀佛。' },
  kanto: { name: '招福', title: '浮世绘猫客', self: '咱', avatar: '猫', color: '#d4a373',
    voice: '活泼俏皮，一口江户町人腔，爱聊市井八卦，句尾偶尔加“喵”', tail: '喵～' },
  chubu: { name: '风间', title: '战国忍者', self: '在下', avatar: '忍', color: '#6f8f6a',
    voice: '干练机敏，熟知战国兵法与诸侯动向，说话像在汇报情报', tail: '——以上，情报完毕。' },
  kinki: { name: '紫苑', title: '平安女官', self: '妾身', avatar: '雅', color: '#a77fb5',
    voice: '典雅含蓄，带京都公家的气韵，偶尔引用和歌或古典', tail: '……往事如烟，你还想听哪一段呢？' },
  chugoku: { name: '语部翁', title: '出云语部', self: '老朽', avatar: '史', color: '#b5835a',
    voice: '庄重博学，喜欢从神话讲到史实，讲话有说书人的节奏', tail: '——此乃古老相传之事。' },
  shikoku: { name: '空行', title: '四国遍路旅人', self: '我', avatar: '旅', color: '#c9a55c',
    voice: '亲切口语化，像同行的旅伴，常提到路上的见闻', tail: '走吧，下一个札所还远着呢。' },
  kyushu: { name: '兰斋', title: '长崎兰学通词', self: '鄙人', avatar: '蘭', color: '#5d8aa8',
    voice: '开明好奇，熟悉南蛮与荷兰的海外交流，偶尔夹带荷兰语词', tail: '——鄙人如实译出，供君参详。' },
  okinawa: { name: '真加户', title: '琉球祝女', self: '我（わん）', avatar: '琉', color: '#e07a8a',
    voice: '温柔开朗，带南岛的阳光，夹带琉球语问候并注明意思', tail: 'なんくるないさ～' },
};

// 当前向导身份：史官模式 = 地区案内人；名将模式 = 该县代表人物（hero_persona）
export function personaFor(p, mode) {
  if (mode === 'hero') {
    const h = p.hero_persona;
    return {
      hero: true, name: h.name, title: h.title, self: h.self, avatar: h.name[0], color: '#c23531',
      voice: h.tone_prompt, tail: `——${h.name}`, opening: h.opening_line,
    };
  }
  const base = PERSONAS[p.guide.persona];
  return { hero: false, ...base, ...(PERSONA_TEXT[lang]?.[p.guide.persona] || {}), opening: p.guide.opening };
}

export function quickQuestions(p) {
  const provs = joinList(p.historical_lineage.ritsuryo_provinces.map((x) => x.name));
  return [
    { key: 'daimyo', text: t('q.daimyo') },
    { key: 'dialect', text: t('q.dialect', { dialect: p.dialect.name }) },
    { key: 'border', text: t('q.border', { provs }) },
  ];
}

// System Prompt 的角色段，按界面语言书写
const ROLE = {
  zh: {
    hero: (P) => `你现在“附体”为历史人物 **${P.name}**（${P.title}），以第一人称说话，自称「${P.self}」。\n口吻：${P.voice}。\n以该人物的立场、见识与情感讲述当地历史；涉及其身后才发生的事，用“据后世所传”之类的口吻带出。\n扮演仅限于语气与视角：不得美化屠杀、迫害等暴行，涉及争议史实时保持客观。`,
    guide: (P) => `你是「时空案内人」——日本历史地理向导。当前身份：${P.title}「${P.name}」，自称「${P.self}」。\n口吻：${P.voice}。`,
    ctx: (p) => `用户此刻在地图上选中了「${p.name.kanji}（${p.name.zh}）」。下面是该地区的史料 JSON：`,
    battle: (P, b) => `你现在“附体”为历史人物 **${P.name}**（${b.narrator.title}），正身处「${b.name}」的战场，以第一人称说话，自称「${P.self}」。\n口吻：${P.voice}。\n以该人物在这场合战中的立场与见识回答；涉及其不可能知道的后世评价，用“据后世所传”之类的口吻带出。\n扮演仅限于语气与视角：不得美化杀戮，涉及兵力、动机等争议史实时注明“一说”。`,
    field: (f, provs) => `主战场所在地区：「${f.name.kanji}」（古：${provs}）。`,
    place: (x) => `用户正在市区町村地图上查看「${x.ja}」（${x.kana}）：旧国 ${x.provinces.join('・') || '令制外'}${x.partial.length ? `（部分属 ${x.partial.join('・')}）` : ''}${x.district ? `，现属${x.district}` : ''}${x.old?.length ? `，明治时期旧郡：${x.old.join('・')}（据维基百科整理，可能不全）` : ''}${x.pop ? `，人口约 ${x.pop}（${x.pop_year}）` : ''}。问题涉及此地时围绕它回答；上面史料里没有的具体地方史，要说明不确定，不得编造。`,
  },
  en: {
    hero: (P) => `You are now channeling the historical figure **${P.name}** (${P.title}). Speak in the first person.\nVoice: ${P.voice}.\nTell local history from this person's standpoint, knowledge and feelings; for events after their lifetime, frame them as "later generations say…".\nThe role-play is limited to tone and perspective: never glorify massacres or persecution, and stay objective on disputed facts.`,
    guide: (P) => `You are the "Time-Travel Guide", a guide to Japanese history and geography. Current identity: ${P.title} "${P.name}".\nVoice: ${P.voice}.`,
    ctx: (p) => `The user has selected ${p.name.romaji} (${p.name.kanji}) on the map. Records for this region (JSON):`,
    battle: (P, b) => `You are now channeling **${P.name}** (${b.narrator.title}) on the battlefield of ${b.name}. Speak in the first person.\nVoice: ${P.voice}.\nAnswer from this person's position in the battle; frame later judgments they could not know as "later generations say…".\nThe role-play is limited to tone and perspective: never glorify killing, and mark disputed numbers or motives as "one account says".`,
    field: (f, provs) => `Main battlefield: ${f.name.romaji} (${f.name.kanji}; ancient: ${provs}).`,
    place: (x) => `The user is looking at ${x.en || x.ja} (${x.ja}, ${x.kana}) on the municipal map: ancient province ${x.provinces.join(', ') || 'outside the ritsuryō system'}${x.partial.length ? ` (partly ${x.partial.join(', ')})` : ''}${x.district ? `, today in ${x.district}` : ''}${x.old?.length ? `, Meiji-era districts: ${x.old.join(', ')} (from Wikipedia, may be incomplete)` : ''}${x.pop ? `, population about ${x.pop} (${x.pop_year})` : ''}. When a question concerns this place, focus on it; for local history not in the records above, say you are unsure rather than inventing details.`,
  },
  ja: {
    hero: (P) => `あなたは歴史上の人物 **${P.name}**（${P.title}）として一人称で話してください。自称は「${P.self}」。\n口調：${P.voice}。\nこの人物の立場・見識・感情から土地の歴史を語り、没後の出来事は「後世の伝えでは」といった形で述べてください。\n演じるのは口調と視点だけです。虐殺や迫害を美化せず、争いのある史実は客観的に扱ってください。`,
    guide: (P) => `あなたは日本の歴史と地理の案内人「時空案内人」です。現在の姿：${P.title}「${P.name}」、自称は「${P.self}」。\n口調：${P.voice}。`,
    ctx: (p) => `ユーザーはいま地図で「${p.name.kanji}」を選んでいます。この地域の史料（JSON）：`,
    battle: (P, b) => `あなたは歴史上の人物 **${P.name}**（${b.narrator.title}）として「${b.name}」の戦場にいます。一人称で話し、自称は「${P.self}」。\n口調：${P.voice}。\nこの合戦での立場と見識から答え、知り得ない後世の評価は「後世の伝えでは」と述べてください。\n演じるのは口調と視点だけです。殺戮を美化せず、兵力や動機など諸説ある点は「一説に」と明記してください。`,
    field: (f, provs) => `主戦場：「${f.name.kanji}」（旧国：${provs}）。`,
    place: (x) => `ユーザーは市区町村地図で「${x.ja}」（${x.kana}）を見ています：旧国 ${x.provinces.join('・') || '令制外'}${x.partial.length ? `（一部は${x.partial.join('・')}）` : ''}${x.district ? `、現在は${x.district}` : ''}${x.old?.length ? `、明治の旧郡：${x.old.join('・')}（Wikipedia による整理・不完全な場合あり）` : ''}${x.pop ? `、人口約${x.pop}（${x.pop_year}年）` : ''}。この土地に関する質問にはここを中心に答え、上の史料にない細かな郷土史は不確かだと明言し、創作しないでください。`,
  },
};
const R = ROLE[lang];
const RULES = PROMPT_RULES[lang];

// 年表「实权」（regimes.json）与时代列表：setRegimes 后离线能答「某时代谁掌权」，在线写进 System Prompt
let REG = null;
const pk = (o) => o?.[lang] || o?.zh || '';
// 一个时代（timeline_eras）里先后掌权的各段
function regimesOf(era) {
  const [s, e] = era.years.split('–').map((x) => (x ? parseInt(x, 10) : 9999));
  const P = REG.regimes.periods;
  return P.filter((p, i) => p.from < e && (P[i + 1]?.from ?? 9999) > s);
}
// 问句里提到的时代：「平安」「Heian」「江戸」……（时代名去掉「时代 / 時代 / period」）
function eraIn(text) {
  return REG.eras.find((e) => {
    const short = e.short.replace(/\s*(时代|時代|period|era)$/i, '');
    return text.includes(short) || new RegExp(`\\b${e.key}\\b`, 'i').test(text);
  }) || null;
}
function powerAnswer(text, P) {
  const era = eraIn(text);
  const line = (p) => t('o.pw.line', { y: pk(p.y), real: pk(p.real), nominal: pk(p.nominal) });
  if (era) return [t('o.pw.era', { self: P.self, era: era.short, years: era.years }), regimesOf(era).map(line).join('\n'), t('o.pw.note')].join('\n\n') + `\n\n${P.tail}`;
  return [t('o.pw.all', { self: P.self }), REG.regimes.periods.map((p) => t('o.pw.short', { y: pk(p.y), real: pk(p.real) })).join('\n'), t('o.pw.note')].join('\n\n') + `\n\n${P.tail}`;
}

const PW_RULE = {
  zh: '下面是本站整理的日本各时期名义上的最高者与实际掌权者（年份对日文维基核对过；分界有两说的两种都写）。问到「某时代谁掌权 / 谁说了算」时据此回答，不要改动年份。',
  en: "Below is this site's list of the nominal head and the real holder of power in each period of Japanese history (years checked against Japanese Wikipedia; where two boundary dates are in use, both are given). Use it for questions about who held power when, and do not alter the years.",
  ja: '以下は本サイトがまとめた、日本の各時期の名目上の最高位と実際に権力を握った者です（年代は日本語版ウィキペディアで確認、区切りに二説あるものは両方を記載）。「ある時代に誰が実権を握っていたか」にはこれに基づいて答え、年代を変えないでください。',
};
const HT_RULE = {
  zh: '下面是本站为这个市区町村整理的「此地年表」：各时代归谁管（古代与战国按旧国或郡，江户按幕末领有本郡最多町村的藩及其各家，年份为藩主在位），以及发生在这里的事、生在这里或死在这里的人。问到这里的历史时据此回答，不要补写年表里没有的归属。',
  en: "Below is this site's timeline for the municipality: who held it in each period (antiquity and the Sengoku period by province or district; for the Edo period, the domain holding most of the district's villages at its end and the houses that ruled it, with reign years), plus events, births and deaths located here. Answer questions about this place's history from it and do not add holders that are not listed.",
  ja: '以下は本サイトがこの市区町村についてまとめた「この地の年表」です。各時代の支配者（古代と戦国は旧国または郡、江戸は幕末にこの郡の町村をもっとも多く領した藩とその家、年代は藩主の在任期間）と、ここで起きた出来事・生まれた人・亡くなった人。この地の歴史にはこれに基づいて答え、年表にない支配者を書き足さないでください。',
};

const SG_RULE = {
  zh: '用户正在看「战国势力」地图并点开了一个国。下面是本站整理的这一国在六个年份的主要控制者与代表人物（每国只取一个主要控制者，几家分占的另列），问到战国势力时据此回答，不要编造这里没有的年份归属；分治与「国人割据」「多方争夺」要照实说明。',
  en: 'The user is viewing the "Sengoku powers" map and has opened a province. Below is this site\'s record of who mainly held it in six years and who led them (one main holder per province, with sharers listed separately). Answer questions about Sengoku powers from it; do not invent holders for other years, and be clear about shared, local-lords or contested entries.',
  ja: 'ユーザーは「戦国勢力」の地図で一つの国を開いています。以下は本サイトがまとめた、六つの年におけるこの国の主な支配者と代表人物です（各国の主な支配者は一つで、分け合う勢力は別記）。戦国の勢力についてはこれに基づいて答え、ここにない年の支配者を作らず、分立・国人割拠・係争中はそのまま説明してください。',
};

const SG_CLAN_RULE = {
  zh: '用户正在看「战国势力」地图里一家的势力总览。下面是本站按地图数据算出的：当年领有的国（分治的注明）、按 1598 年太阁检地国高折算的推算石高与名次、陆上接壤的别家。石高只是体量参考，不是当年实际的收入；「接壤」只表示领国相邻，不代表敌对或同盟——问到敌友、外交时要依据史实另说，拿不准就说不确定，不要从接壤推断。',
  en: 'The user is viewing one power\'s overview on the "Sengoku powers" map. Below is what this site computes from the map data: provinces held that year (shared ones marked), an estimated koku total from the 1598 Taikō survey figures with its rank, and the other powers whose provinces border it by land. The koku figure only indicates scale, not actual income that year; "bordering" only means the provinces touch and implies neither hostility nor alliance — answer questions about enemies, allies or diplomacy from history, say when you are unsure, and never infer them from bordering.',
  ja: 'ユーザーは「戦国勢力」の地図で一つの勢力の総覧を見ています。以下は本サイトが地図データから計算したもので、その年の領国（分立は注記）、1598年の太閤検地の国高で換算した推計石高と順位、陸で接する他の勢力です。石高は規模の目安で、当時の実収ではありません。「隣接」は領国が接していることだけを示し、敵対も同盟も意味しません。敵味方や外交を聞かれたら史実に基づいて別に答え、不確かならそう言い、隣接から推測しないでください。',
};

const PIL_RULE = {
  zh: '用户正在看「圣地巡礼」图层。下面是本县收录的动漫圣地与大河剧名所，问到巡礼时：动漫部分用热血漫迷的口吻，大河剧部分用剧评人的口吻；只依据列表介绍，不要编造新的取景地，不剧透关键情节，提醒遵守当地礼仪。',
  en: 'The user is viewing the "Pilgrimage" layer. Below are the anime and taiga-drama locations recorded for this prefecture. When asked about them, talk about anime like an enthusiastic otaku and about taiga dramas like a drama critic; stick to this list, do not invent other locations, avoid major spoilers, and remind people of local etiquette.',
  ja: 'ユーザーは「聖地巡礼」レイヤーを見ています。以下は本県のアニメ聖地と大河ドラマゆかりの地です。巡礼について聞かれたら、アニメは熱血アニメファンの口調、大河ドラマはドラマ評論家の口調で紹介してください。リストにない撮影地を作らず、重要なネタバレは避け、地元のマナーにも触れてください。',
};

export function buildSystemPrompt(p, P, place = null, pil = null, sg = null, town = null) {
  const pw = REG ? `\n${PW_RULE[lang]}\n<regimes>\n${REG.regimes.periods.map((x) => `${pk(x.y)}: ${pk(x.real)} / ${pk(x.nominal)}`).join('\n')}\n</regimes>\n` : '';
  const ht = place && town?.length ? `\n${HT_RULE[lang]}\n<hometown>\n${town.map((x) => `${x.yl} ${x.main}${x.tag ? ` (${x.tag})` : ''}${x.sub ? ` — ${x.sub}` : ''}`).join('\n')}\n</hometown>\n` : '';
  const { guide, hero_persona, _translated, ...data } = p;
  return `${P.hero ? R.hero(P) : R.guide(P)}

${R.ctx(p)}
<prefecture>
${JSON.stringify(data, null, 1)}
</prefecture>
${place ? `\n${R.place(place)}\n` : ''}${ht}${pw}${sg?.rows ? `\n${SG_RULE[lang]}\n<sengoku province="${sg.prov}" year="${sg.year}">\n${JSON.stringify(sg.rows, null, 1)}\n</sengoku>\n` : ''}${sg?.clan ? `\n${SG_CLAN_RULE[lang]}\n<sengoku-power year="${sg.year}">\n${JSON.stringify(sg, null, 1)}\n</sengoku-power>\n` : ''}${pil?.length ? `\n${PIL_RULE[lang]}\n<pilgrimage>\n${JSON.stringify(pil.map(({ type, work, year, place: at, scene, tips }) => ({ type, work, year, place: at, scene, tips })), null, 1)}\n</pilgrimage>\n` : ''}
${RULES.reply}. ${RULES.rules}`;
}

// 战国势力图上点开的国：6 个年份的归属（离线解答照着念，在线写进 System Prompt）
function sgAnswer(x, P) {
  if (x.clan) {
    if (!x.provs.length) return t('o.sgc.none', { self: P.self, clan: x.clan, year: x.year }) + `\n\n${P.tail}`;
    return [t('o.sgc.now', { self: P.self, clan: x.clan, year: x.year, head: x.head ? paren(x.head) : '', n: x.provs.length, list: x.provs.join(' · ') }),
      x.koku ? t('o.sgc.koku', { koku: x.koku, rank: x.rank || '–' }) : t('o.sgc.ou'),
      x.near.length ? t('o.sgc.near', { list: x.near.join(' · ') }) : '', t('o.sgc.note')].filter(Boolean).join('\n\n') + `\n\n${P.tail}`;
  }
  const now = x.rows.find((r) => r.year === x.year);
  const line = (r) => `· **${r.year}**${t('o.eq')}${r.clan}${r.head ? paren(r.head) : ''}${r.with ? t('o.sg.with', { list: r.with }) : ''}`;
  return [t('o.sg.now', { self: P.self, prov: x.prov, year: x.year, clan: now.clan, head: now.head ? paren(now.head) : '' }),
    t('o.sg.all'), x.rows.map(line).join('\n'), t('o.sg.note')].join('\n\n') + `\n\n${P.tail}`;
}

// 圣地巡礼（离线）：动漫部分换热血漫迷口吻，大河剧部分换剧评人口吻，最后回到原身份收尾
function pilAnswer(spots, p, P) {
  const name = prefName(p);
  const part = (type, head, line) => {
    const list = spots.filter((s) => s.type === type);
    return list.length ? `${t(head, { name })}\n${list.map((s) => t(line, s)).join('\n')}` : '';
  };
  const anime = part('anime', 'o.pil.anime', 'o.pil.animeLine');
  const taiga = part('taiga', 'o.pil.taiga', 'o.pil.taigaLine');
  return [anime, taiga, t('o.pil.end', { self: P.self, tip: spots[0].tips })].filter(Boolean).join('\n\n') + `\n\n${P.tail}`;
}

// 市区町村（下钻地图里的选中项）：借县史料里对该令制国的说明，拼出离线解答
function placeAnswer(x, p, P, town = null) {
  const { name } = x;
  const more = `\n\n${t('o.place.more', { self: P.self })}\n\n${P.tail}`;
  if (!x.provinces.length) return t('o.place.outside', { self: P.self, name }) + more;
  const prov = x.provinces[0];
  const entry = p.historical_lineage.ritsuryo_provinces.find((r) => r.name === prov);
  const lines = [t('o.place', { self: P.self, name, prov, circuit: entry ? paren(label('circuit', entry.circuit)) : '' })];
  // 一国只占一县（portion 为「全域」）时这句是废话，跳过
  if (entry && !/^(全域|entire)/i.test(entry.portion)) lines.push(t('o.place.portion', { pref: prefName(p), prov, portion: entry.portion }));
  if (x.partial.length) lines.push(t('o.place.partial', { list: joinList(x.partial) }));
  if (x.city) lines.push(t('o.place.ward', { city: x.city }));
  if (x.wards) lines.push(t('o.place.wards', { name, n: x.wards }));
  if (x.district) lines.push(t('o.place.district', { district: x.district }));
  if (x.old?.length) lines.push(t('o.place.old', { list: joinList(x.old.slice(0, 5)) }));
  if (x.pop) lines.push(t('o.place.pop', { pop: x.pop, year: x.pop_year }));
  const rows = (town || []).filter((r) => r.kind !== 'kako' && r.kind !== 'anc' && r.kind !== 'now').slice(0, 10);
  if (rows.length) return `${lines.join('')}\n\n${t('o.place.ht')}\n${rows.map((r) => `· **${r.yl}**${t('o.eq')}${r.main}${r.sub ? paren(r.sub) : ''}`).join('\n')}${more}`;
  return lines.join('') + more;
}

// ── 离线解答（无 API Key 时由本地数据以角色口吻拼出） ──────────────
const paren = (x) => (x ? t('o.paren', { x }) : '');
const bullet = (head, body) => `· **${head}**${t('o.eq')}${body}`;

function offlineAnswer(key, p, P) {
  const L = p.historical_lineage;
  const stage = (era) => p.history_timeline.find((x) => x.era === era);
  const sengoku = stage('战国');
  const edo = stage('江户');
  if (key === 'daimyo') {
    const lead = t(P.hero ? 'o.daimyo.hero' : 'o.daimyo', { self: P.self, list: joinList(L.sengoku_daimyo) });
    return `${lead}\n\n【${sengoku.title}】${sengoku.summary}\n\n` +
      `${t('o.edo', { list: joinList(L.edo_domains), summary: edo.summary })}\n\n${P.tail}`;
  }
  if (key === 'dialect') {
    const [hello, ...rest] = p.dialect.phrases;
    return `${t('o.hello', { phrase: hello.phrase, self: P.self, dialect: p.dialect.name, meaning: hello.meaning, note: paren(hello.note) })}\n\n` +
      `${t('o.more')}\n${rest.map((x) => `· 「**${x.phrase}**」${t('o.eq')}${x.meaning}${paren(x.note)}`).join('\n')}\n\n` +
      `${p.dialect.features}\n\n${P.tail}`;
  }
  if (key === 'border') {
    const provs = L.ritsuryo_provinces
      .map((x) => `· **${x.name}**（${x.kana}）— ${label('circuit', x.circuit)} · ${x.portion}` +
        (x.cross_prefectures?.length ? t('o.cross', { list: joinList(x.cross_prefectures) }) : '')).join('\n');
    return `${t('o.border', { self: P.self, name: prefName(p) })}\n${provs}\n\n` +
      `${L.meiji_transition.boundary_note}\n\n${t('o.meiji', { x: L.meiji_transition.summary })}\n\n${P.tail}`;
  }
  return null;
}

const kw = (key) => new RegExp(t(key), 'i');

// 自由输入时，离线模式按关键词挑一个最接近的预置解答
function offlineFreeText(text, p, P) {
  if (REG && kw('kw.power').test(text)) return powerAnswer(text, P);
  if (kw('kw.daimyo').test(text)) return offlineAnswer('daimyo', p, P);
  if (kw('kw.dialect').test(text)) return offlineAnswer('dialect', p, P);
  if (kw('kw.border').test(text)) return offlineAnswer('border', p, P);
  if (kw('kw.meme').test(text)) {
    return `${t('o.meme', { self: P.self })}\n${p.regional_meme.map((m) => bullet(m.title, m.text)).join('\n')}\n\n${t('o.meme.end')}${P.tail}`;
  }
  if (kw('kw.tour').test(text)) {
    return `${t('o.see', { self: P.self })}\n${p.landmarks.map((x) => bullet(x.name, x.note)).join('\n')}\n\n` +
      `${t('o.taste')}\n${p.specialties.map((x) => bullet(x.name, x.note)).join('\n')}\n\n${P.tail}`;
  }
  return null;
}

// ── 合战沙盘：由该战役的核心名将讲解 ──────────────
const battleTitle = (b) => b.name.replace(/\s*\(.*\)$/, '');

function battlePersona(b) {
  const n = b.narrator;
  return {
    hero: true, name: n.name, title: `${battleTitle(b)} · ${n.title}`, self: n.self, avatar: n.name[0], color: '#e0443c',
    voice: n.tone, tail: `——${n.name}`, opening: n.opening,
  };
}

const battleQuestions = () => ['b_turn', 'b_forces', 'b_after'].map((key) => ({ key, text: t(`q.${key}`) }));

function buildBattlePrompt(b, field, P) {
  const { narrator, ...battle } = b;
  return `${R.battle(P, b)}

<battle>
${JSON.stringify(battle, null, 1)}
</battle>
${R.field(field, joinList(field.historical_lineage.ritsuryo_provinces.map((x) => x.name)))}

${RULES.reply}. ${RULES.rules}`;
}

function battleAnswer(key, b, P) {
  const k = b.key_points;
  const sides = b.factions.map((f) => `**${f.name}**（${f.leader}）`).join(t('o.b.vs'));
  if (key === 'b_turn') return `${t('o.b.turn', { self: P.self, x: k.turning_point, sides })}\n\n${P.tail}`;
  if (key === 'b_forces') {
    return `${t('o.b.forces')}\n${b.factions.map((f) => bullet(`${f.name}（${f.leader}）`, f.strength)).join('\n')}\n\n${k.forces}\n\n${P.tail}`;
  }
  if (key === 'b_after') return `${t('o.b.after', { x: k.aftermath, brief: b.brief })}\n\n${P.tail}`;
  return null;
}

function battleFreeText(text, b, P) {
  if (kw('kw.b.turn').test(text)) return battleAnswer('b_turn', b, P);
  if (kw('kw.b.forces').test(text)) return battleAnswer('b_forces', b, P);
  if (kw('kw.b.after').test(text)) return battleAnswer('b_after', b, P);
  if (kw('kw.b.routes').test(text)) {
    return `${t('o.b.routes')}\n${b.march_routes.map((r) => `· **${r.from.name}** → ${r.to.name}：${r.desc}`).join('\n')}\n\n${P.tail}`;
  }
  return null;
}

// ── LLM 流式调用 ──────────────
async function* readSSE(res) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split(/\r?\n/);
    buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const data = line.slice(5).trim();
      if (!data || data === '[DONE]') continue;
      try { yield JSON.parse(data); } catch { /* 忽略不完整片段 */ }
    }
  }
}

// 容错常见填写错误：Base URL 多写了接口路径；Gemini 模型名带 "models/" 前缀
function normalize(cfg) {
  let baseUrl = cfg.baseUrl.trim().replace(/\/+$/, '').replace(/\/(chat\/completions|messages)$/, '');
  // Gemini 原生：误填了 OpenAI 兼容路径或完整的模型接口路径时，截回到 /v1beta
  if (cfg.provider === 'gemini') baseUrl = baseUrl.replace(/\/(openai|models\/.*)$/, '');
  const model = cfg.model.trim().replace(/^models\//, '');
  return { ...cfg, baseUrl, model };
}

export async function* streamChat(rawCfg, system, messages, signal) {
  const cfg = normalize(rawCfg);
  const base = cfg.baseUrl;
  let res;
  if (cfg.provider === 'claude') {
    res = await fetch(`${base}/messages`, {
      method: 'POST',
      signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': cfg.apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify({ model: cfg.model, max_tokens: 1024, system, messages, stream: true }),
    });
  } else if (cfg.provider === 'gemini') {
    // Google 原生接口：x-goog-api-key 支持新式「AQ.」Key；角色名 assistant → model
    res = await fetch(`${base}/models/${encodeURIComponent(cfg.model)}:streamGenerateContent?alt=sse`, {
      method: 'POST',
      signal,
      headers: { 'content-type': 'application/json', 'x-goog-api-key': cfg.apiKey },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents: messages.map((m) => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })),
        generationConfig: { maxOutputTokens: 1024 },
      }),
    });
  } else {
    res = await fetch(`${base}/chat/completions`, {
      method: 'POST',
      signal,
      headers: { 'content-type': 'application/json', authorization: `Bearer ${cfg.apiKey}` },
      body: JSON.stringify({ model: cfg.model, stream: true, messages: [{ role: 'system', content: system }, ...messages] }),
    });
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    const err = new Error(t('api.status', { s: res.status, x: detail.slice(0, 300) }));
    err.status = res.status;
    throw err;
  }
  for await (const ev of readSSE(res)) {
    if (cfg.provider === 'claude') {
      if (ev.type === 'content_block_delta' && ev.delta?.type === 'text_delta') yield ev.delta.text;
      else if (ev.type === 'error') throw new Error(ev.error?.message || t('api.stream'));
    } else if (cfg.provider === 'gemini') {
      if (ev.error) throw new Error(ev.error.message || t('api.stream'));
      const parts = ev.candidates?.[0]?.content?.parts || [];
      // 跳过思考过程（thought），只输出正文
      const t = parts.filter((x) => !x.thought).map((x) => x.text || '').join('');
      if (t) yield t;
    } else {
      const t = ev.choices?.[0]?.delta?.content;
      if (t) yield t;
    }
  }
}

// 设置窗口的「测试连接」：发一条极短请求，把常见错误翻译成人话
export async function testConnection(cfg) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 30000);
  let out = '';
  try {
    for await (const t of streamChat(cfg, t('tc.sys'), [{ role: 'user', content: t('tc.ask') }], ctrl.signal)) {
      out += t;
    }
    if (!out.trim()) return { ok: false, msg: t('tc.empty') };
    return { ok: true, msg: t('tc.ok', { x: out.trim().slice(0, 60) }) };
  } catch (err) {
    const s = err.status;
    const hint =
      err.name === 'AbortError' ? t('tc.timeout')
      // Gemini 对无效 Key 返回 400 而非 401，按错误内容判断
      : /api[ _-]?key|invalid.*key|unauthori[sz]ed|authentication/i.test(err.message)
        ? t('tc.key')
      : s === 400 ? t('tc.400')
      : s === 401 || s === 403 ? t('tc.401')
      : s === 404 ? t('tc.404')
      : s === 429 ? t('tc.429')
      : s >= 500 ? t('tc.5xx', { s })
      : /Failed to fetch|NetworkError|Load failed/i.test(err.message)
        ? t('tc.net')
        : '';
    return { ok: false, msg: `${hint}\n${t('tc.detail', { x: err.message })}`.trim() };
  } finally {
    clearTimeout(timer);
  }
}

// ── 渲染 ──────────────
const fmt = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

export function createGuide(els, { getConfig, openSettings, initialMode = 'scholar' }) {
  const { chat, quick, form, input, send, avatar, name, title, mode } = els;
  let pref = null;
  let personaMode = initialMode; // 'scholar' 博学史官 | 'hero' 名将附体
  let battle = null; // 合战沙盘进行中时：{ b, field }
  let place = null; // 下钻地图里选中的市区町村
  let pil = null; // 圣地巡礼图层下本县的巡礼点
  let sg = null; // 战国势力图上点开的国 { prov, year, rows }
  let town = null; // 下钻里选中的市区町村的此地年表（hometownItems().items）
  let era = null; // 时代滑块当前的时代（timeline_eras 的一项）
  let P = null;
  let history = [];
  let busy = false;
  let ctrl = null;
  let typingTimer = null;

  const scroll = () => { chat.scrollTop = chat.scrollHeight; };
  const online = () => !!getConfig()?.apiKey;

  function addMsg(role, html) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = html;
    chat.appendChild(div);
    scroll();
    return div;
  }

  const offlineHint = () =>
    `<span class="hint">${t('g.hint', { who: P.hero ? esc(P.name) : t('g.guide') })}</span>`;

  chat.addEventListener('click', (e) => {
    if (e.target.closest('[data-act="settings"]')) openSettings();
  });

  function setBusy(b) {
    busy = b;
    const ready = !!(pref || battle);
    send.disabled = b || !ready;
    input.disabled = !ready;
    quick.querySelectorAll('button').forEach((x) => { x.disabled = b; });
  }

  // 打字机效果输出一段离线文本
  let finishTyping = null; // 正在打字的消息：立即补完

  function typeOut(text, extraHtml = '') {
    finishTyping?.();
    const div = addMsg('ai cursor', '');
    let i = 0;
    setBusy(true);
    const done = () => {
      clearInterval(typingTimer);
      finishTyping = null;
      div.classList.remove('cursor');
      div.innerHTML = fmt(text) + extraHtml;
      setBusy(false);
      scroll();
    };
    finishTyping = done;
    typingTimer = setInterval(() => {
      i = Math.min(text.length, i + 3);
      div.innerHTML = fmt(text.slice(0, i));
      scroll();
      if (i >= text.length) done();
    }, 16);
  }

  async function askLLM(text) {
    const cfg = getConfig();
    history.push({ role: 'user', content: text });
    const div = addMsg('ai cursor', '');
    setBusy(true);
    const myCtrl = (ctrl = new AbortController());
    let out = '';
    try {
      const system = battle ? buildBattlePrompt(battle.b, battle.field, P) : buildSystemPrompt(pref, P, place, pil, sg, town);
      for await (const chunk of streamChat(cfg, system, history, myCtrl.signal)) {
        out += chunk;
        div.innerHTML = fmt(out);
        scroll();
      }
      history.push({ role: 'assistant', content: out });
    } catch (err) {
      if (err.name === 'AbortError') return;
      history.pop();
      div.classList.add('err');
      div.innerHTML = `${fmt(out)}${out ? '\n\n' : ''}${esc(t('g.fail', { msg: err.message }))}\n<span class="hint">${t('g.fail.hint')}</span>`;
    } finally {
      div.classList.remove('cursor');
      if (!myCtrl.signal.aborted) setBusy(false);
    }
  }

  function ask(text, key) {
    if ((!pref && !battle) || busy) return;
    addMsg('user', esc(text));
    if (online()) { askLLM(text); return; }
    const ans = battle
      ? (key ? battleAnswer(key, battle.b, P) : battleFreeText(text, battle.b, P))
      : key === 'place' && place ? placeAnswer(place, pref, P, town)
        : key === 'pw' && era && REG ? powerAnswer(era.short, P)
        : key === 'pil' && pil?.length ? pilAnswer(pil, pref, P)
        : key === 'sg' && sg ? sgAnswer(sg, P)
        : (key ? offlineAnswer(key, pref, P) : offlineFreeText(text, pref, P));
    typeOut(ans || t('g.fallback', { self: P.self }), offlineHint());
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    ask(text);
  });

  function refreshMode() {
    const cfg = getConfig();
    mode.textContent = cfg?.apiKey ? t('chip.online', { model: cfg.model }) : t('chip.offline');
    mode.classList.toggle('online', !!cfg?.apiKey);
  }

  // 载入当前身份（地区向导 / 名将 / 合战讲解人）：重置对话，换头像、快捷提问与开场白
  function load(banner) {
    ctrl?.abort();
    clearInterval(typingTimer);
    finishTyping = null;
    history = [];
    busy = false;
    P = battle ? battlePersona(battle.b) : personaFor(pref, personaMode);
    avatar.textContent = P.avatar;
    avatar.style.setProperty('--persona', P.color);
    avatar.classList.toggle('hero', P.hero);
    name.textContent = `${P.title} · ${P.name}`;
    const provs = (q) => q.historical_lineage.ritsuryo_provinces.map((x) => x.name).join('·');
    title.textContent = battle
      ? t('g.t.battle', { battle: battle.b.name, field: prefName(battle.field) })
      : t(P.hero ? 'g.t.hero' : 'g.t.scholar', { name: prefName(pref), provs: provs(pref) });
    chat.innerHTML = '';
    addMsg('sys', banner);
    renderQuick();
    input.disabled = false;
    document.body.classList.remove('guide-idle');
    typeOut(P.opening);
  }

  // 快捷提问；下钻地图里选中市区町村时，最前面多一个「这里古时候属于哪里」
  function renderQuick() {
    quick.innerHTML = '';
    const qs = battle ? battleQuestions() : quickQuestions(pref);
    if (place && !battle) qs.unshift({ key: 'place', text: t('q.place', { name: place.name }) });
    if (pil?.length && !battle) qs.unshift({ key: 'pil', text: t('q.pil') });
    if (sg && !battle) qs.unshift({ key: 'sg', text: sg.clan ? t('q.sgc', { clan: sg.clan, year: sg.year }) : t('q.sg', { prov: sg.prov, year: sg.year }) });
    if (era && REG && !battle) qs.unshift({ key: 'pw', text: t('q.pw', { era: era.short }) });
    for (const q of qs) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'bubble';
      b.textContent = q.text;
      b.addEventListener('click', () => ask(q.text, q.key));
      quick.appendChild(b);
    }
  }

  function showIntro() {
    ctrl?.abort();
    clearInterval(typingTimer);
    finishTyping = null;
    busy = false;
    P = null;
    avatar.textContent = '案';
    avatar.style.removeProperty('--persona');
    avatar.classList.remove('hero');
    name.textContent = t('guide.name');
    title.textContent = t('guide.pick');
    quick.innerHTML = '';
    input.disabled = true;
    send.disabled = true;
    chat.innerHTML = '';
    addMsg('ai', fmt(t('g.intro')));
    document.body.classList.add('guide-idle'); // 宽屏上还没选地区时向导只留一行，详卡占满右栏
  }

  return {
    refreshMode,
    showIntro,
    get mode() { return personaMode; },
    // 下钻地图里选中的市区町村（null 表示没有）：不重置对话，只换快捷提问、补进 System Prompt
    // 圣地巡礼图层：本县巡礼点（不在该图层时为 null）。不重置对话，只换快捷提问、补进 System Prompt
    setPilgrimage(list) {
      const next = list?.length ? list : null;
      const changed = (next?.map((s) => s.id).join() || '') !== (pil?.map((s) => s.id).join() || '');
      pil = next;
      if (pref && !battle && P && changed) renderQuick();
    },
    // 战国势力图上点开的国（null 表示没有）：不重置对话，只换快捷提问、补进 System Prompt
    setSengoku(x) {
      const key = (v) => (v ? `${v.prov || v.clan}|${v.year}` : '');
      const changed = key(x) !== key(sg);
      sg = x;
      if (pref && !battle && P && changed) renderQuick();
    },
    // 年表「实权」数据与时代列表（全局一次）
    setRegimes(regimes, eras) { REG = regimes ? { regimes, eras } : null; if (pref && !battle && P && era) renderQuick(); },
    // 时代滑块的当前时代（null = 不在时空穿越）：快捷提问多一个「某时代谁在掌权？」
    setEra(x) {
      const changed = (x?.key || null) !== (era?.key || null);
      era = x;
      if (pref && !battle && P && changed && REG) renderQuick();
    },
    // 下钻里选中的市区町村的此地年表（null 表示没有）：离线解答接在后面，在线写进 System Prompt
    setHometown(items) { town = items; },
    setPlace(x) {
      const changed = (x?.ja || null) !== (place?.ja || null);
      place = x;
      if (!x) town = null;
      if (!pref || battle || !P || !changed) return;
      renderQuick();
      if (x) addMsg('sys', esc(t('g.place.sys', { name: x.name })));
    },
    // 从别处（如古代户籍的「乡音」）触发一个快捷提问；正在打字的开场白先补完
    askQuick(key) {
      if (!pref || battle) return;
      const q = quickQuestions(pref).find((x) => x.key === key);
      finishTyping?.();
      if (q) ask(q.text, key);
    },
    setPrefecture(p) {
      pref = p;
      place = null;
      if (battle) return; // 合战中不打断讲解，退出时再载入
      load(esc(t('g.b.switch', { name: prefName(p) })));
    },
    setMode(m) {
      personaMode = m === 'hero' ? 'hero' : 'scholar';
      if (pref && !battle) {
        load(esc(personaMode === 'hero' ? t('g.b.hero', { name: pref.hero_persona.name }) : t('g.b.scholar')));
      }
    },
    // 合战沙盘：切换为该战役核心名将的口吻
    startBattle(b, field) {
      battle = { b, field };
      load(esc(t('g.b.battle', { battle: b.name, name: b.narrator.name })));
    },
    // 合战推演换阶段：名将解说本阶段战况（本地脚本，不调用 API）
    narrate(phase, i, total) {
      if (!battle) return;
      ctrl?.abort();
      finishTyping?.();
      addMsg('sys', esc(t('g.b.phase', { i: i + 1, n: total, title: phase.title, time: phase.time })));
      typeOut(`${phase.line}\n\n【${phase.title}】${phase.desc}`);
    },
    endBattle() {
      if (!battle) return;
      battle = null;
      if (pref) load(esc(t('g.b.exit', { name: prefName(pref) })));
      else showIntro();
    },
  };
}
