# 国家抽象（第 1 步）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让网站能按「当前地图」（`#map=…`）选择数据与本地存储，日本模式的行为、链接、存储键与现在完全一致。

**Architecture:** 新增 `src/js/country.js`，页面加载时（与语言一样）定下当前地图并导出配置；`store.js` 的数据路径与存储键、`i18n.js` 的地址片段、`app.js` 的探索计数改为读这份配置。切换地图走整页重载（与切换语言相同），不做运行时拆装。只登记 `japan` 一个地图——日本独有功能的开关等第 2 步有了半岛数据再按实际需要加，现在不预先抽象。

**Tech Stack:** 原生 ES Modules，无构建；测试为 `tools/check_data.py` + `tests/smoke.py`（Playwright）。

**Spec:** `docs/superpowers/specs/2026-11-01-korean-peninsula-design.md`（§3 模式切换、§4 目标、§7 第 1 步）

## Global Constraints

- 日本模式行为与现在完全一致（smoke 全过，截图无变化）。
- 深链接 `#map=korea`；不带 `map` 时为日本，现有链接全部照旧可用。
- 日本模式的 localStorage 键名不变（`je.visited`、`je.goshuin`、`je.ichinomiya`、`je.ui.*`），老用户的进度不能丢。
- 不引入构建工具；`sw.js` 的 `SHELL` 要覆盖全部 `src/js`，改动时 `VERSION` 加一（`je-v13` → `je-v14`）。

## Review Focus

1. 老链接 `#pref=26&lang=ja`：上次看的是别的地图也必须打开日本——Task 1 的 `pickMap` 规则 + Task 3 smoke 场景 `country`。
2. `#map=` 写了不存在的值（手打、旧版本链接）：退回日本，不报错——Task 3 场景 `country`。
3. 日本模式选县后地址栏不出现 `map=`（分享出去的链接与现在一模一样）——Task 3 场景 `country`。
4. 切换语言时 `map=` 不丢——Task 2 `setLang` 保留 `map`；smoke 场景 `country` 覆盖。
5. 老用户数据：日本模式仍读写 `je.visited`——Task 3 场景 `country` 检查键名。

---

### Task 1: `country.js` 与数据 / 存储路径

**Files:**
- Create: `src/js/country.js`
- Modify: `src/js/store.js`（路径与键名）
- Modify: `sw.js`（SHELL 加 `src/js/country.js`，`VERSION` → `je-v14`）

**Interfaces:**
- Produces（`country.js`）：
  - `export const MAPS = { japan: { key: 'japan', geo: 'src/assets/geojson/japan.json', data: 'src/data', units: 47, store: 'je.' } }`
  - `export function pickMap(hash: string, saved: string|null): string` —— 纯函数：`hash` 里 `map` 是已登记的键 → 用它；否则 `hash` 里有 `pref` → `'japan'`（老链接）；否则 `saved` 是已登记的键 → 用它；否则 `'japan'`。
  - `export const mapKey: string`（`pickMap(location.hash, 读 localStorage 'je.ui.map')`，并把结果写回 `je.ui.map`）
  - `export const MAP = MAPS[mapKey]`
- Produces（`store.js`）：`loadAll` / `loadFiles` / `loadProvinces` / `loadProvinceEras` 用 `MAP.geo`、`` `${MAP.data}/…` ``；`visited` / `goshuinBook` / `ichinomiya` 键名为 `` `${MAP.store}visited` `` 等（日本即原名）。`uiPref` 里 `filter`、`layer` 两项按地图分开（键 `` `${MAP.store}ui.${name}` ``），其余（lang、audio、tourDone、guideMode、split、hudFolded、kosekiName、map）全站共用、键名不变。`je.api` 不分。
- 注意循环依赖：`country.js` 不 import `store.js`，直接 try/catch 读 `localStorage`。

- [ ] **Step 1:** 写 `country.js`（含 `pickMap`，文件头注释说明规则与「切换走整页重载」）。
- [ ] **Step 2:** 改 `store.js`；`fetchJSON` 的所有 `src/data/…` 改为 `${MAP.data}/…`，`japan.json` 改为 `MAP.geo`。
- [ ] **Step 3:** 改 `sw.js`。
- [ ] **Step 4:** 运行 `python -X utf8 tools/check_data.py`，预期全部通过（SHELL 检查覆盖新文件）。
- [ ] **Step 5:** 浏览器验证 `pickMap`：起 `python -m http.server`，在页面控制台 `import('./src/js/country.js')` 依次断言
  `pickMap('', null)==='japan'`、`pickMap('#map=nope', null)==='japan'`、`pickMap('#pref=26&lang=ja', 'japan')==='japan'`、`pickMap('#map=japan&pref=3', null)==='japan'`。
  （第 2 步登记 korea 后补 `pickMap('#pref=26', 'korea')==='japan'` 与 `pickMap('', 'korea')==='korea'`——写进 Task 3 的 smoke 场景，用 evaluate 直接调 `pickMap`，不依赖已登记的值。）
- [ ] **Step 6:** Commit `Add a map registry; load data and storage keys through it`。

### Task 2: 地址片段与计数

**Files:**
- Modify: `src/js/i18n.js`（`stateHash`、`setLang`）
- Modify: `src/js/app.js:22-25`（`updateCounter`）

**Interfaces:**
- Consumes: `mapKey`, `MAP`（Task 1）
- Produces: `stateHash(prefId)` —— `mapKey !== 'japan'` 时在 `pref` 前加 `map=<key>`；日本输出与现在逐字相同（`#pref=26&lang=ja`）。`setLang` 改写地址栏的条件加上 `h.has('map')`。
- `updateCounter`：分母用 `MAP.units`（不改 index.html 静态文字）。

- [ ] **Step 1:** 改 `stateHash` / `setLang`。
- [ ] **Step 2:** 改 `updateCounter`。
- [ ] **Step 3:** Commit `Keep the map in links and language switches`。

### Task 3: smoke 场景 `country` + 全量回归

**Files:**
- Modify: `tests/smoke.py`（新方法 `country`；`plan()` 中文全跑列表加 `('country', 'map=nope&pref=26', ['country', 'deeplink'])`）
- Modify: `CLAUDE.md`（技术架构「深链接」与目录结构加 `country.js` 一行；本地存储一节写明 `filter` / `layer` 按地图分开、`je.ui.map`）

- [ ] **Step 1: 写场景**

```python
def country(self, page):
    # #map=nope 退回日本，并且日本模式的链接里不出现 map=
    assert page.evaluate("import('./src/js/country.js').then((m) => m.mapKey)") == 'japan'
    assert 'map=' not in page.evaluate('location.hash'), '日本模式的地址栏不应带 map='
    # 规则本身（不依赖已登记哪些地图）
    rules = page.evaluate("""import('./src/js/country.js').then(({ pickMap: p }) => [
        p('', null), p('#map=nope', null), p('#pref=26&lang=ja', 'japan'), p('#pref=26', 'nope')])""")
    assert rules == ['japan'] * 4, f'pickMap 结果 {rules}'
    # 老用户数据键名不变
    assert page.evaluate("JSON.parse(localStorage.getItem('je.visited') || '[]').includes(26)"), '日本模式应写入 je.visited'
```

- [ ] **Step 2:** 运行 `SMOKE_ONLY='country' python -X utf8 tests/smoke.py`，预期 Task 1–2 完成后 ✓ 三个尺寸。
- [ ] **Step 3:** 全量回归：`python -X utf8 tools/check_data.py` 与 `python -X utf8 tests/smoke.py`（不设 PW_CHANNEL，用 Playwright 自带 Chromium，与 CI 一致），预期 0 失败。
- [ ] **Step 4:** 截图对比：改动前在 HEAD 跑一次 `python -X utf8 tools/make_screens.py`，把 `docs/screen-*.jpg` 复制到 scratchpad 作基准，改完再跑一次逐张比较（允许 JPEG 噪声级差异），然后 `git checkout docs/screen-*.jpg`，不提交截图。
- [ ] **Step 5:** 更新 CLAUDE.md，Commit `Smoke test for map selection; document it`。推送前问用户。
