# 验证记录

日期：2026-10-26。这里区分单元测试、实际集成运行和仍未覆盖的部分。

## 已执行

| 范围 | 证据与结果 |
| --- | --- |
| Python 打包 | 本地 editable wheel 构建并安装成功；复用已有依赖，不等于全新机器安装验证 |
| 自动测试 | 14 项本地测试通过，包含实际 FFmpeg 对照、TinySoundFont 渲染与 PDF/SVG 排版；不是只运行语法检查 |
| MIDI 踏板 | 原创 56 音符示例；另用本地 477 音符演奏验证：455 音符延长、294 处同音重奏截断，起点/音高/通道/力度不变。后者文件未纳入公开仓库 |
| tempo map | 原创示例前 16 拍 96 BPM、后 16 拍 84 BPM，MIDI 21.428576 秒；渲染含 6 秒释放尾音共 27.428571 秒 |
| SF2 渲染 | Salamander Grand Piano SF2，bank 0/preset 0；原 CC64 与音符长度近似各实际渲染一次，无新增 EQ/混响 |
| 同响度对照 | 两版无损输出均 −23.02 LUFS；真峰值分别 −6.21、−6.51 dBTP；仅固定增益。LRA 原生版 3.4→3.4 LU，近似版 3.3→3.4 LU，差异在测量舍入范围内 |
| 模型音频入口 | 从原创示例渲染的音频，调用 DuET 的音频接口，实际经过 Transkun 与 DuET epoch83；CUDA 完成约 32.74 秒，产出 56 个预测音符。音符数相同不等于逐音符识别准确 |
| 模型 MIDI 入口与整条编排 | `run` 从原创演奏 MIDI 经 DuET、PDF 排版、踏板兼容、SF2 渲染、试听页完整通过，约 25.91 秒 |
| 乐谱排版 | 原创 XML 排版输出 1 页 PDF；56 项音高/起点/时值/谱表事件一致，56 个 XML 音符片段与 SVG 可见音符组一致；PDF 已重新打开并渲染为图片检查。另一个本地 477 音符案例输出 2 页，513 个拆分后片段与 SVG 可见组一致 |
| 浏览器 | 系统 Edge 无头实际加载公开试听页：1120 px 桌面、375 px 手机均已截图检查；切换版本保留 6 秒位置，无 JS 异常，手机无水平溢出 |

测试命令：

```powershell
$env:PIANO_WORKBENCH_TEST_SF2 = "C:/SoundFonts/test-piano.sf2"
$env:PIANO_WORKBENCH_TEST_PRESET = "0"
python -m unittest discover -s tests -v
```

没有 SF2 环境变量时，音源集成测试会明确跳过；没有 FFmpeg/ffprobe 时，音频集成测试也会跳过；未安装 `[score]` 时跳过排版测试。GitHub Actions 覆盖 Windows/Ubuntu 24.04 与 Python 3.11/3.12，并另设安装 FFmpeg 和 `[score]` 的 Linux 集成任务；CI 不附带 SF2，也不运行模型推理。云端结果以仓库 [Actions](https://github.com/Puiching-Memory/piano-workbench/actions) 对应提交为准。

首次云端安装暴露了 Linux 上 PyAudio 编译缺少 `portaudio.h` 的问题；CI 与安装说明已补充 `portaudio19-dev`。本地模型集成结果不代表云端 GPU 验证。

另一次运行在 Ubuntu 26 的软件源下载 FFmpeg 依赖时耗时过长，尚未运行测试便取消；Linux CI 已固定为 Ubuntu 24.04，并限制每个任务最长 15 分钟。

## 已验证的本机组件

Python 3.12.15；NumPy 2.5.4；mido 1.3.3；tinysoundfont 0.3.7；DuET 代码提交 `c98699c021affd3778434c3e7a5cd82214052418`；Transkun 2.0.1；torch 2.12.0+cu132；music21 10.5.1；Verovio 6.3.0；ReportLab 5.1.0；svglib 2.3.2。

模型运行复用了本机已有的音频环境及其 torchaudio 兼容适配，不宣称这组依赖在全新 Windows 或 Linux 安装下已通过。适配说明见 `windows.md`。

## 尚未完成的验证

- 多首真实录音的逐音符准确率、复杂音色或非钢琴混音的转谱表现。
- 全新设备安装、Linux 实机 GPU 与不同 SF2 实现的兼容性。
- 自动听音评分、物理踏板共鸣或半踏板还原。
- 通用 FL Studio GUI 自动化、所有版本的插件兼容、试用版重开工程。

本项目提供可复现流程和检查记录，不把“程序运行成功”包装成“还原了原曲演奏与音色”。
