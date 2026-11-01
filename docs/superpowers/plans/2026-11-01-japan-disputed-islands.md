# 日本模式的争议地区（第 2b 步）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 日本模式里竹岛与北方四岛不再涂成岛根县 / 北海道的颜色：画成中性灰，标两个名字（实际管辖方的叫法在前，括注有争议），点开列出双方立场。

**Architecture:** 数据文件不动（历代旧国底图保持历史原貌：1869 年千岛国确含国后、择捉）。新增 `src/js/disputed.js`：争议区的外框、`splitDisputed(geo)`（把中心落在外框里的多边形从县 / 市町村要素里拆出）、`disputedAt(pt)`、`disputeCard(key)`。全国地图（app.js → map.js）与市区町村下钻（muni.js）在注册地图前拆分；半岛模式的独岛卡片也改用同一个 `disputeCard`。

**Spec:** `docs/superpowers/specs/2026-11-01-korean-peninsula-design.md` §3、§8

## Global Constraints

- 名字顺序固定（与半岛模式一致）：竹岛写「独岛 / 竹岛（有争议）」；北方四岛写「南千岛群岛 / 北方领土（有争议）」/ "Southern Kurils / Northern Territories (disputed)" /「南クリル諸島 / 北方領土（係争中）」。
- 不涂任一方颜色；卡片只列双方立场（出处：维基百科），不作判断。
- 旧国底图（五畿七道、古国国力、古国巡礼、时间轴）不叠争议层，保持历史边界。
- 日本模式其余行为不变：现有 smoke 全过。

## Review Focus

1. 拆分不能误伤：根室半岛（纳沙布岬 145.80, 43.385）、根室市区、野付半岛外的小岛仍属北海道——Task 1 断言。
2. 点国后岛不应选中北海道，而是弹争议卡——Task 2 smoke。
3. 定位落在国后岛：不说「似乎不在日本」，弹争议卡——Task 2 smoke。
4. 北海道市区町村下钻：齿舞群岛拆成灰色单独一块，六个村标为争议地区；标题里的市町村数不变——Task 3 smoke。
5. 半岛模式的独岛卡片内容不变——`korea_dispute` 照旧通过。

---

### Task 1: `src/js/disputed.js`

- `DISPUTED = { takeshima: { area: [[131.80,37.20],[131.80,37.30],[131.95,37.30],[131.95,37.20]], label: [131.8667, 37.2417], point: true, card: 'kr.dokdo', rows: ['where','now','kr','jp'] }, kurils: { area: [[145.84,43.30],[145.84,43.55],[145.38,43.62],[145.38,44.62],[149.3,45.9],[149.3,43.3]], label: [147.25, 44.2], card: 'dsp.kurils', rows: ['where','now','ru','jp'] } }`
- `splitDisputed(geo) -> { geo, parts: { key: [polygon…] } }`（不改入参；要素的多边形全被拆走时保留原要素、加 `properties.disputed = key`）。
- `disputedAt([lon, lat]) -> key | null`；`disputeLabel(key)`；`disputeCard(key)`（含 `data-act="card-close"` 关闭钮）。
- i18n：`dsp.kurils*` 三语、`dsp.kicker`、`dsp.note`。
- smoke 场景 `disputed_split`：在页面里 import 后对 japan.json 断言（北海道不含国后 [145.95,44.05]、择捉 [147.9,45.0]、色丹 [146.75,43.82]、齿舞水晶岛 [145.91,43.44]；含纳沙布 [145.80,43.385]、根室 [145.58,43.33]、野付 [145.32,43.57] 附近小岛不被拆；岛根不含竹岛）。

### Task 2: 全国地图与定位

- map.js：`createMap(..., { disputed, onDispute })`，系列 `disputed`（custom，灰色半透明填充 + 虚线框，可点）与 `disputed-names`（标签；竹岛另画空心圆点）；旧国底图或合战时不画。
- app.js：注册前 `splitDisputed(data.geo)`；`onDispute` → `#art-card` 显示 `disputeCard`；定位不在任何县但 `disputedAt` 命中时弹同一张卡。
- smoke `disputed_jp`（中文三尺寸 + 英日 desktop）：点竹岛圆点 → 卡片两个名字顺序对；点国后岛中部 → 卡片含「北方领土」且详卡没换成北海道；`locate` 变体：模拟定位国后岛 → 弹卡。

### Task 3: 市区町村下钻

- muni.js `load()`：`splitDisputed` 后，被拆出的多边形组成伪要素 `code: 'dsp-<key>'`、`disputed: key`；全被拆走的六村带 `disputed`。着色灰、不计入图例与标题的数量；点伪要素弹争议卡（下钻自己的 `.muni-card`），点六村时信息卡多一行「有争议（见…）」。
- smoke `disputed_muni`：`pref=1&muni=1` → 存在 `dsp-kurils` 区域且为灰；`#pref=32&muni=1` 存在 `dsp-takeshima`。

收尾：全量 smoke、check_data，CLAUDE.md（争议地区一节、新场景），提交。
