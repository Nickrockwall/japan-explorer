// 朝鲜半岛模式的入口（app.js 在 mapKey === 'korea' 时载入）：同一套页面外壳，数据与交互自成一套
import { applyStatic } from './i18n.js';
import { setupLangSwitch, setupMapSwitch } from './shell.js';

const $ = (id) => document.getElementById(id);

export async function main() {
  applyStatic();
  setupLangSwitch();
  setupMapSwitch();
  $('loading').classList.add('hidden');
}
