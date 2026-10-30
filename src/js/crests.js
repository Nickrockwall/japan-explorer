// 家纹 / 神纹 SVG 印纹库：crestSVG(code) → <svg> 字符串（viewBox 0 0 100 100，fill 为 currentColor）
// code 为 goshuin.crest_icon；"char:X" 表示以单字作印纹
const rot = (deg, body) => `<g transform="rotate(${deg} 50 50)">${body}</g>`;
const ring = (r = 44, w = 5) => `<circle cx="50" cy="50" r="${r}" fill="none" stroke="currentColor" stroke-width="${w}"/>`;
const around = (n, r0, fn) => Array.from({ length: n }, (_, i) => fn((360 / n) * i, r0)).join('');
const polar = (deg, r) => {
  const a = ((deg - 90) * Math.PI) / 180;
  return [50 + r * Math.cos(a), 50 + r * Math.sin(a)];
};

const SHAPES = {
  // 三叶葵：三片心形叶
  aoi: () => ring() + around(3, 0, (d) => rot(d,
    '<path d="M50 50 C36 40 28 22 50 12 C72 22 64 40 50 50Z"/><path d="M50 48 L50 18" stroke="var(--crest-bg,#fff)" stroke-width="2"/>')),
  // 武田菱：四枚菱形
  bishi: () => [[50, 28], [28, 50], [72, 50], [50, 72]]
    .map(([x, y]) => `<path d="M${x} ${y - 19} L${x + 19} ${y} L${x} ${y + 19} L${x - 19} ${y}Z"/>`).join(''),
  // 一文字三星
  mitsuboshi: () => '<rect x="20" y="20" width="60" height="11" rx="2"/>' +
    '<circle cx="50" cy="50" r="11"/><circle cx="33" cy="72" r="11"/><circle cx="67" cy="72" r="11"/>',
  // 丸十字
  juji: () => ring(40, 8) + '<rect x="45" y="12" width="10" height="76"/><rect x="12" y="45" width="76" height="10"/>',
  // 木瓜：四瓣外形 + 花心
  mokko: () => [[50, 30], [70, 50], [50, 70], [30, 50]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="19"/>`).join('') +
    '<circle cx="50" cy="50" r="15" fill="var(--crest-bg,#fff)"/><circle cx="50" cy="50" r="6"/>' +
    around(4, 0, (d) => rot(d + 45, '<rect x="48.5" y="35" width="3" height="9"/>')),
  // 梅钵
  umebachi: () => '<circle cx="50" cy="50" r="10"/>' + around(5, 27, (d, r) => {
    const [x, y] = polar(d, r);
    return `<circle cx="${x}" cy="${y}" r="13"/>`;
  }),
  // 三巴
  tomoe: () => ring(45, 4) + around(3, 0, (d) => rot(d,
    '<circle cx="50" cy="29" r="12"/><path d="M62 29 A26 26 0 0 1 72 66" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round"/>')),
  // 桔梗：五瓣尖花
  kikyo: () => around(5, 0, (d) => rot(d, '<path d="M50 50 L37 22 L45 16 L50 22 L55 16 L63 22Z"/>')) +
    '<circle cx="50" cy="50" r="6" fill="var(--crest-bg,#fff)"/>',
  // 十六八重表菊
  kiku: () => around(16, 0, (d) => rot(d, '<ellipse cx="50" cy="25" rx="6" ry="20"/>')) +
    '<circle cx="50" cy="50" r="11" fill="var(--crest-bg,#fff)"/><circle cx="50" cy="50" r="8"/>',
  // 龟甲（内含花菱）
  kikko: () => {
    const pts = (r) => Array.from({ length: 6 }, (_, i) => polar(60 * i + 30, r).map((v) => v.toFixed(1)).join(',')).join(' ');
    return `<polygon points="${pts(44)}" fill="none" stroke="currentColor" stroke-width="6"/>` +
      `<polygon points="${pts(34)}" fill="none" stroke="currentColor" stroke-width="3"/>` +
      around(4, 0, (d) => rot(d, '<ellipse cx="50" cy="39" rx="6" ry="10"/>'));
  },
  // 六文钱
  rokumon: () => [24, 50, 76].flatMap((x) => [32, 68].map((y) =>
    `<circle cx="${x}" cy="${y}" r="11.5" fill="none" stroke="currentColor" stroke-width="5"/><rect x="${x - 4}" y="${y - 4}" width="8" height="8"/>`)).join(''),
  // 九曜
  kuyo: () => '<circle cx="50" cy="50" r="13"/>' + around(8, 32, (d, r) => {
    const [x, y] = polar(d, r);
    return `<circle cx="${x}" cy="${y}" r="9"/>`;
  }),
  // 二引两
  hikiryo: () => ring(42, 7) + '<rect x="12" y="34" width="76" height="11"/><rect x="12" y="55" width="76" height="11"/>',
  // 大中黑
  nakaguro: () => ring(42, 8) + '<rect x="10" y="38" width="80" height="24"/>',
  // 三鳞
  uroko: () => '<path d="M50 14 L71 50 L29 50Z"/><path d="M28 54 L49 90 L7 90Z"/><path d="M72 54 L93 90 L51 90Z"/>',
  // 井桁
  igeta: () => rot(45, '<rect x="34" y="12" width="9" height="76"/><rect x="57" y="12" width="9" height="76"/>' +
    '<rect x="12" y="34" width="76" height="9"/><rect x="12" y="57" width="76" height="9"/>'),
  // 卍
  manji: () => '<path d="M44 14h12v30h30v12H56v30H44V56H14V44h30Z"/>' +
    '<path d="M56 14h20v12H56Z M86 56v20H74V56Z M44 86H24V74h20Z M14 44V24h12v20Z"/>',
  // 月星
  tsukiboshi: () => '<path d="M58 14 A36 36 0 1 0 58 86 A30 30 0 1 1 58 14Z"/><circle cx="66" cy="50" r="9"/>',
  // 花菱
  hanabishi: () => around(4, 0, (d) => rot(d, '<path d="M50 48 C38 38 40 18 50 12 C60 18 62 38 50 48Z"/>')) +
    '<circle cx="50" cy="50" r="4" fill="var(--crest-bg,#fff)"/>',
  // 违鹰羽
  takanoha: () => [-28, 28].map((d) => rot(d,
    '<ellipse cx="50" cy="50" rx="11" ry="40"/><path d="M50 12 L50 90" stroke="var(--crest-bg,#fff)" stroke-width="2.5"/>')).join(''),
  // 五稜星（北辰）
  star: () => ring(45, 4) + `<polygon points="${Array.from({ length: 10 }, (_, i) =>
    polar(36 * i, i % 2 ? 15 : 36).map((v) => v.toFixed(1)).join(',')).join(' ')}"/>`,
  // 五本骨扇月丸
  ogi: () => '<path d="M50 86 L12.7 41.6 A58 58 0 0 1 87.3 41.6Z"/>' +
    [-26, -13, 0, 13, 26].map((d) =>
      `<line x1="50" y1="86" x2="50" y2="30" stroke="var(--crest-bg,#fff)" stroke-width="2" transform="rotate(${d} 50 86)"/>`).join('') +
    '<circle cx="50" cy="48" r="11" fill="var(--crest-bg,#fff)"/><circle cx="50" cy="48" r="8"/>',
};

export function crestSVG(code, cls = 'crest') {
  let body;
  if (code?.startsWith('char:')) {
    const ch = code.slice(5).replace(/[<>&]/g, '');
    body = ring(44, 4) + `<text x="50" y="52" text-anchor="middle" dominant-baseline="central" font-size="50" font-weight="900" font-family="'Noto Serif SC','Noto Serif JP',serif">${ch}</text>`;
  } else {
    body = (SHAPES[code] || SHAPES.tomoe)();
  }
  return `<svg class="${cls}" viewBox="0 0 100 100" fill="currentColor" aria-hidden="true">${body}</svg>`;
}

export const CREST_CODES = Object.keys(SHAPES);
