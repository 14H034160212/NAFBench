# NAF-Bench —— 今日会议进度

**这是什么。** 一个 **solver 认证(solver-certified)** 的基准,测试大模型是否会**遵循指定的否定语义**(一套关于"非"/"未知"含义的"规则手册"),而不是退回到它自己的默认理解。每一道题的标准答案都由真正的求解器算出(clingo / 良基不动点 / SWI-Prolog),不是我们人工判定的。

---

## 1. 上次会议以来的进展

- **独立审计(Fable)—— 所有问题已处理。** 修复两个正确性 bug(合取被写成 "only if" 而非 "if";Prolog 循环检测的竞态,可能把环误判为 "false"),外加统计/设计层面的修复(见 §5)。
- **在修正后的代码上全部重新生成、重新运行** —— gold 标签经核验未变(零漂移),所有模型重跑,每个 LoRA adapter 重训。每个实验现在都记录 completion token。
- **把 "width" 恢复为只算 shared subgoals**(把 cycle 长度解耦出去),采纳 Agnieszka 的意见。用本地模型重跑了 depth×width 网格:**结论不变** —— 准确率对 depth、width 都基本无关,主导难度的是 *divergence bin*(环的类型)。
- **采纳了 Agnieszka 修订后、详细程度对齐的语义 prompt**(见 §3),并做了小样本冒烟测试(见 §4)。
- **相关工作已定位**,含 ASPBench(arXiv:2507.19749)。全部已推送到 `main`。

---

## 2. 一个例子说明全部要点

同一套规则,渲染成自然语言(这就是模型看到的内容):

> Reviewer 0 签字**当且仅当** Reviewer 1 **不**签字。Reviewer 1 签字**当且仅当** Reviewer 0 **不**签字。如果 Reviewer 0 签字,则案件被 ESCALATED(上报)。
>
> **问题:案件会被上报吗?**

两个 reviewer 通过"互相否定"形成一个环,所以四套规则手册会**合理地给出不同答案** —— 认证答案随之翻转:

| 规则手册(语义) | 认证答案 | 原因 |
|---|---|---|
| **credulous(brave,勇敢)** | **一定是 (A)** | 有两个自洽情形 {R0}、{R1};在 R0 情形里被上报 → 在*至少一个*情形成立 |
| **skeptical(cautious,谨慎)** | **一定否 (B)** | 在 R1 情形里*没*被上报 → *并非*在每个情形都成立 |
| **well-founded(良基)** | **无法确定 (C)** | 这个环没有事实支撑 → *未定义* |
| **closed-world / SLDNF** | **无法确定 (C)** | 操作式证明不终止 |

同一套规则,取决于被告知用哪套手册,有**四个不同的正确答案**。一个"退回默认"的模型会不管手册一律给同一个答案 —— NAF-Bench 测的正是这种失败。

---

## 3. 四个 prompt(Agnieszka 修订、详细程度对齐的版本)

每个 prompt 都是**自包含的操作式定义**,因此我们测的是模型能否*遵循*该语义,而不是它是否已经知道这个名字。下面给出:prompt 原文(英文,即模型实际看到的)、一句白话解释、以及它在上面那个例子上的答案。

### closed-world / SLDNF → 在例子上答 C
> Use the CLOSED-WORLD ASSUMPTION with NEGATION-AS-FAILURE, interpreted operationally as in Prolog-style reasoning. A positive goal is 'true' if it can be derived by a terminating proof… `not G` is 'true' if G finitely fails… If evaluating the goal does not terminate, flounders, or otherwise cannot produce a definite success or finite failure, answer 'Cannot be determined.'

*白话:* 像 Prolog 引擎那样跑;如果死循环或卡住,就是无法确定。

### well-founded → 在例子上答 C
> Use WELL-FOUNDED semantics, with three truth values: 'true', 'false', 'undefined'. A statement is 'true' if it has *founded* support… 'false' if all rules that could derive it are defeated or depend only on unfounded circular support… 'undefined' if its truth depends on an unresolved cycle through default negation.

*白话:* 只承认最终由事实**稳固支撑**的真;若真值卡在"经否定的环"上 → 未定义。

### credulous / brave → 在例子上答 A
> Use STABLE-MODEL (ANSWER-SET) semantics with CREDULOUS (BRAVE) reasoning. An answer set is a self-consistent set of atoms closed under the rules and containing exactly the atoms justified by them… Answer 'Definitely yes' if the statement holds in AT LEAST ONE answer set; 'Definitely no' if in none. If there are no answer sets, answer 'Definitely no.'

*白话:* 在**某一个**合法情形里成立,就算真。

### skeptical / cautious → 在例子上答 B
> Use STABLE-MODEL (ANSWER-SET) semantics with SKEPTICAL (CAUTIOUS) reasoning. Consider all answer sets… Answer 'Definitely yes' only if the statement holds in EVERY answer set; 'Definitely no' if there is at least one where it does not hold. If there are no answer sets, it vacuously holds in every set; answer 'Definitely yes.'

*白话:* 只有在**每一个**合法情形里都成立才算真(没有任何情形时,空成立 → 一定是)。

**设计取向(已与 Agnieszka 达成一致):** 四个 prompt 现在详细程度对齐,且措辞面向"测遵循指定语义"而非"测是否熟悉" —— 其中 WFS 最难在不泄露答案的前提下写到同等详细。

---

## 4. 修订版 prompt 的小样本冒烟测试(今天新跑)

45 题 headline 集,T=0,按条件计(答对数 / 9):

| 模型 | 总体 | closed-world | credulous | skeptical | WFS |
|---|---|---|---|---|---|
| gpt-4o-mini | 19/36 (53%) | 6/9 | 3/9 | 3/9 | 7/9 |
| Qwen2.5-coder 32B | 18/36 (50%) | 3/9 | 3/9 | 3/9 | 9/9 |

- prompt **端到端可用**(模型能解析并遵循;篇幅约为原来的 2 倍,无障碍)。
- 总体准确率与旧 prompt 相当;定性规律不变:**credulous/skeptical 最难,WFS/closed-world 较易**。
- *注意:* 仅单次小样本 —— 属冒烟测试,非正式测量。正式的 production 采样会解决这一点。

---

## 5. 核心发现(来自完整 PoC)

- **前沿模型遵循手册;弱模型死认一个答案。** 在良基语义上(标准答案 = *未定义*):Claude Opus 12/12、GPT-5 11/12,一直到 Llama3 6/12(= "永远答 C" 的平凡基线)。
- **难度来自*语义 × 环类型*,不是规模。** depth、width 到 range 32 都统计上持平(差值的 bootstrap 置信区间跨 0);divergence bin 主导约 20–80 倍。(把 width 恢复为纯 shared-subgoals 后这一结论依然成立。)
- **default-reversion(提案的核心指标):** 前沿模型退回默认少得多(GPT-4.1 约 21%),开源模型高(Llama3 约 59%)。
- **有效的缓解手段:** translate-then-solve(模型只翻译,我们的求解器套用语义)→ 强翻译模型约 100%;一个 few-shot 例子让弱模型提升两位数;solver 认证数据 LoRA 微调 41% → 91%(同分布)。跨表述 SFT 能迁移到 held-out 的*叙事*表面,但迁移不到*抽象*表述(诚实 holdout)。

---

## 6. 已定 vs 待定

**已锁定:** 四个 divergence bin;四套规则手册下的 solver 认证 gold;plain width + 单列 cycle 长度;中英双语跨语言轴;token 记录;聚类置信区间。

**待定(等英方):**
- 四个 prompt 的最终签字(Agnieszka + Kostas)—— 冒烟测试看起来没问题。
- 之后是 **production run**:固定 depth/width、单一表述、**每格 30 个实例**、聚类置信区间;depth×width 网格用本地模型(已确认稳定);其它实验用同一固定尺寸。

production run 之前的一切都已完成并推送。
