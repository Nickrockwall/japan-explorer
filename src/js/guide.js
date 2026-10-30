// 右下：AI 历史向导（时空案内人）
import { esc } from './detail.js';

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
  return { hero: false, ...PERSONAS[p.guide.persona], opening: p.guide.opening };
}

export function quickQuestions(p) {
  const provs = p.historical_lineage.ritsuryo_provinces.map((x) => x.name).join('、');
  return [
    { key: 'daimyo', text: '战国时这里战况如何？' },
    { key: 'dialect', text: `用${p.dialect.name}和我打声招呼` },
    { key: 'border', text: `古代的${provs}和今天的界线有什么不同？` },
  ];
}

export function buildSystemPrompt(p, P) {
  const { guide, hero_persona, ...data } = p;
  const role = P.hero
    ? `你现在“附体”为历史人物 **${P.name}**（${P.title}），以第一人称说话，自称「${P.self}」。
口吻：${P.voice}。
以该人物的立场、见识与情感讲述当地历史；涉及其身后才发生的事，用“据后世所传”之类的口吻带出。
扮演仅限于语气与视角：不得美化屠杀、迫害等暴行，涉及争议史实时保持客观。`
    : `你是「时空案内人」——日本历史地理向导。当前身份：${P.title}「${P.name}」，自称「${P.self}」。
口吻：${P.voice}。`;
  return `${role}

用户此刻在地图上选中了「${p.name.kanji}（${p.name.zh}）」。下面是该地区的史料 JSON，涵盖古代令制国（五畿七道）、战国大名、江户诸藩、明治废藩置县后的县域变迁、名胜物产、方言与地缘梗：
<prefecture>
${JSON.stringify(data, null, 1)}
</prefecture>

回答规则：
1. 用中文回答，可点缀日语原词并用括号注明读音或意思；保持上述人设口吻，但不要喧宾夺主。
2. 优先依据史料作答；史料之外的知识可以补充，但存疑之处标注“据传”或“一说”，不要编造具体年份与人名。
3. 篇幅约 150–300 字，多给具体的年份、人物、地名；需要时可用 **加粗** 标出关键词。
4. 若用户问到其他地区，可简要回答，并建议在地图上点选那个地区以切换向导。`;
}

// ── 离线解答（无 API Key 时由本地数据以角色口吻拼出） ──────────────
function offlineAnswer(key, p, P) {
  const L = p.historical_lineage;
  const stage = (era) => p.history_timeline.find((t) => t.era === era);
  const sengoku = stage('战国');
  const edo = stage('江户');
  if (key === 'daimyo') {
    const lead = P.hero
      ? `${P.self}所知的战国，这片土地上的风云人物有 **${L.sengoku_daimyo.join('、')}**。`
      : `${P.self}记得，战国时这片土地上活跃着 **${L.sengoku_daimyo.join('、')}**。`;
    return `${lead}\n\n【${sengoku.title}】${sengoku.summary}\n\n` +
      `到了江户时代，这里由 **${L.edo_domains.join('、')}** 治理——${edo.summary}\n\n${P.tail}`;
  }
  if (key === 'dialect') {
    const [hello, ...rest] = p.dialect.phrases;
    return `「**${hello.phrase}**」！——${P.self}用${p.dialect.name}向你问好，意思是“${hello.meaning}”${hello.note ? `（${hello.note}）` : ''}。\n\n` +
      `再教你两句：\n${rest.map((x) => `· 「**${x.phrase}**」＝${x.meaning}${x.note ? `（${x.note}）` : ''}`).join('\n')}\n\n` +
      `${p.dialect.features}\n\n${P.tail}`;
  }
  if (key === 'border') {
    const provs = L.ritsuryo_provinces
      .map((x) => `· **${x.name}**（${x.kana}）— ${x.circuit}，${x.portion}` +
        (x.cross_prefectures?.length ? `；此国今跨界，另一部分属于${x.cross_prefectures.join('、')}` : '')).join('\n');
    return `${P.self}来给你摊开古地图：今天的${p.name.zh}在律令时代对应——\n${provs}\n\n` +
      `${L.meiji_transition.boundary_note}\n\n` +
      `【明治的县域变迁】${L.meiji_transition.summary}\n\n${P.tail}`;
  }
  return null;
}

// 自由输入时，离线模式按关键词挑一个最接近的预置解答
function offlineFreeText(text, p, P) {
  if (/大名|战国|战况|武将|藩|江户|谁/.test(text)) return offlineAnswer('daimyo', p, P);
  if (/方言|招呼|怎么说|口音|话/.test(text)) return offlineAnswer('dialect', p, P);
  if (/界|令制|国|古代|明治|县/.test(text)) return offlineAnswer('border', p, P);
  if (/梗|段子|偏见|吐槽|修罗场|笑话/.test(text)) {
    return `说到这里的“地域修罗场”，${P.self}可听过不少：\n` +
      `${p.regional_meme.map((m) => `· **${m.title}**：${m.text}`).join('\n')}\n\n——玩笑话，别当真。${P.tail}`;
  }
  if (/名胜|景点|好玩|去哪|特产|好吃|美食|物产/.test(text)) {
    return `${P.self}推荐你看看：\n${p.landmarks.map((x) => `· **${x.name}**：${x.note}`).join('\n')}\n\n` +
      `再尝尝：\n${p.specialties.map((x) => `· **${x.name}**：${x.note}`).join('\n')}\n\n${P.tail}`;
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

const BATTLE_QUESTIONS = [
  { key: 'b_turn', text: '这场仗的胜负关键是什么？' },
  { key: 'b_forces', text: '双方兵力各有多少？' },
  { key: 'b_after', text: '战后天下格局如何变化？' },
];

function buildBattlePrompt(b, field, P) {
  const { narrator, ...battle } = b;
  return `你现在“附体”为历史人物 **${P.name}**（${b.narrator.title}），正身处「${b.name}」的战场，以第一人称说话，自称「${P.self}」。
口吻：${P.voice}。
以该人物在这场合战中的立场与见识回答；涉及其不可能知道的后世评价，用“据后世所传”之类的口吻带出。
扮演仅限于语气与视角：不得美化杀戮，涉及兵力、动机等争议史实时注明“一说”。

战役史料：
<battle>
${JSON.stringify(battle, null, 1)}
</battle>
主战场所在地区：「${field.name.kanji}」（古：${field.historical_lineage.ritsuryo_provinces.map((x) => x.name).join('、')}）。

回答规则：中文，150–300 字，多给具体的时间、人物、地名；可用 **加粗** 标出关键词。`;
}

function battleAnswer(key, b, P) {
  const k = b.key_points;
  const sides = b.factions.map((f) => `**${f.name}**（${f.leader}）`).join(' 对 ');
  if (key === 'b_turn') return `${P.self}来说说这一仗的要害：\n\n${k.turning_point}\n\n${sides}，胜负就在这里分出。\n\n${P.tail}`;
  if (key === 'b_forces') {
    return `两军阵容如下：\n${b.factions.map((f) => `· **${f.name}**（${f.leader}）：${f.strength}`).join('\n')}\n\n${k.forces}\n\n${P.tail}`;
  }
  if (key === 'b_after') return `此战之后——\n\n${k.aftermath}\n\n【战况速览】${b.brief}\n\n${P.tail}`;
  return null;
}

function battleFreeText(text, b, P) {
  if (/关键|转折|为什么|怎么赢|怎么输|胜负/.test(text)) return battleAnswer('b_turn', b, P);
  if (/兵力|多少人|人数|规模/.test(text)) return battleAnswer('b_forces', b, P);
  if (/之后|结果|影响|格局|后来/.test(text)) return battleAnswer('b_after', b, P);
  if (/路线|进军|行军|从哪/.test(text)) {
    return `各军进军路线：\n${b.march_routes.map((r) => `· **${r.from.name}** → ${r.to.name}：${r.desc}`).join('\n')}\n\n${P.tail}`;
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
    const err = new Error(`接口返回 ${res.status}：${detail.slice(0, 300)}`);
    err.status = res.status;
    throw err;
  }
  for await (const ev of readSSE(res)) {
    if (cfg.provider === 'claude') {
      if (ev.type === 'content_block_delta' && ev.delta?.type === 'text_delta') yield ev.delta.text;
      else if (ev.type === 'error') throw new Error(ev.error?.message || '流式响应出错');
    } else if (cfg.provider === 'gemini') {
      if (ev.error) throw new Error(ev.error.message || '流式响应出错');
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
    for await (const t of streamChat(cfg, '你是测试助手。', [{ role: 'user', content: '用不超过15个字向我问好。' }], ctrl.signal)) {
      out += t;
    }
    if (!out.trim()) return { ok: false, msg: '连接成功但模型没有返回文字，请换一个模型试试。' };
    return { ok: true, msg: `连接成功 ✓ 模型回复：「${out.trim().slice(0, 60)}」` };
  } catch (err) {
    const s = err.status;
    const hint =
      err.name === 'AbortError' ? '30 秒无响应，请检查 Base URL 与网络。'
      // Gemini 对无效 Key 返回 400 而非 401，按错误内容判断
      : /api[ _-]?key|invalid.*key|unauthori[sz]ed|authentication/i.test(err.message)
        ? 'API Key 无效：请重新复制 Key，注意不要带空格或漏字符。'
      : s === 400 ? '请求被拒（400）：多半是模型名写错，或该模型不支持此接口。'
      : s === 401 || s === 403 ? 'Key 无效或无权限（401/403）：请重新复制 API Key，注意不要带空格。'
      : s === 404 ? '找不到接口或模型（404）：请检查 Base URL 和模型名。'
      : s === 429 ? '额度用完或请求太频繁（429）：免费额度通常次日恢复，或换一个额度更高的模型。'
      : s >= 500 ? `服务端错误（${s}）：稍后再试。`
      : /Failed to fetch|NetworkError|Load failed/i.test(err.message)
        ? '请求没有发出去：Base URL 写错、网络不通，或该接口不允许浏览器跨域调用。'
        : '';
    return { ok: false, msg: `${hint}\n详情：${err.message}`.trim() };
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
    `<span class="hint">（离线模式 · 预置解答）<a data-act="settings">接入 API</a> 即可与${P.hero ? esc(P.name) : '案内人'}无限畅聊。</span>`;

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
      const system = battle ? buildBattlePrompt(battle.b, battle.field, P) : buildSystemPrompt(pref, P);
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
      div.innerHTML = `${fmt(out)}${out ? '\n\n' : ''}⚠ 调用失败：${esc(err.message)}\n<span class="hint">请检查 <a data-act="settings">API 设置</a>（Key、Base URL、模型名，以及接口是否允许浏览器跨域）。</span>`;
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
      : (key ? offlineAnswer(key, pref, P) : offlineFreeText(text, pref, P));
    typeOut(ans || `${P.self}一时答不上这个问题……离线时${P.self}只记得几段旧事，试试下面的快捷提问吧。`, offlineHint());
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
    mode.textContent = cfg?.apiKey ? `在线 · ${cfg.model}` : '离线模式';
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
      ? `合战沙盘：${battle.b.name} · 主战场 ${battle.field.name.kanji}`
      : P.hero
        ? `名将附体中：${pref.name.kanji}（${provs(pref)}）`
        : `正在为你讲述：${pref.name.kanji}（${provs(pref)}）`;
    chat.innerHTML = '';
    addMsg('sys', banner);
    quick.innerHTML = '';
    for (const q of battle ? BATTLE_QUESTIONS : quickQuestions(pref)) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'bubble';
      b.textContent = q.text;
      b.addEventListener('click', () => ask(q.text, q.key));
      quick.appendChild(b);
    }
    input.disabled = false;
    typeOut(P.opening);
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
    name.textContent = '时空案内人';
    title.textContent = '请先在地图上选择一个地区';
    quick.innerHTML = '';
    input.disabled = true;
    send.disabled = true;
    chat.innerHTML = '';
    addMsg('ai', fmt('我是**时空案内人**。我会随你所到之处更换身份——在江户是浮世绘里的猫，在京都是平安朝的女官，在长崎是出岛的兰学通词……\n\n' +
      '切换到**名将附体**，还能请来织田信长、坂本龙马、伊达政宗亲自开讲；打开**合战演武**，名将们还会在沙盘上为你复盘经典战役。请先在左侧地图上点选一个地区吧。'));
  }

  return {
    refreshMode,
    showIntro,
    get mode() { return personaMode; },
    setPrefecture(p) {
      pref = p;
      if (battle) return; // 合战中不打断讲解，退出时再载入
      load(`— 时空切换至 ${esc(p.name.kanji)} · 已载入该地史料 —`);
    },
    setMode(m) {
      personaMode = m === 'hero' ? 'hero' : 'scholar';
      if (pref && !battle) {
        load(personaMode === 'hero'
          ? `— 名将附体：${esc(pref.hero_persona.name)} 降临 —`
          : '— 恢复博学史官模式 —');
      }
    },
    // 合战沙盘：切换为该战役核心名将的口吻
    startBattle(b, field) {
      battle = { b, field };
      load(`— 合战沙盘：${esc(b.name)} · ${esc(b.narrator.name)} 登场 —`);
    },
    // 合战推演换阶段：名将解说本阶段战况（本地脚本，不调用 API）
    narrate(phase, i, total) {
      if (!battle) return;
      ctrl?.abort();
      finishTyping?.();
      addMsg('sys', `— 第 ${i + 1} / ${total} 阶段 · ${esc(phase.title)}（${esc(phase.time)}）—`);
      typeOut(`${phase.line}\n\n【${phase.title}】${phase.desc}`);
    },
    endBattle() {
      if (!battle) return;
      battle = null;
      if (pref) load(`— 退出合战沙盘 · 回到 ${esc(pref.name.kanji)} —`);
      else showIntro();
    },
  };
}
