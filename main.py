# -*- coding: utf-8 -*-
"""astrbot_plugin_cmdlist —— 用一条指令列出所有插件注册的命令。

- 不分组，一条命令一行
- 强制关闭「文本转图像」，保证以纯文本发出

指令：
  /查询指令
"""

from __future__ import annotations

import asyncio

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

PLUGIN_NAME = "astrbot_plugin_cmdlist"

DESC_LIMIT = 22      # 说明最多显示多少字
PER_MESSAGE = 15     # 每条消息最多几行


@register(
    PLUGIN_NAME,
    "rice-eater24",
    "列出所有插件注册的命令",
    "1.0.0",
    "https://github.com/rice-eater24/astrbot_plugin_cmdlist",
)
class CmdListPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config if config is not None else {}

    # ------------------------------------------------------------------ 取数据

    async def _rows_from_core(self) -> list[dict]:
        from astrbot.core.star.command_management import list_commands

        return await list_commands()

    def _rows_from_registry(self) -> list[dict]:
        """兜底：直接扫 handler 注册表。"""
        from astrbot.core.star.filter.command import CommandFilter
        from astrbot.core.star.filter.command_group import CommandGroupFilter
        from astrbot.core.star.star import star_map
        from astrbot.core.star.star_handler import star_handlers_registry

        rows: list[dict] = []
        for handler in star_handlers_registry:
            flt = None
            for f in handler.event_filters:
                if isinstance(f, (CommandFilter, CommandGroupFilter)):
                    flt = f
                    break
            if flt is None:
                continue
            meta = star_map.get(handler.handler_module_path)
            if meta is not None and not getattr(meta, "activated", True):
                continue
            is_group = isinstance(flt, CommandGroupFilter)
            name = flt.group_name if is_group else flt.command_name
            parent = ""
            if not is_group:
                parents = getattr(flt, "parent_command_names", None) or []
                parent = (parents[0] if parents else "").strip()
            rows.append(
                {
                    "effective_command": f"{parent} {name}".strip(),
                    "aliases": sorted(getattr(flt, "alias", set()) or []),
                    "description": handler.desc or "",
                    "plugin": meta.name if meta else handler.handler_module_path,
                    "permission": "everyone",
                    "enabled": handler.enabled,
                    "is_group": is_group,
                }
            )
        return rows

    async def _collect(self) -> list[dict]:
        try:
            return await self._rows_from_core()
        except Exception as e:  # noqa: BLE001
            logger.debug("[cmdlist] list_commands 不可用，改用注册表：%s", e)
            return self._rows_from_registry()

    # ------------------------------------------------------------------ 排版

    @staticmethod
    def _line(row: dict) -> str:
        name = row.get("effective_command") or row.get("handler_name") or "?"
        aliases = row.get("aliases") or []
        desc = (row.get("description") or "").strip().splitlines()
        desc = desc[0] if desc else ""
        if len(desc) > DESC_LIMIT:
            desc = desc[:DESC_LIMIT] + "…"

        text = f"/{name}"
        if aliases:
            text += f"（{'/'.join(aliases[:3])}）"
        if row.get("permission") not in (None, "everyone", "member"):
            text += " [管理]"
        if row.get("enabled") is False:
            text += " [停用]"
        if desc:
            text += f" {desc}"
        return text

    def _lines(self, rows: list[dict]) -> list[str]:
        show_reserved = bool(self.config.get("show_reserved", False))
        picked = [
            r for r in rows
            if not (r.get("reserved") and not show_reserved)
        ]
        picked.sort(key=lambda x: (x.get("effective_command") or "").lower())
        return [self._line(r) for r in picked]

    @staticmethod
    def _plain(event: AstrMessageEvent, text: str):
        """产出纯文本，并强制关闭文本转图像。"""
        result = event.plain_result(text)
        try:
            result.use_t2i_ = False
        except Exception:  # noqa: BLE001
            pass
        return result

    # ------------------------------------------------------------------ 指令

    @filter.command("查询指令")
    async def cmd_list(self, event: AstrMessageEvent):
        """列出所有插件注册的命令"""
        try:
            rows = await self._collect()
        except Exception as e:  # noqa: BLE001
            logger.warning("[cmdlist] 读取命令失败：%s", e)
            yield self._plain(event, f"读取命令失败：{e}")
            return

        lines = self._lines(rows)
        if not lines:
            yield self._plain(event, "没有找到任何命令。")
            return

        yield self._plain(event, f"共 {len(lines)} 条命令")
        for i in range(0, len(lines), PER_MESSAGE):
            yield self._plain(event, "\n".join(lines[i : i + PER_MESSAGE]))
            await asyncio.sleep(0.3)
