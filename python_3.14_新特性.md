# 🐍 Python 3.14 新特性速览

> **发布日期**: 2025年10月7日
> **当前版本**: Python 3.14.6
> **本文档来源**: 基于 Python 官方文档 `whatsnew/3.14.html` 整理

---

## 📌 摘要：最重要的变化

Python 3.14 是 Python 编程语言的最新稳定版本，包含了语言层面、实现层面和标准库的诸多改进。

**最值得关注的变化：**
- 模板字符串字面量 (Template String Literals)
- 延迟评估注解 (Deferred Evaluation of Annotations)
- 标准库中对子解释器的支持
- 标准库新增 Zstandard 压缩支持
- asyncio 自省能力大幅增强
- 默认 REPL 支持语法高亮

---

## 🆕 一、语言新特性

### 1. PEP 750 — 模板字符串字面量 (Template String Literals)

这是 Python 3.14 最亮眼的特性之一！引入了新的字符串前缀 `t`，允许创建模板字符串对象：

```python
def render(name: str, price: float) -> str:
    t = t"Hello {name}, the price is {price:.2f}"
    # t 是一个 Template 对象，可以被安全地渲染
    return t.render()

# 相比 f-string，模板字符串更安全（避免过早求值带来的注入风险）
# 它保留模板结构，可在需要时才填充值
```

### 2. PEP 649 & PEP 749 — 延迟评估注解

彻底解决了 Python 类型注解的"前向引用"老大难问题。

```python
# Python 3.14 之前，需要这样写：
from __future__ import annotations
class A:
    def method(self) -> A:  # 需要 from __future__ 才能引用自身
        ...

# Python 3.14 之后，默认延迟评估：
class B:
    def method(self) -> B:  # 直接写就行，无需 __future__
        ...
```

注解不再在类定义时立即求值，而是延迟到 `typing.get_annotations()` 等函数需要时才求值。

### 3. PEP 734 — 标准库支持多解释器

终于把子解释器（subinterpreters）能力放到了标准库里！

```python
import interpreters

# 创建一个新的子解释器
interp = interpreters.create()
interp.run("""
import sys
print(f"我在子解释器中运行，GIL状态: {sys._is_gil_enabled()}")
""")
```

每个子解释器有独立的 GIL，可以真正实现多核并行，摆脱 GIL 限制。

### 4. PEP 768 — 安全外部调试器接口

为 CPython 提供了一个安全的调试器接口，允许外部调试器在不修改 Python 源码的情况下进行调试。

### 5. PEP 758 — `except` / `except*` 表达式允许不带括号

```python
# 以前必须这样：
try:
    ...
except (ValueError, TypeError):  # 必须加括号
    ...

# Python 3.14 现在可以这样：
try:
    ...
except ValueError, TypeError:  # 更简洁！
    ...
```

### 6. PEP 765 — `finally` 块中的控制流

对 `finally` 块中的 `return`、`break`、`continue` 行为进行了更严格的限制，减少隐式 bug。

---

## 🛠️ 二、标准库改进

### PEP 784 — 标准库新增 Zstandard 压缩支持

全新模块：`compression.zstd`

```python
import compression.zstd as zstd

# 压缩数据
compressed = zstd.compress(b"Hello, 世界!")

# 解压
data = zstd.decompress(compressed)
```

Zstandard（Facebook 开源）是当今最快的无损压缩算法之一，压缩比和速度都很优秀。

### asyncio 自省能力大幅提升

现在可以更方便地查看异步任务的内部状态：

```python
import asyncio

task = asyncio.create_task(some_coro())
print(task.get_name())      # 获取任务名
print(task.cancelling())    # 是否正在取消
print(task.uncancel())      # 取消计数器
```

新增了大量用于监控和调试 asyncio 程序的 API。

### 并发安全的 warnings 控制

`warnings` 模块现在是线程安全的，多个线程同时操作 warnings 过滤器不会再出乱子。

### 默认交互式 Shell 支持语法高亮

启动 Python 时，REPL 现在默认带颜色！

```bash
$ python3.14
Python 3.14.6 (main, Oct  7 2025, 12:00:00) [Clang 15.0.0] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> import os        # 关键字、字符串、注释都有颜色了！
```

同时多个标准库 CLI（如 `python -m json.tool`）也支持了彩色输出。

---

## 🧠 三、解释器与运行时改进

### 1. 新的解释器类型

CPython 引入了"实验性"的新型解释器实现，为未来进一步优化做铺垫。

### 2. Free-threaded 模式改进（PEP 779）

Python 3.13 实验性的无 GIL 多线程模式，在 3.14 中成为**正式支持**的特性！

```bash
# 构建时启用 free-threaded 支持
$ ./configure --disable-gil
$ make

# 运行时会看到
>>> import sys
>>> sys._is_gil_enabled()
False  # GIL 已关闭，真正多核并行！
```

Windows 和 macOS 的官方二进制发行版现在也支持这个实验性 JIT 编译器。

### 3. 增量式垃圾回收

垃圾回收器改为增量模式，减少 GC 暂停时间，对实时性要求高的程序更友好。

### 4. 错误信息改进

错误提示更加清晰、友好，帮助快速定位问题。比如 `SyntaxError` 的提示会更准确指出错误位置。

---

## 🔧 四、C API 与平台支持

### PEP 741 — Python 配置 C API

新增了一套标准的 C API 来配置 Python 解释器，嵌入 Python 到 C/C++ 程序中更方便了。

### PEP 776 — Emscripten 官方支持（Tier 3）

Python 正式支持通过 Emscripten 编译到 WebAssembly（WASM），在浏览器中运行 Python 更加靠谱。

### 新增 Android 二进制发行版

官方开始提供 Android 平台的预编译二进制包。

### Windows / macOS 支持实验性 JIT

官方二进制包包含了实验性的 JIT（Just-In-Time）编译器，某些场景下性能有明显提升。

---

## ⚠️ 五、弃用与移除

- **PEP 761**: 官方发布包不再提供 PGP 签名，改用 Sigstore 签名
- 一些老旧 C API 被标记为弃用
- 部分模块中的遗留 API 被清理

> 完整迁移指南请参考官方文档：[Porting to Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html#porting-to-python-3-14)

---

## 📊 六、快速对比一览

| 特性 | Python 3.13 | Python 3.14 |
|------|------------|-------------|
| 模板字符串 | ❌ | ✅ (PEP 750) |
| 延迟注解评估 | 需 `__future__` | ✅ 默认开启 |
| 子解释器标准库支持 | 有限 | ✅ (PEP 734) |
| Free-threaded 模式 | 实验性 | ✅ 正式支持 |
| Zstandard 压缩 | ❌ | ✅ (PEP 784) |
| REPL 语法高亮 | ❌ | ✅ |
| Emscripten 官方支持 | ❌ | ✅ (Tier 3) |
| JIT 编译器 | ❌ | ✅ 实验性 |

---

## 🚀 七、升级建议

1. **可以先尝鲜**：3.14 的新特性很有吸引力，尤其是模板字符串和延迟注解
2. **生产环境**：等待小版本稳定后再升级（如 3.14.3+）
3. **依赖检查**：确认所有第三方库都支持 Python 3.14
4. **测试**：重点测试使用了类型注解和并发代码的部分

---

## 📚 参考链接

- [Python 3.14 What's New (官方文档)](https://docs.python.org/3.14/whatsnew/3.14.html)
- [PEP 750 - Template Strings](https://peps.python.org/pep-0750/)
- [PEP 649 - Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/)
- [PEP 734 - Multiple Interpreters](https://peps.python.org/pep-0734/)
- [PEP 784 - Zstandard Support](https://peps.python.org/pep-0784/)

---

> 本文档生成于 2026-06-13，基于 Python 3.14.6 官方文档整理。
