# Japan Explorer · 古今日本地图

交互式历史地图应用：在日本全图上点选任一都道府县，查看其古代令制国沿革、历史时间轴、名胜物产、方言与地缘梗；用「时空滤镜」看五畿七道、战国势力、幕末阵营；打卡收集御朱印；拖动「时空穿越滑块」看九个时代的版图与政权中枢；在「合战演武」沙盘上回放经典战役；切换「拉面 / 地酒」风土图层；并与「AI 历史向导」对话（博学史官 ⇄ 名将附体 / 合战名将）。

## 技术架构

- 原生 HTML5 + CSS3 + 原生 ES Modules，无构建工具、无 npm 依赖，纯静态运行。
- 地图：Apache ECharts 5.5.1，**随站点发布在 `src/vendor/echarts.min.js`**（附 LICENSE/NOTICE），是只含本站所用部件的按需打包（map / scatter / effectScatter / lines / custom + geo / tooltip + canvas，`tools/echarts/entry.js`，`sh tools/echarts/build.sh` 重建，需 Node；完整版 1 MB → 0.55 MB）。用到新的图表类型或组件（visualMap、legend、markPoint…）时先在 entry.js 登记再重建，否则 ECharts 只在控制台警告、不画出来。不走 CDN——jsdelivr 在国内常挂起，同步脚本会让整页卡住（smoke 测试的 china 场景会屏蔽外部 CDN 检查这一点）。用 `echarts.registerMap` 注册本地 GeoJSON。
- 字体：正文（`--sans`）一律用系统字体；只取当前语言的一种衬线字体（中文 Noto Serif SC，日文 / 英文 Noto Serif JP），由 index.html 头部的内联脚本按与 `i18n.js` `detect()` 相同的规则判定语言、设好 `<html lang>` 后插入 `src/fonts/{sc,jp}.css`，`display: optional` 非阻塞（没能马上就绪就整页用系统字体）。字体随站点发布（3.24 起不再用 Google Fonts，国内打不开）：`python -X utf8 tools/build_fonts.py`（需 fonttools、brotli）只收网站文字里出现的字（index.html、src/js、src/data 全部 JSON，界面文字加权），按字频每 160 字切一片、字重 500 / 700（写 900 的取 700），文件名带内容哈希，`sw.js` 对 `src/fonts/*.woff2` 缓存优先（`je-fonts`，不随版本清空）。**数据或界面里出现新字后重跑**，`check_data.check_fonts` 核对没有漏字（字体本身没有的字记在 `tools/fonts_lacking.json`）。首屏约 15 片、0.6 MB。许可 SIL OFL（`src/fonts/OFL.txt`）。canvas 上的地图标签用 `serifFont()`（i18n.js，读 CSS 的 `--serif`），不要写死字体名。
- 深链接：`index.html#pref=26&lang=ja` 直接打开对应地区并指定语言；`&muni=1&m=23211` 打开市区町村地图并选中（政令市整市为各区代码以 `.` 连接）（`lang` 可省略；链接里的语言优先于本地设置并会被记住）。选中地区时地址栏自动写成这种形式，详卡「分享」按钮复制/分享的就是它。
- **当前地图**（`src/js/country.js`）：`MAPS` 登记各地图的 GeoJSON、数据目录、单元数与存储键前缀（日本 = `src/data`、`je.`，与改造前完全相同）。页面加载时由 `pickMap(hash, 上次的地图)` 定下：链接里 `map=` 是已登记的键 → 用它；否则链接带 `pref=`（老链接都是日本）→ 日本；否则上次看的地图（`je.ui.map`）；都没有 → 日本。日本以外的地图在 `stateHash` 里写 `map=`，日本链接不带。切换地图走整页重载（与切换语言相同）。数据路径一律写成 `${MAP.data}/…`，不要再写死 `src/data/`。
- 日文 → 简体：`build_bundle.ja_to_zh_table()` 把 search.js 的对照表反过来用，只收 GB 2312 里有的字（对照表也有异体字，反用曾把崎写成﨑、富写成冨），另把 zhconv 的「㭴」改回「樫」；han_tool / sengoku_tool / rulers_tool 的 `JA_ZH` 都从它来，`check_han` 核对藩名与藩主中文名里没有这几个字。
- **数据打包（改数据后必做）**：`python tools/build_bundle.py` 把每种语言的 47 县 + 合战/时代数据合并成 `src/data/bundle/{zh,en,ja}.json`（每种语言 1 个请求）。前端优先读 bundle，读不到才回退为逐个文件加载——所以**改了 JSON 却忘记重新打包，线上会继续显示旧内容**。
- PWA：`manifest.webmanifest` + `sw.js`（本站文件网络优先、CDN 库与字体缓存优先，只缓存 GET）。`SHELL` 由 `python -X utf8 tools/build_sw.py` 生成（src/js 下全部模块含 `lang/`，加上 index、css、ECharts、字体 CSS、japan.json、图标），列表变化时自动把 `VERSION` 加一；新增 / 删除 / 改名模块后跑它，`check_data.check_shell` 核对。图标在 `src/assets/icons/`：标志是朱印里的列岛剪影（3.26 起，替换以前的「古」与「旅」），`python -X utf8 tools/make_icons.py` 从 japan.json 生成 `seal.svg`（顶栏左上角 `.brand-seal`）、`favicon.svg`（剪影加粗、去掉内框，16px 也认得）与各尺寸 PNG（主屏幕图标是纸色底；maskable 版印缩在中间 60%）。分享卡片封面 `src/assets/og-cover.png`（1200×630）。
- 必须通过 HTTP 服务器访问（`fetch` 读取 JSON），不能直接双击 `file://` 打开：
  - `python3 -m http.server 8000`（Windows 用 `python`）或 `npx serve .`
- 浏览器本地存储（`localStorage`）：
  - `je.visited` — 已探索的都道府县 id 数组
  - `je.api` — LLM 接口配置 `{provider, baseUrl, model, apiKey}`（仅存于用户浏览器）
  - `je.goshuin` — 御朱印 `{ [id]: 盖印时间 ISO }`
  - `je.ui.filter` / `je.ui.guideMode` / `je.ui.split` / `je.ui.layer` — 当前滤镜、向导模式（scholar|hero）、右侧上下比例（%）、风土图层（history|ramen|sake）
  - 按地图分开的键：`visited` / `goshuin` / `ichinomiya` 与 `ui.filter` / `ui.layer` 前面接 `MAP.store`（日本即 `je.`，键名不变）；其余 `je.ui.*` 全站共用。`je.ui.map` — 上次看的地图
  - `je.ui.kosekiName` — 古代户籍的户主名（只存本机）
  - `je.ui.tourDone` — 看过（或跳过）新手教程；smoke 除 `tour` 场景外都预先写入，免得教程遮住页面
  - `je.ui.audio` — 声音 `{muted, bgm, bgmVol, sfxVol}`（默认音效开、背景音乐关）

## 目录结构

```
index.html                     入口
src/css/style.css              全部样式（设计 token 定义于 :root）
src/js/app.js                  入口模块：加载数据、协调各模块
src/js/country.js              当前地图（MAPS 登记、pickMap 规则、MAP 配置、setMap 换地图）
src/js/shell.js                两种地图共用的外壳：标签页、提示、设置弹窗、声音、拖动条、语言与地图开关
src/js/korea.js                朝鲜半岛模式的入口（地图、详卡、争议标注）
src/js/disputed.js             有争议的地区（竹岛、北方四岛）：外框、splitDisputed 拆分、disputedAt、争议卡片（两种地图共用）
src/data/korea/regions.json    半岛 29 个一级行政区 + 军事分界线 + 独岛位置（tools/build_korea_geo.py 生成）
src/data/korea/counties/NN.json 各一级区的市郡区（同一脚本生成，下钻时才加载）
src/js/korea-counties.js       半岛的市郡区下钻（#muni 容器，按人口着色）
src/js/store.js                数据加载 + localStorage 读写
src/js/map.js                  ECharts 地图（geo 坐标系）+ 时空滤镜 FILTERS + 风土图层 LAYERS + 时代/合战叠加层
src/js/detail.js               右上：地区风土与历史详卡
src/js/guide.js                右下：AI 案内人（史官/名将双模式、快捷提问、离线解答、LLM 流式调用）
src/js/goshuin.js              御朱印帐弹窗（47 格、按地方筛选）
src/js/crests.js               家纹/神纹 SVG 印纹库（crestSVG(code)）
src/js/audio.js                和风音频单例：Web Audio 合成音效与背景音乐（可选 mp3 见 src/assets/audio/）
src/assets/geojson/japan.json  47 都道府县 GeoJSON（properties: id, name, nam, nam_ja；name = 规范汉字全称如「京都府」，须与县数据 name.kanji 及 ECharts series.data.name 严格一致）
src/data/index.json            47 县清单（id, slug, file, kanji, zh, region）
src/data/historical_events.json  全国共享：timeline_eras（10 个时代，3.14 加了大正·昭和前期 1912–1945）+ historic_battles（5 场合战）
src/data/prefectures/NN_slug.json  各县数据（01_hokkaido … 47_okinawa）
src/data/provinces.json        68 令制国真实边界 + 县界线（tools/build_provinces.py 由市区町村合并生成）
src/data/province_eras.json    古国演变时间轴：712 / 757 / 1869 年与 824 年的差异（remove + add）
src/data/hiroshige.json        广重《六十余州名所图会》69 幅（tools/fetch_hiroshige.py 生成；图片在 src/assets/hiroshige/NN.webp）
src/js/hiroshige.js            古国地图上的作品卡、详卡「广重笔下」、大图浏览
src/data/province_names.json   「国名今犹在」：旧国 → 今天仍带国名的东西（tools/province_names_tool.py 核验）
src/js/provnames.js            国名标签：古国悬停提示、古国卡片、详卡
src/data/koku_sites.json       古国巡礼：诸国一宫·国府·国分寺（tools/fetch_koku.py 生成并核验）
src/js/koku.js                 古国巡礼的卡片、详卡「古国三迹」、御朱印帐「诸国一宫」篇
src/data/kokuryoku.json        古国国力：68 国今日人口 / 面积 / 市区町村数 + 江户人口与石高（tools/build_kokuryoku.py 生成，打进数据包）
src/js/kokuryoku.js            古国国力：指标、着色、提示、反常识头条、榜单与宿敌 PK 卡片
src/data/sengoku.json          战国势力：68 国 × 6 个年份的归属、各家代表人物、家纹出处、1598 年各国石高（tools/sengoku_tool.py 生成并核对）
src/data/sengoku_units.json    战国势力图的底图改动：陆奥、出羽按郡的 43 块与虾夷地的和人地（tools/build_provinces.py 生成，{remove, add}，打开战国图时才下载）
tools/ou_units.py              上面这些分区的定义：明治旧郡 → 分区、横跨几郡的市（MUNI）、和人地的市町村
src/assets/crests/<键>.png     家纹旗用的家纹（白色图案透明底 96px，tools/crest_tool.py 生成；出处与许可在 tools/clan_crests.json）
src/data/rulers.json           天皇 126 代 · 将军 · 镰仓执权的代数与在位年份（tools/rulers_tool.py）
src/data/people.json           人物详写：三语简介、相关人物、家纹、肖像（tools/people_tool.py；肖像在 src/assets/people/QID.jpg）
src/js/sengoku.js              战国势力：着色、提示、图例、国别卡片与人物卡
src/js/rulers.js               年表对话框：实权（各时期名义 / 实际掌权者）· 天皇 · 将军 · 执权
src/data/regimes.json          「实权」20 段（tools/regimes_tool.py：三语自写，年份与人名对日文维基核对）
src/data/kako.json             彼时今日：{MM-DD: [事件 / 诞生 / 忌日]}（tools/kako_tool.py）
src/js/kako.js                 彼时今日：每人一个种子的当天顺序、欢迎卡一节、详卡「本县的彼时今日」
src/data/han.json              江户诸藩的历代藩主（tools/han_tool.py）
src/js/han.js                  详卡「江户诸藩」、藩主 ⇄ 彼时今日
src/js/bday.js                 生日帖：某一天的全部条目、几个数字、存图
src/data/emblems.json          47 都道府县章（tools/fetch_emblems.py：Wikidata P94 → Commons 只收公有领域 → src/assets/emblems/NN.png 透明底），详卡头像
src/js/tour.js                 新手教程：聚光灯 + 说明气泡，步骤由 app.js 给出（首次访问自动开始）
src/js/toc.js                  详卡目录：一行吸顶的跳转按钮（日本与半岛详卡共用）
src/js/koseki.js               古代户籍《古今人别帐》：按市区町村 / 定位点列出各时代归谁管（卷轴 HTML + 存图 canvas）
src/js/hometown.js             户籍末尾「此地年表」：古代的国 → 战国 → 江户的藩与各家 → 今天，插入落在本市区町村的彼时今日条目
src/data/region_eras.json      冲绳、北海道、奄美群岛的地区年表（tools/region_eras_tool.py：三语自写，年份对日文维基核对；北海道条目分 all / wajin 和人地 / ezo）
src/js/report.js               「数据有误？」：各卡片末尾的 GitHub issue 链接（点的时候才拼地址）
tools/domains.json             幕末各郡的领主与町村数（tools/fetch_domains.py 由维基各郡条目的《旧高旧領取調帳》表整理，build_bundle 拼进数据包 domains）
tools/main_gun.json            户籍江户一段的主要郡 / 整市 / 江户京都市街（tools/fetch_main_gun.py，build_bundle 拼进数据包 main_gun）
tools/mura.json                1889 年町村制时今属各市区町村的町村（tools/fetch_mura.py）
tools/seats.json               城下町：存续藩的藩厅落在哪个市区町村（tools/fetch_seats.py，build_bundle 并进 main_gun 的 seat）
tools/wiki_revisions.json      各数据工具读过的维基条目版本号（pilgrimage_tool.record_revisions）
tools/yurai.json               地名的来历 124 条（tools/yurai_tool.py，三语自写、关键词对条目或官网核对）
tools/kyudaka.json             今天各市区町村里幕末各村的领主与石高合计（tools/fetch_kyudaka.py，歴博《旧高旧領取調帳データベース》）
tools/wamyo.json               《和名类聚抄》各郡的郷与读音、市区町村 → 古郡（tools/fetch_wamyo.py，奈文研「古代地名検索システム」）
tools/codh.py                  CODH 数据的共用读法：TopoJSON → shapely、按面积对到今天的市区町村、按坐标定位、nrct 村坐标
src/data/bundle/town/<lang>/NN.json  明治町村、地名来历、kyu、wamyo 按语言、按县打包（build_bundle 的 build_town，打开某县的户籍时才下载那一县，每份十几到几十 KB）
src/js/locate.js               「我在哪」：浏览器定位 → 县（map.prefAt）→ 市区町村（该县的 municipalities 文件）→ 结果卡片
```

## 朝鲜半岛模式（korea.js）

设计见 `docs/superpowers/specs/2026-11-01-korean-peninsula-design.md`。品牌标题旁的 `#map-switch`（手机上取代标题文字，印章保留）切换「日本 / 朝鲜半岛」，走 `setMap` 整页重载；`app.js` 在 `mapKey !== 'japan'` 时改载 `korea.js`，日本的代码路径不动。`<html data-map>` 标记当前地图，日本独有的按钮、工具条、时代滑块、定位、图例、教程入口在 `:root[data-map="korea"]` 下隐藏；皮肤（丹青配色、韩纸纹、顶栏五方色带）也在那里覆盖 token。地图配色写在 korea.js 的 `COLOR`，着色走 `geo.regions`（map 系列绑在 geo 上时系列数据的颜色不生效）。

- **名称规矩**：模式叫朝鲜半岛 / Korean Peninsula / 朝鮮半島，不叫「韩国」。地名写「当前语言名 / 한글 / 罗马字」（详卡沿用 `.modern-title` 的 kanji / kana / romaji 三格）。界面不加韩文。
- **争议标注**：独岛 / 竹岛是中性灰的空心点，不属于任何区、不着色；标签与卡片两个名字并列，三语顺序固定（`kr.dokdo*`）。卡片列出位置、现状与韩日双方立场（含韩方「不存在领土争端」），不作判断。海名「日本海 / 东海」（`kr.sea`）。南北之间画「军事分界线」（`kr.mdl`），不叫国界。
- **数据**：`python -X utf8 tools/build_korea_geo.py`（需 shapely）一次生成一级区与市郡区。先做市郡：韩国 ADM2（2020）逐块配 Wikidata 条目（各一级区的 P150 下级；坐标落在块里 + 罗马字名对得上，同名的区取最近），**一级区由配上的条目定**（geoBoundaries 的韩国 ADM1 来自 Natural Earth，太粗，会把首尔恩平区、仁川西区 / 江华 / 瓮津划进京畿；脚本断言这些已归对）；韩国每个市郡必须恰好配上一块。ADM2 缺了全南灵光郡，用 ADM3 里没被盖住的邑面洞补（板门店一带无条目的碎片并给相邻市郡）。仁川按 2026-07-01 区划拼成济物浦区 / 永宗区 / 检丹区 / 西海区（ADM3 的旧检丹 1～5 洞）。朝鲜 ADM2（2019）按同源 ADM1 归属（按块，不按名字：两道各有一个 Unsan），配不上的按罗马字名搜 Wikidata（只收坐标在块里的「…군/시/구역/地区」），仍配不上的 3 个只有罗马字名。市郡一起简化后合并成一级区，再整体粗一点简化。下载缓存在 `.cache/korea/`（出错的回应不缓存，429 会等）。改正为现行区划：军威郡 → 大邱（2023）、光州 + 全南 → 全南光州统合特别市（2026-07-01）、罗先与开城（含 2023 年并入的长丰郡）单列。南北在非军事区里的重叠从北侧裁掉，约 3 公里内的缝隙并给接触边最长的一侧，全部一起 `coverage_simplify`；军事分界线取北侧边界里离南侧不到约 300 米的部分。名称表 `UNITS` 手写，与 Wikidata 韩文标签逐个比对（`KO_ALIAS` 是核对过的简称）；人口取最新年份的 P1082（朝鲜多为 2008 年普查，开城的说明在 `NOTES`）。下载缓存在 `.cache/korea/`。
- `regions.json`：`features[].properties` = `{id 1–16 南 / 17–29 北, name 한글全称（ECharts 区域名）, side, zh, ja, en, rr, wd, pop, pop_year, area, note}`；`mdl` 为折线数组；`dokdo.coords`。
- 存储：探索进度 `je.korea.visited`（`MAP.store`）。深链接 `#map=korea&pref=1`，编号不在 1–29 时回到欢迎卡；`&muni=1` 打开市郡区下钻，`&m=4-3` 并选中（代码为 `一级区-序号`）。
- 历代政区（`#kr-eras`，地图左上，从古到今：新罗 / 高丽 / 朝鲜 / 1896 / 今天）：`python -X utf8 tools/build_korea_eras.py` 由市郡文件按归属合并，输出 `src/data/korea/eras/{silla,goryeo,joseon,1896}.json`（坐标两位小数，选到时才加载）。1896 十三道与朝鲜八道按市郡归属拼面：默认按今天的一级区，例外在脚本 `EXCEPT`（锦山→全北、蔚珍→江原、元山 / 文川 / 安边 / 川内 / 高山 / 法东→咸南，韩文维基核对过），两江、慈江整体归大部分所属的道。高丽（11 世纪）与新罗（8 世纪）只画疆域（今天哪些区在内，`SILLA_IN` / `GORYEO_IN`）与州治 / 道的位置标签，不画内部界线——古代州界与今天的市郡对不上。历代图层下点击按坐标选中今天的一级区，详卡时间轴展开对应一段（`ERA_STAGE`，加 `.hl`）；图例显示并注明近似 / 示意。
- 道名今犹在：`build_korea_eras.py` 的 `NAME_SOURCES` 写八道（与慈江道）名字来源的两座城，输出 `src/data/korea/names.json`（开页加载）与八道 / 1896 图层里的 `sources`（地图上标出这些城，提示「某道的名字就有它一个字」）。详卡「道名的来历」按 korea.js 的 `ORIGIN`（今天的区 → 来源），京畿 / 两江 / 罗先另有说明。
- 此地古今（korea-place.js）：`placeHistory(regions, pt)` 在本机查出今天的区与市郡、1896 / 朝鲜的道、是否在高丽与新罗疆域内、最近的新罗州治（直线距离），`placeCard` 画卡片（`#loc-card`）。入口：地图右侧定位按钮（落在争议岛上弹争议卡，半岛外提示 `kr.loc.outside`）与市郡卡片的「📜 古今户籍」（取市郡的标签点）。
- 史话：`src/data/korea/content/{zh,en,ja}.json`，每区 `{seat, timeline[6], landmarks, specialties, dialect, meme}`；时间轴 6 段固定为三国 / 统一新罗 / 高丽 / 朝鲜王朝 / 近代（1897–1945）/ 1945 年以后；韩文方言原句三语一致（check_data 核对）。
- 市郡区下钻（korea-counties.js）：详卡「市郡区」按钮进入，按人口（对数）着色，名字取当前语言标签、缺时用韩文；图例底部注明南北数据来源与精度。
- 向导（korea-guide.js）：只有一位「时空案内人·丹青」，复用 guide.js 的 `streamChat` 与对话样式。快捷提问：历史 / 方言 / 名字来历；离线由本区史话拼答，关键词还能答名胜与吃的；有 API Key 时把本区史话（JSON）写进 System Prompt，规则（`kr.g.rules`）要求：南北用正式国名、半岛不只叫韩国、争议名字并列只述立场、共同历史先讲双方都承认的事实再讲各方叙述、不做假平衡。
- 声音：audio.js 在半岛模式下换平调五声音阶（G A C D E）与 G/D 持续低音，拨弦多带「弄弦」颤音。
- 半岛印帐（korea-book.js）：顶栏 `#btn-book` 与 `#book` 对话框沿用日本的，文字换成 `kr.book*`、计数 /29。「29 区」篇每区一枚韩式方印，印面只有韩文简称（`sealText`：南北道用两字简称 경북 / 평남，其余去掉行政单位；四字的「전남광주」排成 2×2、右列先读），不用徽章旗帜；按朝鲜八道分组（`GROUPS`：开城归京畿、济州归全罗、慈江归平安、两江归咸镜）。详卡「盖印」按钮（`stampButton` / `playStamp`，复用 `.seal-drop`），存 `je.korea.goshuin`（`goshuinBook`）。「乡校篇」：`src/data/korea/hyanggyo.json`（`python -X utf8 tools/fetch_hyanggyo.py`，需 shapely zhconv）——Wikidata 乡校（Q5952771）带坐标的条目，汉字取韩文维基首句括号（没有的写进工具的 `HANJA`），简体用 zhconv、日文新字体按 `JA_MAP`；坐标须落在名字或条目提到的市郡，旧郡县并进别的市郡的人工核对后写进 `CHECKED`，对不上的不收（任实乡校：坐标落在益山）；目前全在南边，界面注明北边暂缺。选中的区在地图上标出本区乡校（`hy` 系列，只在「今天」图层），点开 `#art-card`：记下到访 / 1 公里内实地打卡（`hyanggyoBook`，存 `je.korea.hyanggyo`）；详卡末尾「乡校」一节列出本区乡校。手机上印帐的标签单行横滑（`.book-tabs` 要 `flex: none`）。
- 传统酒：`src/data/korea/sul.json`（`{区 id: [{ko, hanja, zh, ja, rr, src, find?, origin?, note}]}`），只收列入各市道 / 国家无形遗产或「대한민국식품명인」名录的，`python -X utf8 tools/korea_sul_tool.py` 核对每条的酒名与汉字确实出现在出处页（src，韩文维基条目名）；说明只写出处里有的。`origin: true` 按原产地收（문배주 → 平壤），说明里写今天在哪酿。北边其余区没有可核实的资料就不收，详卡不出这一栏。
- 《大东舆地图》：`python -X utf8 tools/build_daedong.py`（需 pillow numpy scipy；`--fit` 重新配准，参数存 `tools/daedong_fit.json`）。Commons 的拼接全图（17837×30000，奎章阁藏本，公有领域）半尺寸解码后按区裁切到 `src/assets/daedong/NN.jpg`（长边 1200），尺寸写 `src/data/korea/daedong.json`。配准：小图上笔画密处为陆地，只取本土大陆块（岛群会把陆地往海里撑，对齐整体偏南），三次多项式先最大化与今天陆地的 IoU，再加上海岸线距离一起细调（IoU 约 0.91、海岸平均约 5 公里）；济州与罗先按古图位置手工框（`MANUAL`）；外框只算面积够大、离主体 60 公里内的陆块，至少 70 公里见方。改了配准后把 29 块拼成总览图逐块看过（城市是否在框里）再提交。详卡「《大东舆地图》上的这里」（`ddHTML`），点开 `dialog#kr-dd-view`，点图在适应窗口 / 原尺寸间切换；图注写明是估算。
- 半岛国力（korea-power.js）：`#kr-eras` 末尾的「国力」（`data-era="power"`，地图仍是今天的区，`todayMap()`）。数据 `src/data/korea/power.json` 由 `python -X utf8 tools/fetch_sejong.py [--verify]` 生成：抓国史编纂委员会网站的《世宗实录·地理志》（kda_400PP 道页 → 组页 → `_NNN` 属县页，缓存 `.cache/korea/sillok/`），解析原文「戶N, 口N」「墾田N結」，打印各道合计与道总论的差（南边 ≤10 户；两界收了 1432 年后新设的州镇，对不上）。安峡县原文残缺按道总数补（`PATCH`），汉城府只有户数。定位：名字对上今天市郡的直接定，其余写在 `tools/sejong_locate.py` 的 `MANUAL`，`--verify` 用韩文维基（或写明的条目）/ 地理志原文「四境」核对，全部要通过。罗先没有郡县，不排名。卡片 `#power-card`（`kp.*` 文字），点榜单选区；指标 pop / hh / kyol / density / rise（1432 户数排名 → 今日人口排名）。
- 半岛古战场（korea-battle.js）：`src/data/korea/battles.json` 六场（三语同文件，4 段，路线示意），`python -X utf8 tools/korea_battles_tool.py` 核对结构与 `evidence`（要出现在 `sources` 的维基条目里）。沿用 `#btn-battle`（文字换成「古战场」）、`#battles`、`#battle-hud`；地图系列 `b-routes / b-origins / b-markers / b-impact` 在 korea.js 里先建好。向导 `startBattle / narrate / endBattle`，旁述不扮演人物；合战中点地图不换区；深链接 `#map=korea&battle=salsu`。`setupBattleVoice` / `setupHudFold` 在 shell.js，两种地图共用。
- 历代图层（三国 / 新罗 / 高丽）：`build_korea_eras.py` 里新罗九州按韩文维基「신라의 행정 구역」表格投票（郡治两票，同名取离州治近的，没提到的按相邻市郡补，庆州为王京）；三国由九州来历推出（`OLD_KINGDOM`，康州与金官为伽倻）；高丽按 `GORYEO_DEFAULT` + `GORYEO_EXCEPT`，并与《高丽史·地理志》（维基文库卷 56–58）同名郡县核对（`CHECK_SKIP` 是同名不同地）。有 `units` 的图层按单位顺序取色（`unitColor`），`out` / `tamna` 用中性色。
- 新手教程：半岛另有 7 步（`tour.kr*`），第一次进半岛（不带 pref 的链接）自动开始，记在 `je.ui.tourKorea`（smoke 预先写入）；欢迎卡与设置里可重看。

## 日本与朝鲜半岛的共同历史（shared.js）

`src/data/shared_history.json` 三语写在同一个文件里，两种模式共用一个对话框（`dialog#shared`），入口在两种模式的欢迎卡与半岛详卡（`data-act="shared"`，不带 `data-key` 时打开最早的一件）。9 件事按年代排（`key`：torai / baekgang / mongol / imjin / tongsinsa / annex / rule / normalization / dprk），标题即标签名，要短到手机一行放得下；`years` 可以是字符串或三语对象。标签一行横向滑动（`.sh-tabs` 必须 `flex: none`，否则在对话框里被压扁），选中的那件滚到中间（`showTab`）。每个事件：各方的称呼（`names`）、**双方都承认的事实**（`facts`，按语言）、**各方的主流叙述**（`views`：日本 / 韩国 / 朝鲜）、来源（维基百科条目）。写作规矩：措辞用「某方的主流叙述」而不是「某国人认为」；有充分史料的事实（如河野谈话承认军方参与慰安所、1965 年协定的「完全且最终解决」条文、2018 年大法院判决）照实写，不做假平衡；网站不下结论。新增事件时三层都要有、三语都要齐，smoke `shared` 会核对两种模式内容一致。

## 有争议的地区（disputed.js）

竹岛（独岛）与北方四岛（南千岛群岛）在两种地图里都按同一规矩画：中性灰、不涂任何一方的颜色，两个名字并列且顺序固定（实际管辖方的叫法在前，括注有争议：「独岛 / 竹岛」「南千岛群岛 / 北方领土」），点开只列双方立场（出处维基百科），不作判断。

- **数据文件不动**：japan.json 与市区町村文件里这些岛仍属岛根县 / 北海道；全国地图（app.js → `createMap(..., { disputed, onDispute })`）与市区町村下钻（muni.js `load`）在注册地图前用 `splitDisputed` 把中心落在 `DISPUTED[k].area` 外框里的多边形拆出来。外框要避开根室半岛（纳沙布岬 145.80）与野付半岛外的小岛（145.32）；`disputed_split` 场景会核对。
- **旧国底图不叠争议层**（五畿七道、古国国力、古国巡礼、时间轴）：那是历史边界，1869 年的千岛国确实包括国后、择捉。
- 全国地图：`disputed` 是只负责画的 custom 系列（`silent`），点击按坐标判断（`chart.getZr()` 的 click + `dspAt`；自定义路径的命中检测在交互后不可靠）；`disputed-names` 是标签，竹岛另有空心圆点（`point: true`），点标签 / 圆点走系列点击。点在争议岛上时 `prefs` 的点击不选县。合战与旧国底图时不画。
- 卡片借用 `#art-card`（`data-act="card-close"` 关闭）；定位不在任何县但落在争议外框里时也弹这张卡。
- 下钻：被拆出的岛组成伪要素 `dsp-<key>`（`pseudo: true`，不计入标题的市町村数、不出户籍、`placeOf` 返回 null）；北方四岛的六村整体带 `disputed`，信息卡多一行。两者都着灰色，图例单列「有争议」。
- 半岛模式的独岛卡片也用 `disputeCard('takeshima')`（文字键 `kr.dokdo.*`）；北方四岛的文字键 `dsp.kurils.*`。

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

- **实权与此地年表（3.13）**：`guide.setRegimes(regimes, eras)`（app 启动时后台下载 regimes）后，离线自由提问命中 `kw.power` 走 `powerAnswer`（问句里有时代名就只列与该时代重叠的各段，否则列全部）；时代滑块 `guide.setEra(era)` 让快捷提问多一个 `q.pw`（`key: 'pw'`）；在线时 `<regimes>` 与 `PW_RULE` 一直写进 System Prompt。下钻选中单个市区町村时 app 的 `townOf(pid, code)` 算出此地年表交给 `guide.setHometown(items)`：离线 `placeAnswer` 末尾接 `o.place.ht` 与最多 10 行（不含彼时今日条目），在线写 `<hometown>` 与 `HT_RULE`。
- **上下文联动**：用户每切换一个地区，向导立即换人设并以该县完整 JSON（令制国演变、沿革、方言等）重建 System Prompt；对话历史随之重置。
- **System Prompt 规范**（见 `buildSystemPrompt`）：
  1. 角色设定：身份、自称、口吻；用中文回答，可点缀日语原词并注假名。
  2. 注入当前地区 JSON 作为「史料」，回答优先依据史料；史料外的内容需标明“据传/一说”，不得编造年份与人名。
  3. 回答简洁（约 150–300 字），多用具体年份、人物、地名。
- **快捷提问**：每县 3 个（战国时这里战况如何？/ 用当地方言和我打声招呼 / 古今界线）。
- **无 API Key**：快捷提问与关键词匹配的自由提问（含“地缘梗”）由本地数据以当前角色第一人称拼出，打字机效果输出，并提示可接入 API 解锁自由对话。
- **有 API Key**：流式调用 —
  - 接口类型下拉里的 DeepSeek（`api.deepseek.com/v1`）与通义千问（`dashscope.aliyuncs.com/compatible-mode/v1`）只是预填了地址与模型的 OpenAI 兼容接口（`DEFAULT_API`，store.js；两家都允许浏览器跨域调用），走下面同一条路。
  - OpenAI 兼容：`POST {baseUrl}/chat/completions`，`stream: true`，解析 SSE `choices[0].delta.content`。
  - Claude：`POST https://api.anthropic.com/v1/messages`，带 `anthropic-dangerous-direct-browser-access: true`，解析 `content_block_delta`。
  - Gemini 原生：`POST {baseUrl}/models/{model}:streamGenerateContent?alt=sse`，Key 放 `x-goog-api-key`（支持新式「AQ.」Key；OpenAI 兼容端点强制要 `Authorization`，AQ Key 在那里会报 ACCESS_TOKEN_TYPE_UNSUPPORTED），解析 `candidates[0].content.parts[].text`，跳过 `thought` 部分。

## 多语言（中文 / English / 日本語）

- 界面词典在 `src/js/lang/{zh,en,ja}.js`（各 `export default {键: 文}`），`i18n.js` 用顶层 `await import()` 只载入当前语言的那一份（以前三语都在 i18n.js 里，183 KB）。三种语言的键必须一致，`t()` 不再回退到中文；`check_data.check_ui_strings` 核对键与 `{占位符}`（译文可以不用中文里的某个占位符，如自称 `{self}`，但不能多出中文没有的；调用处同时给几种写法的列在 `UI_ALT_VARS`）。
- `src/js/i18n.js`：语言在页面加载时确定（`je.ui.lang` > 浏览器语言：ja→日语、en→英语、其余中文），切换语言会重新载入页面（保留 `#pref`）。
- 界面文字：`t(key, vars)` 查词典 `D`；静态 HTML 用 `data-i18n` / `data-i18n-ph` / `data-i18n-title` / `data-i18n-aria`，由 `applyStatic()` 填充。
- **分类键不翻译**：`region`、`circuit`、`history_timeline[].era`、`ramen.category`、`sake.quadrant`、`map_filters.*` 等是逻辑键，显示时用 `label(group, key)` 转换。
- 数据翻译是**覆盖层**：`src/data/i18n/{en,ja}/prefectures/NN_slug.json` 与 `historical_events.json` 只含文字字段，按 `deepMerge` 叠加到中文底本（对象逐键、对象数组按下标、字符串数组整体替换）。
- `src/data/i18n/manifest.json` 记录各语言已翻译的县 id 与 events；未列入的县显示中文并带“翻译中”提示（不发请求，避免 404）。
- 向导：史官人设的译文在 `PERSONA_TEXT`；System Prompt 的角色段与回答规则按语言生成（`ROLE` / `PROMPT_RULES`），离线解答模板与关键词正则也在词典里。
- 日语与英语界面通过 `:root[lang="ja"]` / `:root[lang="en"]` 改用 Noto Serif JP 与日文系统字体，显示日文字形。

## 设计规范

- **国絵图浅色主题**（3.23 改版，方案见 `docs/superpowers/specs/2026-11-08-kuniezu-redesign.md`）：楮纸 `--bg #e7dec6`、胡粉 `--panel/--card-bg #f4efe2`、群青淡刷的海 `--sea`、墨 `--ink #2a2520`（正文、边线、选中的筛选按钮）、朱 `--shu #b3302a` 只用于「印」（品牌印章、盖印、主按钮、当前选中的地区）、黄土 `--kin #7a5719`（已探索 / 次强调）。浮在地图上的卡片用 `--float`（一道硬投影），弹窗用 `--lift`；不用发光阴影。地图：陆地胡粉、墨线县界，选中地区的名字写在短册里（map.js `SLIP`，中日竖排、英文横排），凡例色块是小判形椭圆（`.sw`）；地图标签一律墨字 + 纸色描边。数据配色是中明度的岩绘具色，`check_data.check_palette` 核对：文字 token 在三种纸色上 ≥4.5，各分类色与墨 ≥3、与陆地 ΔE ≥0.08（中性的化外 / 国人割据等除外）、同一组内两两 ΔE ≥0.05。新加颜色先过这项检查。半岛模式仍是深色的丹青皮肤（`:root[data-map="korea"]` 把 `--ink` / `--on-shu` 反过来）。
- 布局：顶栏 + 左 58% 地图 + 右 42%（上：详卡，下：向导，中间拖动条可调比例 20–80%）；窄屏改为上下堆叠。
- 响应式断点：≤900px（及高 ≤520px 的横屏）改为底部标签栏三页切换（`body[data-tab]` = map | detail | guide，见 `setupTabs`）：地图 / 详卡 / 向导各占满顶栏与标签栏之间，不整页滚动；选县时留在地图页，「详情」标签显示县名并闪一下；打开下钻或合战切到地图页；名将解说的「提问」切到向导页；不带 muni 的县链接直接打开详情页。横屏另有一组压缩样式（顶栏一行、标签栏横排）。≤560px 为手机：顶栏一行（印章、地图开关、探索计数、`#btn-more`），合战 / 御朱印 / 声音 / 设置 / 语言收进「更多」菜单（`#topbar-menu` 即宽屏的 `.topbar-right`，`body.menu-open` 时浮出；shell.js `setupMenu`，点菜单里的按钮或外面收起，声音开关除外；教程第 8 步在手机上先打开菜单）；工具条里 `.toolbar-row` 变成 `display: contents`，图层收成 `#layer-pick` 下拉（`body.layers-open`），与滤镜同一行，年份 / 指标等子行在第二行；图例只留一行色块（点一下 `.show-cap` 看说明）；时空滑块一行；时代刻度换成当前时代名、快捷提问单行横滑、合战面板默认折叠、地图用 `MOBILE_VIEW` 放大视角。手机上按钮大多 ≥36px 高、字号 ≥12px（style.css 末尾「手机体验」一节）。smoke 点顶栏按钮与图层要用 `self.top()` / `self.layer()`（手机上先开菜单 / 下拉）。改界面后用 390×844 尺寸截图检查。
- **底部抽屉**（≤900px 且不是横屏手机，`body.sheets`，shell.js `setupSheets`）：地图上的 `.muni-card`（含国力、战国、浮世绘、古国巡礼、巡礼、我在哪、市区町村卡）贴底、最高 44%，顶部 24px 是 CSS 画的把手（卡片内容由各模块整块重写，不能放真元素）：点把手或上拖 → `.sheet-full`，下拖收回，再下拖点它的 `.muni-card-x` 关闭；重新出现时回到半截。触摸用 touch 事件（按住把手时拦下滚动），鼠标用 pointer 事件。`watchCards`（shell.js）统一处理所有卡片的 `map.setInset`（展开成整屏时不动），之后 `map.reveal()` 把 2 秒内点过的地方挪进露出来的那块；半岛地图同样调用。卡片与搜索下拉背景是不透明的 `--card-bg`。
- 能横滑的按钮行（`.filters`、图例、快捷提问、`.toc` 等，见 shell.js `HINT`）有内容未露出的一侧加 `.more-r` / `.more-l` 渐隐，选中项变了会滚进视野。
- 详卡目录（toc.js `addToc`，日本与半岛详卡渲染后调用）：扫 `.section-h` / `.art-section-h` / 地域修罗场与圣地巡礼的 summary，在统计格下放一行吸顶按钮，点了展开折叠并滚过去，滚动时标出当前一节。江户诸藩超过 8 个时先列 6 个（`.hn-x` + 「显示其余」`data-act="hn-more"`）。年表 `.rl-jump` 按时代分组跳转。
- **横屏手机**（高 ≤520px 的横屏，`SHORT`）：地图页工具条一行（图层左半、滤镜右半，子行换到第二行左侧），底部一行（图例左半、去掉说明；时空滑块右半、只留播放键 + 滑轨 + 时代名）；各种卡片（`.muni-card`，含国力榜、古国 / 巡礼 / 我在哪卡）改放右侧；`layoutCenter` 把地图中心放在上下两行之间，取景用 `LANDSCAPE_VIEW`；合战时 `setInset({ left })` 让地图避开左上的合战面板。转屏（竖屏手机 / 横屏手机 / 宽屏三种形态之间）时 `resize` 回到该形态的默认取景。smoke 有 `landscape`（844×390）视口，只跑 `LANDSCAPE_CASES`。
- 新手教程（tour.js）：`createTour(steps)`，步骤 `{ key, target, before }`，文案 `tour.<key>.h/.b`；目标不可见的步骤自动跳过；窄屏的「详情」「向导」步骤指向底部标签按钮。首次访问且地址栏不带 `pref=` 时自动开始，设置弹窗与欢迎卡可再打开；走完或跳过都记 `tourDone`。
- 欢迎卡「从这里开始」（3.25）：三个按钮只是替用户按下已有的控件——`st-home` 切到地图页、聚焦搜索框并提示「选中后点古代户籍」，`st-sg` 打开战国势力滤镜，`st-loc` 点「我在哪」。不要往这里加新功能入口，入口多了就失去意义。
- 键盘与读屏（3.25）：页面第一个可聚焦元素是「跳到搜索」链接（`.skip-link`，平时在屏幕外），`#map` 有 `aria-label` 说明用搜索框；「/」聚焦搜索框（正在输入或有对话框时不抢）；空搜索框按 ↓ 按编号列出 47 都道府县（`allPrefs`），Enter 打开。地图本身是 canvas，键盘用户一律走搜索框。
- 彼时今日数据（kako.json，约 160 KB）在浏览器空闲时才下载（`requestIdleCallback`，最多等 1.5 秒），让首屏先拿地图与数据包；`#kako=` / `#bday=` 链接立即下载。
- 刘海屏安全区域：页面用 `viewport-fit=cover`，四周边距统一走 `--safe-t/r/b/l` 变量（取自 `env(safe-area-inset-*)`），弹窗高度用 `--vh`（支持时为 `100dvh`）。新增贴边或 `position: fixed` 的元素时要加上对应的安全区域边距。测试时可在页面里覆盖这些变量模拟 iPhone（竖屏 上 47 / 下 34，横屏 左右 47 / 下 21）。横屏手机（高 ≤520px）同样走上下堆叠布局。

## 时空滤镜

| 模式 | 分类依据 |
|---|---|
| 探索进度 | 未探索 / 已探索 / 当前 |
| 现代区划 | `region` 八地方 |
| 五畿七道 | **底图换成 68 令制国真实边界**（`provinces.json`，首次选该滤镜时才下载），按旧国的 `circuit` 着色；加载失败时退回按县内首个令制国着色 |
| 战国势力 | **底图换成 68 国（824 年）**，按 `sengoku.json` 的所选年份着色（见下「战国势力」）；数据未就绪时退回 `map_filters.sengoku_1572` 按县着色 |
| 幕末阵营 | `map_filters.bakumatsu`：戊辰战争时县内主导势力立场（萨长土肥 / 新政府方 / 佐幕方 / 天领直辖） |
| 古国国力 | 底图同样换成 68 国（824 年），按 `kokuryoku.js` 的指标着色（见下「古国国力」） |

一县多藩、势力交错时只能取主导势力，属近似表达；切换只改 `geo.regions[].itemStyle`，不重载 GeoJSON。

### 令制国底图（五畿七道）

- `python -X utf8 tools/build_provinces.py`（需 `pip install shapely`，仅生成时用）：市区町村先按「旧国 × 县」合并成小块，**一起** `coverage_simplify`，再拼出旧国与县界——两套边界由同一批边组成，叠加时完全对齐。跨两国的市町村整块归 `province`（主要一方），国界是近似。改了市区町村数据或 `province_overrides.json` 后重跑；`check_data` 会核对 68 国与市区町村里出现的旧国一致。
- 输出：`features`（`key` 日文国名、`zh/ja/en`、`kana`、`circuit`、`prefs` 今属县 id；`key: "-"` 为奄美·小笠原等令制外）+ `pref_borders`（只含陆上县与县交界的折线，不含海岸线）。
- 前端（map.js）：`setProvinces(g)` 注册第二张底图 `provinces`；`provMode()`（历史图层 + 五畿七道 + 非时代 / 非合战）时 geo 换图，叠加 `provnames`（按面积排序的国名，`hideOverlap`）、`prefborders`（虚线县界）、`prefactive`（选中县轮廓，取自 japan.json）。两张底图共用 `boundingCoords`（japan.json 的范围），换图时比例与位置不变。点击时按坐标在 japan.json 里找所在县（`prefAt`），仍走 `onSelect(县 id)`。
- 测试里换算点击位置时，`convertToPixel` 给的是相对地图容器的坐标，要加上 `#map` 的 `getBoundingClientRect()` 偏移。

### 古国国力（kokuryoku.js）

- `python -X utf8 tools/build_kokuryoku.py`（需 shapely）：今日人口与市区町村数按市区町村的 `province` 汇总（跨两国的整个算给主要一方 → 约数，界面注明）；面积取 provinces.json 的国界；江户人口（享保6年 1721、弘化3年 1846）与石高（天保5年 1834）取日文维基「江戸時代の日本の人口統計」的旧国别表（幕府调查，不含武士等；CC BY-SA 4.0，已登记）。宿敌 PK 用到的郡（`DISTRICTS`，如近江国甲贺郡）按明治旧郡汇总，只算整体属于该郡的市町村。改了市区町村数据后重跑，再 `build_bundle.py`。
- 指标 `METRICS`：pop / pop1721 / density / koku / rise（1721 人口排名 → 今日排名的升降）。令制外（虾夷地、琉球）不计江户指标与逆袭。量级指标按排名分五档着色，逆袭按名次升降分五档。
- 反常识头条全部由数字算出（`headlines()`），条件不成立的那条不出；东京巨蛋按棒球赛约 43,500 席（日文维基）。宿敌 PK 预设在 `PK`，一方可以是几国之和（长州 = 周防 + 长门）或一个郡。
- 前端：`map.setPower(power)` 后滤镜 `power` 生效（`powerMode()`；旧国边界未载入时按探索进度显示）；`body.power-mode` 显示指标行 `#power-metrics`，一进入就摊开 `#power-card`。卡片摊开时 `map.setInset` 让地图中心避开它（宽屏让右侧、窄屏让底部）。点地图上的国 → `onPower(key)` 高亮榜单该行；点榜单 → `map.focusProvince` 飞过去。

### 战国势力（sengoku.js）

- 数据：`python -X utf8 tools/sengoku_tool.py [--check]` 写出 `src/data/sengoku.json`。`DATA` 是每国 `[1467, 1560, 1573, 1582, 1590, 1600]` 的主要控制者（`CLANS` 的键；1600 年为 `SIDES` 的东军 / 西军 / 倒戈 / 分裂 / 观望），几家分占写进 `SPLIT`（界面「分治」），拿不准的用总称 `gunyu`（国人割据）/ `contest`（多方争夺），不硬涂。核对（日文维基，缓存 `.cache/sengoku/`）：1467 年要在该国条目「守護 → 室町幕府」名单里任期覆盖 1467 的那一行出现家名；其余年份要该国条目出现家名，或该家条目出现国名；通不过的人工确认后写进 `CHECKED`（条目 + 原文）。1600 年的倒戈 / 分裂 / 观望必须在 `SIDE_EV` 写依据原文。1590 年按 `Y1590` 给大大名的国单独着色，其余为 `toyo_small`（丰臣直辖与中小大名，代表人物秀吉，人物卡按全国计）。`HEADS` 是各年份各家的代表人物，Wikidata（缺时取信息框）的生卒要覆盖该年，或在 `HEAD_EV` 写原文依据。
- 实权（3.11）：`python -X utf8 tools/regimes_tool.py` 写出 `src/data/regimes.json`。`PERIODS` 每段 `{key, frm, y, nominal, real, seat, note, tab, ev}`，文字三语自己写；`ev` 是 {日文维基条目: [必须出现在条目里的词]}（分界年份、人名、制度名），有一个不在就报错不写出（缓存 `.cache/power/`）。有两种通行说法的分界两种都写（「1185（一说 1192）」）。`tab` 是点「看…名单」跳去的页，前端按 `from` 滚到开始年不晚于它的最后一组。年表对话框（`rulersHTML(..., regimes)`）第一页就是它，欢迎卡「谁在掌权」（`data-act="pw-open"`）不经战国图也能打开（`ensureRulers` 补下载 rulers / people / regimes）；战国年份行的「年表」也先开这一页。深链接 `#rl=power|emperor|shogun|shikken`（打开时地址栏写成这样，关掉时恢复）。`check_data` 的 `check_regimes` 核对三语与顺序。
- 天皇 / 将军 / 执权：`python -X utf8 tools/rulers_tool.py`（需 zhconv）解析「天皇の一覧」「征夷大将軍」「鎌倉幕府の執権一覧」的 wikitext，核对代数连续、起止不倒退；西历年只取括号里的（前面的是和历）；后小松从 1392 年南北朝合一算起；尊氏、义稙的再任带 `again`。女性天皇英文写 Empress（`EMPRESS`）。
- 人物详写：`python -X utf8 tools/people_tool.py [--check]`（需 pillow）。简介自己写（维基正文是 CC BY-SA），`ev` 里的每个词与简介里的西历年都必须出现在该人日文维基条目里，三语年份要一致；肖像取 Wikidata P18（没有则取日文维基条目首图），收公有领域与 CC BY / BY-SA（记下 `author`，人物卡注明作者与许可），宽 240px 存 `src/assets/people/<QID>.jpg`，人工看过不是肖像的（花押、石碑）写进 `NOT_PORTRAIT`；`crest` 只写确实是该图案的家纹。
- 奥羽按郡与虾夷地（3.10）：`tools/ou_units.py` 的 `UNITS` 定义 43 个分区（战国时的郡或郡群，如「糠部」「胆沢・江刺」「大崎」「庄内」）与「和人地」，市区町村按第一个整体属于的明治旧郡归入，横跨几郡的市与没有旧郡记录的在 `MUNI` 人工指定（市役所所在的旧郡），和人地按近世松前地（龟田—熊石）的市町村 `WAJINCHI`。`build_provinces.py` 把分区当作小块的第五个维度，与旧国、县一起 `coverage_simplify`，所以分区界与国界、县界由同一批边拼成；输出 `sengoku_units.json`（去掉陆奥、出羽、虾夷地，加上 45 块；剩下的虾夷地 = 阿伊努的土地）。`sengoku_tool.py` 的 `OU` 是每块 6 个年份的归属（1467 仍为总称 `ou`：奥羽没有一般的守护），`OU_SPLIT` 分治，核对规则同各国（分区的条目列表里出现家名，或家的条目出现郡名），通不过的写 `OU_CHECKED`（如葛西大崎旧领 13 郡、蒲生「会津40万石、中通り20万石弱」、伊达「陆奥出羽之内 13 郡」），1600 年观望写 `OU_SIDE_EV`；输出 `units` 与 `muni_units`（团体代码 → 分区，古代户籍用，精度印「郡」）。陆奥、出羽、虾夷地整国的旧记录仍在 `provinces` 里。`ainu`（阿伊努的土地）在 `CLANS` 与 `SIDES` 里都有，前端算总称 `LOOSE`：不插旗、不出总览。前端 `map.setSengokuUnits(u)` 后 `buildProv('sengoku')` 是战国图的底图（`curProv()`、旗、合并边界、接壤都用它；`edgesOf(features)` 按底图缓存），`createSengoku` 的 `keys` 含分区，`entry` 先查 `units`。分区没有石高：领有分区的家 `clanStats().ou`，石高写「≥」（只算其余部分）或「—」，不排名（`rankOf` 只排没有分区的家），全国合计仍按 68 国国高；柱状消长在一年都没有石高时按块数画。图例最多 13 项（`slice(0, 13)`），其余合成「其余 N 家」。旗的大小与缩小时插不插按领地面积相当于几个国（68 国面积中位数，≥1.8 才在缩小时插）。
- 石高：`koku` 是各国 1598 年太阁检地高（日文维基「石高」的「旧国別石高の変遷」表第一列，`koku1598()` 解析并断言山城 / 近江的值）。壱岐、对马那一列是 0（未检地）记 null；出羽国的数字条目自己注明明显偏少（置赐郡等可能算进陆奥），势力总览含出羽或陆奥时注明。
- 家纹：`python -X utf8 tools/crest_tool.py [--sheet]`（需 pillow）取各家条目（跟随重定向）信息框的「家紋」「家紋名称」，信息框没有的只在 `MANUAL` 写明图档与条目原文（工具核对原文在条目里）才收；Commons 只收公有领域 / CC0 / CC BY / CC BY-SA（记作者与文件页）。图先铺白底，四周偏亮取深色为图案、偏暗（黑底白纹）取亮色，自动拉对比度，裁边成 96px 方图，判断反了的写 `FLIP`。`--sheet` 存总览图 `.cache/sengoku/crests-sheet.png`，改动后人工看一遍。一揆、寺社与总称不配家纹（`NOT_FAMILY` / 无条目）。`MANUAL` 现有三家：前田（分家信息框）、三木（「姉小路氏」信息框的家纹名剑菱 + Commons 标明剑菱紋的公有领域图）、堀越公方（足利一门，取「足利氏」信息框的足利二つ引）；`MANUAL` 的出处条目写进 `clan_crests.json` 的 `wiki`。家纹名三种界面都显示日文原名。改完重跑 `sengoku_tool.py` 把 `mon` 并进 sengoku.json。
- 合并国界（map.js）：`edgesOf()` 由 provinces.json 824 年各国轮廓找出两国共用的线段（相邻国的边共用同一串顶点），按国对串成链；`sgedges` custom 系列按 `sg.edgeKind(a, b)` 分三类画：同一家（都不分治、都不是总称 `LOOSE`）不画、两家之间画亮色前线（深色衬底 + `#f3e2c0`）、其余照常画国界；战国图下底图国界压成 0.5px 半透明、县界虚线更淡。
- 家纹旗（`sgflags` scatter）：`sg.banners()` 给出当年各家独占的国（1600 年不插），旗插在离领地面积加权重心最近的那一国、标在国名上方（`symbolOffset`）；领国越多旗越大，缩放 < `KOKU_ZOOM` 只插 ≥2 国的家（`sgNear`），正在看总览的那家放大。旗图由 `sg.loadIcons` 用 canvas 画（深色方牌、代表色描边、家纹 `source-in` 涂金；没有家纹写家名两个字），画好后重画。点旗 → `onClan`。
- 势力总览（`clanCard`）：图例里的家（`updateLegend` 第 4 项，总称没有）、国别卡里的家名（`.sg-clan`）、旗、深链接 `&sgc=键` 都能打开；`share(国, 家)` 独占 1、分治按家数平分。卡片：领国数（+分治）、推算石高（按份额加权）、占全国、当年名次（不含总称）、领国按钮（点了开该国卡片）、1467–1590 柱状消长（看 1600 年两军时不画；点柱子换年份）、陆上接壤的别家（`setAdjacency` 由 `edgesOf` 传入；只说相邻，不写敌友）、家纹出处。地图聚光：本家原色、相邻国压暗 45%、其余 78%。换到没有这一家的年份（如家族 → 1600）总览自动关掉；`card()` 返回空时 app 关卡片。向导 `guide.setSengoku(sg.clanGuide())`：快捷提问 `q.sgc`，离线 `sgAnswer` 的 clan 分支，在线 `SG_CLAN_RULE` 要求不从接壤推断敌友。
- 前端：选「战国势力」时 `ensureSengoku` 下载 sengoku / rulers / people 三个文件（与旧国边界一起），`map.setSengoku(createSengoku(...))` 后 `sgMode()` 生效（底图 824 年）。`#sg-years` 年份行（选的年份存 `ui.sgYear`，默认 1560）末尾「年表」打开 `dialog#rulers`（`rulers.js`：天皇按时代分组写都城，镰仓到江户写平安京 + 幕府所在地）。点国 → `#sg-card` 国别卡（6 个年份 + 代表人物），点人名或年表的一行 → 人物卡（`showPerson`；从年表来的「返回」回年表）。图例：超过 12 家时只占一国的合成一项。地址栏（`pageHash`）在战国图下带 `&sg=年&sgp=国`，打开这样的链接会切到该滤镜、年份并弹出该国卡片（手机上留在地图页）。点开一国时 `guide.setSengoku(sg.guideInfo(国))`：向导多一个快捷提问 `q.sg`，离线 `sgAnswer` 列出六个年份，在线写进 System Prompt（`SG_RULE` + `<sengoku>`）。

### 彼时今日（kako.js）与江户诸藩（han.js）

- 彼时今日的地点（3.14）：地点 QID 为日本（Q17，坐标 (136, 35) 在滋贺）的跳过、换下一个；地点的日文标签是都道府县、旧国、政令市（由市区町村名「○○市○○区」得出）或 `BIG`（江户、东京、京都…）的记 `g: 1`。`check_kako` 断言没有条目在 (136, 35)。
- 彼时今日数据：`python -X utf8 tools/kako_tool.py`（需 shapely；缓存 `.cache/kako/`，Wikidata 实体只存精简字段 `titles-compact2.json`，原始实体几万条会吃掉几 GB 内存）。读日文维基 366 个「N月N日」条目的「できごと / 誕生日 / 忌日」。事件：链接的条目在 Wikidata 上有 P585/P580，精确到日时年月日要对上，只到年时年份对上；地点取 P625，没有就取 P276/P131 的坐标。生卒：只看这一行第一个链接，P569/P570 年月日要对上，地点取出生地 P19 / 去世地 P20；1880 年以前出生的全收，1880–1949 年出生的近代人物要已去世（有 P570），知名度按日文维基 2025 年全年浏览量（`views-2025.json`；各语言条目数不可靠——日本足球国脚的条目被机器人建到几十种语言，只用条目数 ≥`PRE` 粗筛），每天取浏览量最高的 `MODERN_CAP`（2）位且 ≥`FAMOUS`，这一天不足 3 条时再补到 3 条（≥`FILL`）。`check_data` 的 `check_kako` 要求 366 天每天至少 3 条。坐标须落在某县（japan.json，3 公里内容差），三语标签齐全才收。日期按公历（1582 年以前按儒略历，与维基一致）。
- 前端：`dayOrder(list, 日期, 种子, 去过的县)` 按种子洗牌（`ui.kakoSeed`，第一次随机生成，只存本机；去过的县稍微靠前），每页 3 条，「换一批」翻页，日期选择器换日子，`#kako=MM-DD` 深链接。欢迎卡里插在「新手教程」按钮前，底部「🎂 生日帖」打开 `dialog#bday`（bday.js：这一天全部诞生 / 忌日 / 事件，三格数字——条目数的全年名次、最早一件、条目最多的县；名字与古代户籍的户主名共用 `kosekiName`；存图沿用户籍的和纸样式，`saveImage` 与户籍共用；深链接 `#bday=MM-DD`）；县详卡末尾 `kakoPrefHTML`（本县最近的 5 个周年）。点一条：`map.onSelect(县)` + `map.setKako({c, label})`（朱红图钉，Esc 去掉），窄屏切到地图页。
- 江户诸藩：`python -X utf8 tools/han_tool.py`（需 zhconv；缓存 `.cache/han/`）。名单取「藩の一覧」，江户中途废绝、转封的也收（变迁框止于 1600 年以前的不收），`y` 为起止年（`span`：止年取 Wikidata P576 与「行政区の変遷」框中较晚的，框里晚于 1871 的按 1871——框常写到后来的县；起年取框，没有取 P571；不详的为 null），`k` = 止年 ≥1871（两边都没有止年的看 `KEPT`）；不以正文有无「廃藩置県」判断（大坂藩、葛野藩等都提到这个词却早已废藩）；重定向到非藩条目（松平義行領）的不收；藩主取「歴代…」小节（没有就取标题带「藩主」的），列表行取第一个人名链接、表格取每行第一个以链接开头的格子、`;○○家` 也算分家标题，「藩知事」不收，`NOT_LORD` / `NOT_NAME` 滤掉官位、年号等非人名链接。所在县：工具里人工核对的 `PREF` → 名单里的国只对应一个县（68 国加明治国）→ 正文「現在の○○県」→ 分类「○○県の歴史」→ 正文提到最多的县；国与正文不一致时打印，核对后写进 `PREF`（名单会把一个藩列在几个国下，「現在の」也可能写的是转封地）。没有自己条目、重定向到本藩条目某一节的支藩（久居 → 津藩、黒石 → 弘前藩、岩崎 → 久保田藩、出羽松山 → 庄内藩）由 `branch()` 取那一节（没有「歴代」小标题的从「歴代藩主は以下の通り」往后读，立藩前的「歴代…領主」去掉），能解析出藩主才收，起年取那一节信息框的立藩年或名单的「（1669年 - ）」，写到废藩置县的记存续；fetch_seats 跳过这些（缓存里是本藩条目，会读成本藩的城）。条目没有藩主列表、藩主写在正文里的在 `LORDS` 人工列出（工具核对名字在条目里有链接），年份在 `YEARS`；明治初年才设、只有藩知事的藩不补。`check_data.py` 的 `check_han` 核对结构、年份与 k 一致、每县至少一个藩、除东京 / 山梨 / 冲绳外每县至少一个存续藩、存续藩总数 255–280 与几个锚点藩的县。工具末尾断言会津 / 浜松 / 甲府 / 徳島 / 备后福山 / 足守的县与存续藩数 ≥260。`han.json` 不在首页加载：`ensureHan()` 在第一次画详卡或打开古代户籍时才下载。藩主在位年份（3.11）：藩主行第 6 项 `[起, 止]`（再任的 `[起, 止, 起, 止]`，不详的省略），取藩主条目末尾的「○○藩主」导航模板里的「起年 - 止年」（`navboxes`，只缓存模板，`.cache/han/lord_navbox.json`；模板名 = 藩名 + 主，「柏原藩 (丹波国)」认「丹波柏原藩主」）；「? - 1626年」不收；只写一个年份的（多是在位不到一年），只在前一位的退任年与后一位的就任年夹出任期、且这个年份正好是其中一头时收（约 30 位）；藩的起年（变迁框写的常是最后一次设立：弘前藩 1871、下館藩 1702）早于最早的就任年时改为最早的就任年（止年不动，导航框的止年有时跨到改名转封后的藩），`check_data` 锚定弘前 1590、下館 1598；家名去掉读音括注；藩条目表格有「在任 / 在職期間」一栏时也读（`lords` 的第 4 项）；列表行只认紧跟在名字后面的「（1862 - 1868）」「 1602-1633」（记作 `L:起-止`），与 Wikidata 生卒年（`lifespans`，`.cache/han/life.json`）±1 相同、或不在生卒之间的不收；`NOT_LORD` 含「県」（白河藩的「白河県」曾被当成藩主）；按 Wikidata 生年，1870 年以后出生的从名单里去掉（「歴代」一节有的接着列明治以后的家主），两边差 1 年以上两边都不收，同一家后一位就任早于前一位的也不收；同一人在一个藩出现两次（再任）按出现顺序取各段。维基两处都没写的，取 Wikidata「担任职务」（P39）里标签正好是「藩名＋主」的职位的起止年（`positions`，`.cache/han/lord_p39.json`；两头都要有、在生卒年之间、不早于前一位的就任年；与导航框都有年份的 3664 位里 99% 起止相差不超过 1 年；同一人再任时已用过的那段不再给第二次）；约 94% 的藩主有年份；工具末尾断言上田藩松平忠固 1830–1858、会津藩蒲生秀行 1601–1612。前端 `reignText`，藩主名后小字，`lordOfFn` 的「某藩主」也带年份。藩主 ⇄ 彼时今日按日文维基条目名对上：`setLordDays(kako)` 后藩主名后面出现诞生 / 忌日日期小标签（`data-kako`，详卡与户籍里都能点，在地图上标出出生 / 去世地）；`lordOfFn(han)` 让彼时今日与生日帖的条目写出「某藩主」（han.json 载入后才有）。详卡 `hanSection`（折叠，存续到 1871 年的在前，其余在「中途废藩或转封」小标题下，带年份；点开藩看各家藩主，英文家名取首位藩主英文名的姓）。

### 古代户籍（koseki.js）

- 入口：市区町村详情卡（单个市町村）与「我在哪」卡片的「📜 古代户籍」按钮，深链接 `#pref=20&muni=1&m=20203&koseki=1`（关掉对话框时地址栏去掉 `koseki=1`）。`openKoseki(pid, code, pt)`：经 `locate.js` 的 `muniGeo(pid)` 取该市町村，`pt` 缺省为市町村质心（定位进来的用真实位置）。
- 各栏与精确度印（`seal`）：本贯（道 · 国 · 明治旧郡，市）、氏神（本国最近的一宫，方向 + 直线距离，市）、律令（最近的国府与国分寺，步行天数按 30 公里/天，市）、战国（`sengoku6`：所属旧国在 6 个年份的归属，国；没有 sengoku.json 时退回 `map_filters.sengoku_1572`，县）、幕末领主（郡；查不到时用县的 `edo_domains`，县）、戊辰（`map_filters.bakumatsu`，县）、今日国力（kokuryoku 的人口排名，国）、乡音（`dialect.phrases[0]`，县；按钮调 `guide.askQuick('dialect')`）。令制外（虾夷地、琉球）不出氏神与国府。只用已核验数据计算，不给单个市町村手写剧情。
- 幕末领主：`python -X utf8 tools/fetch_domains.py` 读 `tools/districts.json` 里每个郡的维基条目，解析「旧高旧領取調帳」后的「知行 / 村数」表（老式每格一行 `table()`；新式 hlist `hlist()`：知行在每行最后一个 `!` 表头格的列表里，几项 = 相给，村数在其后第一个 `|` 格）；没有表的读正文（`prose()`：「全域が○○藩領であった」「全域を○○代官所が管轄」「幕府直轄地（天領）であった」，这类没有町村数，记 0）；仍没有的、1896 年前后合并新设的郡按变迁框 `s-bef` 的前身郡（同县；名字按「・」「、」「および」拆开、去掉 `<br />`）相加（前身郡都要有带町村数的表；「○○郡の一部」只在原郡第一位的领主占九成以上时沿用，海津郡、稻叶郡因此不收）。县链 `meiji_chain` 每行带来源县（「福知山県の管轄地域が豊岡県」），前端 `cur` 只顺着本地当前的县走；主语是具体的岛、村、町的行不收。`build_bundle` 对合计为 0 的郡照收第一家（以前被滤成空记录，名取市等户籍报错），户籍写「某郡全域」（`ks.edo.all`）。知行规范化为幕府领（含代官所、郡代、预地）/ 旗本领 / 寺社领 / 公家领 / 相给（几方共管）/ 藩 / 明治初设的府县 / 其他；明治初年改名的藩（名古屋藩、鹿儿岛藩、高知藩…）在日文维基整页重定向到藩名单里的藩时记 `han`（重定向到某一节的是支藩，如久居藩 → 津藩#久居藩，不算），build_bundle 显示藩名单里的名字（尾張藩），户籍才能展开历代藩主；藩名去掉开头的旧国名（同名而国不同的保留，如纪伊田边藩），英文名取 Wikidata。`build_bundle.py` 按县 id → 郡名输出前 3 位 + 其余合计（`@bakufu` 等代号由前端翻译），中文藩名按 search.js 对照表反向转简体。解析器依次试（`parse()`，条目里「旧高旧領取調帳」出现几次就从每一处往后试——都筑郡开头先说石高）：老式表 `table()`、hlist `hlist()`、京都诸郡的按村勾选表 `matrix()`（各列皇室 / 公家 / 幕府 / 寺社…领打〇，一村一方的记给它，几方的记相给；皇室、宫家、公家、女官、地下役人、北面众、杂色领合为「公家領」，类别 `court`，前端 `ks.lord.court`）、按列的 hlist `colist()`（安倍郡：知行格 + 「2町 96村」格）、分项列表 `boldlist()`（小豆郡「'''幕府領'''（3村）」）、`bold_whole()`（那一段「全域が…'''仙台藩'''領」「幕末時点では…'''盛岡藩'''領」，町村数只在同一段里找——下一段常是 1889 年町村制的数）、`counted()`（「仙台藩領<br />（34村）」「49村が仙台藩領」）、最后正文 `prose()`。旧郡条目里只列一方的「後の'''北群馬郡'''域」记给后来的郡（`subareas`）。合并新设的郡：变迁框 `s-bef`（几个框取写了郡名的；「楢葉郡の一部（川前村を除く）」只除去点名的村，按整郡算）或正文「…の区域をもって'''仲多度郡'''が発足」「大住郡・淘綾郡が合併して」；前身郡不在 districts.json 的（高安郡）按郡名取条目，周准 / 周淮异体字都认，多轮合并（中新川郡 = 上新川郡の一部）。
- 主要郡（`python -X utf8 tools/fetch_main_gun.py`，在 fetch_domains 之后跑，输出 `tools/main_gun.json`，打包为 `main_gun`）：只处理按现有规则得不出江户一段的市区町村。① 市区町村条目（政令市的区试「浦和区」「中区 (浜松市)」，取正文提到该市的）原文里有「○○郡＋本名的町 / 村」（「西茨城郡 *** '''笠間町'''」「那珂郡に'''丸亀町'''」），郡名从长到短取第一个本县的郡（「仲多度郡」不截成「多度郡」）且有记录，匹配到的町村名正是本县另一个现存市町村（府中市条目里的「安芸郡府中町」）的不收，几个候选第一位领主不一致不写 → `{g}`；② 政令市的区没有旧郡：整市一级（市区町村文件的 `cities`）至少两个有记录的郡、第一位领主都相同 → `{lord, city}`，精度印「全市」（`ks.p.city`，名古屋各区 → 名古屋藩，广岛中区 → 广岛藩）；③ 江户与京都的市街 `TOWN`（千代田 / 中央 / 港 / 文京 / 台东，京都上京 / 中京 / 下京）→ `{lord: 幕府領, town}`，优先于郡的记录，工具核对：区条目提到前身的东京 15 区、「東京15区」条目写明当初是墨引（町奉行管辖）之地、上京 / 下京条目写明郡区町村编制法设区（中京区写由两区分出）、「京都町奉行」条目写明幕府所设。户籍 `kosekiRows` 与此地年表 `hometownItems` 都先看 `mainGun[code]`。按市区町村约 97%、按人口约 96% 有江户一段；没有的（伊豆诸岛、隐岐、富山新川三郡、浜松各区、东大阪等）是条目里没有按村的知行，不写。
- 此地年表（hometown.js，3.11）：`hometownItems({...户籍 ctx, geometry, kako})` → `hometownHTML`，插在户籍说明与按钮之间，存图时画在各栏之后（`kosekiImage(..., town)`，`ks.town`）。古代：本国；战国：与户籍同一分区 / 旧国的 6 个年份，相邻同一家的合并（1600 单列东西军）；江户：主要郡的幕末领主排第一的那一方，是藩就按 `findHan` 列出各家（年份 = 该家第一位有年份的就任 → 最后一位的退任，头一位或末一位不详时那一头写「…」；整家都不详时不写年份、排在前一家之后），存续到废藩置县的加一行 1871；主要郡没有记录（会津若松的北会津郡是 1879 年才分出的郡）时，只在其余几个郡排第一的领主都相同时才用，否则不写；彼时今日：坐标落在本市区町村多边形里的条目（`kakoIn`，同一 `q` + 类型只算一次），事件优先，最多 20 条，其余写「还有 N 条」。点一条走 `showKako(q, kt)`。冲绳（47）、北海道（1）与奄美群岛（46 里 province 为空的市町村）另加地区年表（`region`，打开这几处的户籍时才下载 `region_eras.json`，`kind: 'reg'`）。废藩置县之后：`ken`（`bundle/ken-<lang>.json`，build_bundle 的 `build_ken`，第一次打开户籍时才下载；来自 fetch_domains 的 `meiji_chain`：郡条目沿革里 1871–1890 年写着粗体县名的行）——本郡的链，废藩置县那一行列了几个县时按藩名（上田藩 → 上田县 / Ueda Domain → Ueda Prefecture）挑，挑不出不写；英文县名先看同名藩的英文名，否则只收以 Prefecture 结尾的标签。彼时今日里带 `g`（地点只到县、旧国、政令市或江户 / 东京）的条目不算进任何市区町村：北海道按 `sengoku.muni_units[code] === '和人地'` 取 all + wajin，否则 all + ezo；战国一段跳过 `outside`（令制外），1600 年跳过 `ainu`。
- 彼时今日的条目按钮都带 `data-kt`（born / died / 空）：同一人可能诞生与忌日各一条、地点不同，`showKako` 按 q + 类型找（曾把菅原道真的诞生标到太宰府）。
- 数据有误？（report.js，3.11）：`fixLink(说明)` 输出 `a[data-fix]`，捕获阶段的点击把 href 改成 `issues/new?title=&body=`（卡片说明、`location.href`、界面语言，文字 `fix.*`）。放在县详卡、半岛详卡、战国卡片（国别 / 势力总览 / 人物）、古代户籍、生日帖、年表末尾（`.fix-row`）。
- 城下町认藩（3.18）：`python -X utf8 tools/fetch_seats.py`（需先有 han.json 与 `.cache/han/wikitext.json`）。存续到 1871 的藩，藩厅取信息框「居城」或开头写着 藩庁 / 居城 / 政庁 那一句的第一个城、阵屋链接（江户城等在勤的城不算），坐标取条目 coordinates（退 Wikidata P625），没有坐标的用那一句的「現在の○○市」（本县）；落进的市区町村只在藩名或城名就在市名里时才算（大垣藩 → 大垣市、金沢城 → 金沢市；长冈市的与板藩、长野市的松代藩、奈良市的柳生藩这类合并进来的旧町不算，上越、丰田这类改了名的城下町也因此不收），同市几藩取市名以藩名结尾的。户籍「幕末领主」写「某藩的藩厅（某城）所在的城下町」+ 郡的町村统计，印「市」；此地年表江户一段同样用它。工具断言大垣 / 津山 / 彦根 / 上田 / 加贺。
- 取维基条目（pilgrimage_tool.pages）：跟随 API 的 `continue`（一批全文超过回应上限时只给一部分，以前不跟，缺的条目被悄悄当成没有内容）；取完仍有条目（不是「不存在」）没有内容就报错；带 `error` 的回应不进缓存。取全文时顺带取版本号，fetch_domains / fetch_main_gun / fetch_mura / yurai_tool 结束时写进 `tools/wiki_revisions.json`。fetch_domains 里藩名去国名的对应改为排序后固定取最长的全名（以前按集合顺序，结果随运行变化）。
- 户籍每一栏有 `data-k`（home / edo / mura / yurai…），测试按它取栏，不按位置。本贯的郡也优先用主要郡（笠间市写西茨城郡）。
- 明治町村（3.17）：`python -X utf8 tools/fetch_mura.py` 读各郡条目「町村制の施行により…発足」那一段（段首可缩进、年份在上一行或上面最近的高一级日期行，1888–1908 年；段首与条目之间的 `<!-- -->` 跳过；条目比段首低一级，北足立郡的「:*」也算），每行的新町村只认这一行写明的「現・○○」（「（現○○）」「（現：○○）」「（現在の○○）」也认，「現」要紧跟括号或句号——行方市有「現原村」；「（現存）」只对应同名的市町村），没写的用段首「特記以外は現・○○ / 全域が現・○○」，都没有不收；一行写了几个「現・」的各算一份、标「一部」；外县的、只写到政令市一级的（「現・さいたま市」）不收，所以政令市的区可能不全。输出 `{代码: [[町村, 一部, 施行年]]}`，工具断言上田 / 笠间 / 向日的锚点。户籍在戊辰之后加「明治町村」一栏（`ks.mura`，年份取中位数，最多列 14 个），此地年表加一行（`kind: 'mura'`，`ht.mura`，列 8 个）。英文界面町村名仍用日文。
- 精确到市区町村的幕末领主（3.20）：`python -X utf8 tools/fetch_kyudaka.py`（需 shapely；CODH 数据缺了由 tools/codh.py 自动下载到 `.cache/codh/`）。按旧国检索歴博数据库（`.cache/kyudaka/<国>.json`，每次请求停 1 秒；利用规程：非营利、注明出处，网站只放汇总），旧领名规范化 `norm_lord`（括号里的藩名「酒井雅楽頭（姫路藩）領分」、预所 / 取缔 → 幕府领、只有人名的 → 旗本领、御三卿 → 家领），各领主的石高按今天的市区町村相加（一村几方共管的按各方石高分开，不记相给）。「市町村コード１」是 1990 年前后的代码：用 CODH 1985 / 1995 年边界按面积对到今天的市区町村（`codh.overlap_map`），跨今界的旧市町村里，村名在 nrct 数据集有坐标、且坐标落在该旧市町村里的按坐标定位。藩名对藩名单：名单里有 → domains.json 已查的重定向 → 日文维基重定向 → `ALIAS`（明治初年的改称、按藩厅新址的叫法、别县的飞地；每条带必须出现在目标藩条目里的词，用 han_tool 的条目缓存核对）→ 按所在县找带旧国名的同名藩（伊勢亀山藩）→ 全国唯一的同写法藩（`canon` 统一 ノ・ヶ・之、舘冨竜峯）。名单里本来就有的藩名不去旧国名（伊勢崎藩曾被去成「崎藩」）。御三卿家领不是藩，不算对不上。只登记到政令市整市一级的村：先用 nrct 条目的「上位地名」（大系出版时的市区町村，如「大阪市 生野区」）对今天的市区町村，对不上（已合并的旧区）才按坐标——坐标在市界附近常偏；同市同名几处按读音（nrct 的读音带「むら」、小写假名写成大写）、再按明治旧郡（`old_districts`）挑；区里没有、而数据库第二个代码（`c2`）正好有读音对得上的同名村的，记给 c2（岸田堂村等 → 东大阪市）；大系里没有「某村新田」的用本村。工具断言上田 / 隠岐の島 / 大垣 / 姫路 / 高知 / 伊勢崎 / 諏訪的第一位、黒石市有黒石藩、久居等支藩对上名单、岸田堂村在东大阪。前端：城下町、江户京都市街之后优先用 `town.kyu`（印「市」，`ks.edo.kyu` 列前 4 位的百分比 + 其余），此地年表江户一段同样先看它；没有的才按主要郡 / 旧郡 / 全市。
- 明治町村补全（3.20）：fetch_mura 末尾 `codh_villages(index)` 读 CODH 1920 年各县 TopoJSON（`.cache/codh/1920_NN.topojson`），成立日在 1888–1908 年的町村按面积记给今天的市区町村（≥90% 算整个，其余 ≥15% 的各记一份标「一部」），只补维基没收的市区町村，并打印两边都有时的吻合率（约 78%，对不上的多是 1920 年前已并掉的）。维基分错的也拿它改：同县、同郡、同名、町村制时成立的町村在 1920 年里恰好一个且整个落在另一个市区町村、维基分给的市区町村里没有同名町村时，挪过去并打印（3.21 改了 10 处）。CODH nrct 数据的「都道府県コード」是《大系》卷号（京都以后错开），`nrct_points()` 只按名字取，调用方按坐标核对。
- 古代乡名（3.20）：`python -X utf8 tools/fetch_wamyo.py` 按旧国检索奈文研系统（POST 检索词后同一会话 GET 结果页，缓存 `.cache/wamyo/`；三河在系统里写参河），只收《和名类聚抄》本身的郷（不收标 ＊△☆ 的、驿名）。市区町村 → 古郡：主要郡或第一个整体属于的明治旧郡（只部分属于几个郡的不写），异体字 `canon()`、去方位字、`RENAME`（足柄上 → 足上、春日井 → 春部…）。户籍在律令之后加 `wamyo` 一栏（印「郡」，中日文附假名、英文附罗马字——build_bundle 的 `romaji()`），此地年表古代一行带郡与乡数。
- 藩主年份的英文维基来源（3.20）：han_tool 的 `en_tables` 取日文藩条目语言链接到的英文条目，读藩主表里 `{{nihongo|…|汉字名}}` 那一行的「起–止」，只给前面各来源都没有年份的藩主用，检查与 Wikidata 一样（缓存 `.cache/han/en_tables.json`）。
- 地名来历（3.17）：`python -X utf8 tools/yurai_tool.py` 的 `Y` 是县厅所在地、政令市与人口 30 万以上的市里条目写了来历的 48 个（青森、秋田、松山、冈山等条目没写的不收），三语自写一两句，`ev` 词与说明里的西历年都要出现在条目里（先去掉粗体标记）；条目没写来历的城市，第三项写市 / 县官网的网址，改对官网页面核对（`page_text`，缓存 `.cache/yurai/`，PDF 用 pypdf 逐页取、出错的页跳过；装了 truststore 就用系统证书库，大分市官网证书链不完整要靠它）。3.25 加了人口 15 万以上、日文维基条目里写了来历一节的 50 个市区（东京特别区的条目名带「 (東京都)」，第三项写条目名），共 124 条。户籍最后一栏 `yurai`：本市区町村有就用（印「市」），政令市的区用市名的来历（印「全市」）。
- 幕末领主一栏下面按郡里出现的藩（`findHan`：按当前语言名字匹配，去掉旧国名的也认，本县与存续藩优先）列出可展开的历代藩主（`kosekiHanHTML`，存图里不画）。
- 存图：`kosekiImage` 在 canvas 上画 1080 宽的竖版图；手机（`pointer: coarse` 且支持文件分享）走系统分享，否则直接下载。

### 古国演变时间轴（712 / 757 / 824 / 1869）

- 824 年（多褹岛并入大隅、68 国定型）就是 `provinces.json` 的底图；其他三档在 `build_provinces.py` 的 `ERAS` 里定义：`merge`（子国并回母国）、`tane`（种子岛·屋久岛四市町为多褹岛）、`meiji`（东北与北海道按明治国）。各档只存与 824 年不同的国，写进 `province_eras.json`（`{年: {remove: [key], add: [Feature]}}`，第一次点时间轴时才下载）。所有档都由同一批「旧国 × 明治国 × 县」小块一起简化后拼出，边界完全对齐。
- 明治国对照 `tools/meiji_provinces.json`（团体代码 → 国）由 `python -X utf8 tools/fetch_meiji.py` 生成：市区町村的明治旧郡 → 日文维基郡条目的分类「○○国の郡」（陆奥取「陸奥国の郡 (1869-)」；按县限定可能的国）。1878 年后拆出的郡看 `PARENT`（原郡）；同名郡用 `TITLE` 指定条目名；近年新设的郡（北海道日高郡、二海郡）跳过；北海道上川郡·中川郡按市町村写在 `AMBIG`（核对「上川郡 (石狩国)」等条目列有该市町村）；旧郡都只部分属于又分属多国的市町村在 `MAIN` 写中心市街所在的郡（核对市町村条目里出现该郡名）。分类的 `cllimit` 是整批共享的，必须跟随 continue 取完。
- 新出现的国（多褹岛、明治 18 国）的三语名、读音、所属之道在 `NEW`；北海道十一国的「道」为 `北海道`（`FILTERS.circuit.cats` 与 `label('circuit')` 已加）。
- 前端：`map.setProvEras(d)` / `setProvEra(year)`，每档注册一张 `provinces-<年>` 底图（缓存）；图例按当年计数，说明取 `prov.era.<年>`。`#prov-eras` 只在 `body.prov-mode`（古国底图）显示，`syncProvEras` 随 `syncArtCard` 一起更新。

### 广重《六十余州名所图会》（hiroshige.js）

- `python -X utf8 tools/fetch_hiroshige.py`（需 `pip install pillow`）：解析日文维基百科「六十余州名所図会」的表格（69 幅，第 70 幅目录页跳过）→ 在 Commons 核对许可，**只收公有领域** → 原图缓存到 `.cache/hiroshige/`，缩到宽 560px 存 `src/assets/hiroshige/NN.webp`（WebP q75，比原来的 JPEG 小约三成；Commons 在国内打不开，图片随站点发布）。
- 画中地点：画题里第一个有坐标的链接条目（`PLACE` 可指定别的条目、或写 None 表示不用链接），落到市区町村边界里；**定位结果的旧国（`province` 或 `partial`）必须与作品的国一致**，否则列为待处理。画题无链接的：该国只有一个市町村就取它；`MANUAL` 里人工确认的取人工值（市区町村名为 None = 只确定到县）；其余只记县、界面写「具体地点不详」。不要为了填满而猜地点。
- 题名译文在工具的 `TITLES`（中 / 英；日文界面显示原题）。`build_bundle.py` 按语言拼好 `title_t`、旧国名 `prov`、市区町村名 `place` 放进数据包的 `hiroshige`（逐个文件回退加载时不显示浮世绘）。
- 「国名今犹在」（provnames.js）：`province_names.json` 为 `{ 旧国: [{ja, zh, en, type, wiki, evidence?, evidence_note?}] }`，type ∈ place / nature / food / craft / transit / culture。新增后必须跑 `python -X utf8 tools/province_names_tool.py verify`（需 shapely）：① 名字里含国名简称或 `ALIASES` 别称；② place / transit / nature 的条目坐标在该国内（自然地物容许 60 公里），food / craft / culture 的条目正文提到该国或今属县名。通不过就不收，确需例外写 `evidence` 并在 `evidence_note` 说明（如信浓川：河口在越后）。数据包 `province_names` 每国带 `prov` 显示名与 `prefs`；`map` 的 `provTipExtra` 往古国提示里加一行，古国卡片 `namesBlock`，详卡 `namesSection`（按县涉及的旧国）。
- 县界叠加层 `prefborders` 是 custom series：全部县界（`borderChains()` 先把首尾相接的段串成链）画成一条 path，拖动时每帧只重算坐标。原来 3,000 多段 `lines` 每段一个元素，慢手机上拖动每帧约 36ms，现约 11ms。
- 「我在哪」（locate.js）：地图右侧 `#btn-locate`，只在点按时调用 `navigator.geolocation`（超时 12 秒，不要求高精度）。县由 `map.prefAt`（japan.json）判断，市区町村在该县文件里点内判断、落空取最近的；不在任何县内 → 提示「似乎不在日本」。卡片 `#loc-card`（复用 `.art-card` 定位样式）写旧国（`province` + `partial`）、今天的县与市区町村、明治旧郡，并附该国浮世绘（`printRows`）与今日国名；`map.setYou(pt)` 放蓝色脉冲标记并拉近，关卡片时去掉。位置不发往任何地方。smoke `locate` 用 Playwright 的 `geolocation` 模拟京都中京区。
- 古国巡礼（koku.js，图层 `koku`）：`python -X utf8 tools/fetch_koku.py` 解析维基「一宮」（按七道分多张表，取表头含「二宮以下」的）、「国府」「国分寺」的一览表。坐标：一宫取神社条目，国分寺取「○○国分寺跡」或继承寺院条目（表头脚注里的链接要先去掉），国府取史迹条目；没有坐标的按地址文字匹配该国所属县的市区町村（取最长名称），图钉放在市町村内（`precise: false`，画成空心）。核验：坐标离该国 ≤5 公里、市町村的 province/partial 含该国；地址文字与坐标的市町村不一致时列出待核（已核对的进 `CHECKED`）；人工覆盖写在 `MANUAL`（`wiki: None` = 不用条目坐标）。「未詳」的不放图钉。市町村判断必须先精确包含、再放宽，否则会落到邻市。数据为 CC BY-SA 4.0（见 LICENSE-CONTENT）。
  - 底图：`koku` 图层用 824 年 68 国（`curProv()`），压暗作衬底；`provBaseOn()` 统管「旧国底图」（五畿七道或古国巡礼），`provMode()` 仍只指五畿七道（浮世绘卡片、时间轴、悬停国名只在那里）。
  - 图钉密度：「全部」时缩放 < `KOKU_ZOOM`（3）只画一宫（`drawnKoku`），放大或选了子分类才画国府、国分寺；选中的那颗总是画。图例计数仍按全部。
  - 一宫：`ichinomiya` 存 `je.ichinomiya`（`{旧国: {at, site, real, realAt}}`），一国任一论社即算。「实地打卡」：精确坐标的神社要在 `CHECKIN_KM`（1 公里）内；只到市町村的神社要人在同一市町村。`map.setKokuStamps` 让已参拜的一宫描金边、亲临的发光。御朱印帐 `createBook(..., { ichi })` 多一个「诸国一宫」模式（按七道分页）。设置里的「重置」也清一宫。
- 前端：古国底图下 `map` 的 `onProvince(properties)` → `#art-card`（武藏另带第 17 图「江户」）；离开古国底图时 `syncArtCard` 收起。详卡 `hiroshigeSection` 列出画中地点在本县的作品。`#art` 大图对话框按编号循环翻页（‹ › / 方向键）。

## historical_events.json

```jsonc
{
  "timeline_eras": [{                 // 10 个：飞鸟 奈良 平安 镰仓 室町 战国 江户 明治 大正·昭和前期 现代（滑块的 max 与刻度列数由 app.js 按个数设置）
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
- 时空滑块的「战国」与「战国势力」滤镜是同一张图（3.26 合并）：`setEra` 到 `SG_ERA` 时记下原来的滤镜（`sgPrevFilter`），换成 `sengoku` 滤镜、`map.setEra(null)`（由战国势力图着色，时代的按县 1572 着色不再用），横幅、刻度、实权照常；离开战国或退出时空穿越时换回原来的滤镜。点「战国势力」按钮 = 把滑块拖到战国（`applyFilter('sengoku')` → `setEra(SG_ERA)`）；上次停在战国势力的，打开页面时滑块也在战国。时空穿越时其余滤镜按钮变暗，「战国势力」仍亮。向导的快捷提问里战国国 / 家（`q.sg`）排在时代的「谁在掌权」前面。smoke `sengoku_era`。

- 风土图层：`history | ramen | sake`。非历史图层时隐藏滤镜与时代滑块，详卡顶部换成拉面解构图 / 酒标卡；切回历史图层时滤镜与时代原样恢复。
- 时代滑块：拖动/点刻度/播放即进入「时空穿越」（`body.time-travel`），按时代 `prefecture_colors` 着色并在 `capital.coords` 放脉冲点；报幕横幅多一行「实权」（`.pw-line`，固定一行高、放不下省略、全文在 title；手机上固定两行高）：`powerChain(regimes, era)` 取 `regimes.json` 里与这个时代的年份（`years` 的「起–止」）重叠的各段短名（`short`），第一次进时空穿越才下载 regimes，到了补进横幅；点任一滤镜或 × 退出。选中县时高亮对应 `timeline_stage`。
- 合战沙盘：`startBattle` 记住当前视角并缩放到 `view`，按当前阶段（`setBattlePhase`）叠加 `lines`（polyline，箭头流动）、出阵点、要地标记与战场爆点；HUD 可点阶段条、上/下一阶段或自动推演（每 7 秒一段），每换一段向导以名将口吻解说；`body.in-battle` 隐藏工具条与滑块；向导切换为 `narrator`。退出（按钮或 Esc）恢复视角、图层、滤镜与向导。合战中地图点击被忽略。
- 窄屏合战：`setupBattleVoice` 用 MutationObserver 把向导最新一条 AI 发言（打字机与 LLM 流式输出都会同步）镜像到地图底部的 `#battle-voice` 浮窗，「提问」切到向导页。
- 飞线 `effect.trailLength` 必须为 0：拖尾会开启 zlevel 运动模糊，缩放时留残影。
- 各地图的 `geo` 必须设 `animationDurationUpdate: 0`：ECharts 在 setOption（改中心 / 缩放、重设着色）时会用全局的 update 动画把底图 group 滑向新位置，而拖动只直接改 group；动画途中一拖，动画结束时把底图拉回旧目标，填色就与 `animation: false` 的叠加层（线、国名、图钉、旗）永久错开。smoke `map_sync` 核对。
- 衬线字体（Noto Serif SC/JP）用于标题与古名，无衬线（系统字体）用于正文。

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

- `python -X utf8 tools/check_data.py`：数据与仓库一致性——分类键取值（直接读 map.js / crests.js / guide.js，不另抄）、时间轴 6 段、译文覆盖层结构（不得含逻辑键、对象数组长度一致）、时代与合战、**数据包是否过期**（用 `build_bundle.build()` 重算比较）、市区町村字段与对照表名字、`sw.js` 的 SHELL 是否与 build_sw 算出的一致、界面词典三语的键与占位符、字体切片有无漏字、仓库里有无 `__pycache__` / 测试页等杂物。
- `python -X utf8 -m unittest discover -s tests -p "test_*.py"`（`tests/test_tools.py`，只用标准库、不联网，CI 的 data 任务也跑）：fetch_domains 的 whole / count / norm / kind_of / strip_province，build_bundle 的 deep_merge / romaji / ja_to_zh_table，字体切片没有漏字，sw.js SHELL 是最新，地名来历三语年份一致、yurai.json 与工具同步。改抓取脚本的正则后先跑；以前出过错的写法加进这里。
- `python -X utf8 tests/smoke.py`（本地可加 `PW_CHANNEL=chrome` 用已装的 Chrome；`SMOKE_ONLY='phone.*zh'` 只跑部分；`SMOKE_JOBS=4` 本机开 4 个子进程各跑一片再汇总，完整一遍约 6–7 分钟；`SMOKE_SHARD=2/8` 只跑第 2 片，按场景顺序轮流分）：Playwright 在 电脑 1280×800 / 平板 820×1180 / 手机 390×844 下跑深链接、横向溢出、下钻、搜索、合战、时代滑块、盖印位置、离线向导、标签页；中文全跑，英日只跑语言相关场景。任何控制台报错或页面异常即失败，截图存 `tests/artifacts/`。
- GitHub Actions（`.github/workflows/checks.yml`）每次推送：数据检查 → 冒烟测试（`ui` 是 8 片的 matrix，`fail-fast: false`，失败截图按片上传 `smoke-screenshots-N`；`~/.cache/ms-playwright` 按 Playwright 版本缓存，命中时只装系统依赖；升级 Playwright 时一并改 cache key）→ （仅 main 且两项都通过）发布到 GitHub Pages。Pages 的 Source 设为「GitHub Actions」，检查失败网站保持上一版。发布只打包 `index.html`、`manifest.webmanifest`、`sw.js`、`src/`——**新增网站需要的根目录文件时要加进 deploy 步骤的 cp 列表**。推送后约 5–6 分钟才上线（测试 8 片并行）。
- CSS 有全局 `[hidden] { display: none !important; }`，组件里写 `display` 不会再盖掉 hidden 属性。
- 重跑：场景因 Playwright 超时（等元素 / 点击 / 页面加载）失败时自动重跑一次，重跑通过算通过，但打印并在 CI 写一条 `::warning`（含调用记录头几行：卡在哪个元素）；断言失败与控制台报错不重跑。页面没加载完时报错列出未返回的请求。测试服务器的连接队列加大到 128（冷启动时并发请求四十多个文件）。
- 新增功能时在 `tests/smoke.py` 里补一个场景。现有回归场景（按场景名排序）：
  - `amami_town`（龙乡町年表有 1609 / 1946 / 1953、废藩置县后属鹿儿岛县）
  - `audio_broken`（声音不可用时照常运行）
  - `bday`（深链接 6 月 21 日生日帖：三格数字、条目数与数据一致、有 1582、不出屏不横向溢出、存图、换日期改地址栏、点一条选中县）
  - `china`（屏蔽 jsdelivr / unpkg / Google Fonts 后仍能打开）
  - `country`（`#map=nope` 退回日本、日本链接不带 `map=`
  - `crests_added`（三木剑菱、堀越公方足利二つ引的数据与图）
  - `deeplink` 另查字体（只请求当前语言的一种 Noto Serif、不请求无衬线，`<html lang>` 与 `serifFont()` 一致；三语）
  - `disputed_jp`（日本地图点竹岛圆点 / 国后岛弹卡、不选中北海道）
  - `disputed_muni`（北海道下钻里齿舞与色丹同为灰、标题数量不含争议块、点齿舞弹卡）
  - `disputed_split`（拆分不误伤根室、争议岛不再属于县、不改入参）
  - `era_stable` 另查滑块 10 个时代、大正·昭和前期的实权有军部
  - `era_stable` 另查战国时代横幅的实权一行有织田与丰臣
  - `era_stable`（换时代时图例与报幕横幅尺寸不变）
  - `fixlink`（详卡纠错链接：issue 标题有县名、正文有 pref=26 与语言，点击时写好 href）
  - `guide_power`（平安时代快捷提问答出藤原与上皇，自由提问江户答出德川）
  - `guide_town`（上田市的「古时候属于哪里」接上仙石与 1871）
  - `han` 另查松平忠固 1830–1858
  - `han` 另查先列 6 藩）
  - `han`（长野县 ≥5 藩、有「中途废藩」分组、上田藩有真田信之）
  - `hiroshige`（古国地图点武藏出两幅、大图加载与翻页、详卡列出）
  - `hometown` 另查只到「京都」的菅原道真不算进中京区
  - `hometown`（京都中京区此地年表有 1582、不重复、不横向溢出、点第一条菅原道真诞生标在京都）
  - `keyboard`（第一个 Tab 到「跳到搜索」、地图容器有 aria-label；宽屏「/」聚焦搜索框、空框按 ↓ 列出 47 都道府县、Enter 打开第 26 个）
  - `kako`（深链接 6 月 21 日每页 3 条、刷新顺序不变、翻页能见到 1582、点一条选中县）
  - `koku`（古国巡礼图层、出云大社卡片、参拜、模拟定位实地打卡得亲临印、御朱印帐一宫篇）
  - `korea`（三语首尔详卡与韩文名、分母 29、日本按钮隐藏、只有首尔着色
  - `korea_battle`（6 场、鸣梁推到底、旁述、Esc、深链接萨水）
  - `korea_book`（庆北盖印得「경북」印、计数 1；印帐 29 格、平安组 5 格、乡校篇 141 所、标签不被压扁；详卡点庆山乡校记下到访，模拟定位在庆州乡校时庆山打不了卡、庆州可以）
  - `korea_counties`（仁川 11 区、深链接选中永宗区、不溢出、Esc 退出）
  - `korea_daedong`（29 张图都在、平壤详卡图加载、大图不出屏、点图放大、Esc 关闭）
  - `korea_dispute`（点独岛弹卡、两个名字顺序固定、卡片不出屏、Esc 关闭）
  - `korea_eras`（五个历代图层的图例条数 5 / 12 / 10 / 8 / 13、三国图层扶余 = 百济 · 金海 = 伽倻、新罗图层点庆州选中庆尚北道并展开统一新罗一段、州治 10 个、回到今天收起图例）
  - `korea_guide`（快捷提问字与底色对比度 ≥3；离线：济州方言给出「혼저 옵서예」、庆尚北道名字来历讲尚州）
  - `korea_koseki`（元山的古今户籍：1896 年属咸镜南道）
  - `korea_locate`（模拟定位庆州：卡片含庆尚北道 / 庆尚道 / 王京，详卡道名来历含尚州）
  - `korea_power`（国力 28 区、户数第一庆北、换指标、对决、点平壤）
  - `korea_sul`（庆北两种酒、平壤문배주带原产地标、慈江道不出这一栏）
  - `korea_switch`（顶栏切到半岛、地址栏带 `map=korea`、不溢出；之后打开日本老链接仍是日本）
  - `korea_tour`（全新访客进半岛自动出现 7 步、气泡不出屏、记住）
  - `koseki` 另查上田县 → 长野县
  - `koseki` 另查此地年表（1560–1573 武田合并、上田藩三家年份、5 段战国、按年份排）
  - `koseki`（深链接打开上田市户籍：10 栏（含古代乡名小县郡 8 郷有童女、明治町村有 1889 与上田町）、今辖境 111 村上田藩 79%、精度印「市」、展开上田藩历代藩主有真田信之、氏神诹访大社、卷轴不出屏、户主名记住、存图、市区町村卡片入口、乡音跳向导；三语都跑）
  - `koseki_branch`（黑石市：幕末领主列出黑石藩，能展开历代藩主有津轻承叙——支藩从弘前藩条目那一节取）
  - `koseki_city`（名古屋市东区：旧高旧领写尾张藩（数据里的名古屋藩按重定向改名）、精度印「市」、能展开历代藩主）
  - `koseki_main`（大分市按石高列出臼杵藩与府内藩、精度印「市」）
  - `koseki_seat`（笠间市是笠间藩藩厅所在的城下町：写笠间藩与笠间城、精度印「市」；明治町村有笠间町与宍户町、此地年表有 1889 年町村制一行）
  - `koseki_ou`（伊达市户籍「战国」一栏 1560 伊达、1600 西军、精度印郡）
  - `koseki_town`（京都上京区：幕末领主幕府直辖、写京都町奉行、精度印「市」，此地年表江户一段是幕府；最后一栏是京都市的地名来历、精度印「全市」）
  - `koseki_whole`（名取市户籍：没有町村数的「全域が仙台藩領」郡照常打开、写仙台藩、此地年表有仙台藩与废藩置县）
  - `locate`（模拟定位京都：卡片内容、选中京都府、带浮世绘、打开市区町村地图）
  - `locate_kurils`（定位在国后岛弹争议卡）
  - `map_sync`（程序改 geo 中心后马上拖动，停下后底图 group 与坐标系的平移缩放差 <1px）
  - `okinawa_town`（那霸户籍的此地年表有 1429 / 1609 / 1879 / 1972、没有战国行）
  - `phone_ui`（详卡目录跳转、手机顶栏一行与「更多」菜单、图层下拉、工具条按钮 ≥32px、抽屉点把手展开 / 下拖收回 / 再拖关闭
  - `pickMap` 规则、仍写 `je.visited`）
  - `pilgrimage`（切图层、点图钉、子分类、详卡条目、离线漫迷解说）
  - `power`（古国国力：榜首武藏、逆袭首位河内、卡片不出屏、点武藏国选中埼玉并高亮榜单、PK 表与自选、离开后收起；三语都跑）
  - `pref=99` 回欢迎卡）
  - `provinces` 另含时间轴（1869 年底图、点札幌选中北海道、712 年、离开后隐藏）
  - `provinces`（换成旧国底图、点武藏国里的埼玉仍选中埼玉、换滤镜后换回县）
  - `regimes`（欢迎卡打开实权页 20 段、镰仓写两说、不出屏、点江户的「看将军名单」换页并滚到江户幕府、末尾有纠错链接）
  - `rl_link`（`#rl=power` 打开实权页、换页改地址栏、关掉去掉 rl=）
  - `search_fits`（搜索下拉完整落在屏幕内）
  - `starts`（欢迎卡「从这里开始」：查家乡聚焦搜索框、窄屏切到地图页；战国按钮打开战国势力滤镜）
  - `sengoku` 的年表先是实权 20 段再换天皇页
  - `sengoku`（默认 1560 年居首的家是三好 9 国、图例最多 13 项加「其余」、1600 年 7 类（含阿伊努的土地）西军 39 块东军 53 块、甲斐 6 个年份 1573 胜赖、人物简卡与详写（信玄肖像 / 三方原 / 相关人物谦信）、年表天皇 126 行将军 41 届、点义满开人物卡并返回年表、Esc、离开后隐藏；三语与横屏都跑）
  - `sengoku_clan`（深链接 1573 武田总览：3 国 + 2 分治、5 根柱、接壤首位北条、注明 1598
  - `sengoku_link`（深链接 1600 美浓弹卡、换年份改地址栏、Esc 去掉 sgp、宽屏向导首个快捷提问问 1600 年）
  - `sengoku_ou`（深链接 1582 伊达总览 5 块不含伊具、石高「—」不排名、注明按郡、底图有津轻与和人地而无陆奥；津轻 1573 南部与津轻分治、1582 津轻）
  - `sgedges` 有内容、家纹旗含武田织田、标题家纹与许可；点柱子换 1560、点接壤的家换人、图例点织田 1582 居首、换 1600 后收起且无旗；三语三种尺寸）
  - `shared`（共同历史对话框：9 件按年代、标签一行且选中的不被截断或压扁、每件 4–6 条事实 / ≥2 方叙述 / ≥2 条来源、不出屏，日本与半岛两种模式内容一致）
  - `sound`（音效触发、静音保存、开背景音乐）
  - `tour`（全新访客自动出现、9 步气泡不出屏且聚光灯对准、走完记住、刷新不再出现、设置里重开、Esc 关闭）；横屏 `landscape` 视口跑 deeplink / power / sengoku / battle / koseki / tour
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
- 版权与许可：© 2026 Nickrockwall；代码 MIT（`LICENSE`，保持纯 MIT 原文以便 GitHub 识别），内容 CC BY-NC 4.0，范围与第三方清单在 `LICENSE-CONTENT.md`。新增第三方素材时登记到该表，并在 README 三语「数据从哪来」一节与界面上注明出处。
- README（三语）是给第一次来的人看的简介：语气平实，不写更新日志；各版本改动记在 `CHANGELOG.md` / `CHANGELOG.en.md` / `CHANGELOG.ja.md`（日期 + 几条要点，最新在上）。副标题是「古今日本地图 / Japan, Then and Now / 古今日本地図」。
- 详卡头像是县章：PNG 当 CSS 遮罩统一涂金色（只看 alpha；工具把接近白色的像素变透明，白色画在彩色底上的县章才显出图案）。Wikidata P94 不是县章的在工具的 `OVERRIDE` 指定（岐阜）。没有县章的县用旧国名朱印（`badge()`，最多两国竖排）。地图悬停提示里县名前也放县章（`emblemTip`，createMap 的 `emblems` 参数）；`badge.icon`（emoji）现在不再显示。
- 手机上放不下完整文字的按钮同时输出全称与简称（`twoLabels`，`.lbl-full` / `.lbl-short` 按 ≤560px 切换，全称进 title）：盖印（日文简称「御朱印」）、已盖印（只留「已盖印」，日期进 title）、英文「Cities & towns」→「Towns」。
- 分享封面 `src/assets/og-cover{,-en,-ja}.png` 由 `python -X utf8 tools/make_og.py` 截 `tools/og_cover.html` 生成（文字在模板的 `T` 里改）；README 截图 `docs/screen-{sengoku,power,bday,koseki}-{zh,en,ja}.jpg`（电脑：1582 年战国势力图、年表「实权」页（滚到摄关政治）；手机：6 月 21 日生日帖、上田市古代户籍）由 `python -X utf8 tools/make_screens.py` 生成；README 里「先点开这几个看看」的链接与截图是同样的深链接。界面有明显变化时重跑。全国地图须注明「出典：地球地図日本」（欢迎卡与设置弹窗底部的 `legalHTML()`）。来自维基百科的数据是 CC BY-SA 4.0，不能并入 NC 内容。
