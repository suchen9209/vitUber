# 🎙️ GPT-SoVITS 语音克隆配置指南

> 使用自己的声音或角色声音，告别机械音

---

## 什么是 GPT-SoVITS？

**GPT-SoVITS** 是一个开源的语音合成项目，可以让你：

- ✅ 用5-10秒音频克隆任意声音
- ✅ 本地运行，无需联网
- ✅ 支持中日英三语
- ✅ 情感和语调更自然
- ✅ **完全免费**

相比 Edge TTS：
| 特性 | Edge TTS | GPT-SoVITS |
|------|---------|-----------|
| 成本 | 免费 | 免费 |
| 音质 | 标准 | 更好 |
| 音色 | 固定几种 | 任意克隆 |
| 情感 | 较机械 | 更自然 |
| 部署 | 开箱即用 | 需要本地部署 |
| 显存需求 | 无 | 4GB+ |

---

## 方案选择

### 方案A：自己部署（推荐，效果最好）

**适合**：有NVIDIA显卡（4GB+显存）的用户

**优点**：
- 完全本地，隐私安全
- 可训练自己的专属模型
- 延迟最低

**缺点**：
- 第一次部署较麻烦
- 需要显卡

### 方案B：使用现成服务

**适合**：没有显卡，或不想折腾的用户

**做法**：
- 找已经部署好的GPT-SoVITS API服务
- 修改配置文件中的URL即可

**缺点**：
- 可能需要付费
- 隐私问题（音频上传）

---

## 方案A：本地部署步骤

### 步骤1：下载GPT-SoVITS

```bash
# 克隆仓库
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS

# 创建conda环境
conda create -n gptsovits python=3.9
conda activate gptsovits

# 安装依赖
pip install -r requirements.txt
```

### 步骤2：下载预训练模型

```bash
# 运行下载脚本
python tools/download_models.py

# 或者手动下载放到对应目录：
# - GPT_SoVITS/pretrained_models/
# - tools/uvr5/
```

### 步骤3：准备参考音频

**需要准备**：
- 1-3个参考音频文件（WAV格式）
- 每个5-10秒
- 清晰的说话声，无背景噪音
- 内容最好是目标角色的台词

**放在哪**：
```
GPT-SoVITS/
└── reference_audio/
    ├── sample1.wav
    ├── sample1.txt      # 对应的文字内容
    ├── sample2.wav
    └── sample2.txt
```

### 步骤4：启动推理服务

```bash
# 启动API服务（默认端口9880）
python api.py

# 或者启动WebUI手动测试
python webui.py
```

看到以下输出说明启动成功：
```
Running on local URL:  http://0.0.0.0:9880
```

### 步骤5：配置项目使用

编辑 `ai_streamer/config/api_keys.yaml`：

```yaml
tts:
  engine: "gpt_sovits"  # 改为这个
  gpt_sovits_url: "http://localhost:9880"
```

---

## 方案B：快速体验（无显卡）

如果没有显卡，可以用Colab免费版：

1. 打开 [GPT-SoVITS Colab](https://colab.research.google.com/)
2. 运行所有单元格
3. 在「API模式」单元格启动服务
4. 使用 ngrok 获取公网URL
5. 把URL填到配置文件

**注意**：Colab免费版有使用时长限制（约12小时）

---

## 参考音频制作建议

### 录制自己的声音：

```bash
# 用ffmpeg录制（需要安装ffmpeg）
ffmpeg -f avfoundation -i ":0" -t 10 -acodec pcm_s16le -ar 22050 -ac 1 myvoice.wav
```

### 录制建议：
- 环境安静，无回音
- 距离麦克风15-20cm
- 语速正常，吐字清晰
- 内容有情感变化（开心、惊讶、平静）

### 从视频提取：

```bash
# 提取视频中的音频
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 22050 -ac 1 output.wav

# 裁剪10秒片段
ffmpeg -i output.wav -ss 00:01:30 -t 10 sample.wav
```

---

## 测试语音合成

部署完成后测试：

```bash
curl -X POST "http://localhost:9880" \
  -H "Content-Type: application/json" \
  -d '{
    "refer_wav_path": "reference_audio/sample1.wav",
    "prompt_text": "这是参考音频的文字内容",
    "prompt_language": "zh",
    "text": "你好，我是AI主播",
    "text_language": "zh"
  }' \
  --output test.wav

# 播放测试
afplay test.wav  # Mac
aplay test.wav   # Linux
```

---

## 集成到项目

代码已经支持GPT-SoVITS，只需要改配置：

### 1. 修改配置文件

```yaml
# ai_streamer/config/api_keys.yaml
tts:
  engine: "gpt_sovits"
  gpt_sovits_url: "http://localhost:9880"
  
  # 参考音频配置（可选，也可代码中动态设置）
  gpt_sovits_ref_audio: "path/to/your/voice.wav"
  gpt_sovits_ref_text: "参考音频的文字内容"
  gpt_sovits_language: "zh"
```

### 2. 重启项目

```bash
./start.sh 你的房间号
```

现在AI说话就是你设定的声音了！

---

## 进阶：训练专属模型

如果想要更好的效果，可以训练自己的GPT-SoVITS模型：

### 数据准备：
- 30分钟-1小时的干净音频
- 切割成5-10秒的片段
- 人工标注或ASR识别文字

### 训练流程：
1. 数据预处理（切割、标注）
2. SoVITS训练（声音特征）
3. GPT训练（语义特征）
4. 推理测试

详细步骤参考：[官方教程](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/docs/cn/README.md)

---

## 常见问题

### Q: 启动报错 CUDA out of memory
**A**: 
- 显存不足，需要4GB+
- 尝试降低batch size
- 或使用CPU模式（慢很多）

### Q: 合成声音不像
**A**: 
- 参考音频质量不够好
- 参考音频太短（建议5-10秒）
- 需要更多参考音频（3-5个）
- 尝试微调模型

### Q: 有电流声/杂音
**A**: 
- 参考音频有背景噪音
- 使用UVR5工具先分离人声
- 提高录音质量

### Q: 中英混合说得不好
**A**: 
- GPT-SoVITS对中英混合支持一般
- 尽量用单一语言
- 或准备中英双语的参考音频

### Q: 延迟太高
**A**: 
- 首次加载模型较慢
- 后续会快很多
- 可开启模型预热

---

## 推荐配置

### 最低配置（能跑）：
- GPU: GTX 1050 4GB
- RAM: 8GB
- 存储: 10GB

### 推荐配置（流畅）：
- GPU: RTX 3060 12GB
- RAM: 16GB
- 存储: SSD 20GB

### 当前 Edge TTS vs GPT-SoVITS 对比：

| 项目 | Edge TTS | GPT-SoVITS |
|------|---------|-----------|
| 启动难度 | ⭐ 一键启动 | ⭐⭐⭐ 需要部署 |
| 运行成本 | ⭐ 免费 | ⭐ 免费（需电费） |
| 声音质量 | ⭐⭐⭐ 标准 | ⭐⭐⭐⭐⭐ 优秀 |
| 个性化 | ⭐ 固定音色 | ⭐⭐⭐⭐⭐ 任意克隆 |
| 情感表达 | ⭐⭐ 较机械 | ⭐⭐⭐⭐ 更自然 |
| 推荐度 | 新手首选 | 进阶选择 |

---

## 总结

**没有显卡/不想折腾**：用 Edge TTS，效果够用

**有显卡/追求效果**：部署 GPT-SoVITS，5分钟音频就能克隆声音

**需要我帮你**：
- [ ] 写自动化部署脚本？
- [ ] 制作参考音频教程？
- [ ] 集成其他TTS（如Azure、阿里云）？
