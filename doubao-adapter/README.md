# Codex 专家工作团：本地技能适配器

这是原创的角色建议、私有技能索引检索和协调技能安装工具，使用 Python 3.10+ 标准库。公开发布位于 `dong120ask-eng/codex-expert-teams` 仓库的 `doubao-adapter/` 子目录。它可以独立下载使用。

在 Codex 直接说：“帮我做一个客户管理网页，完成后运行测试并交付。”负责人根据已有项目选技能、分配实现与独立验证。无需背诵角色或技能名称。

```powershell
python scripts/expert_group.py list
python scripts/expert_group.py route "开发客户管理网页，后端接口和测试"
python scripts/expert_group.py install
```

安装只添加 `expert-workgroup` 技能，不改代理配置。若目标技能已存在则拒绝覆盖。安装后在 Codex 新会话中使用；显式选择可写 `$expert-workgroup`。已有专家团角色及技能沿用原配置。

有自己合法持有的本地技能索引时，可指定路径，资料留在本机：

```powershell
python scripts/expert_group.py install --codex-home "你的Codex配置目录" --catalog "本地索引.json"
python scripts/expert_group.py catalog "办公" --catalog "本地索引.json"
```

索引是包含 `entries` 数组的 JSON，各记录可以包含 `id`、`name`、`category`、`capabilities`、`execution_status`、`mapped_codex_skills` 和 `private_path`。检索只输出匹配元数据，不执行资料内的代码。

关键词路由只是建议，技能候选包括现有 `wb-*` 方法，项目没有复制这些技能。不存在的技能显示未安装；安装不等于外部工具、账号或服务已实测。原平台伙伴定义和专属服务不会凭空转移。源资料无再分发许可时留在私有目录，不纳入此项目许可证。

验证：`python -m unittest discover -s tests -v`。代码使用 MIT 许可证；第三方私有资料不在公开包中。
