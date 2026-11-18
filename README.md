# astrbot_plugin_cmdlist

一条指令列出 AstrBot 里所有插件注册的命令。

## 用法

```
/查询指令
```

输出是一条命令一行，不分插件：


每行包含：

- 命令名（含子命令）
- 别名，最多 3 个
- `[管理]` 仅管理员可用
- `[停用]` 命令被关闭
- 一行说明，最长 22 字
指令多时按每 15 行一条消息分开发，间隔 0.3 秒。

## 数据来源

优先调用 AstrBot 内置接口：

```python
from astrbot.core.star.command_management import list_commands
```

当版本没有这个函数时，退化为扫描 `star_handlers_registry`，此时只能拿到命令名和别名，没有说明和权限。

## 配置

| 配置 | 默认 | 说明 |
|---|---|---|
| show_reserved | false | 是否包含 AstrBot 内置指令（/help、/reset 等） |

## 许可

MIT
