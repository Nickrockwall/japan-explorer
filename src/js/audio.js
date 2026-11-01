// 和风音频：背景音乐（BGM）+ 音效（SFX），全站单例。
// 默认全部用 Web Audio 实时合成：无音频文件、无版权问题、断网也能出声。
// 想换成录好的 mp3：放进 src/assets/audio/，再在下面 FILES 里登记一行，登记了的优先用文件，加载失败自动退回合成。
// （不自动探测文件是否存在：请求不存在的文件会在控制台留下 404。）
// 任何音频故障都只在控制台警告，绝不影响地图与主流程。
import { uiPref } from './store.js';
import { mapKey } from './country.js';

const DIR = 'src/assets/audio/';
const FILES = {
  // bgm: 'bgm_edo_ambience.mp3',
  // click: 'sfx_click.mp3',
  // stamp: 'sfx_stamp.mp3',
  // battle: 'sfx_battle.mp3',
  // drum: 'sfx_drum.mp3',
};

// 各音效的基础音量与最短间隔（毫秒）：连续快速触发时不叠成一片
const SFX = {
  click: { gain: 0.35, gap: 70 },   // 竹筒轻击
  stamp: { gain: 0.9, gap: 400 },   // 盖印：沉闷的太鼓一击
  battle: { gain: 0.6, gap: 1500 }, // 开战：太鼓两击 + 法螺贝长鸣
  drum: { gain: 0.7, gap: 400 },    // 交战爆点：太鼓「咚咚」
};
const BGM_LEVEL = 0.8;

const prefs = { muted: false, bgm: false, bgmVol: 0.5, sfxVol: 0.8, ...uiPref.get('audio', {}) };
const listeners = new Set();
const played = {};
const lastAt = {};
let ctx = null;      // AudioContext，首次用户操作后才创建
let failed = false;  // 浏览器不支持或创建失败：之后全部静默
let nodes = null;    // { master, sfx, bgm, verb }
let noise = null;    // 白噪声缓冲（打击音的起音）
const buffers = {};  // 已解码的 mp3 音效
let music = null;    // 正在播放的背景音乐 { stop() }
let musicStop = null;

const warn = (msg, err) => console.warn(`[audio] ${msg}`, err?.message || err || '');
function safe(fn) {
  try { return fn(); } catch (err) { warn('出错，已忽略', err); return undefined; }
}

function setSession(type) {
  try {
    if (navigator.audioSession && navigator.audioSession.type !== type) navigator.audioSession.type = type;
  } catch (err) { warn('无法设置音频会话', err); }
}

// ── 初始化：首次手势时解锁 AudioContext（浏览器自动播放限制） ──
function unlock() {
  if (failed) return;
  try {
    if (!ctx) {
      // iOS 16.4+：声明为「播放类」，静音模式下也出声（像视频网站；顶栏喇叭可一键静音）。
      // 代价：出声时会暂停其他 App 正在放的音乐，所以只在未静音时声明。
      if (!prefs.muted) setSession('playback');
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) throw new Error('浏览器不支持 Web Audio');
      ctx = new AC();
      build();
      loadFiles();
    }
    // 还没解锁，或 iOS 来电、切后台把 AudioContext 挂起（Safari 为 interrupted）：在这次操作里恢复
    if (ctx.state !== 'running' && ctx.state !== 'closed') {
      ctx.resume().catch((err) => warn('无法恢复播放', err));
      // 旧版 iOS Safari 还要在手势里真正播放一个声音才算解锁：播一个 1 采样的静音
      const s = ctx.createBufferSource();
      s.buffer = ctx.createBuffer(1, 1, 22050);
      s.connect(ctx.destination);
      s.start(0);
    }
  } catch (err) {
    failed = true;
    ctx = null;
    warn('音频不可用，声音已关闭', err);
    return;
  }
  syncMusic();
}

function build() {
  const master = ctx.createGain();
  master.gain.value = prefs.muted ? 0 : 1;
  master.connect(ctx.destination);
  const sfx = ctx.createGain();
  const bgm = ctx.createGain();
  sfx.gain.value = curve(prefs.sfxVol);
  bgm.gain.value = 0;
  // 混响：用衰减噪声生成冲激响应，给拨弦和打击一点「空灵」的余韵
  const verb = ctx.createConvolver();
  verb.buffer = impulse(2.6);
  const wet = ctx.createGain();
  wet.gain.value = 0.32;
  verb.connect(wet).connect(master);
  sfx.connect(master);
  bgm.connect(master);
  nodes = { master, sfx, bgm, verb };

  noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
  const d = noise.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
}

function impulse(sec) {
  const len = Math.floor(ctx.sampleRate * sec);
  const buf = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) ** 3;
  }
  return buf;
}

async function loadFiles() {
  for (const [name, file] of Object.entries(FILES)) {
    if (name === 'bgm') continue;
    try {
      const res = await fetch(DIR + file);
      if (!res.ok) throw new Error(`${res.status}`);
      buffers[name] = await ctx.decodeAudioData(await res.arrayBuffer());
    } catch (err) {
      warn(`${file} 加载失败，改用合成音`, err);
    }
  }
}

// 音量滑块 0–1 → 增益（平方曲线听感更均匀）
const curve = (v) => Math.max(0, Math.min(1, v)) ** 2;

function ramp(param, value, sec) {
  const t = ctx.currentTime;
  param.cancelScheduledValues(t);
  param.setValueAtTime(param.value, t);
  param.linearRampToValueAtTime(value, t + sec);
}

// ── 合成音色 ──
function env(t, peak, attack, decay) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.linearRampToValueAtTime(peak, t + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
  return g;
}

function tone(type, t, f0, f1, glide, g, out, stop) {
  const o = ctx.createOscillator();
  o.type = type;
  o.frequency.setValueAtTime(f0, t);
  if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + glide);
  o.connect(g).connect(out);
  o.start(t);
  o.stop(t + stop);
  return o;
}

function burst(t, filterType, freq, peak, decay, out, q = 1) {
  const s = ctx.createBufferSource();
  s.buffer = noise;
  const f = ctx.createBiquadFilter();
  f.type = filterType;
  f.frequency.value = freq;
  f.Q.value = q;
  s.connect(f).connect(env(t, peak, 0.002, decay)).connect(out);
  s.start(t);
  s.stop(t + decay + 0.05);
}

// 竹筒轻击：空心木质的「笃」——两个快速衰减的正弦 + 一点高频噪声
function woodTok(t, out) {
  tone('sine', t, 1150, 720, 0.05, env(t, 0.5, 0.002, 0.11), out, 0.15);
  tone('sine', t, 2700, 2500, 0.03, env(t, 0.12, 0.001, 0.04), out, 0.08);
  burst(t, 'bandpass', 3200, 0.22, 0.02, out, 2);
}

// 太鼓「咚」：低频正弦向下滑音 + 鼓皮的低通噪声
function taiko(t, s, out) {
  tone('sine', t, 150, 50, 0.35, env(t, s, 0.004, 1.0), out, 1.1);
  tone('triangle', t, 95, 44, 0.3, env(t, 0.35 * s, 0.004, 0.6), out, 0.7);
  burst(t, 'lowpass', 650, 0.55 * s, 0.09, out);
}

// 法螺贝：带颤音的长鸣，起音略低再升到正音，音色由低通滤波「吹亮」
function conch(t, dur, out) {
  const f = 196;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.linearRampToValueAtTime(0.45, t + 0.22);
  g.gain.linearRampToValueAtTime(0.36, t + dur - 0.4);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.Q.value = 4;
  lp.frequency.setValueAtTime(500, t);
  lp.frequency.linearRampToValueAtTime(1400, t + 0.3);
  lp.frequency.linearRampToValueAtTime(850, t + dur);
  lp.connect(g).connect(out);
  const vib = ctx.createOscillator();
  vib.frequency.value = 5.2;
  const depth = ctx.createGain();
  depth.gain.setValueAtTime(0, t);
  depth.gain.linearRampToValueAtTime(3.5, t + 0.6);
  vib.connect(depth);
  for (const [type, mul, lvl] of [['sawtooth', 1, 1], ['square', 2, 0.15]]) {
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(f * mul * 0.94, t);
    o.frequency.exponentialRampToValueAtTime(f * mul, t + 0.25);
    o.frequency.setValueAtTime(f * mul, t + dur - 0.35);
    o.frequency.exponentialRampToValueAtTime(f * mul * 0.96, t + dur);
    depth.connect(o.frequency);
    const lg = ctx.createGain();
    lg.gain.value = lvl;
    o.connect(lg).connect(lp);
    o.start(t);
    o.stop(t + dur + 0.05);
  }
  vib.start(t);
  vib.stop(t + dur + 0.05);
  // 吹气声
  const s = ctx.createBufferSource();
  s.buffer = noise;
  s.loop = true;
  const bp = ctx.createBiquadFilter();
  bp.type = 'bandpass';
  bp.frequency.value = 1200;
  const ng = ctx.createGain();
  ng.gain.value = 0.06;
  s.connect(bp).connect(ng).connect(g);
  s.start(t);
  s.stop(t + dur);
}

const SYNTH = {
  click: (t, out) => woodTok(t, out),
  stamp: (t, out) => {
    taiko(t, 1, out);
    burst(t + 0.02, 'lowpass', 1800, 0.12, 0.15, out); // 印面压上和纸
  },
  drum: (t, out) => { taiko(t, 0.8, out); taiko(t + 0.26, 1, out); },
  battle: (t, out) => { taiko(t, 0.9, out); taiko(t + 0.3, 0.9, out); conch(t + 0.55, 1.9, out); },
};

// ── 音效 ──
function play(name) {
  if (!ctx || failed || prefs.muted || ctx.state === 'closed') return;
  const spec = SFX[name];
  if (!spec) return;
  const now = performance.now();
  if (now - (lastAt[name] || 0) < spec.gap) return;
  lastAt[name] = now;
  safe(() => {
    const t = ctx.currentTime + 0.005;
    const out = ctx.createGain();
    out.gain.value = spec.gain;
    out.connect(nodes.sfx);
    const send = ctx.createGain();
    send.gain.value = 0.35;
    out.connect(send).connect(nodes.verb);
    if (buffers[name]) {
      const s = ctx.createBufferSource();
      s.buffer = buffers[name];
      s.connect(out);
      s.start(t);
    } else SYNTH[name](t, out);
    played[name] = (played[name] || 0) + 1;
  });
}

// ── 背景音乐：都节音阶（E F A B C）随机生成的古筝拨弦 + 柔和持续低音，不循环 ──
// 朝鲜半岛模式换成平调五声音阶（G A C D E）、G/D 持续低音，拨弦带伽倻琴式的「弄弦」（较宽的慢颤音）
const KOREA = mapKey === 'korea';
const MIYAKO = [0, 1, 5, 7, 8];
const PYEONGJO = [0, 2, 5, 7, 9];
const SCALE = KOREA
  ? [-1, 0, 1].flatMap((o) => PYEONGJO.map((s) => 196 * 2 ** ((o * 12 + s) / 12)))
  : [-1, 0, 1].flatMap((o) => MIYAKO.map((s) => 329.63 * 2 ** ((o * 12 + s) / 12)));
const DRONE = KOREA ? [98, 146.83, 196] : [82.41, 123.47, 164.81];
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

function pluck(t, freq, vel, out) {
  const g = env(t, vel, 0.004, 2.4);
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.setValueAtTime(Math.min(freq * 7, 9000), t);
  lp.frequency.exponentialRampToValueAtTime(freq * 1.6, t + 1.4);
  lp.connect(g).connect(out);
  const o = ctx.createOscillator();
  o.type = 'triangle';
  o.frequency.setValueAtTime(freq, t);
  if (KOREA && Math.random() < 0.55) {
    // 弄弦：按弦的手在余音里上下揉弦
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 4.5 + Math.random() * 1.5;
    const depth = ctx.createGain();
    depth.gain.setValueAtTime(0, t);
    depth.gain.linearRampToValueAtTime(freq * 0.018, t + 0.6);
    lfo.connect(depth).connect(o.frequency);
    lfo.start(t + 0.2);
    lfo.stop(t + 2.5);
  } else if (Math.random() < 0.12) {
    // 偶尔「押し」：弦被按压，音高微微上推再回落
    o.frequency.setValueAtTime(freq, t + 0.3);
    o.frequency.linearRampToValueAtTime(freq * 1.03, t + 0.55);
    o.frequency.linearRampToValueAtTime(freq, t + 1.1);
  }
  o.connect(lp);
  o.start(t);
  o.stop(t + 2.5);
  const h = ctx.createOscillator();
  h.frequency.value = freq * 2;
  const hg = env(t, vel * 0.25, 0.003, 0.5);
  h.connect(hg).connect(out);
  h.start(t);
  h.stop(t + 0.6);
  burst(t, 'highpass', 2500, vel * 0.15, 0.015, out);
}

function synthMusic() {
  const out = ctx.createGain();
  out.connect(nodes.bgm);
  const send = ctx.createGain();
  send.gain.value = 0.7;
  out.connect(send).connect(nodes.verb);

  // 持续低音：E2 + B2（半岛模式 G2 + D3），慢速起伏
  const drone = ctx.createGain();
  drone.gain.value = 0.05;
  const dlp = ctx.createBiquadFilter();
  dlp.type = 'lowpass';
  dlp.frequency.value = 380;
  dlp.connect(drone).connect(out);
  const lfo = ctx.createOscillator();
  lfo.frequency.value = 0.07;
  const lfoDepth = ctx.createGain();
  lfoDepth.gain.value = 0.025;
  lfo.connect(lfoDepth).connect(drone.gain);
  const oscs = [lfo, ...DRONE.map((f, i) => {
    const o = ctx.createOscillator();
    o.type = i === 2 ? 'sine' : 'triangle';
    o.frequency.value = f;
    o.detune.value = (i - 1) * 4;
    o.connect(dlp);
    return o;
  })];
  for (const o of oscs) o.start();

  // 拨弦：在音阶上随机游走，一句 4–7 个音，句间留白
  let idx = 7;
  let left = 0;
  let next = ctx.currentTime + 0.8;
  const tick = () => safe(() => {
    while (next < ctx.currentTime + 1.2) {
      if (left <= 0) {
        left = 4 + Math.floor(Math.random() * 4);
        next += 1.6 + Math.random() * 2.4;
        idx = 5 + Math.floor(Math.random() * 6);
        continue;
      }
      idx = Math.max(2, Math.min(SCALE.length - 2, idx + pick([-2, -1, -1, 0, 1, 1, 2])));
      const vel = 0.16 + Math.random() * 0.08;
      if (Math.random() < 0.15) pluck(next - 0.09, SCALE[idx + 1], vel * 0.6, out); // 装饰音
      pluck(next, SCALE[idx], vel, out);
      if (Math.random() < 0.2) pluck(next, SCALE[idx] / 2, vel * 0.7, out);         // 低八度和音
      left -= 1;
      next += left === 0 ? 1.4 : pick([0.45, 0.6, 0.6, 0.9, 1.2]);
    }
  });
  tick();
  const timer = setInterval(tick, 250);
  return {
    stop() {
      clearInterval(timer);
      for (const o of oscs) safe(() => o.stop());
      out.disconnect();
    },
  };
}

function fileMusic(file) {
  const el = new Audio(DIR + file);
  el.loop = true;
  ctx.createMediaElementSource(el).connect(nodes.bgm);
  const p = el.play();
  p?.catch((err) => {
    warn(`${file} 无法播放，改用合成音乐`, err);
    if (music?.el === el) music = synthMusic();
  });
  return { el, stop() { el.pause(); el.src = ''; } };
}

// 背景音乐是否该响：开启 + 未静音 + 已解锁 + 页面在前台
function syncMusic() {
  if (!ctx || failed) return;
  safe(() => {
    const want = prefs.bgm && !prefs.muted && ctx.state !== 'closed' && document.visibilityState === 'visible';
    if (want) {
      clearTimeout(musicStop);
      musicStop = null;
      if (!music) music = FILES.bgm ? fileMusic(FILES.bgm) : synthMusic();
      ramp(nodes.bgm.gain, BGM_LEVEL * curve(prefs.bgmVol), 2.0); // 淡入
    } else if (music && !musicStop) {
      ramp(nodes.bgm.gain, 0, 1.2); // 淡出后再停
      musicStop = setTimeout(() => {
        music?.stop();
        music = null;
        musicStop = null;
      }, 1300);
    }
  });
}

function save() {
  uiPref.set('audio', prefs);
  for (const fn of listeners) safe(() => fn(state()));
}

const state = () => ({ ...prefs });

export const audio = {
  play,
  state,
  onChange(fn) { listeners.add(fn); },
  setMuted(on) {
    prefs.muted = !!on;
    if (ctx) setSession(on ? 'auto' : 'playback'); // 静音时把其他 App 的音乐还给用户
    if (nodes) safe(() => ramp(nodes.master.gain, on ? 0 : 1, 0.25));
    syncMusic();
    save();
  },
  toggleMute() { this.setMuted(!prefs.muted); },
  setMusic(on) {
    prefs.bgm = !!on;
    syncMusic();
    save();
  },
  setVolume(kind, v) {
    if (kind === 'bgm') prefs.bgmVol = v;
    else prefs.sfxVol = v;
    if (nodes) safe(() => {
      if (kind === 'sfx') ramp(nodes.sfx.gain, curve(v), 0.05);
      else if (music && !musicStop) ramp(nodes.bgm.gain, BGM_LEVEL * curve(v), 0.1);
    });
    save();
  },
  // 测试用：当前播放状态
  debug: () => ({ ready: !!ctx && !failed, ctx: ctx?.state || null, played: { ...played }, music: !!music && !musicStop }),
};

// 全局首次手势解锁；之后保留监听，用于恢复被系统挂起的 AudioContext。
// 触摸屏上「按下」（touchstart / 触摸的 pointerdown）不算解锁声音的用户操作，要等「抬起」：
// 所以 pointerup / touchend / click 都要监听，否则手机上永远解不了锁。
// 鼠标的 pointerdown 算数，保留它让电脑上第一下点击就能出声。
for (const ev of ['pointerdown', 'pointerup', 'touchend', 'click', 'keydown']) {
  addEventListener(ev, unlock, { capture: true, passive: true });
}
document.addEventListener('visibilitychange', syncMusic);
