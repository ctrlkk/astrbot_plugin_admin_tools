# AstrBot Admin Tools Plugin

这是一个 AstrBot 管理工具插件，提供群聊管理和用户黑名单功能。

## 功能

### 群聊管理
- **set_group_ban**: 群聊禁言用户
- **set_group_kick**: 群聊踢出用户

### 用户黑名单
- **add_to_blacklist**: 添加用户到黑名单，支持设置拉黑时间
- **remove_from_blacklist**: 从黑名单移除用户

黑名单用户发送的消息将被自动忽略。

> 黑名单功能迁移至：https://github.com/ctrlkk/astrbot_plugin_blacklist_tools