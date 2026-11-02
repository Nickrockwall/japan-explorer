# Japan Explorer · 古今日本地图

交互式历史地图应用：在日本全图上点选任一都道府县，查看其古代令制国沿革、历史时间轴、名胜物产、方言与地缘梗；用「时空滤镜」看五畿七道、战国势力、幕末阵营；打卡收集御朱印；拖动「时空穿越滑块」看九个时代的版图与政权中枢；在「合战演武」沙盘上回放经典战役；切换「拉面 / 地酒」风土图层；并与「AI 历史向导」对话（博学史官 ⇄ 名将附体 / 合战名将）。

## 技术架构

- 原生 HTML5 + CSS3 + 原生 ES Modules，无构建工具、无 npm 依赖，纯静态运行。
- 地图：Apache ECharts 5.5.1，**随站点发布在 `src/vendor/echarts.min.js`**（附 LICENSE/NOTICE），不走 CDN——jsdelivr 在国内常挂起，同步脚本会让整页卡住（smoke 测试的 china 场景会屏蔽外部 CDN 检查这一点）。用 `echarts.registerMap` 注册本地 GeoJSON。
- 字体：Google Fonts 以 `display=optional` 非阻塞加载（没能马上就绪就整页用系统字体，不中途替换导致排版跳动）；`--serif` / `--sans` 带各系统中文字体回退。
- 深链接：`index.html#pref=26&lang=ja` 直接打开对应地区并指定语言；`&muni=1&m=23211` 打开市区町村地图并选中（政令市整市为各区代码以 `.` 连接）（`lang` 可省略；链接里的语言优先于本地设置并会被记住）。选中地区时地址栏自动写成这种形式，详卡「分享」按钮复制/分享的就是它。
- **当前地图**（`src/js/country.js`）：`MAPS` 登记各地图的 GeoJSON、数据目录、单元数与存储键前缀（日本 = `src/data`、`je.`，与改造前完全相同）。页面加载时由 `pickMap(hash, 上次的地图)` 定下：链接里 `map=` 是已登记的键 → 用它；否则链接带 `pref=`（老链接都是日本）→ 日本；否则上次看的地图（`je.ui.map`）；都没有 → 日本。日本以外的地图在 `stateHash` 里写 `map=`，日本链接不带。切换地图走整页重载（与切换语言相同）。数据路径一律写成 `${MAP.data}/…`，不要再写死 `src/data/`。
- **数据打包（改数据后必做）**：`python tools/build_bundle.py` 把每种语言的 47 县 + 合战/时代数据合并成 `src/data/bundle/{zh,en,ja}.json`（每种语言 1 个请求）。前端优先读 bundle，读不到才回退为逐个文件加载——所以**改了 JSON 却忘记重新打包，线上会继续显示旧内容**。
- PWA：`manifest.webmanifest` + `sw.js`（本站文件网络优先、CDN 库与字体缓存优先，只缓存 GET）。改动应用外壳文件列表（`SHELL`）时把 `VERSION` 加一。图标在 `src/assets/icons/`，分享卡片封面 `src/assets/og-cover.png`（1200×630）。
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
src/data/historical_events.json  全国共享：timeline_eras（9 个时代）+ historic_battles（5 场合战）
src/data/prefectures/NN_slug.json  各县数据（01_hokkaido … 47_okinawa）
src/data/provinces.json        68 令制国真实边界 + 县界线（tools/build_provinces.py 由市区町村合并生成）
src/data/province_eras.json    古国演变时间轴：712 / 757 / 1869 年与 824 年的差异（remove + add）
src/data/hiroshige.json        广重《六十余州名所图会》69 幅（tools/fetch_hiroshige.py 生成；图片在 src/assets/hiroshige/NN.jpg）
src/js/hiroshige.js            古国地图上的作品卡、详卡「广重笔下」、大图浏览
src/data/province_names.json   「国名今犹在」：旧国 → 今天仍带国名的东西（tools/province_names_tool.py 核验）
src/js/provnames.js            国名标签：古国悬停提示、古国卡片、详卡
src/data/koku_sites.json       古国巡礼：诸国一宫·国府·国分寺（tools/fetch_koku.py 生成并核验）
src/js/koku.js                 古国巡礼的卡片、详卡「古国三迹」、御朱印帐「诸国一宫」篇
src/data/kokuryoku.json        古国国力：68 国今日人口 / 面积 / 市区町村数 + 江户人口与石高（tools/build_kokuryoku.py 生成，打进数据包）
src/js/kokuryoku.js            古国国力：指标、着色、提示、反常识头条、榜单与宿敌 PK 卡片
src/data/sengoku.json          战国势力：68 国 × 6 个年份的归属、各家代表人物（tools/sengoku_tool.py 生成并核对）
src/data/rulers.json           天皇 126 代 · 将军 · 镰仓执权的代数与在位年份（tools/rulers_tool.py）
src/data/people.json           人物详写：三语简介、相关人物、家纹、肖像（tools/people_tool.py；肖像在 src/assets/people/QID.jpg）
src/js/sengoku.js              战国势力：着色、提示、图例、国别卡片与人物卡
src/js/rulers.js               天皇 · 将军年表对话框
src/data/emblems.json          47 都道府县章（tools/fetch_emblems.py：Wikidata P94 → Commons 只收公有领域 → src/assets/emblems/NN.png 透明底），详卡头像
src/js/tour.js                 新手教程：聚光灯 + 说明气泡，步骤由 app.js 给出（首次访问自动开始）
src/js/koseki.js               古代户籍《古今人别帐》：按市区町村 / 定位点列出各时代归谁管（卷轴 HTML + 存图 canvas）
tools/domains.json             幕末各郡的领主与町村数（tools/fetch_domains.py 由维基各郡条目的《旧高旧領取調帳》表整理，build_bundle 拼进数据包 domains）
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
- **横屏手机**（高 ≤520px 的横屏，`SHORT`）：地图页工具条一行（图层左半、滤镜右半，子行换到第二行左侧），底部一行（图例左半、去掉说明；时空滑块右半、只留播放键 + 滑轨 + 时代名）；各种卡片（`.muni-card`，含国力榜、古国 / 巡礼 / 我在哪卡）改放右侧；`layoutCenter` 把地图中心放在上下两行之间，取景用 `LANDSCAPE_VIEW`；合战时 `setInset({ left })` 让地图避开左上的合战面板。转屏（竖屏手机 / 横屏手机 / 宽屏三种形态之间）时 `resize` 回到该形态的默认取景。smoke 有 `landscape`（844×390）视口，只跑 `LANDSCAPE_CASES`。
- 新手教程（tour.js）：`createTour(steps)`，步骤 `{ key, target, before }`，文案 `tour.<key>.h/.b`；目标不可见的步骤自动跳过；窄屏的「详情」「向导」步骤指向底部标签按钮。首次访问且地址栏不带 `pref=` 时自动开始，设置弹窗与欢迎卡可再打开；走完或跳过都记 `tourDone`。
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
- 天皇 / 将军 / 执权：`python -X utf8 tools/rulers_tool.py`（需 zhconv）解析「天皇の一覧」「征夷大将軍」「鎌倉幕府の執権一覧」的 wikitext，核对代数连续、起止不倒退；西历年只取括号里的（前面的是和历）；后小松从 1392 年南北朝合一算起；尊氏、义稙的再任带 `again`。女性天皇英文写 Empress（`EMPRESS`）。
- 人物详写：`python -X utf8 tools/people_tool.py [--check]`（需 pillow）。简介自己写（维基正文是 CC BY-SA），`ev` 里的每个词与简介里的西历年都必须出现在该人日文维基条目里，三语年份要一致；肖像取 Wikidata P18（没有则取日文维基条目首图），收公有领域与 CC BY / BY-SA（记下 `author`，人物卡注明作者与许可），宽 240px 存 `src/assets/people/<QID>.jpg`，人工看过不是肖像的（花押、石碑）写进 `NOT_PORTRAIT`；`crest` 只写确实是该图案的家纹。
- 前端：选「战国势力」时 `ensureSengoku` 下载 sengoku / rulers / people 三个文件（与旧国边界一起），`map.setSengoku(createSengoku(...))` 后 `sgMode()` 生效（底图 824 年）。`#sg-years` 年份行（选的年份存 `ui.sgYear`，默认 1560）末尾「年表」打开 `dialog#rulers`（`rulers.js`：天皇按时代分组写都城，镰仓到江户写平安京 + 幕府所在地）。点国 → `#sg-card` 国别卡（6 个年份 + 代表人物），点人名或年表的一行 → 人物卡（`showPerson`；从年表来的「返回」回年表）。图例：超过 12 家时只占一国的合成一项。地址栏（`pageHash`）在战国图下带 `&sg=年&sgp=国`，打开这样的链接会切到该滤镜、年份并弹出该国卡片（手机上留在地图页）。点开一国时 `guide.setSengoku(sg.guideInfo(国))`：向导多一个快捷提问 `q.sg`，离线 `sgAnswer` 列出六个年份，在线写进 System Prompt（`SG_RULE` + `<sengoku>`）。

### 古代户籍（koseki.js）

- 入口：市区町村详情卡（单个市町村）与「我在哪」卡片的「📜 古代户籍」按钮，深链接 `#pref=20&muni=1&m=20203&koseki=1`（关掉对话框时地址栏去掉 `koseki=1`）。`openKoseki(pid, code, pt)`：经 `locate.js` 的 `muniGeo(pid)` 取该市町村，`pt` 缺省为市町村质心（定位进来的用真实位置）。
- 各栏与精确度印（`seal`）：本贯（道 · 国 · 明治旧郡，市）、氏神（本国最近的一宫，方向 + 直线距离，市）、律令（最近的国府与国分寺，步行天数按 30 公里/天，市）、战国（`sengoku6`：所属旧国在 6 个年份的归属，国；没有 sengoku.json 时退回 `map_filters.sengoku_1572`，县）、幕末领主（郡；查不到时用县的 `edo_domains`，县）、戊辰（`map_filters.bakumatsu`，县）、今日国力（kokuryoku 的人口排名，国）、乡音（`dialect.phrases[0]`，县；按钮调 `guide.askQuick('dialect')`）。令制外（虾夷地、琉球）不出氏神与国府。只用已核验数据计算，不给单个市町村手写剧情。
- 幕末领主：`python -X utf8 tools/fetch_domains.py` 读 `tools/districts.json` 里每个郡的维基条目，解析「旧高旧領取調帳」后的「知行 / 村数」表；没有表的读正文「全域が○○藩領であった」。知行规范化为幕府领（含代官所、郡代、预地）/ 旗本领 / 寺社领 / 相给（几方共管）/ 藩 / 明治初设的府县 / 其他；藩名去掉开头的旧国名（同名而国不同的保留，如纪伊田边藩），英文名取 Wikidata。`build_bundle.py` 按县 id → 郡名输出前 3 位 + 其余合计（`@bakufu` 等代号由前端翻译），中文藩名按 search.js 对照表反向转简体。按市町村约 79%、按人口约 84% 能精确到郡；多摩郡、都筑郡等条目写法不同，未解析。
- 存图：`kosekiImage` 在 canvas 上画 1080 宽的竖版图；手机（`pointer: coarse` 且支持文件分享）走系统分享，否则直接下载。

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
- 新增功能时在 `tests/smoke.py` 里补一个场景。现有回归场景：`tour`（全新访客自动出现、9 步气泡不出屏且聚光灯对准、走完记住、刷新不再出现、设置里重开、Esc 关闭）；横屏 `landscape` 视口跑 deeplink / power / sengoku / battle / koseki / tour；`koseki`（深链接打开上田市户籍：8 栏、小县郡 158 町村中上田藩 106、氏神诹访大社、卷轴不出屏、户主名记住、存图、市区町村卡片入口、乡音跳向导；三语都跑）；`sengoku_link`（深链接 1600 美浓弹卡、换年份改地址栏、Esc 去掉 sgp、宽屏向导首个快捷提问问 1600 年）；`sengoku`（默认 1560 年三好 9 国居首、图例合并单国家、1600 年 6 类西军 27 国、甲斐 6 个年份 1573 胜赖、人物简卡与详写（信玄肖像 / 三方原 / 相关人物谦信）、年表天皇 126 行将军 41 届、点义满开人物卡并返回年表、Esc、离开后隐藏；三语与横屏都跑）；`power`（古国国力：榜首武藏、逆袭首位河内、卡片不出屏、点武藏国选中埼玉并高亮榜单、PK 表与自选、离开后收起；三语都跑）；`koku`（古国巡礼图层、出云大社卡片、参拜、模拟定位实地打卡得亲临印、御朱印帐一宫篇）；`provinces` 另含时间轴（1869 年底图、点札幌选中北海道、712 年、离开后隐藏）；`locate`（模拟定位京都：卡片内容、选中京都府、带浮世绘、打开市区町村地图）、`hiroshige`（古国地图点武藏出两幅、大图加载与翻页、详卡列出）、`provinces`（换成旧国底图、点武藏国里的埼玉仍选中埼玉、换滤镜后换回县）、`sound`（音效触发、静音保存、开背景音乐）、`audio_broken`（声音不可用时照常运行）、`pilgrimage`（切图层、点图钉、子分类、详卡条目、离线漫迷解说）、`era_stable`（换时代时图例与报幕横幅尺寸不变）、`search_fits`（搜索下拉完整落在屏幕内）、`china`（屏蔽 jsdelivr / unpkg / Google Fonts 后仍能打开）；`country`（`#map=nope` 退回日本、日本链接不带 `map=`、`pickMap` 规则、仍写 `je.visited`）；`korea_switch`（顶栏切到半岛、地址栏带 `map=korea`、不溢出；之后打开日本老链接仍是日本）；`korea`（三语首尔详卡与韩文名、分母 29、日本按钮隐藏、只有首尔着色、`pref=99` 回欢迎卡）；`korea_dispute`（点独岛弹卡、两个名字顺序固定、卡片不出屏、Esc 关闭）；`disputed_split`（拆分不误伤根室、争议岛不再属于县、不改入参）；`disputed_jp`（日本地图点竹岛圆点 / 国后岛弹卡、不选中北海道）；`locate_kurils`（定位在国后岛弹争议卡）；`korea_counties`（仁川 11 区、深链接选中永宗区、不溢出、Esc 退出）；`korea_eras`（五个历代图层的图例条数 5 / 12 / 10 / 8 / 13、三国图层扶余 = 百济 · 金海 = 伽倻、新罗图层点庆州选中庆尚北道并展开统一新罗一段、州治 10 个、回到今天收起图例）；`korea_locate`（模拟定位庆州：卡片含庆尚北道 / 庆尚道 / 王京，详卡道名来历含尚州）；`korea_koseki`（元山的古今户籍：1896 年属咸镜南道）；`korea_tour`（全新访客进半岛自动出现 7 步、气泡不出屏、记住）；`korea_sul`（庆北两种酒、平壤문배주带原产地标、慈江道不出这一栏）；`korea_book`（庆北盖印得「경북」印、计数 1；印帐 29 格、平安组 5 格、乡校篇 141 所、标签不被压扁；详卡点庆山乡校记下到访，模拟定位在庆州乡校时庆山打不了卡、庆州可以）；`korea_power`（国力 28 区、户数第一庆北、换指标、对决、点平壤）；`korea_battle`（6 场、鸣梁推到底、旁述、Esc、深链接萨水）；`korea_daedong`（29 张图都在、平壤详卡图加载、大图不出屏、点图放大、Esc 关闭）；`korea_guide`（快捷提问字与底色对比度 ≥3；离线：济州方言给出「혼저 옵서예」、庆尚北道名字来历讲尚州）；`shared`（共同历史对话框：9 件按年代、标签一行且选中的不被截断或压扁、每件 4–6 条事实 / ≥2 方叙述 / ≥2 条来源、不出屏，日本与半岛两种模式内容一致）；`disputed_muni`（北海道下钻里齿舞与色丹同为灰、标题数量不含争议块、点齿舞弹卡）。
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
- 分享封面 `src/assets/og-cover{,-en,-ja}.png` 由 `python -X utf8 tools/make_og.py` 截 `tools/og_cover.html` 生成（文字在模板的 `T` 里改）；README 截图 `docs/screen-{desktop,phone}-{zh,en,ja}.jpg` 由 `python -X utf8 tools/make_screens.py` 生成。界面有明显变化时重跑。全国地图须注明「出典：地球地図日本」（欢迎卡与设置弹窗底部的 `legalHTML()`）。来自维基百科的数据是 CC BY-SA 4.0，不能并入 NC 内容。
