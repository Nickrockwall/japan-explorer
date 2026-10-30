# Japan Explorer · 日本47都道府县古今变迁图鉴

交互式历史地图应用：在日本全图上点选任一都道府县，查看其古代令制国沿革、历史时间轴、名胜物产、方言与地缘梗；用「时空滤镜」看五畿七道、战国势力、幕末阵营；打卡收集御朱印；拖动「时空穿越滑块」看九个时代的版图与政权中枢；在「合战演武」沙盘上回放经典战役；切换「拉面 / 地酒」风土图层；并与「AI 历史向导」对话（博学史官 ⇄ 名将附体 / 合战名将）。

## 技术架构

- 原生 HTML5 + CSS3 + 原生 ES Modules，无构建工具、无 npm 依赖，纯静态运行。
- 地图：Apache ECharts 5.5.1（jsdelivr CDN，失败时回退 unpkg → npmmirror 国内镜像），用 `echarts.registerMap` 注册本地 GeoJSON。
- 深链接：`index.html#pref=26` 直接打开对应地区。
- 必须通过 HTTP 服务器访问（`fetch` 读取 JSON），不能直接双击 `file://` 打开：
  - `python3 -m http.server 8000`（Windows 用 `python`）或 `npx serve .`
- 浏览器本地存储（`localStorage`）：
  - `je.visited` — 已探索的都道府县 id 数组
  - `je.api` — LLM 接口配置 `{provider, baseUrl, model, apiKey}`（仅存于用户浏览器）
  - `je.goshuin` — 御朱印 `{ [id]: 盖印时间 ISO }`
  - `je.ui.filter` / `je.ui.guideMode` / `je.ui.split` / `je.ui.layer` — 当前滤镜、向导模式（scholar|hero）、右侧上下比例（%）、风土图层（history|ramen|sake）

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
src/assets/geojson/japan.json  47 都道府县 GeoJSON（properties: id, name, nam, nam_ja；name = 规范汉字全称如「京都府」，须与县数据 name.kanji 及 ECharts series.data.name 严格一致）
src/data/index.json            47 县清单（id, slug, file, kanji, zh, region）
src/data/historical_events.json  全国共享：timeline_eras（9 个时代）+ historic_battles（5 场合战）
src/data/prefectures/NN_slug.json  各县数据（01_hokkaido … 47_okinawa）
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

## 设计规范

- 雅致和风 × 深色科技仪表盘：底色 `#18181c`，朱红 `#c23531`（选中/强调），青金 `#d4a373`（已探索/次强调）。
- 布局：顶栏 + 左 58% 地图 + 右 42%（上：详卡，下：向导，中间拖动条可调比例 20–80%）；窄屏改为上下堆叠。

## 时空滤镜

| 模式 | 分类依据 |
|---|---|
| 探索进度 | 未探索 / 已探索 / 当前 |
| 现代区划 | `region` 八地方 |
| 五畿七道 | 县内**首个**令制国的 `circuit`（跨多道的县以主要国为准，tooltip 列出全部古国） |
| 战国势力 | `map_filters.sengoku_1572`：固定 **1572 年（元龟三年）信玄西上前夕** 的县内主导势力 |
| 幕末阵营 | `map_filters.bakumatsu`：戊辰战争时县内主导势力立场（萨长土肥 / 新政府方 / 佐幕方 / 天领直辖） |

一县多藩、势力交错时只能取主导势力，属近似表达；切换只改 `geo.regions[].itemStyle`，不重载 GeoJSON。

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
- 飞线 `effect.trailLength` 必须为 0：拖尾会开启 zlevel 运动模糊，缩放时留残影。
- 衬线字体（Noto Serif SC/JP）用于标题与古名，无衬线用于正文。

## 约定

- 跨界令制国（陆奥、出羽、武藏、摄津、丹波、纪伊、肥前、丰前、日向、伊豆、下总）在 `cross_prefectures` 中注明，前端卡片显示「跨界」小标签。
- 9 个时代的着色是按各时代主导结构的近似表达（如平安按朝廷/平氏/源氏/奥州藤原，江户按天领/亲藩/谱代/外样），图例中注明依据。
- 坛之浦按史实用源氏白旗、平氏赤旗配色；其余合战红蓝对阵。
- 无 API Key 时向导绝不报错：快捷提问与关键词匹配的自由提问均由本地 JSON 以角色口吻 + 打字机效果输出。
- `file://` 打开时由 index.html 内联脚本弹出和风提示（模块脚本在 file:// 下会被拦截，不能放在 app.js 里检测）。
- 新增或修改县数据时保持 schema 一致，`history_timeline` 必须恰好 6 段（律令/镰仓/室町/战国/江户/近现代）。
- 史实以通行说法为准，存疑处用“据传”标注。
- 不引入构建工具；新增模块用原生 ES Modules `import`。
