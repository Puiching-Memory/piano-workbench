# Windows 本地环境

基础功能无需 GPU。建议先跑 `demo`、`inspect`、`bake-pedal`、`render`、`compare`，确认音源和 FFmpeg 可用，再添加模型。

## 基础安装

在项目目录使用 PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
ffmpeg -version
ffprobe -version
piano-workbench doctor
```

不需要改变系统执行策略也可以直接调用：

```powershell
.\.venv\Scripts\python.exe -m piano_workbench doctor
```

SF2 路径有空格时加引号。避免把大音源、下载缓存和模型放进 Git；`.gitignore` 已排除这些文件。

## DuET 与 CUDA

按 [PyTorch 官方安装器](https://pytorch.org/get-started/locally/) 为驱动和硬件选择组合，再安装 `.[transcription]`。音频前端需要兼容的 PyTorch/torchaudio。`doctor` 只读取安装版本，不会据此宣称 GPU 能运行。

本机最初案例曾复用 torch 2.12.0+cu132，并对 torchaudio 可选原生扩展做过兼容适配；**该本机改动未打包进本项目**。因此它不是推荐给新用户照抄的通用安装组合。先用官方兼容组合；有问题时保留错误与版本记录。

DuET 代码依赖固定提交 `c98699c021affd3778434c3e7a5cd82214052418`。上游可变化，模型仓库访问条件也可能变化。可提前准备本地模型目录并通过 `--model` 传入；CLI 不接管登录，也不存储 token。

```powershell
piano-workbench transcribe piano.wav --model "D:/Models/DuET" --device cuda --output runs/transcription
```

## 失败后如何继续

完整 `run` 失败时会保留已完成文件及 `failure.json`。不要覆盖同一个输出目录。可以把已完成的 `performance.mid` 交给 `render`，把原始 MusicXML 交给 `engrave`，或直接对已完成 WAV 使用 `compare`。

`run --skip-score` 仅接受 MIDI；这样可以独立验证渲染，不触发模型加载或网络下载。

## 文件与声音

- `performance.mid`：保留演奏时间、力度和踏板；不包含钢琴采样。
- `score.mid`：按谱面整理的事件，不保证与录音同速。
- `performance_pedal_baked.mid`：给 DAW 的兼容近似；不要再将其与原 CC64 叠加。
- SF2 渲染使用固定 bank/preset（从 0 编号）；忽略 MIDI program change，转发其他支持的控制器。发现鼓通道或 bank-select 时会要求先整理输入。
- FFmpeg 匹配输出默认约 −23 LUFS；如峰值需要更多余量，整组目标会降低。
