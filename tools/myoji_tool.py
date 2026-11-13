"""同姓的氏族（3.43，古代户籍户主名下面一行）：填了户主名，就找日文维基里同姓、写明了出身地的氏族。

    python -X utf8 tools/myoji_tool.py      # 需 zhconv

资料：用了「日本の氏族」信息框的条目（Template:日本の氏族 的嵌入页，约 1500 个），条目名「○○氏」的 ○○ 当作姓
（「○○家」「○○氏 (…)」去掉括号注后同样处理；「清和源氏」这类不以姓为名的、四字以上的不收），只读信息框「出身地」一栏：
去掉脚注、模板，取第一个「…国」及后面的郡、乡名，写成「信濃国小県郡真田郷」这样的短文字；没有写出身地的不收。
不是在说「你家就出自这一族」——同一个姓往往有好几族、普通人家多是明治以后才取的姓，界面写明。
输出 tools/myoji.json：{姓: [[氏族名, 出身地（日文）, 旧国]…]}；build_bundle 写 bundle/myoji-<lang>.json（户籍打开时才下载）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'myoji.json')
NOTE = re.compile(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>|<!--.*?-->|\{\{[Ee]fn[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}', re.S)


def embedded():
    titles, cont = [], {}
    while True:
        d = api({'action': 'query', 'list': 'embeddedin', 'eititle': 'Template:日本の氏族', 'einamespace': 0, 'eilimit': 500, **cont})
        titles += [x['title'] for x in d['query']['embeddedin']]
        if 'continue' not in d:
            return titles
        cont = {'eicontinue': d['continue']['eicontinue']}


def origin(wt):
    m = re.search(r'^\s*\|\s*出身地\s*=([^\n]*)', wt, flags=re.M)
    if not m:
        return None, None
    v = NOTE.sub('', m.group(1))
    v = re.sub(r'\{\{[^{}]*\}\}', '', v)
    v = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', v)
    v = re.sub(r'<[^>]+>', ' ', v)
    m = re.search(r'([一-龥々]{1,4}国)((?:[一-龥々ヶ]{1,6}[郡庄郷村荘])*)', v)
    if not m:
        return None, None
    return (m.group(1) + m.group(2))[:20], m.group(1)


def main():
    titles = embedded()
    got = pages(titles, 'revisions', rvprop='content', rvslots='main')
    provs = {f['properties']['key'] for f in json.load(open(os.path.join(ROOT, 'src', 'data', 'provinces.json'), encoding='utf-8'))['features']}
    out = {}
    for t in titles:
        base = re.sub(r' \(.*\)$', '', t)
        m = re.fullmatch(r'([一-龥々ヶ]{1,3})(氏|家)', base)
        if not m:
            continue
        pg = got.get(t, {})
        wt = pg['revisions'][0]['slots']['main']['content'] if pg.get('revisions') else ''
        text, prov = origin(wt)
        if not text or prov not in provs:
            continue
        out.setdefault(m.group(1), []).append([base, text, prov])
    for v in out.values():
        v.sort(key=lambda x: (x[0].endswith('家'), x[0]))
    assert any(x[0] == '真田氏' and x[2] == '信濃国' and '真田' in x[1] for x in out['真田']), out.get('真田')
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(titles)} 个氏族条目 → {len(out)} 个姓、{sum(len(v) for v in out.values())} 族写明了出身地')


if __name__ == '__main__':
    main()
