// 语音（3.46）：浏览器自带的朗读（speechSynthesis）与语音识别（SpeechRecognition），不接外部服务、不下载声音文件。
// - 🔊 读音按钮 sayBtn(读音, 'ja')：日文地名、人名用假名读（汉字直接交给系统常读错：一宮、神戸、伊達），
//   没有假名的人名用罗马字转假名（kanaOf）；转不出来就不出按钮。
// - 「听一遍」sayAllBtn()：把同一块里 [data-say-line] 的文字按当前界面语言顺序读出来。
// - 合战旁白朗读：sayNarration(text)，开关存 je.ui.sayBattle。
// - 语音搜索：setupVoiceSearch(input)，浏览器不支持就不出麦克风。
// 只在点按时出声；再点一次（或点别的读音按钮）停下。系统没有那种语言的声音时提示一次。
import { lang, t } from './i18n.js';
import { uiPref } from './store.js';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const CAN_SAY = typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function';
const TAG = { ja: 'ja-JP', zh: 'zh-CN', en: 'en-US' };

// ── 罗马字 → 平假名（修正平文式；长音符号转成 う / あ…，读出来与长音一样）──
const SYL = {
  a: 'あ', i: 'い', u: 'う', e: 'え', o: 'お',
  ka: 'か', ki: 'き', ku: 'く', ke: 'け', ko: 'こ', ga: 'が', gi: 'ぎ', gu: 'ぐ', ge: 'げ', go: 'ご',
  sa: 'さ', shi: 'し', si: 'し', su: 'す', se: 'せ', so: 'そ', za: 'ざ', ji: 'じ', zi: 'じ', zu: 'ず', ze: 'ぜ', zo: 'ぞ',
  ta: 'た', chi: 'ち', ti: 'ち', tsu: 'つ', tu: 'つ', te: 'て', to: 'と', da: 'だ', di: 'ぢ', du: 'づ', dzu: 'づ', de: 'で', do: 'ど',
  na: 'な', ni: 'に', nu: 'ぬ', ne: 'ね', no: 'の', ha: 'は', hi: 'ひ', fu: 'ふ', hu: 'ふ', he: 'へ', ho: 'ほ',
  ba: 'ば', bi: 'び', bu: 'ぶ', be: 'べ', bo: 'ぼ', pa: 'ぱ', pi: 'ぴ', pu: 'ぷ', pe: 'ぺ', po: 'ぽ',
  ma: 'ま', mi: 'み', mu: 'む', me: 'め', mo: 'も', ya: 'や', yu: 'ゆ', yo: 'よ',
  ra: 'ら', ri: 'り', ru: 'る', re: 'れ', ro: 'ろ', wa: 'わ', wi: 'ゐ', we: 'ゑ', wo: 'を',
  kya: 'きゃ', kyu: 'きゅ', kyo: 'きょ', gya: 'ぎゃ', gyu: 'ぎゅ', gyo: 'ぎょ', sha: 'しゃ', shu: 'しゅ', sho: 'しょ', she: 'しぇ',
  ja: 'じゃ', ju: 'じゅ', jo: 'じょ', je: 'じぇ', cha: 'ちゃ', chu: 'ちゅ', cho: 'ちょ', che: 'ちぇ', nya: 'にゃ', nyu: 'にゅ', nyo: 'にょ',
  hya: 'ひゃ', hyu: 'ひゅ', hyo: 'ひょ', bya: 'びゃ', byu: 'びゅ', byo: 'びょ', pya: 'ぴゃ', pyu: 'ぴゅ', pyo: 'ぴょ',
  mya: 'みゃ', myu: 'みゅ', myo: 'みょ', rya: 'りゃ', ryu: 'りゅ', ryo: 'りょ', fa: 'ふぁ', fi: 'ふぃ', fe: 'ふぇ', fo: 'ふぉ',
};
const LONG = { 'ā': 'aa', 'ī': 'ii', 'ū': 'uu', 'ē': 'ee', 'ō': 'ou', 'â': 'aa', 'î': 'ii', 'û': 'uu', 'ê': 'ee', 'ô': 'ou' };
export function kanaOf(roma) {
  if (!roma) return null;
  const s = roma.normalize('NFC').replace(/\s+/g, ' ').replace(/\s*\([^)]*\)/g, '').trim().toLowerCase().replace(/[āīūēōâîûêô]/g, (c) => LONG[c]).replace(/[-‐]/g, '').replace(/’/g, "'");
  if (/[^a-z' ]/.test(s)) return null;
  let out = '';
  for (let i = 0; i < s.length;) {
    const c = s[i], nx = s[i + 1] || '';
    if (c === ' ') { out += ' '; i++; continue; }
    if (c === "'") { i++; continue; }
    if (c === 'n' && (nx === "'" || !nx || nx === ' ' || !'aiueoy'.includes(nx))) { out += 'ん'; i++; continue; }
    if (c === 'm' && 'bpm'.includes(nx) && nx) { out += 'ん'; i++; continue; }
    if (c === nx && !'aiueon'.includes(c)) { out += 'っ'; i++; continue; }
    if (c === 't' && s.startsWith('ch', i + 1)) { out += 'っ'; i++; continue; }
    const k = [3, 2, 1].map((n) => s.slice(i, i + n)).find((x) => SYL[x]);
    if (!k) return null;
    out += SYL[k];
    i += k.length;
  }
  return out.trim() || null;
}

// 人名的日语读音：天皇有假名（rulers 的 kana）；其余取罗马字（「Oda Nobunaga」）转假名
export function personYomi(p) {
  if (!p) return null;
  if (p.kana && /天皇$/.test(p.ja || '')) return `${p.kana}てんのう`;
  if (p.kana) return p.kana;
  return kanaOf((p.en || '').replace(/^Emperor\s+/i, ''));
}

// ── 朗读 ──
let playing = null; // 正在读的按钮
let warned = false;
const voices = () => (CAN_SAY ? window.speechSynthesis.getVoices() : []);
function voiceFor(l) {
  const vs = voices();
  const want = TAG[l] || l;
  const norm = (v) => v.lang.replace('_', '-').toLowerCase();
  return vs.find((v) => norm(v) === want.toLowerCase()) || vs.find((v) => norm(v).startsWith(l)) || null;
}
export function hasVoice(l) {
  return !voices().length || !!voiceFor(l); // 声音列表还没载入时先当作有
}

function mark(btn, on) {
  if (!btn) return;
  btn.classList.toggle('saying', on);
  btn.setAttribute('aria-pressed', String(on));
}

export function stopSay() {
  if (!CAN_SAY) return;
  window.speechSynthesis.cancel();
  mark(playing, false);
  playing = null;
}

// 读一段或几段文字；btn 是触发的按钮（读完自动复原）；返回是否开始读了
export function say(text, l = lang, { btn = null, onNoVoice = null } = {}) {
  if (!CAN_SAY) return false;
  const parts = (Array.isArray(text) ? text : [text]).map((x) => String(x || '').trim()).filter(Boolean);
  if (!parts.length) return false;
  stopSay();
  const v = voiceFor(l);
  if (!v && voices().length && !warned) {
    warned = true;
    onNoVoice?.(t('say.novoice', { lang: t(`say.lang.${l}`) }));
  }
  playing = btn;
  mark(btn, true);
  parts.forEach((x, i) => {
    const u = new window.SpeechSynthesisUtterance(x);
    u.lang = TAG[l] || l;
    if (v) u.voice = v;
    u.rate = l === 'ja' && parts.length === 1 && x.length < 16 ? 0.85 : 1; // 单个名字读慢一点
    if (i === parts.length - 1) u.onend = u.onerror = () => { if (playing === btn) { mark(btn, false); playing = null; } };
    window.speechSynthesis.speak(u);
  });
  return true;
}

// 🔊 读音按钮（读日语）：yomi 是假名；label 写进提示（读的是什么）
export function sayBtn(yomi, { l = 'ja', label = '' } = {}) {
  if (!CAN_SAY || !yomi) return '';
  const title = t(l === 'ja' ? 'say.ja' : 'say.btn', { name: label || yomi });
  return `<button type="button" class="say" data-say="${esc(yomi)}" data-say-lang="${l}" title="${esc(title)}" aria-label="${esc(title)}" aria-pressed="false">`
    + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></button>';
}

// 「听一遍」：读所在块（最近的 [data-say-scope]）里所有 [data-say-line]
export function sayAllBtn() {
  if (!CAN_SAY) return '';
  return `<button type="button" class="say-all" data-say-all aria-pressed="false" title="${esc(t('say.all.title'))}">`
    + `<span aria-hidden="true">🔊</span> <span class="say-all-lbl">${esc(t('say.all'))}</span></button>`;
}

export function setupSay(toast = () => {}) {
  if (!CAN_SAY) return;
  window.speechSynthesis.getVoices(); // 有的浏览器要先问一次才开始载入声音
  document.addEventListener('click', (e) => {
    const b = e.target.closest?.('[data-say], [data-say-all]');
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    if (playing === b) { stopSay(); return; }
    if (b.hasAttribute('data-say-all')) {
      const scope = b.closest('[data-say-scope]');
      const lines = scope ? [...scope.querySelectorAll('[data-say-line]')].map((x) => x.dataset.sayLine || x.textContent) : [];
      say(lines, lang, { btn: b, onNoVoice: toast });
    } else {
      say(b.dataset.say, b.dataset.sayLang || 'ja', { btn: b, onNoVoice: toast });
    }
  }, true);
  // 关掉对话框、换页时停下
  document.addEventListener('close', () => stopSay(), true);
  window.addEventListener('pagehide', () => stopSay());
}

// ── 合战旁白朗读（开关在合战面板标题栏）──
export const narrationOn = () => CAN_SAY && !!uiPref.get('sayBattle', false);
export function sayNarration(text) {
  if (!narrationOn()) return;
  say(String(text).replace(/【|】/g, ' '), lang);
}
export function setupNarrationToggle(btn) {
  if (!btn) return;
  if (!CAN_SAY) { btn.hidden = true; return; }
  const apply = () => {
    const on = narrationOn();
    btn.setAttribute('aria-pressed', String(on));
    btn.classList.toggle('on', on);
    btn.title = t(on ? 'say.battle.off' : 'say.battle.on');
  };
  apply();
  btn.addEventListener('click', () => {
    uiPref.set('sayBattle', !narrationOn());
    if (!narrationOn()) stopSay();
    apply();
  });
}

// ── 语音搜索 ──
const Rec = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;
export const CAN_LISTEN = !!Rec;
export function setupVoiceSearch(input, btn, toast = () => {}) {
  if (!btn || !input) return;
  if (!Rec) { btn.hidden = true; return; }
  btn.hidden = false;
  btn.parentElement?.classList.add('has-mic');
  btn.addEventListener('pointerdown', (e) => e.preventDefault()); // 不让搜索框失焦（手机上失焦就收回成放大镜）
  let rec = null;
  const done = () => { btn.classList.remove('listening'); btn.setAttribute('aria-pressed', 'false'); rec = null; };
  btn.addEventListener('click', () => {
    if (rec) { rec.abort(); done(); return; }
    stopSay();
    try {
      rec = new Rec();
    } catch {
      btn.hidden = true;
      return;
    }
    rec.lang = TAG[lang];
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const text = (e.results?.[0]?.[0]?.transcript || '').trim().replace(/[。．.、，,！!？?]$/u, '');
      if (!text) return;
      input.value = text;
      input.focus({ preventScroll: true });
      input.dispatchEvent(new Event('input', { bubbles: true }));
    };
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') toast(t('say.mic.denied'));
      else if (e.error !== 'aborted' && e.error !== 'no-speech') toast(t('say.mic.fail'));
    };
    rec.onend = done;
    btn.classList.add('listening');
    btn.setAttribute('aria-pressed', 'true');
    toast(t('say.mic.listening'));
    try { rec.start(); } catch { done(); }
  });
}
