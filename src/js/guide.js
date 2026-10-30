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
    place: (x) => `用户正在市区町村地图上查看「${x.ja}」（${x.kana}）：旧国 ${x.provinces.join('・') || '令制外'}${x.partial.length ? `（部分属 ${x.partial.join('・')}）` : ''}${x.district ? `，${x.district}` : ''}${x.pop ? `，人口约 ${x.pop}（${x.pop_year}）` : ''}。问题涉及此地时围绕它回答；上面史料里没有的具体地方史，要说明不确定，不得编造。`,
  },
  en: {
    hero: (P) => `You are now channeling the historical figure **${P.name}** (${P.title}). Speak in the first person.\nVoice: ${P.voice}.\nTell local history from this person's standpoint, knowledge and feelings; for events after their lifetime, frame them as "later generations say…".\nThe role-play is limited to tone and perspective: never glorify massacres or persecution, and stay objective on disputed facts.`,
    guide: (P) => `You are the "Time-Travel Guide", a guide to Japanese history and geography. Current identity: ${P.title} "${P.name}".\nVoice: ${P.voice}.`,
    ctx: (p) => `The user has selected ${p.name.romaji} (${p.name.kanji}) on the map. Records for this region (JSON):`,
    battle: (P, b) => `You are now channeling **${P.name}** (${b.narrator.title}) on the battlefield of ${b.name}. Speak in the first person.\nVoice: ${P.voice}.\nAnswer from this person's position in the battle; frame later judgments they could not know as "later generations say…".\nThe role-play is limited to tone and perspective: never glorify killing, and mark disputed numbers or motives as "one account says".`,
    field: (f, provs) => `Main battlefield: ${f.name.romaji} (${f.name.kanji}; ancient: ${provs}).`,
    place: (x) => `The user is looking at ${x.en || x.ja} (${x.ja}, ${x.kana}) on the municipal map: ancient province ${x.provinces.join(', ') || 'outside the ritsuryō system'}${x.partial.length ? ` (partly ${x.partial.join(', ')})` : ''}${x.district ? `, ${x.district}` : ''}${x.pop ? `, population about ${x.pop} (${x.pop_year})` : ''}. When a question concerns this place, focus on it; for local history not in the records above, say you are unsure rather than inventing details.`,
  },
  ja: {
    hero: (P) => `あなたは歴史上の人物 **${P.name}**（${P.title}）として一人称で話してください。自称は「${P.self}」。\n口調：${P.voice}。\nこの人物の立場・見識・感情から土地の歴史を語り、没後の出来事は「後世の伝えでは」といった形で述べてください。\n演じるのは口調と視点だけです。虐殺や迫害を美化せず、争いのある史実は客観的に扱ってください。`,
    guide: (P) => `あなたは日本の歴史と地理の案内人「時空案内人」です。現在の姿：${P.title}「${P.name}」、自称は「${P.self}」。\n口調：${P.voice}。`,
    ctx: (p) => `ユーザーはいま地図で「${p.name.kanji}」を選んでいます。この地域の史料（JSON）：`,
    battle: (P, b) => `あなたは歴史上の人物 **${P.name}**（${b.narrator.title}）として「${b.name}」の戦場にいます。一人称で話し、自称は「${P.self}」。\n口調：${P.voice}。\nこの合戦での立場と見識から答え、知り得ない後世の評価は「後世の伝えでは」と述べてください。\n演じるのは口調と視点だけです。殺戮を美化せず、兵力や動機など諸説ある点は「一説に」と明記してください。`,
    field: (f, provs) => `主戦場：「${f.name.kanji}」（旧国：${provs}）。`,
    place: (x) => `ユーザーは市区町村地図で「${x.ja}」（${x.kana}）を見ています：旧国 ${x.provinces.join('・') || '令制外'}${x.partial.length ? `（一部は${x.partial.join('・')}）` : ''}${x.district ? `、${x.district}` : ''}${x.pop ? `、人口約${x.pop}（${x.pop_year}年）` : ''}。この土地に関する質問にはここを中心に答え、上の史料にない細かな郷土史は不確かだと明言し、創作しないでください。`,
  },
};
const R = ROLE[lang];
const RULES = PROMPT_RULES[lang];

export function buildSystemPrompt(p, P, place = null) {
  const { guide, hero_persona, _translated, ...data } = p;
  return `${P.hero ? R.hero(P) : R.guide(P)}

${R.ctx(p)}
<prefecture>
${JSON.stringify(data, null, 1)}
</prefecture>
${place ? `\n${R.place(place)}\n` : ''}
${RULES.reply}. ${RULES.rules}`;
}

// 市区町村（下钻地图里的选中项）：借县史料里对该令制国的说明，拼出离线解答
function placeAnswer(x, p, P) {
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
  if (x.pop) lines.push(t('o.place.pop', { pop: x.pop, year: x.pop_year }));
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
      const system = battle ? buildBattlePrompt(battle.b, battle.field, P) : buildSystemPrompt(pref, P, place);
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
      : key === 'place' && place ? placeAnswer(place, pref, P)
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
    typeOut(P.opening);
  }

  // 快捷提问；下钻地图里选中市区町村时，最前面多一个「这里古时候属于哪里」
  function renderQuick() {
    quick.innerHTML = '';
    const qs = battle ? battleQuestions() : quickQuestions(pref);
    if (place && !battle) qs.unshift({ key: 'place', text: t('q.place', { name: place.name }) });
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
  }

  return {
    refreshMode,
    showIntro,
    get mode() { return personaMode; },
    // 下钻地图里选中的市区町村（null 表示没有）：不重置对话，只换快捷提问、补进 System Prompt
    setPlace(x) {
      const changed = (x?.ja || null) !== (place?.ja || null);
      place = x;
      if (!pref || battle || !P || !changed) return;
      renderQuick();
      if (x) addMsg('sys', esc(t('g.place.sys', { name: x.name })));
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
