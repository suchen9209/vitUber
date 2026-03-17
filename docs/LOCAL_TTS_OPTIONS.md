# 🎙️ 本地TTS方案选择

根据你的硬件配置，推荐不同方案：

## 方案对比

| 方案 | 需要显卡 | 音质 | 延迟 | 部署难度 | 推荐指数 |
|------|---------|------|------|---------|---------|
| **pyttsx3** | ❌ 不需要 | ⭐⭐ 机械 | 低 | 极简 | ⭐⭐⭐ 应急用 |
| **ChatTTS** | ✅ 需要 4GB+ | ⭐⭐⭐⭐ 自然 | 中 | 中等 | ⭐⭐⭐⭐⭐ 推荐 |
| **GPT-SoVITS** | ✅ 需要 4GB+ | ⭐⭐⭐⭐⭐ 优秀 | 中 | 较复杂 | ⭐⭐⭐⭐ 效果最好 |
| **CosyVoice** | ✅ 需要 6GB+ | ⭐⭐⭐⭐ 自然 | 中 | 中等 | ⭐⭐⭐⭐ |

---

## 🚀 快速选择

### 如果你没有显卡 / 想最简单
→ **pyttsx3**（5分钟搞定，就是声音机械点）

### 如果你有NVIDIA显卡（4GB+显存）
→ **ChatTTS**（30分钟部署，声音自然，支持情感）

---

## 方案1: pyttsx3（无显卡，极简）

完全离线，使用系统自带语音。

### 安装
```bash
pip install pyttsx3
```

### 配置
```yaml
# config/api_keys.yaml
tts:
  engine: "pyttsx3"
```

### 特点
- ✅ 真正零依赖，断网也能用
- ✅ Windows/Mac/Linux都支持
- ❌ 声音比较机械（Siri早期水平）
- ❌ 中文支持一般

---

## 方案2: ChatTTS（推荐，有显卡）

开源项目，声音非常自然，支持笑声、停顿、情感。

### 安装部署
```bash
# 克隆项目
git clone https://github.com/2noise/ChatTTS.git
cd ChatTTS

# 安装依赖
pip install -r requirements.txt

# 下载模型（自动）
python -c "import ChatTTS; ChatTTS.Chat().load()"

# 启动API服务
python examples/api/api.py
```

### 配置
```yaml
# config/api_keys.yaml
tts:
  engine: "chattts"
  chattts_url: "http://localhost:8080"
```

### 特点
- ✅ 声音非常自然（接近真人）
- ✅ 支持笑声、停顿、语气词
- ✅ 可调节语速、音调
- ❌ 需要4GB+显存
- ❌ 第一次启动要下载模型（约2GB）

---

## 方案3: GPT-SoVITS（效果最好，有显卡）

前面介绍过，可以克隆任意声音。

---

## 我现在给你做的

你可以告诉我：

1. **你有没有NVIDIA显卡？** 有的话显存多大？
2. **能不能接受机械音？** 还是一定要自然？

我直接：
- 帮你写好本地TTS的代码
- 写好部署脚本
- 改好配置文件

你复制粘贴就能用。
