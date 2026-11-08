"""重写 sw.js 的 SHELL（离线时必须有的应用外壳文件）并在列表变化时把 VERSION 加一。

新增 / 删除 / 改名 src/js 下的模块后跑：python -X utf8 tools/build_sw.py。check_data.check_shell 会核对 SHELL 与这里算出的一致。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXED = ['./', 'index.html', 'manifest.webmanifest', 'src/css/style.css']
TAIL = ['src/vendor/echarts.min.js', 'src/fonts/sc.css', 'src/fonts/jp.css', 'src/assets/geojson/japan.json', 'src/assets/icons/icon-192.png', 'src/assets/icons/seal.svg', 'src/assets/icons/favicon.svg']
FIRST = ['app.js', 'country.js', 'shell.js']  # 入口与最先用到的放前面（顺序不影响功能，只为好读）


def shell():
    js_root = os.path.join(ROOT, 'src', 'js')
    mods = []
    for d, _, files in os.walk(js_root):
        for f in files:
            if f.endswith('.js'):
                mods.append(os.path.relpath(os.path.join(d, f), js_root).replace(os.sep, '/'))
    mods.sort(key=lambda m: (m not in FIRST, FIRST.index(m) if m in FIRST else 0, '/' in m, m))
    return FIXED + [f'src/js/{m}' for m in mods] + TAIL


def render(paths):
    lines, line = [], '  '
    for p in paths:
        item = f"'{p}', "
        if len(line) + len(item) > 120:
            lines.append(line.rstrip())
            line = '  '
        line += item
    lines.append(line.rstrip())
    return 'const SHELL = [\n' + '\n'.join(lines) + '\n];'


def current(sw):
    return re.findall(r"'([^']+)'", re.search(r'const SHELL = \[(.*?)\];', sw, flags=re.S).group(1))


def main():
    path = os.path.join(ROOT, 'sw.js')
    sw = open(path, encoding='utf-8').read()
    want = shell()
    if current(sw) == want:
        print('sw.js SHELL 已是最新')
        return
    sw = re.sub(r'const SHELL = \[.*?\];', lambda _: render(want), sw, flags=re.S)
    sw = re.sub(r"const VERSION = 'je-v(\d+)';", lambda m: f"const VERSION = 'je-v{int(m.group(1)) + 1}';", sw)
    open(path, 'w', encoding='utf-8', newline='\n').write(sw)
    print('sw.js SHELL 已更新，VERSION', re.search(r"je-v\d+", sw).group(0))


if __name__ == '__main__':
    main()
