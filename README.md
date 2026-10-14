# Codex Expert Teams

中文 Codex 专家目录、自动分工规则与可安装技能。直接提出需求，由负责人选择相关技能和角色；简单问题直接处理，复杂任务按依赖协作并验收。

## 公开版范围

- 448 个事实目录条目，含 54 个专家团、15 个类别、35 项行业顾问。
- 16 个原创路由技能、11 个可选角色配置、3 类原创协作工作流。
- 15 个具有完整 MIT/Apache 根许可证的主角色方法，保留原许可证与来源声明。
- 433 个条目只提供目录，不附第三方原文。目录不等于完整方法，更不等于模型权重或服务授权。

本项目源于对可访问 WorkBuddy 专家资源的整理，与腾讯、WorkBuddy 或 OpenAI 无官方关联。**不是 WorkBuddy 全部原文的开源镜像。** 未取得再分发许可的文本、专有工具、二进制、账户资料与日志不在本仓库中。详见 [许可审计](docs/license-audit.json)、[覆盖统计](docs/coverage.json) 和 [第三方声明](THIRD_PARTY_NOTICES.md)。

## 安装

需要 Python 3.11+。在下载或克隆的项目目录运行：

```sh
python scripts/install.py --dry-run
python scripts/install.py
```

默认安装到 `CODEX_HOME/skills`；未设置 `CODEX_HOME` 时使用 `~/.codex/skills`。可用 `--skills-dir` 指定目录。**默认保留已有同名技能**，因此不会把你已有完整私人专家库降级成公开版。`--replace` 会先备份再替换。

可选安装角色配置：

```sh
python scripts/install.py --include-roles
```

角色路径在安装时替换成实际技能目录。角色默认保留同名配置；安装器不修改 `config.toml`。当前验证版本是 Codex CLI `0.162.0-alpha.2`，角色目录为 `CODEX_HOME/agents`，团队测试使用普通会话。是否支持角色与子代理，以实际 Codex 版本和可用工具为准。

在希望应用自动分工的项目中使用本仓库 [AGENTS.md](AGENTS.md) 的规则，或将规则合并到自己的项目约定。新聊天会重新发现技能。

## 使用

直接说：

- 帮我开发一个四年级中英文打字练习软件。
- 评估我的创业方向，设计最小验证实验。
- 根据我提供的资料做行业研究，给出证据与分歧。
- 为这个产品制定营销定位和内容计划。

负责人按需读技能与角色方法，最多同时运行 3 个子代理，落实独立检查和验收。没有子代理或外部数据时，说明实际限制并完成可做部分；不模拟多人发言，不宣称已接入专有服务。

专家目录可用本地检索查看：

```sh
python skills/wb-expert-hub/scripts/find_expert.py 软件开发
python skills/wb-expert-hub/scripts/find_expert.py 创业
python skills/wb-expert-hub/scripts/find_expert.py A股 --team
```

已有许可覆盖的本地方法可以私下适配。转换器只读取明确的角色文档，不联网、不运行源代码，不把原文写入公开技能目录：

```sh
python scripts/import_local.py --source /path/to/your/local/plugins --output .local/methods --local-use-only
```

输入布局为 `<plugin>/agents/*.md`。输出必须是新的或空目录；`.local/` 被版本控制忽略。此选项不授予再分发权，也不自动替换已安装的专家参考。

## 验证

```sh
python -m unittest discover -s tests -v
```

验证内容见 [验收说明](docs/verification.md)。结构与代表场景验证不代表 448 个专家的效果都已实测。

## 许可

原创代码、路由说明和规则使用 [MIT](LICENSE)。`skills/wb-expert-hub/references/library/` 中的第三方文本遵循各自原许可证，详见 [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES)；根 MIT 不能替代它们的条款。公开版不包含 GPL、非商业条件许可、专有或许可不明确的原文。

GitHub 对开源许可的说明：[Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)。
