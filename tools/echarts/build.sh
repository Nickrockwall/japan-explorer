#!/bin/sh
# 生成 src/vendor/echarts.min.js：ECharts 5.5.1 只打包 entry.js 里登记的部件（完整版 1 MB，这样约一半）。
# 用法：sh tools/echarts/build.sh（需要 Node；依赖装在 .cache/echarts-build，不进仓库）
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
work="$root/.cache/echarts-build"
mkdir -p "$work"
cp "$here/entry.js" "$work/entry.js"
cd "$work"
[ -f package.json ] || npm init -y >/dev/null
npm install --no-audit --no-fund echarts@5.5.1 esbuild@0.24.0 >/dev/null
{
  sed -n '1,/^\*\//p' node_modules/echarts/dist/echarts.min.js 2>/dev/null || true
  npx esbuild entry.js --bundle --minify --format=iife --global-name=echarts --target=es2018 --legal-comments=none
} > "$root/src/vendor/echarts.min.js"
wc -c "$root/src/vendor/echarts.min.js"
