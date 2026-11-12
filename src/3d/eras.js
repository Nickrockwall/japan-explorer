// 立体图的六个时代（3.35 五个，3.38 加室町）：每个时代几个年份、用哪张底图、都城在哪、古代官道（示意）与江户 / 明治的配色
export const ERAS = [
  { key: 'kodai', years: ['712', '757', '824'] },
  { key: 'kamakura', years: ['1200', '1250', '1300'] },
  { key: 'muromachi', years: ['1350', '1400', '1440'] },
  { key: 'sengoku', years: ['1467', '1560', '1573', '1582', '1590', '1600'] },
  { key: 'edo', years: ['1867'] },
  { key: 'meiji', years: ['1871', '1876', '1888'] },
];
export const YEARS = ERAS.flatMap((e) => e.years);
export const eraOf = (y) => ERAS.find((e) => e.years.includes(String(y)))?.key;
export const eraYears = (k) => ERAS.find((e) => e.key === k)?.years || [];

// 底图：古代按当年的国界（province_eras），镰仓按 824 年 68 国，战国另把奥羽按郡细分（与平面战国图相同），
// 江户与 1871（废藩置县，藩原样改县）用幕末的藩领，1876 / 1888 用当年的府县
const BASE = { 712: 'p712', 757: 'p757', 824: 'p824', 1867: 'edo', 1871: 'edo', 1876: 'm1876', 1888: 'm1888' };
export const baseOf = (y) => BASE[y] || (eraOf(y) === 'sengoku' ? 'sg' : 'p824');

// 都：710–784 平城京（平城宫），794 起平安京（京都御所），1869 起东京（皇居）
const HEIJO = [135.7956, 34.6911];
const KYOTO = [135.7621, 35.0254];
const TOKYO = [139.7528, 35.6852];
export function capitalOf(y) {
  y = +y;
  if (y < 794) return { at: HEIJO, key: 'heijo' };
  if (y < 1869) return { at: KYOTO, key: 'kyo' };
  return { at: TOKYO, key: 'tokyo' };
}
// 幕府所在（第二枚印，写「幕」）：镰仓（大仓幕府附近，鹤冈八幡宫）、江户城
export const SHOGUNATE = {
  kamakura: { at: [139.5565, 35.3259], key: 'kamakura' },
  edo: { at: TOKYO, key: 'edo' },
};

// 古代官道（示意）：各道按国府连线，`CAP` 是当年的都；画在国府（有精确坐标的）或国的中心之间，不是真实的路线
export const ROUTES = [
  ['CAP', '伊賀国', '伊勢国', '尾張国', '三河国', '遠江国', '駿河国', '相模国', '上総国', '下総国', '常陸国'], // 东海道（走水渡海到上总）
  ['伊勢国', '志摩国'], ['駿河国', '甲斐国'], ['駿河国', '伊豆国'], ['上総国', '安房国'],
  ['CAP', '近江国', '美濃国', '信濃国', '上野国', '下野国', '陸奥国'], ['美濃国', '飛騨国'], ['陸奥国', '出羽国'], // 东山道
  ['CAP', '若狭国', '越前国', '加賀国', '越中国', '越後国'], ['越中国', '能登国'], ['越後国', '佐渡国'], // 北陆道
  ['CAP', '丹波国', '但馬国', '因幡国', '伯耆国', '出雲国', '石見国'], ['丹波国', '丹後国'], ['出雲国', '隠岐国'], // 山阴道
  ['CAP', '摂津国', '播磨国', '備前国', '備中国', '備後国', '安芸国', '周防国', '長門国', '筑前国'], ['播磨国', '美作国'], // 山阳道
  ['CAP', '紀伊国', '淡路国', '阿波国', '讃岐国', '伊予国', '土佐国'], // 南海道
  ['筑前国', '筑後国', '肥後国', '薩摩国'], ['筑前国', '豊前国', '豊後国', '日向国', '大隅国'], ['筑前国', '肥前国'], ['肥前国', '壱岐国', '対馬国'], // 西海道
];
// 武藏国 771 年以前属东山道（kodai.json 的 musashi_tosando_until）：那时上野—武藏有一条支路
export const ROUTE_MUSASHI_TOSANDO = ['上野国', '武蔵国'];
export const ROUTE_MUSASHI_TOKAIDO = ['相模国', '武蔵国', '下総国'];

// 五畿七道的颜色（与平面地图的五畿七道相同）
export const CIRCUIT_COLOR = {
  畿内: '#d46e64', 东海道: '#d2a171', 东山道: '#89aa79', 北陆道: '#79aac3',
  山阴道: '#9d92c9', 山阳道: '#d9875e', 南海道: '#60ada5', 西海道: '#ce7ea2', 北海道: '#b7c4cc', 令制外: '#d6ccb6',
};

// 江户的领主类别与明治府县：相邻两块不同色（贪心着色，面积大的先挑）
export const KIND_COLOR = {
  bakufu: '#c9a24e', hatamoto: '#cdbf98', jisha: '#b9a6c9', mixed: '#d3c9b1', sankyo: '#a99bd6',
  ezo: '#e3dccb', ryukyu: '#9fc5b9', none: '#e9e0c8',
};
const PALETTE = ['#d46e64', '#669dd1', '#87ae67', '#e3a06a', '#a186db', '#57a983', '#d57ead', '#67b0ac', '#b0607c', '#8fa3c4'];
export function graphColors(regions, edges, skip = () => false) {
  const nb = new Map(regions.map((r) => [r.key, new Set()]));
  for (const e of edges) { nb.get(e.a)?.add(e.b); nb.get(e.b)?.add(e.a); }
  const out = new Map();
  for (const r of [...regions].sort((a, b) => b.area - a.area)) {
    if (skip(r)) continue;
    const used = new Set([...nb.get(r.key)].map((k) => out.get(k)));
    out.set(r.key, PALETTE.find((c) => !used.has(c)) || PALETTE[out.size % PALETTE.length]);
  }
  return out;
}
