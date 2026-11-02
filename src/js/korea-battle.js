// 半岛古战场：src/data/korea/battles.json（三语写在同一个文件里，tools/korea_battles_tool.py 核对）。
// 界面沿用日本合战沙盘的 #btn-battle / #battles 列表 / #battle-hud 面板；地图是 korea.js 的同一个 ECharts 实例，
// 合战用的四个系列（b-routes / b-origins / b-markers / b-impact）在 korea.js 里先建好、这里只换数据。
// 解说由向导「丹青」以旁述口吻播出，不扮演历史人物；不收朝鲜战争（1950–1953）。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';
import { audio } from './audio.js';
import { setupHudFold } from './shell.js';

const $ = (id) => document.getElementById(id);
export const L = (o) => (o == null ? '' : typeof o === 'string' ? o : o[lang] || o.zh);

export function createKoreaBattle({ chart, battles, guide, onStart, onEnd }) {
  let cur = null;
  let phase = 0;
  let saved = null;
  let timer = null;
  const hud = $('battle-hud');
  const phaseBox = $('hud-phases');
  setupHudFold();

  function series() {
    const b = cur;
    const ph = b?.phases[phase];
    const color = (k) => b.factions.find((f) => f.key === k)?.color || '#ccc';
    const shown = b ? b.routes.filter((_, i) => ph.routes.includes(i)) : [];
    const clash = !!b && ph.impact;
    const markers = b ? ph.markers.map((m) => ({ name: L(m.name), value: m.coords })) : [];
    if (b && !clash) markers.push({ name: L(b.field.name), value: b.field.coords, itemStyle: { color: '#ffb648' } });
    return [
      { id: 'b-routes', data: shown.map((r) => ({ coords: [r.from.coords, ...r.via, r.to.coords], lineStyle: { color: color(r.faction) } })) },
      { id: 'b-origins', data: shown.map((r) => ({ name: L(r.from.name), value: r.from.coords, itemStyle: { color: color(r.faction) } })) },
      { id: 'b-markers', data: markers },
      { id: 'b-impact', data: clash ? [{ name: L(b.field.name), value: b.field.coords }] : [] },
    ];
  }

  function stopAuto() {
    clearInterval(timer);
    timer = null;
    $('hud-auto').textContent = t('hud.auto');
  }
  function setPhase(i, { narrate = true } = {}) {
    if (!cur) return;
    const n = cur.phases.length;
    const prev = phase;
    phase = Math.max(0, Math.min(n - 1, i));
    const ph = cur.phases[phase];
    if (narrate && ph.impact && phase !== prev) audio.play('drum');
    chart.setOption({ series: series() });
    phaseBox.querySelectorAll('li').forEach((li, k) => {
      li.classList.toggle('done', k < phase);
      li.classList.toggle('on', k === phase);
    });
    $('hud-brief').innerHTML = `<b>${esc(L(ph.time))}</b>${esc(L(ph.desc))}`;
    $('hud-prev').disabled = phase === 0;
    $('hud-next').disabled = phase === n - 1;
    if (narrate) guide.narrate(`**${phase + 1}/${n} · ${L(ph.title)}**　${L(ph.desc)}`);
  }

  function start(b) {
    stopAuto();
    const g = chart.getOption().geo[0];
    if (!cur) saved = { center: g.center, zoom: g.zoom };
    cur = b;
    phase = 0;
    onStart(b);
    audio.play('battle');
    document.body.classList.add('in-battle');
    $('hud-title').textContent = L(b.name);
    $('hud-sides').innerHTML = b.factions.map((f) =>
      `<span class="side" style="--c:${f.color}"><b>${esc(L(f.name))}</b>${esc(L(f.leader))}<small>${esc(L(f.strength))}</small></span>`).join('<em>VS</em>');
    phaseBox.innerHTML = b.phases.map((ph, k) => `<li data-i="${k}"><span class="ph-n">${k + 1}</span><span class="ph-t">${esc(L(ph.title))}</span></li>`).join('');
    hud.hidden = false;
    chart.setOption({ geo: { center: b.view.center, zoom: b.view.zoom } });
    // 合战面板盖在地图上方：把取景中心挪到面板下面那块空地的正中
    requestAnimationFrame(() => {
      const m = chart.getDom().getBoundingClientRect();
      const h = hud.getBoundingClientRect();
      const free = Math.max(0, Math.min(h.bottom, m.bottom) - m.top);
      if (!free || h.width < m.width * 0.6) return; // 面板只占左上一角（宽屏）时不挪
      const dy = free / 2;
      const c = chart.convertFromPixel({ geoIndex: 0 }, [m.width / 2, m.height / 2 - dy]);
      if (c) chart.setOption({ geo: { center: c } });
    });
    guide.startBattle(b);
    setPhase(0, { narrate: false });
  }
  function exit() {
    if (!cur) return;
    stopAuto();
    cur = null;
    document.body.classList.remove('in-battle');
    hud.hidden = true;
    chart.setOption({ series: series(), geo: saved ? { center: saved.center, zoom: saved.zoom } : {} });
    saved = null;
    guide.endBattle();
    onEnd();
  }

  // 列表：按年代排
  const dlg = $('battles');
  const list = battles.slice().sort((a, b) => a.year - b.year);
  dlg.querySelector('h2').textContent = t('kb.h');
  dlg.querySelector('.battles-head p').textContent = t('kb.sub');
  $('battle-list').innerHTML = list.map((b) => `
    <button type="button" class="battle-card" data-k="${b.key}">
      <span class="bc-year">${b.year}</span>
      <span class="bc-name">${esc(L(b.name))}</span>
      <span class="bc-field">⚔ ${esc(L(b.field.name))}</span>
      <span class="bc-sides">${b.factions.map((f) => `<i style="--c:${f.color}">${esc(L(f.name))} · ${esc(L(f.leader))}</i>`).join('<em>vs</em>')}</span>
      <span class="bc-brief">${esc(L(b.brief))}</span>
    </button>`).join('') + `<p class="legal kb-note">${t('kb.note')}</p>`;
  $('battle-list').addEventListener('click', (e) => {
    const c = e.target.closest('[data-k]');
    if (!c) return;
    dlg.close();
    start(battles.find((b) => b.key === c.dataset.k));
  });
  dlg.querySelector('.battles-close').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });
  const btn = $('btn-battle');
  btn.title = t('kb.title');
  btn.querySelector('[data-i18n="btn.battle"]').textContent = t('kb.btn');
  btn.querySelector('.battle-ico').textContent = t('kb.ico');
  btn.addEventListener('click', () => dlg.showModal());

  phaseBox.addEventListener('click', (e) => {
    const li = e.target.closest('[data-i]');
    if (li) { stopAuto(); setPhase(+li.dataset.i); }
  });
  $('hud-prev').addEventListener('click', () => { stopAuto(); setPhase(phase - 1); });
  $('hud-next').addEventListener('click', () => { stopAuto(); setPhase(phase + 1); });
  $('hud-auto').addEventListener('click', () => {
    if (timer) { stopAuto(); return; }
    setPhase(phase >= cur.phases.length - 1 ? 0 : phase + 1);
    $('hud-auto').textContent = t('hud.pause');
    timer = setInterval(() => {
      if (!cur || phase >= cur.phases.length - 1) { stopAuto(); return; }
      setPhase(phase + 1);
    }, 7000);
  });
  $('hud-exit').addEventListener('click', exit);

  return {
    get active() { return cur; },
    start, exit,
    // 深链接：#map=korea&battle=salsu
    byKey: (k) => battles.find((b) => b.key === k),
  };
}
