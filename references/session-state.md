# 会话状态与准备检查

此记录用于避免漏读、重复教学、遗失用户偏好或在上下文压缩后虚构进度。它可以保留在会话中；仅在用户要求导出、保存或当前工作已授权落盘时写为文件。不要把用户的论文、译文或学习档案保存到 skill 仓库。

## 两个独立进度

**准备进度**描述全文是否实际读完、核验并理解；**教学进度**描述哪些单元已经向用户讲过。准备完成不等于教学完成，教学尚未开始也不等于论文未读。一次答对问题不等于掌握，未回答问题不阻止“继续”。

先遵守 [全文研读规则](full-reading.md)，再按 [分段规则](segmentation.md) 建立计划。状态是已完成工作的记录，不能通过预先填 `true` 代替工作。

## 最小记录

可复制 [空白模板](../assets/session-template.json)。模板有意不能通过就绪检查；不要把模板当作现成的完成记录。

| 字段 | 含义与约束 |
|---|---|
| `paper` | 标题、版本、可复核的来源身份。日期或页数不明时据实说明，不能猜。`identity_verified` 仅在核对实际来源后置为 `true`。 |
| `inventory` | `confirmed` 表示已把实际完整材料与清单逐项核对；`supplements_checked` 表示已经检查补充材料的存在和访问情况，不能把“没有找到”随意写成“没有”。 |
| `sources` | 来源身份、角色、可用性、完整清单和原文单元；必需材料不能因不可访问而移出范围。 |
| `synthesis` | 研究问题、方法、结果、边界、证据记录以及未解决的疑问。 |
| `segments` | 有原文归属、分段理由和先修关系的教学计划。 |
| `preferences` | 已有明确偏好优先；未配置不妨碍在准备完成后示范第一单元。 |
| `progress` | 已讲与暂存单元、待答问题、已理解概念和下一步。暂存不能被算作已经讲解。 |

### 来源与原文单元

每个来源包含 `id`、`role`、`required`、`location`、`sha256`、`availability`、`inventory_complete`、`units`。

- `role` 为 `main`、`appendix`、`supplement` 或 `external`。恰好一个 `main`。附录已在主 PDF 内时作为主来源的单元登记，不必另造文件来源。
- 正文、附录和纳入论文范围的补充材料必须 `required: true`。`availability` 为 `available`、`missing` 或 `blocked`；必需材料不可用即不就绪。
- 普通外引文献可登记为 `external` 且 `required: false`，但要填写 `exclusion_reason` 和 `exclusion_impact`，说明为何不影响当前论文理解。不可把论文附录改名为外引文献绕过完整阅读。
- `sha256` 为本地文件 SHA-256 或 `null`。脚本只检查格式，不重新读取源文件计算散列；恢复会话时由宿主核验身份与指纹。没有可用散列时核对版本、页数和实际内容，明确核验依据。
- `inventory_complete: true` 之前，应当从头到尾核查页面/章节、跨页内容、图表、公式、参考文献与声明。不是统计提取文本长度。

每个 `units` 条目有全局唯一 `id`、精确 `locator`、`kind` 和 `status`：

```json
{
  "id": "main:p04-fig2",
  "locator": "PDF p.4, Figure 2, panels a-c and legend",
  "kind": "figure",
  "status": "read",
  "visual_verified": true
}
```

`kind` 可为 `text`、`equation`、`figure`、`table`、`caption`、`references`、`frontmatter`、`declaration`；`status` 可为 `unread`、`partial`、`read`、`blocked`。图表还需 `visual_verified: true`，公式还需 `notation_verified: true`，均应在对照原始材料核验后记录。生成了图片不等于查看了图片。

文本通常按自然段或明确句组登记。不要用一个笼统的“全文”条目掩盖缺页；参考文献列表可作为有完整范围定位的一组核查。若教学要把一个原文段拆成两块，先把清单细化为 `p03-para2a`、`p03-para2b`，注明句子或字节/行范围，核对两部分连续、不重叠且无遗漏。

### 理解记录与疑问

`synthesis.question/approach/result/boundary` 用简短可核对的文字重建论文。`evidence` 至少包含决定主结论的记录；每条具有 `claim`、`source_ids`、`interpretation` 和 `limits`。不能只用“论文证明有效”代替条件和证据。

`understanding_checked: true` 表示已经对照全文检查解释、方法依赖、证据与边界。它不是模型自信分数，更不是脚本能证明的理解能力。

`unresolved` 条目使用 `question`、`blocking`、`status`（`open` / `resolved`）、`note`。改变方法或主结论解释的疑问必须标为 `blocking: true`，解决前不得教学；非关键不确定性可以保留并在讲到相关内容时披露。解决后在 `note` 写明依据，不直接删除历史疑问。

### 分段、依赖与覆盖

每个教学单元具有 `id`、`kind`（`teaching` / `supporting`）、`focus`、`split_reason`、`source_ids`、`context_ids`、`depends_on`。

- 每个必需原文单元恰有一个 `source_ids` 主归属，便于检查遗漏或无意重复。
- 后文再次引用某个图表或定义时使用 `context_ids`，不重复主归属。
- `depends_on` 指向计划中更早的单元，不允许自依赖、前向依赖或循环。必要时把先修内容作为简短预备单元；默认仍按原文顺序讲解，并说明调整。
- 参考文献、作者信息等可归入 `supporting` 单元：已经完整核查，但无需强迫用户逐条翻译。正文中的方法、证据和限定条件不能借此跳过。用户选择暂不讲某部分，应保留 `deferred_segments`，不得声称教学完整结束。

### 教学选项与恢复

`preferences` 的固定取值为：

| 字段 | 可用值 |
|---|---|
| `setup` | `before_first_unit` / `after_first_unit` / `provided` |
| `question_mode` | `off` / `checkpoints` / `dialogue` |
| `depth` | `foundational` / `standard` / `advanced` |
| `formula_mode` | `intuition` / `derivation` / `both` |
| `pace` | `one_unit` / `several_units` |
| `configured`、`examples`、`recaps` | 布尔值 |

模板的默认方式是完整研读后示范第一单元，再一次询问是否调整。已有用户偏好时写入 `setup: provided`、`configured: true`；不要重问。临时“这次不要提问”应记录作用范围，结束后恢复之前偏好；“以后不要提问”则更新长期会话偏好。可以增加 `temporary_overrides` 等扩展字段，但不要因此改变核心准备规则。

`progress.taught_segments` 和 `deferred_segments` 记录单元 ID；`pending_question` 可以为空或保留未答题。用户说“继续”时直接推进，必要时顺带给出上一题解释，不要求先答题。`known_concepts` 保留已理解与仍不稳的概念，不把一次对话当作测验成绩。`next_action` 写具体下一步。

上下文恢复时先核对论文身份、来源变更和准备记录，再继续上次单元；不重复欢迎问卷。版本变化时把受影响的核查、证据和分段标回未完成，重新核对，不能沿用旧的就绪状态。

## 可选的结构校验

在 skill 根目录执行：

```text
python scripts/check_readiness.py path/to/session.json
python scripts/check_readiness.py path/to/session.json --json
```

脚本仅需 Python 3.9+ 标准库，不联网、不安装依赖、不修改输入。退出码：`0` 为记录检查通过，`1` 为准备未完成或记录不一致，`2` 为文件/JSON 输入错误。Windows 也可使用 `py -3` 替代 `python`。

**`READY (recorded checks only)` 不能证明实际读完、清单完整、提取准确或理解正确。** 脚本只能发现记录中的硬缺口，仍需人工对照原文核查。没有 Python 的宿主按同一清单检查，不因此改成边读边教。

运行仓库测试：

```text
python -m unittest discover -s tests -v
```

测试使用原创合成材料，不包含用户论文。不要把模板、测试样例的通过状态挪用于真实论文。
