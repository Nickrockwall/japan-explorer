// 朝鲜半岛的时空案内人：外观与日本的向导相同（#chat / #quick / #composer），身份只有一位「丹青」。
// 没有 API Key 时，快捷提问与关键词由本地史话（content/{lang}.json）拼出回答；有 Key 时把本区史话写进 System Prompt 流式对话。
// 写作规矩与网站一致：南北都用正式国名，半岛不叫「韩国」；争议地区两种名字并列、只列各方立场；共同历史分「双方都承认的事实 / 各方叙述」。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { streamChat } from './guide.js';

const fmt = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
const QUICK = ['history', 'dialect', 'name'];

export function createKoreaGuide(els, { getConfig, openSettings, origin = () => '' }) {
  const { chat, quick, form, input, send, avatar, name, title, mode } = els;
  let region = null; // { p: regions.json 的 properties, c: 史话, label }
  let battle = null; // 古战场进行中：battles.json 的一场（三语对象）
  const L = (o) => (o == null ? '' : typeof o === 'string' ? o : o[lang] || o.zh);
  let history = [];
  let busy = false;
  let ctrl = null;
  let timer = null;
  let finish = null;

  const online = () => !!getConfig()?.apiKey;
  const scroll = () => { chat.scrollTop = chat.scrollHeight; };
  function addMsg(role, html) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = html;
    chat.appendChild(div);
    scroll();
    return div;
  }
  function setBusy(b) {
    busy = b;
    send.disabled = b || !(region || battle);
    input.disabled = !(region || battle);
    quick.querySelectorAll('button').forEach((x) => { x.disabled = b; });
  }
  function typeOut(text, extra = '') {
    finish?.();
    const div = addMsg('ai cursor', '');
    let i = 0;
    setBusy(true);
    const done = () => {
      clearInterval(timer);
      finish = null;
      div.classList.remove('cursor');
      div.innerHTML = fmt(text) + extra;
      setBusy(false);
      scroll();
    };
    finish = done;
    timer = setInterval(() => {
      i = Math.min(text.length, i + 3);
      div.innerHTML = fmt(text.slice(0, i));
      scroll();
      if (i >= text.length) done();
    }, 16);
  }

  // ── 离线回答 ──
  function offline(key) {
    const { c, label } = region;
    if (!c) return t('kr.g.none');
    if (key === 'history') {
      const eras = ['samguk', 'silla', 'goryeo', 'joseon', 'modern', 'today'];
      return `${t('kr.g.hist', { r: label })}\n${c.timeline.map((x, i) => `**${t(`kr.era.${eras[i]}`)}**　${x}`).join('\n')}`;
    }
    if (key === 'dialect') {
      const ph = c.dialect.phrases.map(([a, b]) => `「${a}」—— ${b}`).join('\n');
      return `${t('kr.g.dia', { d: c.dialect.name })}${c.dialect.features}${ph ? `\n${ph}` : ''}`;
    }
    if (key === 'name') return origin() || t('kr.g.noname', { r: label });
    return null;
  }
  // 古战场里的离线回答：经过 / 兵力 / 结果，都从本场数据拼
  function battleAnswer(key) {
    const b = battle;
    if (key === 'b_forces') return b.factions.map((f) => `**${L(f.name)}**　${L(f.leader)} · ${L(f.strength)}`).join('\n');
    if (key === 'b_after') return `${L(b.brief)}\n\n${L(b.phases[b.phases.length - 1].desc)}`;
    return b.phases.map((ph, i) => `**${i + 1}. ${L(ph.title)}**（${L(ph.time)}）　${L(ph.desc)}`).join('\n');
  }
  function offlineFree(text) {
    const s = text.toLowerCase();
    if (battle) {
      if (/兵力|多少人|forces|troops|army|軍勢/.test(s)) return battleAnswer('b_forces');
      if (/结果|结局|后来|之后|影响|aftermath|result|after|結果|その後/.test(s)) return battleAnswer('b_after');
      return battleAnswer('b_course');
    }
    if (/历史|歴史|沿革|history|新罗|新羅|高丽|高麗|朝鲜王朝|朝鮮王朝|silla|goryeo|joseon/.test(s)) return offline('history');
    if (/方言|话|言葉|dialect|speech|说话|打招呼|あいさつ/.test(s)) return offline('dialect');
    if (/名字|名前|由来|来历|name/.test(s)) return offline('name');
    if (/名胜|景点|名所|landmark|sight/.test(s) && region.c) return region.c.landmarks.map(([a, b]) => `**${a}**　${b}`).join('\n');
    if (/吃|美食|料理|名物|food|eat|特产|物产/.test(s) && region.c) return region.c.specialties.map(([a, b]) => `**${a}**　${b}`).join('\n');
    return t('kr.g.fallback');
  }
  const hint = () => `<span class="hint">${t('g.hint', { who: t('kr.g.name') })}</span>`;

  // ── 在线 ──
  function system() {
    if (battle) {
      const pick = (o) => (Array.isArray(o) ? o.map(pick) : o && typeof o === 'object' ? (o.zh !== undefined && o.en !== undefined ? L(o) : Object.fromEntries(Object.entries(o).map(([k, v]) => [k, pick(v)]))) : o);
      const { evidence, sources, ...b } = battle;
      return [t('kr.g.role'), t('kr.g.rules'), t('kb.g.rules'), `${t('kb.g.data')}\n${JSON.stringify(pick(b))}`].join('\n\n');
    }
    const { p, c, label } = region;
    const data = { region: label, korean: p.name, romanization: p.rr, state: t(`kr.side.${p.side}`), population: p.pop, population_year: p.pop_year, area_km2: p.area, ...(c || {}) };
    return [
      t('kr.g.role'),
      t('kr.g.rules'),
      `${t('kr.g.data')}\n${JSON.stringify(data)}`,
    ].join('\n\n');
  }
  async function askLLM(text) {
    history.push({ role: 'user', content: text });
    const div = addMsg('ai cursor', '');
    setBusy(true);
    const my = (ctrl = new AbortController());
    let out = '';
    try {
      for await (const chunk of streamChat(getConfig(), system(), history, my.signal)) {
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
      if (!my.signal.aborted) setBusy(false);
    }
  }

  function ask(text, key) {
    if (!(region || battle) || busy) return;
    addMsg('user', esc(text));
    if (online()) { askLLM(text); return; }
    const ans = battle ? (key ? battleAnswer(key) : offlineFree(text)) : (key ? offline(key) : offlineFree(text));
    typeOut(ans || t('kr.g.fallback'), hint());
  }
  const regionQuick = () => QUICK.map((k) => `<button type="button" class="bubble" data-q="${k}">${esc(t(`kr.q.${k}`))}</button>`).join('');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    ask(text);
  });
  quick.addEventListener('click', (e) => {
    const b = e.target.closest('[data-q]');
    if (b) ask(b.textContent, b.dataset.q);
  });
  chat.addEventListener('click', (e) => { if (e.target.closest('[data-act="settings"]')) openSettings(); });

  function refreshMode() {
    const cfg = getConfig();
    mode.textContent = cfg?.apiKey ? t('chip.online', { model: cfg.model }) : t('chip.offline');
    mode.classList.toggle('online', !!cfg?.apiKey);
  }

  avatar.textContent = t('kr.g.ava');
  name.textContent = t('kr.g.name');
  title.textContent = t('kr.g.pick');
  chat.innerHTML = '';
  addMsg('ai', fmt(t('kr.g.intro')));
  setBusy(false);
  refreshMode();

  return {
    refreshMode,
    // 换地区：重置对话，换开场白与快捷提问
    setRegion(p, c, label) {
      ctrl?.abort();
      finish?.();
      history = [];
      busy = false;
      region = { p, c, label };
      title.textContent = t('kr.g.title', { r: label });
      addMsg('sys', esc(t('kr.g.switch', { r: label })));
      addMsg('ai', fmt(t('kr.g.open', { r: label })));
      if (!battle) quick.innerHTML = regionQuick();
      setBusy(false);
    },
    // 古战场：开场、逐段旁述、退出
    startBattle(b) {
      ctrl?.abort();
      finish?.();
      history = [];
      busy = false;
      battle = b;
      title.textContent = t('kb.g.title', { b: L(b.name) });
      addMsg('sys', esc(t('kb.g.enter', { b: L(b.name) })));
      addMsg('ai', fmt(`${L(b.brief)}\n\n${t('kb.g.hint')}`));
      quick.innerHTML = ['b_course', 'b_forces', 'b_after'].map((k) => `<button type="button" class="bubble" data-q="${k}">${esc(t(`kb.q.${k}`))}</button>`).join('');
      setBusy(false);
    },
    narrate(text) {
      if (!battle) return;
      ctrl?.abort();
      typeOut(text);
    },
    endBattle() {
      if (!battle) return;
      ctrl?.abort();
      finish?.();
      battle = null;
      history = [];
      busy = false;
      addMsg('sys', esc(t('kb.g.leave')));
      title.textContent = region ? t('kr.g.title', { r: region.label }) : t('kr.g.pick');
      quick.innerHTML = region ? regionQuick() : '';
      setBusy(false);
    },
    askQuick: (k) => { const b = quick.querySelector(`[data-q="${k}"]`); if (b) ask(b.textContent, k); },
  };
}
