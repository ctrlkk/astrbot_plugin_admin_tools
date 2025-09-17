from os import path
import aiosqlite
from datetime import datetime, timedelta
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageEventResult
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.star_tools import StarTools


@register("astrbot_plugin_admin_tools", "ctrlkk", "神奇妙妙小工具", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        data_dir = StarTools.get_data_dir()
        self.db_path = path.join(data_dir, "blacklist.db")

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self._init_db()

    async def _init_db(self):
        """初始化数据库，创建黑名单表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id TEXT PRIMARY KEY,
                    ban_time TEXT NOT NULL,
                    expire_time TEXT,
                    reason TEXT
                )
            """)
            await db.commit()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        sender_id = event.get_sender_id()
        try:
            # 检查用户是否在黑名单中
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM blacklist WHERE user_id = ?", (sender_id,)
                )
                user = await cursor.fetchone()

                if user:
                    expire_time = user[2]
                    if expire_time:
                        expire_datetime = datetime.fromisoformat(expire_time)
                        if datetime.now() > expire_datetime:
                            await db.execute(
                                "DELETE FROM blacklist WHERE user_id = ?", (sender_id,)
                            )
                            await db.commit()
                            logger.info(f"用户 {sender_id} 的黑名单已过期，已自动移除")
                        else:
                            logger.info(f"用户 {sender_id} 在黑名单中，消息已被阻止")
                            event.stop_event()
                    else:
                        logger.info(f"用户 {sender_id} 在永久黑名单中，消息已被阻止")
                        event.stop_event()
        except Exception as e:
            logger.error(f"检查黑名单时出错：{e}")

    @filter.llm_tool(name="set_group_ban")
    async def set_group_ban(
        self, event: AiocqhttpMessageEvent, user_id: str, duration: int
    ) -> MessageEventResult:
        """
        Mute a user in the group chat. The muted user will not be able to send messages during the mute period.
        Args:
            user_id(string): The ID of the user to be muted
            duration(number): The duration of the mute in seconds, must be a multiple of 60 (e.g., 60, 180). Set to 0 to unmute
        """
        group_id = event.get_group_id()
        self_id = event.get_self_id()
        if not group_id:
            return "此操作仅可在群聊中进行。"

        if not event.is_admin():
            return "这项操作需要管理员授权。"

        await event.bot.set_group_ban(
            group_id=group_id, user_id=user_id, duration=duration, self_id=self_id
        )
        logger.info(f"用户：{user_id}在群聊中被：{self_id}执行禁言{duration}秒")
        return f"用户 {user_id} 已被禁言 {duration} 秒。"

    @filter.llm_tool(name="set_group_kick")
    async def set_group_kick(
        self, event: AiocqhttpMessageEvent, user_id: str
    ) -> MessageEventResult:
        """
        Kick a user from the group chat.
        Args:
            user_id(string): The ID of the user to be kicked
        """
        group_id = event.get_group_id()
        self_id = event.get_self_id()
        if not group_id:
            return "此操作仅可在群聊中进行。"

        if not event.is_admin():
            return "这项操作需要管理员授权。"

        await event.bot.set_group_kick(
            group_id=group_id,
            user_id=user_id,
            reject_add_request=False,
            self_id=self_id,
        )
        logger.info(f"用户：{user_id}在群聊中被：{self_id}踢出")
        return f"用户 {user_id} 已被踢出群聊。"

    @filter.llm_tool(name="add_to_blacklist")
    async def add_to_blacklist(
        self, user_id: str, duration: int = 0, reason: str = ""
    ) -> MessageEventResult:
        """
        Add a user to the blacklist. The user's messages will be ignored.
        Args:
            user_id(string): The ID of the user to be added to the blacklist
            duration(number): The duration of the blacklist in seconds. Set to 0 for permanent blacklist
            reason(string): The reason for adding the user to the blacklist
        """
        try:
            ban_time = datetime.now().isoformat()
            expire_time = None

            if duration > 0:
                expire_time = (datetime.now() + timedelta(seconds=duration)).isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO blacklist (user_id, ban_time, expire_time, reason)
                    VALUES (?, ?, ?, ?)""",
                    (user_id, ban_time, expire_time, reason),
                )
                await db.commit()

            if duration > 0:
                logger.info(
                    f"用户 {user_id} 已被加入黑名单，时长 {duration} 秒，原因：{reason}"
                )
                return f"用户 {user_id} 已被加入黑名单，时长 {duration} 秒。"

            else:
                logger.info(f"用户 {user_id} 已被永久加入黑名单，原因：{reason}")
                return f"用户 {user_id} 已被永久加入黑名单。"

        except Exception as e:
            logger.error(f"添加用户 {user_id} 到黑名单时出错：{e}")
            return MessageEventResult().message("添加用户到黑名单时出错")

    @filter.llm_tool(name="remove_from_blacklist")
    async def remove_from_blacklist(self, user_id: str) -> MessageEventResult:
        """
        Remove a user from the blacklist.
        Args:
            user_id(string): The ID of the user to be removed from the blacklist
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT * FROM blacklist WHERE user_id = ?", (user_id,)
                )
                user = await cursor.fetchone()

                if not user:
                    return f"用户 {user_id} 不在黑名单中。"

                await db.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
                await db.commit()

            logger.info(f"用户 {user_id} 已从黑名单中移除")
            return f"用户 {user_id} 已从黑名单中移除。"
        except Exception as e:
            logger.error(f"从黑名单移除用户 {user_id} 时出错：{e}")
            return MessageEventResult().message("从黑名单移除用户时出错")
