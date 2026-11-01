# Japan Explorer · 日本47都道府县古今变迁图鉴

交互式历史地图应用：在日本全图上点选任一都道府县，查看其古代令制国沿革、历史时间轴、名胜物产、方言与地缘梗；用「时空滤镜」看五畿七道、战国势力、幕末阵营；打卡收集御朱印；拖动「时空穿越滑块」看九个时代的版图与政权中枢；在「合战演武」沙盘上回放经典战役；切换「拉面 / 地酒」风土图层；并与「AI 历史向导」对话（博学史官 ⇄ 名将附体 / 合战名将）。

## 技术架构

- 原生 HTML5 + CSS3 + 原生 ES Modules，无构建工具、无 npm 依赖，纯静态运行。
- 地图：Apache ECharts 5.5.1，**随站点发布在 `src/vendor/echarts.min.js`**（附 LICENSE/NOTICE），不走 CDN——jsdelivr 在国内常挂起，同步脚本会让整页卡住（smoke 测试的 china 场景会屏蔽外部 CDN 检查这一点）。用 `echarts.registerMap` 注册本地 GeoJSON。
- 字体：Google Fonts 以 `display=optional` 非阻塞加载（没能马上就绪就整页用系统字体，不中途替换导致排版跳动）；`--serif` / `--sans` 带各系统中文字体回退。
- 深链接：`index.html#pref=26&lang=ja` 直接打开对应地区并指定语言；`&muni=1&m=23211` 打开市区町村地图并选中（政令市整市为各区代码以 `.` 连接）（`lang` 可省略；链接里的语言优先于本地设置并会被记住）。选中地区时地址栏自动写成这种形式，详卡「分享」按钮复制/分享的就是它。
- **数据打包（改数据后必做）**：`python tools/build_bundle.py` 把每种语言的 47 县 + 合战/时代数据合并成 `src/data/bundle/{zh,en,ja}.json`（每种语言 1 个请求）。前端优先读 bundle，读不到才回退为逐个文件加载——所以**改了 JSON 却忘记重新打包，线上会继续显示旧内容**。
- PWA：`manifest.webmanifest` + `sw.js`（本站文件网络优先、CDN 库与字体缓存优先，只缓存 GET）。改动应用外壳文件列表（`SHELL`）时把 `VERSION` 加一。图标在 `src/assets/icons/`，分享卡片封面 `src/assets/og-cover.png`（1200×630）。
- 必须通过 HTTP 服务器访问（`fetch` 读取 JSON），不能直接双击 `file://` 打开：
  - `python3 -m http.server 8000`（Windows 用 `python`）或 `npx serve .`
- 浏览器本地存储（`localStorage`）：
  - `je.visited` — 已探索的都道府县 id 数组
  - `je.api` — LLM 接口配置 `{provider, baseUrl, model, apiKey}`（仅存于用户浏览器）
  - `je.goshuin` — 御朱印 `{ [id]: 盖印时间 ISO }`
  - `je.ui.filter` / `je.ui.guideMode` / `je.ui.split` / `je.ui.layer` — 当前滤镜、向导模式（scholar|hero）、右侧上下比例（%）、风土图层（history|ramen|sake）
  - `je.ui.audio` — 声音 `{muted, bgm, bgmVol, sfxVol}`（默认音效开、背景音乐关）

## 目录结构

```
index.html                     入口
src/css/style.css              全部样式（设计 token 定义于 :root）
src/js/app.js                  入口模块：加载数据、协调各模块
src/js/store.js                数据加载 + localStorage 读写
src/js/map.js                  ECharts 地图（geo 坐标系）+ 时空滤镜 FILTERS + 风土图层 LAYERS + 时代/合战叠加层
src/js/detail.js               右上：地区风土与历史详卡
src/js/guide.js                右下：AI 案内人（史官/名将双模式、快捷提问、离线解答、LLM 流式调用）
src/js/goshuin.js              御朱印帐弹窗（47 格、按地方筛选）
src/js/crests.js               家纹/神纹 SVG 印纹库（crestSVG(code)）
src/js/audio.js                和风音频单例：Web Audio 合成音效与背景音乐（可选 mp3 见 src/assets/audio/）
src/assets/geojson/japan.json  47 都道府县 GeoJSON（properties: id, name, nam, nam_ja；name = 规范汉字全称如「京都府」，须与县数据 name.kanji 及 ECharts series.data.name 严格一致）
src/data/index.json            47 县清单（id, slug, file, kanji, zh, region）
src/data/historical_events.json  全国共享：timeline_eras（9 个时代）+ historic_battles（5 场合战）
src/data/prefectures/NN_slug.json  各县数据（01_hokkaido … 47_okinawa）
src/data/provinces.json        68 令制国真实边界 + 县界线（tools/build_provinces.py 由市区町村合并生成）
src/data/province_eras.json    古国演变时间轴：712 / 757 / 1869 年与 824 年的差异（remove + add）
src/data/hiroshige.json        广重《六十余州名所图会》69 幅（tools/fetch_hiroshige.py 生成；图片在 src/assets/hiroshige/NN.jpg）
src/js/hiroshige.js            古国地图上的作品卡、详卡「广重笔下」、大图浏览
src/data/province_names.json   「国名今犹在」：旧国 → 今天仍带国名的东西（tools/province_names_tool.py 核验）
src/js/provnames.js            国名标签：古国悬停提示、古国卡片、详卡
src/js/locate.js               「我在哪」：浏览器定位 → 县（map.prefAt）→ 市区町村（该县的 municipalities 文件）→ 结果卡片
```

## 核心模型：现代 47 都道府县 ⇄ 古代 68 令制国

- 令制国按「五畿七道」归属：畿内、东海道、东山道、北陆道、山阴道、山阳道、南海道、西海道（共 66 国 2 岛 = 68）。
- 一县可对应多国（爱知 = 尾张 + 三河；兵库 = 摄津西部 + 播磨 + 但马 + 丹波西部 + 淡路），一国也可被多县分割（摄津分属大阪/兵库，肥前分属佐贺/长崎）。
- 令制外地区：北海道（虾夷地）、冲绳（琉球王国），`circuit` 记为 `令制外`。
- 时代主轴：律令 → 镰仓 → 室町 → 战国 → 江户（藩）→ 近现代（废藩置县 1871 及其后的县域合并）。

## Prefecture Schema

```jsonc
{
  "id": 26,                         // 1~47，与 GeoJSON properties.id 一致
  "slug": "kyoto",
  "name": { "kanji": "京都府", "kana": "きょうとふ", "romaji": "Kyoto", "zh": "京都府" },
  "region": "近畿",                 // 北海道/东北/关东/中部/近畿/中国/四国/九州·冲绳
  "capital": "京都市",
  "badge": { "icon": "🌸", "title": "千年王城" },
  "stats": { "population_k": 2578, "area_km2": 4612, "source": "2020年国势调查（约数）" },
  "historical_lineage": {
    "ritsuryo_provinces": [ {
      "name": "丹波国", "kana": "たんば", "circuit": "山阴道", "portion": "东部（桑田·船井·何鹿·天田）",
      "cross_prefectures": ["兵库县"] // 跨界归属：同一令制国今亦属的其他县（中文名），无则为 []
    } ],
    "sengoku_daimyo": [ "…" ],
    "edo_domains": [ "…" ],
    "meiji_transition": { "summary": "…", "boundary_note": "古界线与今县界的差异" }
  },
  "history_timeline": [             // 固定 6 段，顺序不变；代码按 era 名查找，不要按下标取
    { "era": "律令", "period": "7–12世纪", "title": "…", "summary": "…" },
    { "era": "镰仓", "period": "1185–1333", "title": "…", "summary": "…" },
    { "era": "室町", "period": "1336–1467", "title": "…", "summary": "…" },
    { "era": "战国", "period": "1467–1590", "title": "…", "summary": "…" },
    { "era": "江户", "period": "1603–1868", "title": "…", "summary": "…" },
    { "era": "近现代", "period": "1868–", "title": "…", "summary": "…" }
  ],
  "landmarks":   [ { "name": "…", "note": "…" } ],
  "specialties": [ { "name": "…", "note": "…" } ],
  "dialect": {
    "name": "京言葉",
    "features": "发音与文化特征说明",
    "phrases": [ { "phrase": "おいでやす", "meaning": "欢迎光临", "note": "" } ]  // 第一条作为问候语
  },
  "guide": { "persona": "kinki", "opening": "该县专属开场白" },   // 博学史官模式
  "regional_meme": [                // 地缘梗 / 文化偏见（2 条，轻松向）
    { "title": "京都人的“上次战争”", "text": "…" }
  ],
  "goshuin": {                      // 御朱印
    "title": "千年王城",              // 题字（4 字左右）
    "crest_name": "十六八重表菊（皇室）",
    "crest_icon": "kiku"             // crests.js 中的印纹代号；"char:X" 表示以单字作印
  },
  "hero_persona": {                 // 名将附体模式
    "name": "明智光秀", "title": "本能寺之变的谋叛者", "self": "吾",   // self = 第一人称自称（扩展字段）
    "opening_line": "…", "tone_prompt": "口吻与注意事项，会写入 System Prompt"
  },
  "map_filters": {                  // 时空滤镜分类键（扩展字段）
    "sengoku_1572": "oda",           // 战国势力，见 map.js FILTERS.sengoku.cats
    "bakumatsu": "shinseifu"         // 幕末阵营：satcho/shinseifu/sabaku/tenryo/outside
  },
  "ramen": {                        // 在地拉面
    "style_name": "京都背脂酱油拉面", "broth": "酱油（鸡骨猪骨＋背脂）", "noodles": "细直面",
    "toppings": "九条葱、叉烧、背脂",  // 扩展字段：解构图的浇头层
    "highlight": "一句话风味特色",
    "category": "shoyu"              // 扩展字段：着色用 tonkotsu/shoyu/miso/shio/other
  },
  "sake": {                         // 代表地酒（烧酎/泡盛产地以其代表）
    "brand": "月桂冠", "brewery": "月桂冠（伏见）", "taste_profile": "淡丽甘口：……",
    "quadrant": "tanrei_amakuchi",   // 扩展字段：nojun_karakuchi/tanrei_karakuchi/nojun_amakuchi/tanrei_amakuchi/shochu
    "famous": true                   // 扩展字段：地图上显示酒樽徽记
  }
}
```

不包含 quiz 字段（小测验模块已移除）。

## AI 案内人（时空案内人）

- 两种模式（`personaFor(p, mode)` 统一产出身份对象）：
  - **博学史官**（scholar，默认）：身份按地区切换（`guide.persona` 键），定义在 `src/js/guide.js` 的 `PERSONAS`；
  - **名将附体**（hero）：换为该县 `hero_persona`（头像取名字首字、朱红），System Prompt 改为第一人称扮演，并要求不美化暴行、争议史实保持客观。

博学史官身份表：

| persona | 身份 | 自称 | 风格 |
|---|---|---|---|
| hokkaido | 雪原旅人·白枭 | 在下 | 沉静、北国旷野感 |
| tohoku | 行脚僧·云水 | 贫僧 | 温厚禅意，称用户“施主” |
| kanto | 浮世绘猫客·招福 | 咱 | 俏皮江户町人腔，偶尔“喵” |
| chubu | 战国忍者·风间 | 在下 | 干练，熟知兵法诸侯 |
| kinki | 平安女官·紫苑 | 妾身 | 典雅含蓄，偶引和歌 |
| chugoku | 出云语部·老翁 | 老朽 | 庄重博学，从神话讲到史实 |
| shikoku | 遍路旅人·空行 | 我 | 亲切口语，像同行旅伴 |
| kyushu | 兰学通词·兰斋 | 鄙人 | 开明好奇，熟悉海外交流 |
| okinawa | 琉球祝女·真加户 | 我（わん） | 温柔开朗，夹带琉球语 |

- **上下文联动**：用户每切换一个地区，向导立即换人设并以该县完整 JSON（令制国演变、沿革、方言等）重建 System Prompt；对话历史随之重置。
- **System Prompt 规范**（见 `buildSystemPrompt`）：
  1. 角色设定：身份、自称、口吻；用中文回答，可点缀日语原词并注假名。
  2. 注入当前地区 JSON 作为「史料」，回答优先依据史料；史料外的内容需标明“据传/一说”，不得编造年份与人名。
  3. 回答简洁（约 150–300 字），多用具体年份、人物、地名。
- **快捷提问**：每县 3 个（战国时这里战况如何？/ 用当地方言和我打声招呼 / 古今界线）。
- **无 API Key**：快捷提问与关键词匹配的自由提问（含“地缘梗”）由本地数据以当前角色第一人称拼出，打字机效果输出，并提示可接入 API 解锁自由对话。
- **有 API Key**：流式调用 —
  - OpenAI 兼容：`POST {baseUrl}/chat/completions`，`stream: true`，解析 SSE `choices[0].delta.content`。
  - Claude：`POST https://api.anthropic.com/v1/messages`，带 `anthropic-dangerous-direct-browser-access: true`，解析 `content_block_delta`。
  - Gemini 原生：`POST {baseUrl}/models/{model}:streamGenerateContent?alt=sse`，Key 放 `x-goog-api-key`（支持新式「AQ.」Key；OpenAI 兼容端点强制要 `Authorization`，AQ Key 在那里会报 ACCESS_TOKEN_TYPE_UNSUPPORTED），解析 `candidates[0].content.parts[].text`，跳过 `thought` 部分。

## 多语言（中文 / English / 日本語）

- `src/js/i18n.js`：语言在页面加载时确定（`je.ui.lang` > 浏览器语言：ja→日语、en→英语、其余中文），切换语言会重新载入页面（保留 `#pref`）。
- 界面文字：`t(key, vars)` 查词典 `D`；静态 HTML 用 `data-i18n` / `data-i18n-ph` / `data-i18n-title` / `data-i18n-aria`，由 `applyStatic()` 填充。
- **分类键不翻译**：`region`、`circuit`、`history_timeline[].era`、`ramen.category`、`sake.quadrant`、`map_filters.*` 等是逻辑键，显示时用 `label(group, key)` 转换。
- 数据翻译是**覆盖层**：`src/data/i18n/{en,ja}/prefectures/NN_slug.json` 与 `historical_events.json` 只含文字字段，按 `deepMerge` 叠加到中文底本（对象逐键、对象数组按下标、字符串数组整体替换）。
- `src/data/i18n/manifest.json` 记录各语言已翻译的县 id 与 events；未列入的县显示中文并带“翻译中”提示（不发请求，避免 404）。
- 向导：史官人设的译文在 `PERSONA_TEXT`；System Prompt 的角色段与回答规则按语言生成（`ROLE` / `PROMPT_RULES`），离线解答模板与关键词正则也在词典里。
- 日语界面通过 `:root[lang="ja"]` 切换到 Noto Sans/Serif JP 以显示日文字形。

## 设计规范

- 雅致和风 × 深色科技仪表盘：底色 `#18181c`，朱红 `#c23531`（选中/强调），青金 `#d4a373`（已探索/次强调）。
- 布局：顶栏 + 左 58% 地图 + 右 42%（上：详卡，下：向导，中间拖动条可调比例 20–80%）；窄屏改为上下堆叠。
- 响应式断点：≤900px（及高 ≤520px 的横屏）改为底部标签栏三页切换（`body[data-tab]` = map | detail | guide，见 `setupTabs`）：地图 / 详卡 / 向导各占满顶栏与标签栏之间，不整页滚动；选县时留在地图页，「详情」标签显示县名并闪一下；打开下钻或合战切到地图页；名将解说的「提问」切到向导页；不带 muni 的县链接直接打开详情页。横屏另有一组压缩样式（顶栏一行、标签栏横排）。≤560px 为手机：顶栏两行、按钮只留图标、时代刻度换成当前时代名、快捷提问单行横滑、合战面板默认折叠、地图用 `MOBILE_VIEW` 放大视角。改界面后用 390×844 尺寸截图检查。
- 刘海屏安全区域：页面用 `viewport-fit=cover`，四周边距统一走 `--safe-t/r/b/l` 变量（取自 `env(safe-area-inset-*)`），弹窗高度用 `--vh`（支持时为 `100dvh`）。新增贴边或 `position: fixed` 的元素时要加上对应的安全区域边距。测试时可在页面里覆盖这些变量模拟 iPhone（竖屏 上 47 / 下 34，横屏 左右 47 / 下 21）。横屏手机（高 ≤520px）同样走上下堆叠布局。

## 时空滤镜

| 模式 | 分类依据 |
|---|---|
| 探索进度 | 未探索 / 已探索 / 当前 |
| 现代区划 | `region` 八地方 |
| 五畿七道 | **底图换成 68 令制国真实边界**（`provinces.json`，首次选该滤镜时才下载），按旧国的 `circuit` 着色；加载失败时退回按县内首个令制国着色 |
| 战国势力 | `map_filters.sengoku_1572`：固定 **1572 年（元龟三年）信玄西上前夕** 的县内主导势力 |
| 幕末阵营 | `map_filters.bakumatsu`：戊辰战争时县内主导势力立场（萨长土肥 / 新政府方 / 佐幕方 / 天领直辖） |

一县多藩、势力交错时只能取主导势力，属近似表达；切换只改 `geo.regions[].itemStyle`，不重载 GeoJSON。

### 令制国底图（五畿七道）

- `python -X utf8 tools/build_provinces.py`（需 `pip install shapely`，仅生成时用）：市区町村先按「旧国 × 县」合并成小块，**一起** `coverage_simplify`，再拼出旧国与县界——两套边界由同一批边组成，叠加时完全对齐。跨两国的市町村整块归 `province`（主要一方），国界是近似。改了市区町村数据或 `province_overrides.json` 后重跑；`check_data` 会核对 68 国与市区町村里出现的旧国一致。
- 输出：`features`（`key` 日文国名、`zh/ja/en`、`kana`、`circuit`、`prefs` 今属县 id；`key: "-"` 为奄美·小笠原等令制外）+ `pref_borders`（只含陆上县与县交界的折线，不含海岸线）。
- 前端（map.js）：`setProvinces(g)` 注册第二张底图 `provinces`；`provMode()`（历史图层 + 五畿七道 + 非时代 / 非合战）时 geo 换图，叠加 `provnames`（按面积排序的国名，`hideOverlap`）、`prefborders`（虚线县界）、`prefactive`（选中县轮廓，取自 japan.json）。两张底图共用 `boundingCoords`（japan.json 的范围），换图时比例与位置不变。点击时按坐标在 japan.json 里找所在县（`prefAt`），仍走 `onSelect(县 id)`。
- 测试里换算点击位置时，`convertToPixel` 给的是相对地图容器的坐标，要加上 `#map` 的 `getBoundingClientRect()` 偏移。

### 古国演变时间轴（712 / 757 / 824 / 1869）

- 824 年（多褹岛并入大隅、68 国定型）就是 `provinces.json` 的底图；其他三档在 `build_provinces.py` 的 `ERAS` 里定义：`merge`（子国并回母国）、`tane`（种子岛·屋久岛四市町为多褹岛）、`meiji`（东北与北海道按明治国）。各档只存与 824 年不同的国，写进 `province_eras.json`（`{年: {remove: [key], add: [Feature]}}`，第一次点时间轴时才下载）。所有档都由同一批「旧国 × 明治国 × 县」小块一起简化后拼出，边界完全对齐。
- 明治国对照 `tools/meiji_provinces.json`（团体代码 → 国）由 `python -X utf8 tools/fetch_meiji.py` 生成：市区町村的明治旧郡 → 日文维基郡条目的分类「○○国の郡」（陆奥取「陸奥国の郡 (1869-)」；按县限定可能的国）。1878 年后拆出的郡看 `PARENT`（原郡）；同名郡用 `TITLE` 指定条目名；近年新设的郡（北海道日高郡、二海郡）跳过；北海道上川郡·中川郡按市町村写在 `AMBIG`（核对「上川郡 (石狩国)」等条目列有该市町村）；旧郡都只部分属于又分属多国的市町村在 `MAIN` 写中心市街所在的郡（核对市町村条目里出现该郡名）。分类的 `cllimit` 是整批共享的，必须跟随 continue 取完。
- 新出现的国（多褹岛、明治 18 国）的三语名、读音、所属之道在 `NEW`；北海道十一国的「道」为 `北海道`（`FILTERS.circuit.cats` 与 `label('circuit')` 已加）。
- 前端：`map.setProvEras(d)` / `setProvEra(year)`，每档注册一张 `provinces-<年>` 底图（缓存）；图例按当年计数，说明取 `prov.era.<年>`。`#prov-eras` 只在 `body.prov-mode`（古国底图）显示，`syncProvEras` 随 `syncArtCard` 一起更新。

### 广重《六十余州名所图会》（hiroshige.js）

- `python -X utf8 tools/fetch_hiroshige.py`（需 `pip install pillow`）：解析日文维基百科「六十余州名所図会」的表格（69 幅，第 70 幅目录页跳过）→ 在 Commons 核对许可，**只收公有领域** → 原图缓存到 `.cache/hiroshige/`，缩到宽 560px 存 `src/assets/hiroshige/NN.jpg`（Commons 在国内打不开，图片随站点发布）。
- 画中地点：画题里第一个有坐标的链接条目（`PLACE` 可指定别的条目、或写 None 表示不用链接），落到市区町村边界里；**定位结果的旧国（`province` 或 `partial`）必须与作品的国一致**，否则列为待处理。画题无链接的：该国只有一个市町村就取它；`MANUAL` 里人工确认的取人工值（市区町村名为 None = 只确定到县）；其余只记县、界面写「具体地点不详」。不要为了填满而猜地点。
- 题名译文在工具的 `TITLES`（中 / 英；日文界面显示原题）。`build_bundle.py` 按语言拼好 `title_t`、旧国名 `prov`、市区町村名 `place` 放进数据包的 `hiroshige`（逐个文件回退加载时不显示浮世绘）。
- 「国名今犹在」（provnames.js）：`province_names.json` 为 `{ 旧国: [{ja, zh, en, type, wiki, evidence?, evidence_note?}] }`，type ∈ place / nature / food / craft / transit / culture。新增后必须跑 `python -X utf8 tools/province_names_tool.py verify`（需 shapely）：① 名字里含国名简称或 `ALIASES` 别称；② place / transit / nature 的条目坐标在该国内（自然地物容许 60 公里），food / craft / culture 的条目正文提到该国或今属县名。通不过就不收，确需例外写 `evidence` 并在 `evidence_note` 说明（如信浓川：河口在越后）。数据包 `province_names` 每国带 `prov` 显示名与 `prefs`；`map` 的 `provTipExtra` 往古国提示里加一行，古国卡片 `namesBlock`，详卡 `namesSection`（按县涉及的旧国）。
- 「我在哪」（locate.js）：地图右侧 `#btn-locate`，只在点按时调用 `navigator.geolocation`（超时 12 秒，不要求高精度）。县由 `map.prefAt`（japan.json）判断，市区町村在该县文件里点内判断、落空取最近的；不在任何县内 → 提示「似乎不在日本」。卡片 `#loc-card`（复用 `.art-card` 定位样式）写旧国（`province` + `partial`）、今天的县与市区町村、明治旧郡，并附该国浮世绘（`printRows`）与今日国名；`map.setYou(pt)` 放蓝色脉冲标记并拉近，关卡片时去掉。位置不发往任何地方。smoke `locate` 用 Playwright 的 `geolocation` 模拟京都中京区。
- 前端：古国底图下 `map` 的 `onProvince(properties)` → `#art-card`（武藏另带第 17 图「江户」）；离开古国底图时 `syncArtCard` 收起。详卡 `hiroshigeSection` 列出画中地点在本县的作品。`#art` 大图对话框按编号循环翻页（‹ › / 方向键）。

## historical_events.json

```jsonc
{
  "timeline_eras": [{                 // 9 个：飞鸟 奈良 平安 镰仓 室町 战国 江户 明治 现代
    "key": "heian", "name": "平安时代 (794–1185)", "short": "平安时代", "years": "794–1185",
    "timeline_stage": "律令",          // 联动详卡时间轴的阶段：飞鸟·奈良·平安→律令，镰仓→镰仓，室町→室町，战国，江户，明治·现代→近现代
    "capital": { "name": "山城平安京", "prefecture_id": 26, "coords": [135.7681, 35.0116], "description": "…" },
    "banner": "报幕副标题",
    "legend": [{ "key": "court", "label": "朝廷·院政（畿内）", "color": "#a77fb5" }],
    "prefecture_keys":   { "1": "outside", …, "47": "outside" },   // 47 县分类键
    "prefecture_colors": { "1": "#33333a", …, "47": "#33333a" }    // 47 县色值
  }],
  "historic_battles": [{              // 5 场：桶狭间 川中岛 关原 坛之浦 西南战争
    "key": "sekigahara", "name": "关原之战 (1600)", "year": 1600,
    "battlefield": { "name": "美浓国关原", "prefecture_id": 21, "coords": [136.5311, 35.3622] },
    "view": { "center": [137.7, 35.35], "zoom": 5.6 },   // 沙盘视角
    "factions": [{ "key": "east", "name": "东军", "leader": "德川家康", "strength": "约75,000（一说）", "color": "#4f86b8" }],
    "march_routes": [{ "faction": "east", "from": { "name": "江户城", "coords": […], "prefecture_id": 13 },
                       "via": [[lon, lat], …], "to": { "name": "关原", "coords": […] }, "color": "#4f86b8", "desc": "…" }],
    "brief": "100 字以内",
    "key_points": { "turning_point": "…", "forces": "…", "aftermath": "…" },   // 离线解答用
    "narrator": { "name": "德川家康", "title": "东军总大将", "self": "吾", "opening": "开战陈词", "tone": "口吻" },
    "phases": [                       // 固定 4 段：布阵 → 开战 → 转折 → 结局
      { "title": "转折", "time": "9月15日正午", "desc": "本阶段战况", "line": "名将台词（离线/在线都由本地脚本播出）",
        "routes": [0, 2],               // 本阶段显示的 march_routes 下标
        "markers": [{ "name": "松尾山", "coords": [136.516, 35.351] }],   // 本阶段的要地标记
        "impact": true }                // 是否显示交战爆点（否则战场显示为普通标记）
    ]
  }]
}
```

## 地图状态与互斥（map.js `state` + app.js `app`）

着色优先级：**合战沙盘 > 风土图层（拉面/地酒）> 时代滑块 > 时空滤镜**。

- 风土图层：`history | ramen | sake`。非历史图层时隐藏滤镜与时代滑块，详卡顶部换成拉面解构图 / 酒标卡；切回历史图层时滤镜与时代原样恢复。
- 时代滑块：拖动/点刻度/播放即进入「时空穿越」（`body.time-travel`），按时代 `prefecture_colors` 着色并在 `capital.coords` 放脉冲点；点任一滤镜或 × 退出。选中县时高亮对应 `timeline_stage`。
- 合战沙盘：`startBattle` 记住当前视角并缩放到 `view`，按当前阶段（`setBattlePhase`）叠加 `lines`（polyline，箭头流动）、出阵点、要地标记与战场爆点；HUD 可点阶段条、上/下一阶段或自动推演（每 7 秒一段），每换一段向导以名将口吻解说；`body.in-battle` 隐藏工具条与滑块；向导切换为 `narrator`。退出（按钮或 Esc）恢复视角、图层、滤镜与向导。合战中地图点击被忽略。
- 窄屏合战：`setupBattleVoice` 用 MutationObserver 把向导最新一条 AI 发言（打字机与 LLM 流式输出都会同步）镜像到地图底部的 `#battle-voice` 浮窗，「提问」切到向导页。
- 飞线 `effect.trailLength` 必须为 0：拖尾会开启 zlevel 运动模糊，缩放时留残影。
- 衬线字体（Noto Serif SC/JP）用于标题与古名，无衬线用于正文。

## 市区町村下钻（muni.js）

- 详卡「市区町村」按钮或链接 `#pref=23&muni=1` 进入：在地图区上层叠一张独立的 ECharts 地图（`#muni`，`body.muni-open` 隐藏工具条/滑块/图例），全国地图不动。开始合战会自动关闭下钻，Esc 退出。
- 数据 `src/data/municipalities/NN.json`（GeoJSON，每县一个，进入时才加载）由 `python -X utf8 tools/build_municipalities.py [缓存目录]` 生成：
  - 边界：国土数値情報（行政区域）经 smartnews-smri/japan-topography 简化 1%，坐标保留 3 位小数；**必须注明「国土数値情報（行政区域データ）」（国土交通省）を加工して作成**（图例与 README 已写）。
  - 读音 / 英文名 / 人口：Wikidata（P1814 / en label / P1082），缺的在脚本 `MANUAL` 里手补。
  - `province`（主要旧国，决定配色）：多国县取自人工对照表 `tools/province_overrides.json`（`default` + 例外名单，`"-"` = 令制外），单国县即该国。`partial`：Wikidata 沿「町村→郡→国」与「合并前町村 P1365」查到的其他旧国，只保留本县令制国列表里有的；对照表 `partial` 写了就以人工为准（空列表 = 排除误报）。脚本结束会列出对照表与 Wikidata 不一致的条目，需人工复核。
  - `remote`：远离本土的岛（北方领土、伊豆诸岛与小笠原、奄美与吐噶喇），不参与初始取景。
- 地图内部以团体代码作为区域名（同县可能重名，如北海道两个泊村），显示名用 `label`。
- 地名标签：`names` scatter 系列按人口从多到少排列，`labelLayout.hideOverlap` 自动隐藏放不下的，放大后显示更多。
- 向导联动：下钻里选中的市区町村经 `guide.setPlace()` 进入 System Prompt（`ROLE[lang].place`），快捷提问最前面加「这里古时候属于哪里」，离线由 `placeAnswer` 借县史料里该令制国的说明拼出；不重置对话。
- 旧郡（`old_districts`：`[[郡名, 是否只含一部分]]`；政令市只写到市一级的在文件的 `cities`）：`python -X utf8 tools/fetch_districts.py` 从日文维基百科「Category:○○の郡」及「(消滅)」下各郡条目整理成 `tools/districts.json`（可人工修正，已提交），再由 build_municipalities 合并。解析规则：第一个标题前的现属町村 + 「郡域」一节的列表项（嵌套列表把上级市名接到区前）与「郡域は…にあたる」一句；叙述段落不读；括号内容判断完「一部」后去掉再匹配（括号恰好为「全域」才算整体）。指的是明治郡制（1878〜）的郡域，界面上注明「可能不完整」。Wikidata 的合并链覆盖不全且有误，不用于旧郡。
- 旧国独立核对：build_municipalities 会用「整体属于某郡 → 该郡的令制国」核对对照表（约 1,350 个市町村），不一致的打印出来。明治郡有跨旧国改划（如奄美的大岛郡、志布志并入曾于郡），所以「部分属于」不自动采纳，只人工确认后写进对照表的 partial。
- 搜索（`search.js`，自定义下拉替代 datalist，键盘上下 / Enter / Esc；县与旧国优先、旧国按所在县逐条列出、重名市町村分条显示；下钻时搜索框搬进下钻顶栏）：构建脚本同时输出 `src/data/municipalities/index.json`（`[县id, 名称, 读音, 英文名, [代码…], 人口, 年份]`；政令市另有一条整市，代码为其全部区），搜索框首次聚焦时才下载。`fold()` 统一字形（简体/异体字 → 新字体、片假名 → 平假名、去掉长音符号后再 NFC 合成）。排序：县/旧国优先，市区町村按 名称一致 > 去掉「市町村区」一致或英文一致 > 名称/读音/英文开头 > 包含，同分时整市优先、读音越短越优先。选中后 `muni.show(pref, { codes, city })` 直接聚焦并拉近。

## 圣地巡礼（pilgrimage.js + map.js 图层 pilgrimage）

- 数据单独放在 `src/data/pilgrimage.json`（不写进各县 JSON），英日译文在 `src/data/i18n/{en,ja}/pilgrimage.json`（按 id，字段 work / place / scene / tips），由 `build_bundle.py` 合并进数据包的 `pilgrimage`：

```jsonc
{
  "done": [1, 2, …],                 // 已完成的县：动漫与大河剧各至少一处（check_data 检查）
  "spots": [{
    "id": "garupan-oarai", "pref": 8, "type": "anime",   // anime | taiga（NHK 大河剧）
    "year": 2012, "work": "少女与战车", "place": "大洗町（大洗矶前神社）",
    "work_wiki": "ガールズ&パンツァー",                  // 日文维基百科条目（核验用，不进数据包）
    "place_wiki": "大洗磯前神社",                         // 坐标取自此条目（无则 Wikidata P625）
    "evidence": ["大洗"],                                 // 作品条目里须出现其一，或地点条目提到作品名
    "coords": [140.5874, 36.3158],                        // 由工具写入，勿手改（实在没有才手填并标 coords_src: manual）
    "scene": "哪一幕在这里（不剧透）", "tips": "礼仪与注意事项（不写营业时间、票价等易过时信息）"
  }]
}
```

- 新增巡礼点：写好条目后运行 `python -X utf8 tools/pilgrimage_tool.py verify --write`（取坐标、核验作品与地点的对应、检查坐标在县内），`search 关键词` 可查候选；选作品优先参考维基百科「○○県を舞台とした作品一覧」。只收有出处的圣地，宁缺毋滥。
- 图层：底图调暗（`LAYERS.pilgrimage.dim`），`spots` effectScatter 图钉（动漫粉 `#ff7eb6` / 大河古金 `#e0b04c`，`SPOT_COLOR`），子分类「全部 / 动漫 / 大河剧」（`#pil-filter`，`map.setSpotType`）；点图钉 → `openSpot`：选中所在县、`map.focusSpot` 拉近、弹出 `#pil-card`；Esc / × 关闭。详卡底部「圣地巡礼志」（`pilgrimageSection`，经 `renderDetail` 的 `extra` 传入），点条目在地图上定位。
- 向导：巡礼图层下 `guide.setPilgrimage(本县巡礼点)`，快捷提问最前面加「这里有哪些圣地？」；离线由 `pilAnswer` 回答（动漫部分热血漫迷口吻、大河剧部分剧评人口吻）；在线把巡礼点写进 System Prompt（`PIL_RULE`）。

## 声音（audio.js）

- 单例 `audio`：`play(name)`、`toggleMute()` / `setMuted()`、`setMusic(on)`、`setVolume('bgm'|'sfx', 0–1)`、`onChange(fn)`、`debug()`（测试用）。
- 浏览器自动播放限制：首次用户操作才创建 / 恢复 AudioContext，并在手势里播 1 采样静音（旧版 iOS）。**触摸屏上 touchstart 与触摸的 pointerdown 不算解锁操作**，必须同时监听 `pointerup` / `touchend` / `click`（电脑模拟测不出来，只有真手机会失效）。监听一直保留，用于恢复被系统挂起（Safari 为 `interrupted`）的 context。解锁前调用 `play` 静默忽略（深链接打开时不会出声）。
- iOS 16.4+：未静音时设 `navigator.audioSession.type = 'playback'`，静音模式下也出声（会暂停其他 App 的音乐）；顶栏静音时改回 `auto`。
- 默认全部实时合成：`click` 竹筒轻击（选县、选市区町村、点巡礼图钉、跨到另一个时代）、`stamp` 太鼓一击（盖印）、`battle` 太鼓两击 + 法螺贝（开始合战）、`drum` 太鼓「咚咚」（合战推进到 `impact: true` 的阶段）。各音效有最短间隔（`SFX[].gap`），连点不叠音。
- 背景音乐：都节音阶（E F A B C）随机游走的古筝拨弦 + E/B 持续低音 + 合成混响，不循环；默认关，在设置弹窗「声音」区块开启（改动立即生效，不随保存/取消）。开启 + 未静音 + 页面在前台才播放，切后台淡出后停止。
- 想用录好的 mp3：放进 `src/assets/audio/`，在 audio.js 顶部 `FILES` 登记（不自动探测，免得 404 进控制台），加载/播放失败自动退回合成。
- 任何音频错误只 `console.warn`，不得抛出；smoke 的 `audio_broken` 场景删掉 AudioContext 后走一遍盖印、合战、开音乐。

## 检查与测试（改完提交前先跑）

- `python -X utf8 tools/check_data.py`：数据与仓库一致性——分类键取值（直接读 map.js / crests.js / guide.js，不另抄）、时间轴 6 段、译文覆盖层结构（不得含逻辑键、对象数组长度一致）、时代与合战、**数据包是否过期**（用 `build_bundle.build()` 重算比较）、市区町村字段与对照表名字、`sw.js` 的 SHELL 是否覆盖全部 `src/js`、仓库里有无 `__pycache__` / 测试页等杂物。
- `python -X utf8 tests/smoke.py`（本地可加 `PW_CHANNEL=chrome` 用已装的 Chrome；`SMOKE_ONLY='phone.*zh'` 只跑部分）：Playwright 在 电脑 1280×800 / 平板 820×1180 / 手机 390×844 下跑深链接、横向溢出、下钻、搜索、合战、时代滑块、盖印位置、离线向导、标签页；中文全跑，英日只跑语言相关场景。任何控制台报错或页面异常即失败，截图存 `tests/artifacts/`。
- GitHub Actions（`.github/workflows/checks.yml`）每次推送：数据检查 → 冒烟测试 → （仅 main 且两项都通过）发布到 GitHub Pages。Pages 的 Source 设为「GitHub Actions」，检查失败网站保持上一版。发布只打包 `index.html`、`manifest.webmanifest`、`sw.js`、`src/`——**新增网站需要的根目录文件时要加进 deploy 步骤的 cp 列表**。推送后约 3 分钟才上线（原来约 40 秒）。
- CSS 有全局 `[hidden] { display: none !important; }`，组件里写 `display` 不会再盖掉 hidden 属性。
- 新增功能时在 `tests/smoke.py` 里补一个场景。现有回归场景：`provinces` 另含时间轴（1869 年底图、点札幌选中北海道、712 年、离开后隐藏）；`locate`（模拟定位京都：卡片内容、选中京都府、带浮世绘、打开市区町村地图）、`hiroshige`（古国地图点武藏出两幅、大图加载与翻页、详卡列出）、`provinces`（换成旧国底图、点武藏国里的埼玉仍选中埼玉、换滤镜后换回县）、`sound`（音效触发、静音保存、开背景音乐）、`audio_broken`（声音不可用时照常运行）、`pilgrimage`（切图层、点图钉、子分类、详卡条目、离线漫迷解说）、`era_stable`（换时代时图例与报幕横幅尺寸不变）、`search_fits`（搜索下拉完整落在屏幕内）、`china`（屏蔽 jsdelivr / unpkg / Google Fonts 后仍能打开）。
- 时代报幕横幅固定宽度、副标题预留两行、动画不改字间距；窄屏图例单行横滑；搜索下拉在窄屏用 fixed 铺满屏宽，高度按 `visualViewport`（软键盘以上）计算。

## 约定

- 跨界令制国（陆奥、出羽、武藏、摄津、丹波、纪伊、肥前、丰前、日向、伊豆、下总）在 `cross_prefectures` 中注明，前端卡片显示「跨界」小标签。
- 9 个时代的着色是按各时代主导结构的近似表达（如平安按朝廷/平氏/源氏/奥州藤原，江户按天领/亲藩/谱代/外样），图例中注明依据。
- 坛之浦按史实用源氏白旗、平氏赤旗配色；其余合战红蓝对阵。
- 无 API Key 时向导绝不报错：快捷提问与关键词匹配的自由提问均由本地 JSON 以角色口吻 + 打字机效果输出。
- `file://` 打开时由 index.html 内联脚本弹出和风提示（模块脚本在 file:// 下会被拦截，不能放在 app.js 里检测）。
- 新增或修改县数据时保持 schema 一致，`history_timeline` 必须恰好 6 段（律令/镰仓/室町/战国/江户/近现代）。
- 史实以通行说法为准，存疑处用“据传”标注。
- 不引入构建工具；新增模块用原生 ES Modules `import`。
- 版权与许可：© 2026 Nickrockwall；代码 MIT（`LICENSE`，保持纯 MIT 原文以便 GitHub 识别），内容 CC BY-NC 4.0，范围与第三方清单在 `LICENSE-CONTENT.md`。新增第三方素材时登记到该表，并在 README 三语「说明」与界面上注明出处。全国地图须注明「出典：地球地図日本」（欢迎卡与设置弹窗底部的 `legalHTML()`）。来自维基百科的数据是 CC BY-SA 4.0，不能并入 NC 内容。
