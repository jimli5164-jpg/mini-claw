# MiniClaw AI Agent

一个基于 LLM 的智能代理系统，支持工具调用、技能管理、多渠道接入和对话管理。

## ✨ 特性

- **智能工具调用**：支持文件读写、目录浏览、命令执行、网络搜索等多种工具
- **技能系统**：可扩展的技能框架，内置代码审查、翻译、天气查询等技能
- **多渠道支持**：支持 CLI 命令行和飞书机器人接入
- **会话管理**：自动保存和加载对话历史，支持多会话隔离
- **记忆整合**：智能消息压缩和摘要生成，优化对话上下文
- **消息总线架构**：基于异步消息队列的解耦架构，易于扩展新渠道

## 🛠️ 技术栈

- **语言**：Python 3.9+
- **异步框架**：asyncio
- **LLM 兼容**：OpenAI 兼容接口（支持硅基流动、Moonshot 等）
- **飞书 SDK**：lark-oapi
- **搜索工具**：DuckDuckGo (ddgs)
- **配置管理**：JSON + 环境变量

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd "mini claw"
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

复制示例配置文件并填入你的 API Key：

```bash
cp config.json.example config.json
```

修改 `config.json`，填入你的 API Key：

```json
{
    "api_key": "your-api-key",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Pro/moonshotai/Kimi-K2.5",
    "workspace": ".",
    "max_iterations": 32,
    "identity_file": "identity.md"
}
```

**⚠️ 安全提示：** `config.json` 包含敏感信息，已被 `.gitignore` 排除，请不要提交到版本控制。

### 4. 启动服务

```bash
python3 main.py
```

## 📋 工具列表

| 工具名称 | 功能描述 |
|---------|---------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件内容 |
| `list_dir` | 列出目录内容 |
| `get_time` | 获取当前时间 |
| `exec` | 执行系统命令 |
| `web_search` | DuckDuckGo 网络搜索 |
| `web_fetch` | 获取网页内容 |

## 🎯 技能系统

内置技能：

- **代码审查** (`code_review`)：审查代码质量和安全性
- **翻译** (`translator`)：多语言翻译
- **天气查询** (`weather`)：查询天气信息

### 添加自定义技能

在 `skills/` 目录下创建新目录，包含 `SKILL.md` 文件：

```markdown
---
name: "技能名称"
description: "技能描述"
parameters:
  - name: "参数名"
    type: "string"
    description: "参数描述"
---

技能详细说明和使用方法...
```

## 💬 渠道接入

### CLI 渠道

启动后直接在终端输入命令即可交互：

```bash
>>> 你好
>>> /tools          # 查看可用工具
>>> /clear          # 清空历史
>>> /exit           # 退出
```

### 飞书渠道

在 `config.json` 中配置飞书应用信息：

```json
{
    "feishu": {
        "app_id": "your-app-id",
        "app_secret": "your-app-secret",
        "verification_token": "your-verification-token",
        "encrypt_key": ""
    }
}
```

**飞书开发者后台配置要求：**

1. 创建企业自建应用
2. 添加事件订阅：`im.message.receive_v1`
3. 配置权限：`im:chat:readonly`, `im:message:send_as_bot`, `im:message.group_msg`, `im:message.p2p_msg`
4. 发布应用到企业

## 📁 项目结构

```
mini claw/
├── agent/              # Agent 核心模块
│   ├── providers/      # LLM 提供者（OpenAI 兼容）
│   ├── tools/          # 工具实现
│   ├── session/        # 会话管理
│   ├── context.py      # 上下文构建器
│   ├── loop.py         # Agent 主循环
│   ├── memory.py       # 记忆整合
│   └── skills.py       # 技能加载器
├── bus/                # 消息总线
│   └── queue.py        # 消息队列实现
├── channels/           # 渠道实现
│   ├── base.py         # 渠道抽象基类
│   ├── cli.py          # CLI 渠道
│   └── feishu.py       # 飞书渠道
├── skills/             # 技能目录
│   ├── code_review/
│   ├── translator/
│   └── weather/
├── gateway.py          # 网关（协调渠道和 Agent）
├── config.py           # 配置加载
├── config.json         # 配置文件
├── identity.md         # Agent 人设
└── main.py             # 入口文件
```

## 🔧 配置说明

| 配置项 | 说明 | 默认值 |
|-------|------|-------|
| `api_key` | LLM API Key | - |
| `base_url` | API 服务地址 | `https://api.siliconflow.cn/v1` |
| `model` | 使用的模型 | `Pro/moonshotai/Kimi-K2.5` |
| `workspace` | 工作区路径 | `.` |
| `max_iterations` | 最大迭代次数 | `32` |
| `identity_file` | 人设文件 | `identity.md` |

## 📝 使用示例

### 基本对话

```
>>> 你好
🤖 嘿！我是 MiniClaw，你的 AI 小助手。有啥需要帮忙的？

>>> 帮我搜索今天的新闻
【思考】用户需要搜索新闻，调用 web_search 工具...
🤖 以下是今天的热门新闻：...
```

### 文件操作

```
>>> 帮我查看当前目录有哪些文件
【思考】用户需要列出目录，调用 list_dir 工具...
🤖 当前目录包含：
- main.py
- config.json
- agent/
- skills/
...
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交代码：`git commit -m 'feat: xxx'`
4. 推送到远程：`git push origin feature/xxx`
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 代码规范
- 使用类型注解
- 添加适当的文档字符串
- 编写单元测试

## 📄 许可证

MIT License

## 🙏 致谢

- [硅基流动](https://siliconflow.cn) - LLM 服务
- [Moonshot AI](https://moonshot.cn) - Kimi 模型
- [飞书开放平台](https://open.feishu.cn) - 企业即时通讯
