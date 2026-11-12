// 生日帖对话框（3.40 从 app.js 拆出）：彼时今日里某一天的全部条目 + 几个数字、出生年（年号、干支、同龄的他们）、存图、复制链接；深链接 #bday=MM-DD。
// ctx 里是 app.js main() 里的共用状态与函数（kako 是同一个对象，renderKako / showKako / saveImage 等由 app 提供）
import { bdayData, bdayHTML, bdayImage } from './bday.js';
import { lang, t, stateHash } from './i18n.js';
import { uiPref } from './store.js';
import { MAP } from './country.js';
import { audio } from './audio.js';
import { toast, legacyCopy } from './shell.js';

const $ = (id) => document.getElementById(id);

export function setupBday({ kako, ensureHan, prefLabel, lordOf, renderKako, showKako, saveImage, data, app }) {
  // ── 生日帖：彼时今日里某一天的全部条目 + 几个数字，可存图；深链接 #bday=MM-DD ──
  const bdDlg = $('bday');
  let bd = null;
  // 出生年（3.40，只存本机 je.ui.bdayYear）：填了才出年号、干支与「同龄的他们」（ages.json 这时才下载，约 20 KB）
  let ages = null;
  const bdYear = () => { const y = +uiPref.get('bdayYear', 0); return y >= 1873 && y <= new Date().getFullYear() ? y : null; };
  const bdCtx = () => ({ prefName: prefLabel, lordOf, name: uiPref.get('kosekiName', ''), you: bdYear() && bd ? { y: bdYear(), md: bd.key } : null, ages, battles: data.events?.historic_battles || [] });
  async function openBday(key) {
    if (!kako.all) return;
    await ensureHan();
    if (bdYear() && !ages) ages = await fetch(`${MAP.data}/ages.json`).then((r) => r.json()).catch(() => null);
    bd = bdayData(kako.all, key);
    bdDlg.innerHTML = bdayHTML(bd, bdCtx());
    if (!bdDlg.open) bdDlg.showModal();
    bdDlg.scrollTop = 0;
    history.replaceState(null, '', `#bday=${key}&lang=${lang}`);
    audio.play('click');
  }
  bdDlg.addEventListener('close', () => {
    if (/bday=/.test(location.hash)) history.replaceState(null, '', app.currentId ? stateHash(app.currentId) : location.pathname + location.search);
  });
  bdDlg.addEventListener('input', (e) => {
    if (e.target.matches('[data-bd-name]')) uiPref.set('kosekiName', e.target.value.trim());
  });
  bdDlg.addEventListener('change', (e) => {
    if (e.target.matches('[data-bd-year]')) {
      const y = parseInt(e.target.value, 10);
      uiPref.set('bdayYear', y >= 1873 && y <= new Date().getFullYear() ? y : 0);
      if (bd) openBday(bd.key);
      return;
    }
    const m = e.target.closest('[data-bd-date]')?.value.match(/^\d+-(\d\d)-(\d\d)$/);
    if (m) {
      kako.key = `${m[1]}-${m[2]}`;
      kako.page = 0;
      renderKako();
      openBday(kako.key);
    }
  });
  bdDlg.addEventListener('click', async (e) => {
    if (e.target === bdDlg || e.target.closest('[data-act="bd-close"]')) { bdDlg.close(); return; }
    const it = e.target.closest('[data-kako]');
    if (it) { bdDlg.close(); showKako(it.dataset.kako, it.dataset.kt); return; }
    const b = e.target.closest('[data-act]');
    if (!b || !bd) return;
    if (b.dataset.act === 'bd-link') {
      const url = `${location.origin}${location.pathname}#bday=${bd.key}&lang=${lang}`;
      try {
        await navigator.clipboard.writeText(url);
        toast(t('share.copied'));
      } catch {
        toast(t(legacyCopy(url) ? 'share.copied' : 'share.fail'));
      }
    }
    if (b.dataset.act === 'bd-image') {
      b.disabled = true;
      try {
        await saveImage(await bdayImage(bd, bdCtx()), `birthday-${bd.key}.png`, t('bd.kicker'));
      } catch (err) {
        console.warn('生日帖图片生成失败', err);
        toast(t('ks.fail'));
      } finally {
        b.disabled = false;
      }
    }
  });

  return { openBday };
}
