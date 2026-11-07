// 「数据有误？」：各张卡片末尾的小链接，点了打开 GitHub 新建 issue，标题与正文预先填好是哪张卡片、当前链接与界面语言。
// 链接在点的那一刻才拼（地址栏的深链接常在卡片画好之后才改），网站本身不收集也不发送任何东西；提交要登录 GitHub
import { t, lang } from './i18n.js';
import { esc } from './detail.js';

export const REPO = 'https://github.com/Nickrockwall/japan-explorer';

// what：这张卡片是什么（界面语言，如「战国势力 · 武田 1573」）
export function fixLink(what) {
  return `<a class="fix-link" data-fix="${esc(what)}" href="${REPO}/issues/new" target="_blank" rel="noopener">⚑ ${esc(t('fix.link'))}</a>`;
}

export function issueURL(what, href = location.href) {
  const q = new URLSearchParams({
    title: t('fix.title', { what }),
    body: t('fix.body', { what, url: href, lang }),
  });
  return `${REPO}/issues/new?${q}`;
}

// 捕获阶段改写 href：比浏览器跟随链接早一步
document.addEventListener('click', (e) => {
  const a = e.target.closest?.('a[data-fix]');
  if (a) a.href = issueURL(a.dataset.fix);
}, true);
