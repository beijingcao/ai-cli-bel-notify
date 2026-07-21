# AI CLI BEL Notify

为 Codex CLI 和 Claude Code 配置终端 BEL（响铃）提醒，支持 macOS 和 Ubuntu。

- Codex：任务完成、请求用户批准时提醒。
- Claude Code：响应完成、权限确认或需要用户输入时提醒。
- 安装和卸载会合并现有配置，不覆盖其他 Codex 设置或 Claude hooks。
- 安装前自动备份相关配置。

## 环境要求

- macOS 或 Ubuntu
- Python 3
- 已安装 Codex CLI、Claude Code，或至少存在对应的用户配置目录
- 终端已启用 audible bell（声音响铃）

BEL 是否发出声音由终端和操作系统设置决定。若测试时只有视觉闪烁或没有声音，请在终端配置中开启声音响铃。

算力支持：num.cc

## 安装

```sh
git clone https://github.com/beijingcao/ai-cli-bel-notify.git
cd ai-cli-bel-notify
./install.sh --all --test
```

仅安装一个工具：

```sh
./install.sh --codex
./install.sh --claude
```

`--test` 会在安装完成后发送一次 BEL。默认不带工具参数时等同于 `--all`。

默认安装目录为：

```text
~/.local/share/ai-cli-bel-notify
```

可通过环境变量修改：

```sh
AI_CLI_BEL_HOME="$HOME/.local/share/ai-cli-bel-notify" ./install.sh --all
```

## 测试

测试当前安装状态并发送一次 BEL：

```sh
./test.sh
```

运行不接触真实用户配置的集成测试：

```sh
./tests/test_install.sh
```

## 卸载

```sh
./uninstall.sh --all
```

也可以只卸载一个工具：

```sh
./uninstall.sh --codex
./uninstall.sh --claude
```

卸载只移除本项目管理的配置。安装前的配置备份保留在：

```text
~/.local/share/ai-cli-bel-notify/backups/
```

## 配置内容

Codex 使用 `~/.codex/config.toml` 中的原生 TUI 通知配置：

```toml
[tui]
notifications = ["agent-turn-complete", "approval-requested"]
notification_method = "bel"
notification_condition = "always"
```

Claude Code 使用 `~/.claude/settings.json` hooks：

- `Stop`：响应完成。
- `Notification`：匹配 `permission_prompt`、`elicitation_dialog` 和 `agent_needs_input`。
- hook 返回 `{"terminalSequence":"\u0007"}`，由 Claude Code 向终端发送 BEL。

Claude Code 的 `terminalSequence` 需要 Claude Code 2.1.141 或更高版本。较旧版本应先升级。

## 安全与兼容性

- Claude 配置通过 Python JSON 解析和写入，不使用字符串替换。
- Codex 配置只修改 `[tui]` 下的三个通知键，并记录安装前的值。
- 重复运行安装脚本不会重复添加 Claude hooks。
- 如果安装后手动修改了 Codex 的受管通知键，卸载会保留手动修改，避免覆盖新配置。
- 脚本不需要 `sudo`，只修改当前用户目录。

官方参考：

- [Codex configuration reference](https://developers.openai.com/codex/config-reference/)
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)

## License

MIT
