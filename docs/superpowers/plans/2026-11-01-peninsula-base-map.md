# 朝鲜半岛底图（第 2a 步）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 顶栏可在「日本 / 朝鲜半岛」间切换；半岛模式显示南北 29 个一级行政区（现行区划）、军事分界线、独岛 / 竹岛与「日本海 / 东海」标注，点选后出简版详卡（三种名称写法、人口、面积），换丹青配色。

**Architecture:** 半岛模式用同一个 index.html 外壳，入口 `app.js` 发现 `mapKey === 'korea'` 时改载 `src/js/korea.js`，日本的代码路径一行不动。两边共用的外壳函数（标签页、设置、声音、拖动条、语言切换、提示）先从 app.js 原样搬到 `src/js/shell.js`。半岛数据由 `tools/build_korea_geo.py` 从 geoBoundaries + Wikidata 生成 `src/data/korea/regions.json`。日本独有的按钮与工具条在 `:root[data-map="korea"]` 下用 CSS 隐藏。

**Tech Stack:** 原生 ES Modules + ECharts 5.5.1（已随站发布）；Python 3 + shapely（仅生成数据）。

**Spec:** `docs/superpowers/specs/2026-11-01-korean-peninsula-design.md`（§2、§3、§5、§6.1–6.2、§7 第 2 步）

## Global Constraints

- 模式名：朝鲜半岛 / Korean Peninsula / 朝鮮半島；不得只叫「韩国」。
- 界面只有中英日；地名写「当前语言的名称 / 한글 / 罗马字」。
- 争议标注固定顺序、两种模式一致：岛「独岛 / 竹岛（有争议）」，海「日本海 / 东海」；岛不涂任一方颜色；南北之间的线叫「军事分界线」，不叫国界。
- 不用太极旗、朝鲜国旗、任一方国徽元素。只换皮，布局与操作不变。
- 日本模式行为不变：现有 smoke 全过。
- 现行区划（2026-11，已用韩文维基核实）：南 16（2026-07-01 光州 + 全南合并为全南光州统合特别市；军威郡 2023 年起属大邱）；北 13（平壤直辖市、罗先 / 南浦 / 开城 3 特别市、9 道；开城含 2023 年并入的长丰郡）。
- 数据只要求署名：geoBoundaries KOR ADM2（CC BY 3.0）、KOR ADM1（公有领域）、PRK ADM1/ADM2（CC BY 3.0 IGO）、Wikidata（CC0）。登记进 LICENSE-CONTENT.md 并在图例 / 设置底部注明。

## Review Focus

1. 老链接 / 日本链接在用户上次看过半岛后仍打开日本（`#pref=26` 无 `map`）——Task 3 smoke `korea_switch` 断言。
2. 半岛链接里的 `pref` 编号不能被日本代码当成日本县（`#map=korea&pref=26`）——Task 4 `korea.js` 自己解析，smoke `korea` 用越界编号断言不报错。
3. 手机 390 宽下半岛顶栏（多了地图开关）不横向溢出——Task 3 smoke 跑 `no_overflow`（三个尺寸、三种语言）。
4. 南北边界与海岸：南北面之间无重叠无缝隙（构建脚本断言），点分界线附近不会选不到区——Task 1 断言。
5. 独岛 / 竹岛在两种语言里两个名字都出现且顺序固定——Task 4 smoke `korea_dispute` 三语断言。

---

### Task 1: 构建脚本 `tools/build_korea_geo.py` → `src/data/korea/regions.json`

**Files:** Create `tools/build_korea_geo.py`, `src/data/korea/regions.json`（生成物，提交）

**Interfaces — Produces** `regions.json`：
```jsonc
{
  "type": "FeatureCollection",
  "features": [{ "type": "Feature", "geometry": {…}, "properties": {
    "id": 1,                     // 1–16 南（官方顺序：首尔→…→济州），17–29 北（平壤→…→两江）
    "name": "서울특별시",          // ECharts 区域名 = 한글全称（唯一）
    "side": "south",             // south | north
    "zh": "首尔特别市", "ja": "ソウル特別市", "en": "Seoul", "rr": "Seoul-teukbyeolsi",
    "wd": "Q8684", "pop": 9668465, "pop_year": 2020, "area": 605.25,
    "note": null                 // 可选，如开城人口不含长丰郡（各语言 {zh,en,ja}）
  } }],
  "mdl": [[lon, lat], …],         // 军事分界线：南北面共有边（折线）
  "dokdo": { "coords": [131.8686, 37.2414], "wd": "Q39934" }
}
```

- 名称表 `UNITS`（29 行，手写 hangul / zh / ja / en / rr / 所含 ADM1 或 ADM2 名）在脚本里；运行时取 Wikidata ko 标签、人口（取时间最新的 P1082 + P585）、面积 P2046，**hangul 与 ko 标签不一致即报错退出**（核验）。全南光州统合特别市取 Q138870299。
- 几何：南 = KOR ADM2 按与 KOR ADM1 的最大交叠归属，再：光州 + 全南 → 合并单元；`Gunwi-gun` → 大邱。北 = PRK ADM2 按 PRK ADM1 归属，再：`Rason City` → 罗先；`Kaesong City` + `Jangphung` → 开城。与南重叠的部分从北侧裁掉；南北之间 >0 的缝隙并入相邻面积较大一侧。全部单元一起 `shapely.coverage_simplify`（容差与 build_provinces.py 同量级），坐标保留 3 位小数。
- 断言：29 个单元（南 16、北 13）；任两单元交叠面积 < 0.5 km²；`mdl` 折线西端经度 < 126.7、东端 > 128.3；文件 < 600 KB。
- 下载缓存到 `.cache/korea/`（已在 .gitignore 的 `.cache` 下）。

- [ ] Step 1: 写脚本，跑 `python -X utf8 tools/build_korea_geo.py`，预期打印 29 行（id、hangul、pop、area）且断言全过。
- [ ] Step 2: 用 headless 截一张 regions.json 的 ECharts 渲染图目检（南北各自着色、分界线连续、济州 / 郁陵岛在）。
- [ ] Step 3: Commit `Peninsula regions from geoBoundaries and Wikidata`。

### Task 2: 外壳函数搬到 `src/js/shell.js`（纯搬移）

**Files:** Create `src/js/shell.js`; Modify `src/js/app.js`、`sw.js`（SHELL 加 shell.js / korea.js，VERSION → `je-v15`）

**Interfaces — Produces** `shell.js` 导出（签名与 app.js 现有函数完全相同）：`NARROW`, `SHORT`, `setupTabs(onShowMap, onShowDetail)`, `legacyCopy(text)`, `toast(msg)`, `setupSettings(guide, onResetVisited, onTour)`, `setupSound()`, `setupSplitter(onResize)`, `setupLangSwitch()`。

- [ ] Step 1: 搬移，app.js 改为 import。
- [ ] Step 2: `python -X utf8 tools/check_data.py` + `SMOKE_ONLY='desktop zh|phone   zh' python -X utf8 tests/smoke.py`，预期全过。
- [ ] Step 3: Commit `Move shared shell helpers out of app.js`。

### Task 3: 地图开关 + 登记 korea

**Files:** Modify `src/js/country.js`（`MAPS.korea = { key: 'korea', geo: 'src/data/korea/regions.json', data: 'src/data/korea', units: 29, store: 'je.korea.' }`，新增 `setMap(key)`：地址栏改为 `#map=<key>`（保留 lang）后 reload）；`index.html`（顶栏 `#map-switch` radiogroup，在 lang-switch 左边）；`src/js/shell.js`（`setupMapSwitch()`）；`src/js/app.js`（开头设 `document.documentElement.dataset.map = mapKey`；`mapKey === 'korea'` 时 `import('./korea.js')` 并 `return`）；`src/js/i18n.js`（词条 `map.japan` / `map.korea` / `map.aria`）；`src/css/style.css`。

- [ ] Step 1: smoke 场景 `korea_switch`（中文三尺寸 + 英日 desktop）：日本页点 `#map-switch [data-map="korea"]` → 等 `#loading.hidden` → `location.hash` 含 `map=korea`、`document.documentElement.dataset.map === 'korea'`；再打开 `#pref=26`（无 map）→ 详卡标题仍是京都府；`no_overflow`。先跑看它失败。
- [ ] Step 2: 实现到 Step 1 通过（korea.js 此时可以只是空壳：隐藏 loading）。
- [ ] Step 3: Commit `Map switch in the top bar`。

### Task 4: `src/js/korea.js` 半岛模式

**Files:** Create `src/js/korea.js`；Modify `src/js/i18n.js`（`kr.*` 词条三语）、`src/js/detail.js`（`legalHTML` 按地图出不同出处）、`src/css/style.css`

**Interfaces — Consumes:** shell.js 全部导出；`MAP`、`stateHash`、`t`、`lang`、`esc`、`visited`（store 已按 MAP 分键）。
**Produces:** `export async function main()`。

行为：
- 载入 regions.json，`echarts.registerMap('korea', geo)`；默认视角框住半岛 + 独岛；按探索进度着色（同日本「探索进度」三色），南北同一套颜色。
- `mdl` 画虚线（`lines`，不可点），中点标「军事分界线 / Military Demarcation Line / 軍事境界線」。
- 独岛：小圆点（不着任一方颜色，用中性灰描边），标签 `t('kr.dokdo')` = 「独岛 / 竹岛（有争议）」/「Dokdo / Takeshima (disputed)」/「独島 / 竹島（係争中）」；点击弹 `.muni-card`：韩国实际管辖、日本主张领有（岛根县隐岐之岛町）、韩方主张；不下结论。海名标签 `t('kr.sea')` =「日本海 / 东海」/「Sea of Japan / East Sea」/「日本海 / 東海」，放在约 [131.0, 39.6]。
- 点区 → `visited.add`、计数（分母 29）、地址栏 `stateHash(id)`、详卡：标题当前语言名、副行 한글 · 罗马字、所属（`kr.side.south` = 大韩民国 / Republic of Korea / 大韓民国；`kr.side.north` = 朝鲜民主主义人民共和国 / Democratic People's Republic of Korea / 朝鮮民主主義人民共和国）、人口（年份）、面积、`note`、底部「更多内容整理中」。
- 深链接 `#map=korea&pref=N`：N 在 1–29 才选中。
- 向导区：显示一条固定说明（`kr.guide.soon`），输入框禁用。
- 隐藏：合战、御朱印帐、图层 / 滤镜工具条、时代滑块、搜索、定位按钮（CSS）。
- 图例：探索进度 + 出处一行（geoBoundaries / Wikidata）。

- [ ] Step 1: smoke 场景 `korea`（中英日 × 三尺寸）：`map=korea&pref=1` → 详卡标题中文「首尔特别市」/英「Seoul」/日「ソウル特別市」且含「서울특별시」；`map=korea&pref=99` 不报错且无详卡；`no_overflow`。`korea_dispute`（三语 desktop + 中文 phone）：图上点独岛（`convertToPixel` + `#map` 偏移）→ 卡片文字含两个名字。先跑看失败。
- [ ] Step 2: 实现至通过。
- [ ] Step 3: Commit `Korean Peninsula mode: regions, readings, disputed labels`。

### Task 5: 丹青皮肤

**Files:** Modify `src/css/style.css`（`:root[data-map="korea"]` 覆盖 token：底色偏青灰、强调色 丹青绿 + 朱红 + 石黄，探索三色换成五方色系；韩纸质感用纯 CSS 细纹渐变，不加图片）

- [ ] Step 1: 截图（desktop / phone，zh）目检两种模式；对照对比度：正文对底色 ≥ 4.5:1（用脚本算）。
- [ ] Step 2: 全量 `python -X utf8 tests/smoke.py`（不设 PW_CHANNEL）预期 0 失败；`check_data` 通过。
- [ ] Step 3: 更新 CLAUDE.md（半岛模式一节、regions.json schema、构建命令、smoke 新场景）、LICENSE-CONTENT.md 第三方表；Commit `Dancheong skin for the peninsula; docs`。
