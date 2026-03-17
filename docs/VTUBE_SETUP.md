# 🎭 VTube Studio 完整配置指南

> 确保口型同步和动作触发正常工作

---

## 1. 下载和安装

1. **下载 VTube Studio**
   - Steam搜索 "VTube Studio"
   - 免费版即可使用，付费版有更多功能

2. **准备 Live2D 模型**
   - 使用自带的免费模型，或导入自己的模型
   - 模型需要有适当的 BlendShape（口型变形）

---

## 2. OSC 配置（口型同步）

### 步骤：

1. **打开 VTube Studio**
2. 点击右下角 **设置按钮（齿轮图标）**
3. 选择 **「Network」** 标签
4. 找到 **「OSC」** 部分

### 设置参数：

```
☑ Enable OSC = ON
Port = 8001
IP = 127.0.0.1 (本机)
```

### 确认OSC接收：

在同一页面，确保以下接收选项开启：
- ☑ Receive BlendShapes
- ☑ Receive Head Position

---

## 3. 热键配置（表情/动作）

这是**最重要**的部分！需要手动绑定每个表情到键盘快捷键。

### 步骤：

1. 点击右下角 **设置按钮**
2. 选择 **「Hotkeys」** 标签
3. 点击 **「Add Hotkey」** 添加热键

### 绑定列表（按这个来）：

| 功能 | 热键 | VTube Studio设置 |
|------|------|-----------------|
| 开心 | F1 | Expression → Happy |
| 难过 | F2 | Expression → Sad |
| 惊讶 | F3 | Expression → Surprised |
| 生气 | F4 | Expression → Angry |
| 默认 | F5 | Expression → Neutral |
| 笑声 | F6 | Animation → Laugh |
| 挥手 | F7 | Animation → Wave |
| 跳舞 | F8 | Animation → Dance |

### 设置方法：

对于每个表情：
1. 点击 **「Add Hotkey」**
2. **Action** 选择：`Load Expression` 或 `Trigger Animation`
3. **Item** 选择对应的表情/动画名称
4. **Input** 按下对应的 F键
5. 点击 **Save**

**注意**：
- 表情（Expression）会保持，需要设置一个默认表情切换回去
- 动画（Animation）播放一次就结束
- 如果模型没有某个表情，可以用相近的替代

---

## 4. 口型同步验证

### 测试 OSC 连接：

运行项目后，说话时观察模型嘴巴是否张开：

```bash
cd ai_streamer
python main.py --room 你的房间号 --test
```

在测试模式输入任意文字，看模型嘴巴是否动。

### 如果嘴巴不动：

1. **检查OSC端口**
   ```bash
   # 查看8001端口是否被占用
   netstat -an | grep 8001
   ```

2. **检查 BlendShape 名称**
   
   不同模型的 BlendShape 名称可能不同：
   - 标准名称：`JawOpen`, `MouthOpen`
   - 日语模型：`あ`, `い`, `う`
   
   修改 `interfaces/vtube_studio.py` 中的名称：
   ```python
   # 第 158 行附近
   self.osc_client.send_message(
       "/VMC/Ext/Blend/Val",
       ["你的模型嘴巴参数名", float(value)]
   )
   ```

3. **检查防火墙**
   - Windows防火墙可能阻止UDP端口
   - 添加 VTube Studio 为例外

---

## 5. 表情触发验证

### 手动测试：

在键盘上按 F1-F8，看模型是否切换表情。

如果不行：
1. 检查热键是否正确绑定
2. 检查模型是否有对应的 Expression
3. 看 VTube Studio 右下角是否有热键触发提示

### 通过代码测试：

```python
# 在项目目录下运行
python -c "
from interfaces.vtube_studio import VTubeStudioController
import asyncio

vtube = VTubeStudioController()

async def test():
    print('测试表情...')
    vtube.set_expression('happy')
    await asyncio.sleep(2)
    vtube.set_expression('surprised')
    await asyncio.sleep(2)
    vtube.set_expression('neutral')
    print('测试完成')

asyncio.run(test())
"
```

---

## 6. 常见问题

### Q: 口型延迟很高
**A**: 
- 这是OSC的正常现象（约100-200ms延迟）
- 可以降低TTS的句子长度
- 或者用 GPT-SoVITS 预先合成语音

### Q: 嘴巴张得太夸张/太小
**A**: 
- 修改 `vtube_studio.py` 第158行的乘数：
  ```python
  ["JawOpen", float(value) * 0.5]  # 改为0.5减小幅度
  ```

### Q: 某些表情没有反应
**A**: 
- 模型本身可能没有该 Expression
- 在 VTube Studio 的 Expression 面板查看可用表情
- 修改 `KEY_MAP` 使用模型支持的表情名

### Q: 直播时OSC不稳定
**A**: 
- 确保 VTube Studio 和程序在同一台机器
- 关闭其他可能占用OSC的软件
- 检查是否有多个VTube Studio实例

---

## 7. 配置文件对应

你的 `config/api_keys.yaml`：

```yaml
vtube_studio:
  enabled: true
  ip: "127.0.0.1"
  port: 8001
  hotkeys:
    happy: "f1"
    sad: "f2"
    surprised: "f3"
    angry: "f4"
    neutral: "f5"
    laugh: "f6"
    wave: "f7"
    dance: "f8"
```

如果修改了热键，需要同时修改这里和 VTube Studio 的设置。

---

## 8. 快速检查清单

启动前确认：
- [ ] VTube Studio 已打开
- [ ] 模型已加载
- [ ] OSC 已启用 (端口8001)
- [ ] 热键 F1-F8 已绑定
- [ ] 模型有 JawOpen/MouthOpen BlendShape

---

**搞定这些，口型和动作就能正常工作了！**
