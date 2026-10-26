# FL Studio 可选导入与混音

这是原生 DAW 的操作教程。项目不包含通用点击坐标脚本；FL 版本、窗口布局、插件与用户操作都会影响界面自动化。

## 1. 保留原演奏，准备兼容 MIDI

从 DuET 的 `performance.mid` 开始，不从 `score.mid` 开始。先确认 DAW/音源是否正确消费 CC64。

若当前导入与原生音源组合不处理踏板，可用：

```powershell
piano-workbench bake-pedal performance.mid --output runs/performance-for-daw.mid
```

工具保留 tempo、音符起点、音高、力度和通道，将 pedal-down 区间内释放的音符延长到 pedal-up，并在同音重奏处截断前音的重叠。CC64 从兼容输出移除，其他非音符消息保留。原 MIDI 不修改。

这不模拟真实踏板共鸣、半踏板、弱音踏板采样或踏板噪声。

## 2. 导入并只启用一个音源

1. 把当前工程另存为新文件。
2. 导入演奏 MIDI，采用文件原有 tempo；关闭会强制量化/对齐音符的选项。
3. 用 Piano roll 检查音符数、力度和总时长；tempo map 有变化时确认 DAW 已导入。
4. 对比 FL Keys / Dark Piano 与 FLEX / Core Pianos / KEY Bosendorfer。只启用一个通道，避免叠加误判。
5. 把主钢琴路由到独立 Mixer Insert。先保存无新增处理的版本或原始导出。

Core Pianos 是否可用、下载和授权以当前 Image-Line 状态为准；本项目不附带插件或采样。最初案例使用了官方包，安装文件约 248 MB。

## 3. 暖钢琴起点

下面是一次实际案例的起始参数，不能保证适合每首曲子和每个音源。先同音量试听，再决定是否保留。

| 插件 | 设置 |
| --- | --- |
| Fruity Parametric EQ 2 | 35 Hz 高通；136 Hz +1.3 dB；336 Hz −1.2 dB；2.937 kHz −1.7 dB；6.315 kHz 高架 −1.7 dB |
| Fruity Reeverb 2 | 24 ms 预延迟；1.8 s 衰减；220 Hz 低切；18% 湿声；24% 早期反射；其他旋钮保持初始设置 |
| 动态 | 此案例未加入额外压缩器，保留力度起伏 |

EQ 拖动参数按原界面显示取近似值。高通斜率、带宽等未逐项读取的参数不编造为精确复刻条件。参数 JSON 是说明清单，不是 `.fst`。

## 4. 原生导出与对照

- SONG 模式导出完整曲目，保留混响尾音。
- 案例使用 44.1 kHz、立体声、32 位浮点 WAV、512-point sinc，开启插件高质量。
- 导出混音前后两版；前后只改变新增效果的开关，音符、音源与其他电平保持一致。
- 若在导出窗口临时关闭 Insert FX，完成对照后恢复开启，避免后续成品误用旁通设置。

```powershell
piano-workbench compare --audio "before=before.wav" --audio "after=after.wav" --output runs/fl-comparison
```

该操作只改变导出副本的固定增益，不会修改 FL 工程，也不会补救错音。当前案例运行的是试用版：可以保存，但重新打开已保存工程需要正式授权。未将试用版重开工程作为已通过的验证。

## 官方资料

- https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/automation_midiimport.htm
- https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/FLEX.htm
- https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Fruity%20Parametric%20EQ%202.htm
- https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Fruity%20Reeverb%202.htm
