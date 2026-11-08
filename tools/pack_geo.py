"""把网站要下载的 GeoJSON 无损压成 .pack.json（3.27）。

各文件坐标都是 3 位小数：每串坐标（环 / 折线，至少两个 [经, 纬]）改写成 {"_d": [x0, y0, dx1, dy1, …]}，
即乘 1000 取整后与前一点的差，其余结构不动。前端 store.js 的 unpack 还原，结果与原文件逐个数相同
（整数 / 1000 与解析三位小数得到的是同一个 double）。日本全图 1.3 MB → 0.4 MB，gzip 后 292 → 117 KB。

源文件（japan.json、provinces.json、municipalities/NN.json…）不动，各工具照旧读它们；
改了源文件后重跑本脚本，check_data.check_packs 核对 .pack.json 是最新的。

    python -X utf8 tools/pack_geo.py
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sources():
    out = [os.path.join('src', 'assets', 'geojson', 'japan.json')]
    out += [os.path.join('src', 'data', f) for f in ('provinces.json', 'province_eras.json', 'sengoku_units.json')]
    out += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, 'src', 'data', 'municipalities', '[0-9][0-9].json')))
    return out


def pack_path(src):
    return src[:-len('.json')] + '.pack.json'


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_line(o):
    return (isinstance(o, list) and len(o) >= 2
            and all(isinstance(p, list) and len(p) == 2 and _num(p[0]) and _num(p[1]) for p in o))


def pack(o):
    if _is_line(o):
        d, px, py = [], 0, 0
        for x, y in o:
            X, Y = round(x * 1000), round(y * 1000)
            if X / 1000 != x or Y / 1000 != y:
                raise ValueError(f'坐标不是 3 位小数：{x}, {y}')
            d += [X - px, Y - py]
            px, py = X, Y
        return {'_d': d}
    if isinstance(o, list):
        return [pack(x) for x in o]
    if isinstance(o, dict):
        return {k: pack(v) for k, v in o.items()}
    return o


def unpack(o):
    """与 store.js 的 unpack 相同"""
    if isinstance(o, list):
        return [unpack(x) for x in o]
    if isinstance(o, dict):
        if '_d' in o:
            d, out, x, y = o['_d'], [], 0, 0
            for i in range(0, len(d), 2):
                x += d[i]
                y += d[i + 1]
                out.append([x / 1000, y / 1000])
            return out
        return {k: unpack(v) for k, v in o.items()}
    return o


def packed_text(src):
    with open(os.path.join(ROOT, src), encoding='utf-8') as f:
        data = json.load(f)
    p = pack(data)
    assert unpack(p) == data, f'{src} 还原后不一致'
    return json.dumps(p, ensure_ascii=False, separators=(',', ':'))


def main():
    before = after = 0
    for src in sources():
        text = packed_text(src)
        with open(os.path.join(ROOT, pack_path(src)), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        before += os.path.getsize(os.path.join(ROOT, src))
        after += len(text.encode())
    print(f'{len(sources())} 个文件：{before // 1024} KB → {after // 1024} KB')


if __name__ == '__main__':
    main()
