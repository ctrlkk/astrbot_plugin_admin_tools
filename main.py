from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageEventResult
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.star_tools import StarTools


@register(
    "astrbot_plugin_admin_tools", "ctrlkk", "允许LLM禁言、踢出用户", "1.1"
)
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_config()
        self.data_dir = StarTools.get_data_dir()

        # 非授权禁言最大时长（秒）
        self.max_unauthorized_ban_duration = self.config.get(
            "max_unauthorized_ban_duration", 3 * 60
        )

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

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
            if duration > self.max_unauthorized_ban_duration:
                duration = self.max_unauthorized_ban_duration

        await event.bot.set_group_ban(
            group_id=group_id, user_id=user_id, duration=duration, self_id=self_id
        )
        logger.info(f"用户：{user_id}在群聊中被：{self_id}执行禁言{duration}秒")
        return f"用户 {user_id} 已被禁言。"

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
            return f"{event.get_sender_id()} 无法执行该操作"

        await event.bot.set_group_kick(
            group_id=group_id,
            user_id=user_id,
            reject_add_request=False,
            self_id=self_id,
        )
        logger.info(f"用户：{user_id}在群聊中被：{self_id}踢出")
        return f"用户 {user_id} 已被踢出群聊。"
