# 音频文件（可选）

网站默认用 Web Audio 实时合成全部声音，这个目录可以是空的。

想换成录好的音频：把文件放在这里，再到 `src/js/audio.js` 顶部的 `FILES` 里取消对应一行的注释。

| 名称 | 文件名 | 用途 |
|---|---|---|
| bgm | `bgm_edo_ambience.mp3` | 背景音乐（循环播放） |
| click | `sfx_click.mp3` | 选县、切换时代等轻击 |
| stamp | `sfx_stamp.mp3` | 御朱印盖印 |
| battle | `sfx_battle.mp3` | 开始合战 |
| drum | `sfx_drum.mp3` | 合战交战阶段 |

请只放有权使用的音频，并把来源与许可写在这里。文件加载失败时自动退回合成音。
