# 数据与安全边界

本 workflow 仓库只保存流程代码、skills、模板和文档。以下内容不应上传：

- Zotero `zotero.sqlite`、WAL/SHM 文件与配置中的隐私路径
- 受版权保护的原始论文 PDF
- 未决定公开范围的 MinerU 全文、截图和用户精读笔记
- API key、cookie、token、SSH 私钥和模型服务配置
- 带凭据的 pdf2zh 配置或历史译文

如果实际 Vault 需要跨设备同步，建议使用独立的私有仓库，并根据版权与团队权限决定是否跟踪全文和图片；workflow 仓库保持可公开/可复用的数据最小化边界。
