"""自建衬线字体切片：src/fonts/{sc,jp}.css + src/fonts/{sc,jp}/*.woff2。

以前从 Google Fonts 取 Noto Serif SC / JP，国内打不开（页面退回系统字体）。现在随站点发布：
只收网站文字里出现的字（index.html、src/js、src/data 下全部 JSON），按出现频率排好、每片约 SLICE 个字，
每片一个 @font-face（unicode-range），浏览器只下载这一页用到的几片。字重只做 500 / 700，
写 900 的地方浏览器取 700。文件名带内容哈希，sw.js 对 src/fonts/ 缓存优先。

用法：python -X utf8 tools/build_fonts.py（需 fonttools、brotli；原始字体缓存在 .cache/fonts/）。
改了数据或界面文字、出现新字后重跑；check_data.check_fonts 会核对没有漏字（只读 CSS 与 tools/fonts_lacking.json）。
"""
import collections
import hashlib
import io
import json
import pathlib
import shutil
import urllib.request

try:  # 只有生成时需要；check_data 只调 missing()
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
except ImportError:
    subset = TTFont = instancer = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / '.cache' / 'fonts'
OUT = ROOT / 'src' / 'fonts'
LACKS = ROOT / 'tools' / 'fonts_lacking.json'  # 网站里出现但字体本身没有的字（谚文等），check_data 不再报
FONTS = {  # 目录名: (CSS 字体名, google/fonts 里的路径)
    'sc': ('Noto Serif SC', 'ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf'),
    'jp': ('Noto Serif JP', 'ofl/notoserifjp/NotoSerifJP%5Bwght%5D.ttf'),
}
WEIGHTS = (500, 700)
SLICE = 160  # 每片字数；第一片另含全部 ASCII
BOOST = {'index.html': 20}  # 界面文字排在前面
BOOST_DIR = {'lang': 20, 'bundle': 4}


def site_files():
    yield ROOT / 'index.html'
    yield from sorted((ROOT / 'src' / 'js').rglob('*.js'))
    yield from sorted((ROOT / 'src' / 'data').rglob('*.json'))


def site_text():
    """全站文字的字频（界面文字加权）。"""
    freq = collections.Counter()
    for p in site_files():
        w = BOOST.get(p.name, 1) * max([BOOST_DIR.get(d, 1) for d in p.parts] or [1])
        for ch, n in collections.Counter(p.read_text(encoding='utf8')).items():
            freq[ch] += n * w
    return freq


def source(key):
    name, path = FONTS[key]
    f = CACHE / pathlib.PurePosixPath(path).name.replace('%5B', '[').replace('%5D', ']')
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(urllib.request.urlopen(f'https://github.com/google/fonts/raw/main/{path}', timeout=300).read())
    return f


def ranges(cps):
    cps = sorted(cps)
    out, start = [], cps[0]
    for a, b in zip(cps, cps[1:] + [None]):
        if b != a + 1:
            out.append(f'U+{start:X}' if start == a else f'U+{start:X}-{a:X}')
            start = b
    return ', '.join(out)


def woff2(font_bytes, text):
    o = subset.Options()
    o.flavor = 'woff2'
    o.layout_features = ['*']
    o.notdef_outline = True
    o.hinting = False
    s = subset.Subsetter(o)
    s.populate(text=text)
    font = TTFont(io.BytesIO(font_bytes))
    s.subset(font)
    font.flavor = 'woff2'
    b = io.BytesIO()
    font.save(b)
    return b.getvalue()


def slices(freq, cmap):
    ascii_ = [chr(c) for c in range(0x20, 0x7f)]
    rest = [ch for ch, _ in freq.most_common() if ord(ch) in cmap and ch not in ascii_ and ord(ch) > 0x20]
    first, rest = ascii_ + rest[:SLICE], rest[SLICE:]
    return [first] + [rest[i:i + SLICE] for i in range(0, len(rest), SLICE)]


def build(key, freq):
    name, _ = FONTS[key]
    src = source(key)
    cmap = TTFont(src).getBestCmap()
    parts = slices(freq, cmap)
    d = OUT / key
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    css = [f'/* {name}（SIL OFL 1.1，见 src/fonts/OFL.txt）：tools/build_fonts.py 生成，勿手改 */']
    total = 0
    for w in WEIGHTS:
        static = io.BytesIO()
        instancer.instantiateVariableFont(TTFont(src), {'wght': w}).save(static)
        static = static.getvalue()
        for i, chars in enumerate(parts):
            data = woff2(static, ''.join(chars))
            fn = f'{w}-{i:02d}.{hashlib.md5(data).hexdigest()[:8]}.woff2'
            (d / fn).write_bytes(data)
            total += len(data)
            css.append(f"@font-face{{font-family:'{name}';font-style:normal;font-weight:{w};font-display:optional;"
                       f"src:url({key}/{fn}) format('woff2');unicode-range:{ranges([ord(c) for c in chars])}}}")
    (OUT / f'{key}.css').write_text('\n'.join(css) + '\n', encoding='utf8')
    print(f'{key}: {sum(map(len, parts))} 字 × {len(WEIGHTS)} 字重，{len(parts)} 片/字重，共 {total / 1024 / 1024:.1f} MB')


def covered(key):
    css = (OUT / f'{key}.css').read_text(encoding='utf8')
    have = set()
    for part in css.split('unicode-range:')[1:]:
        for r in part.split('}')[0].split(','):
            a, _, b = r.strip()[2:].partition('-')
            have.update(range(int(a, 16), int(b or a, 16) + 1))
    return have


def missing():
    """网站里出现、却既不在切片里也不在「字体没有」名单里的字（check_data 用，不需要原始字体）。"""
    freq = site_text()
    lacks = json.loads(LACKS.read_text(encoding='utf8'))
    out = {}
    for key in FONTS:
        have, no = covered(key), set(lacks[key])
        out[key] = sorted(ch for ch in freq if ord(ch) > 0x20 and ord(ch) not in have and ch not in no)
    return out


if __name__ == '__main__':
    freq = site_text()
    lacks = {}
    for k in FONTS:
        build(k, freq)
        cmap = TTFont(source(k)).getBestCmap()
        lacks[k] = ''.join(sorted(ch for ch in freq if ord(ch) > 0x20 and ord(ch) not in cmap))
    LACKS.write_text(json.dumps(lacks, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
