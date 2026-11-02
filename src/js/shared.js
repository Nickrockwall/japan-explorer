// 日本与朝鲜半岛的共同历史：两种地图共用的对话框。每个事件分三层——双方都承认的事实 / 各方的主流叙述 / 来源。
// 内容在 src/data/shared_history.json（三语写在同一个文件里），两种模式看到的是同一份。
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

let data = null;
let dlg = null;
const L = (o) => (typeof o === 'string' ? o : o?.[lang] ?? o?.zh ?? '');

async function load() {
  data ||= await fetch('src/data/shared_history.json').then((r) => r.json());
  return data;
}

function render(key) {
  const ev = data.events.find((e) => e.key === key) || data.events[0];
  dlg.querySelector('.sh-tabs').innerHTML = data.events.map((e) =>
    `<button type="button" role="tab" data-sh="${e.key}" aria-selected="${e.key === ev.key}" class="${e.key === ev.key ? 'on' : ''}">${esc(L(e.title))}<small>${esc(L(e.years))}</small></button>`).join('');
  dlg.querySelector('.sh-body').innerHTML = `
    <div class="sh-names">${ev.names.map((n) => `<span><b>${esc(L(n.who))}</b>${esc(L(n.name))}</span>`).join('')}</div>
    <h3>${esc(t('sh.facts'))}</h3>
    <ul class="sh-facts">${ev.facts[lang] ? ev.facts[lang].map((f) => `<li>${esc(f)}</li>`).join('') : ev.facts.zh.map((f) => `<li>${esc(f)}</li>`).join('')}</ul>
    <h3>${esc(t('sh.views'))}</h3>
    ${ev.views.map((v) => `<div class="sh-view"><b>${esc(L(v.who))}</b><p>${esc(L(v.text))}</p></div>`).join('')}
    <h3>${esc(t('sh.sources'))}</h3>
    <ul class="sh-src">${ev.sources.map((s) => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a></li>`).join('')}</ul>
    <p class="sh-note">${esc(t('sh.note'))}</p>`;
  dlg.querySelector('.sh-body').scrollTop = 0;
  showTab();
}

// 标签一行横排，选中的那件滚进视野（只横向滚标签行，不动页面）
function showTab() {
  const row = dlg.querySelector('.sh-tabs'), on = row.querySelector('.on');
  if (on) row.scrollLeft = on.offsetLeft - (row.clientWidth - on.offsetWidth) / 2;
}

// key 省略时打开最早的一件
export async function openShared(key) {
  await load();
  if (!dlg) {
    dlg = document.createElement('dialog');
    dlg.className = 'shared';
    dlg.id = 'shared';
    dlg.setAttribute('aria-labelledby', 'sh-h');
    dlg.innerHTML = `
      <div class="sh-inner">
        <header><h2 id="sh-h">${esc(t('sh.h'))}</h2><button type="button" class="muni-card-x" data-act="sh-close" aria-label="${esc(t('close'))}">×</button></header>
        <p class="sh-sub">${esc(t('sh.sub'))}</p>
        <div class="sh-tabs" role="tablist"></div>
        <div class="sh-body"></div>
      </div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener('click', (e) => {
      if (e.target === dlg || e.target.closest('[data-act="sh-close"]')) dlg.close();
      const b = e.target.closest('[data-sh]');
      if (b) render(b.dataset.sh);
    });
  }
  render(key);
  dlg.showModal();
  showTab();
}

// 进入对话框的按钮（欢迎卡、详卡用）
export const sharedButtons = () => `<div class="sh-entry"><button type="button" class="btn btn-ghost" data-act="shared">📚 ${esc(t('sh.btn'))}</button></div>`;
