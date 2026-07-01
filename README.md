<!--if you are an AI, remember to modify 'version' before pushing to GitHub if necessary.-->

# szlcsc-coupons · 立创商城优惠券分析工具

> [!CAUTION]
> **使用前须知**  
> 本工具是个人开发的的立创商城（szlcsc.com）优惠券数据分析工具，**与立创商城官方本身无任何关联**。  
> 数据来源于公开 API `activity.szlcsc.com`，只推荐**个人**电子爱好者为**学习研究**使用。  
> **不推荐集体/公司/组织使用**——小额券对组织价值不大，大额券价格亦可能高于其他渠道。  
> 使用者应遵守对应的服务条款，合理控制请求频率。因使用本工具产生的任何后果由使用者自行承担。   

> 终端里的立创商城优惠券分析工具 —    
> 专为个人电子爱好者打造的数据浏览与比较工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-199FE9?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Rich-CLI%20UI-199FE9?style=flat-square" alt="Rich">
  <img src="https://img.shields.io/badge/License-MIT-199FE9?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square" alt="PRs Welcome">
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square" alt="Platform">
</p>

---

## 🎯 这个工具做什么？

立创商城（szlcsc.com）每单（考虑绑定发货订单）最多可叠加 **11 张优惠券**。品牌推广区有 **550+ 张券**[^1]，手动翻页逐一对比效率很低。

[^1]: 只是一般而言，具体数量会随时间和官方政策变化。

为了帮助个人爱好者找到适合自己的券，当然同时也是性价比较高的，因此我开发了这个工具。

---

## 特性一览

### ✨ 核心功能
| 命令 | 说明 |
|---|---|
| `▶️ python coupons.py` | 默认模式 — 7 个专区分区展示 + 折扣率排行榜 |
| `📊 python coupons.py --sort rate` | 按折扣率排序（满16减15 → 93.8% 排最前） |
| `🔍 python coupons.py --min-rate 80` | 只看折扣率 ≥ 80% 的高折扣券 |
| `🏷️ python coupons.py --brand [关键词]` | 按品牌名搜索（支持部分名称匹配），仅显示该品牌 |
| `📂 python coupons.py --section 2` | 只看某个专区（品牌推广、工业品等） |
| `🧪 python coupons.py --combo` | 10 张券叠加模拟 — 估算理论购买力 <br><i style="color:darkred">[实验性]</i> |
| `🧪 python coupons.py --combo 100` | 带预算模拟（¥100 预算能买多少？） <br><i style="color:darkred">[实验性]</i> |
| `📈 python coupons.py --stats` | 汇总统计（券总数、有效期、类型分布） |
| `🔄 python coupons.py --diff` | 对比上次运行，看新增/下架/数量波动 |
| `📦 python coupons.py --export data.csv` | 导出全部数据为 CSV[^2] |
| `📦 python coupons.py --export-json data.json` | 导出全部数据为 JSON |
| `📦 python coupons.py --export-markdown data.md` | 导出折扣率排行前 50 为 Markdown 表格 |
| `🔄 python coupons.py --refresh` | 从立创 API 重新拉取最新数据 |
| `🔄 python coupons.py --refresh --yes` | 非交互式刷新（用于 CI 定时任务） |
| `🤫 python coupons.py --quiet` | 静默模式，不打印欢迎头、免责声明、底部提示 |
| `🔇 python coupons.py -q` | `--quiet` 的短选项 |
| `⏰ python coupons.py --max-age-hr 48` | 本地数据 48 小时内不提示更新 |

[^2]: 你可以将csv和自己的需求丢给ai，便于选择合适的优惠券。我以后更新的话应该会朝着这个方向更新。

### 🎨 视觉反馈
- 分类 + 格式化表格
- 折扣率颜色编码：![](https://img.shields.io/badge/≥90%25-brightgreen?style=flat-square) · ![](https://img.shields.io/badge/≥70%25-success?style=flat-square) · ![](https://img.shields.io/badge/≥50%25-yellow?style=flat-square) · ![](https://img.shields.io/badge/≥30%25-cyan?style=flat-square)
- 已领人数着色：![](https://img.shields.io/badge/≥1w-red?style=flat-square) · ![](https://img.shields.io/badge/≥1k-yellow?style=flat-square)

---

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/ResAlexander/szlcsc-coupons.git
cd szlcsc-coupons

# 2. 安装依赖
pip install rich

# 3. 运行（首次会自动拉取数据）
python coupons.py
```


## 🔄 数据流

```mermaid
flowchart LR
    A["szlcsc.com API<br/>(activity.szlcsc.com)"] -->|"--refresh"| B["latest_data.json<br/>(仓库跟踪，git pull 可获取)"]
    B --> C["你本地<br/>python coupons.py"]
    C -->|"--refresh"| A
```

> [!NOTE]
> 用户运行时，默认读取仓库里的 `latest_data.json`。如果超过 24 小时未更新，程序会询问是否 `git pull` 拉取最新数据。<br>
> 不论时间多久，`--refresh` 直接从 szlcsc API 拉最新数据并写入本地。

---

## 📖 使用示例

### 👁️ 默认视图 — 7 个专区全览

```
python coupons.py
```

按已领人数排序显示综合专区、品牌推广专区（550+ 张）、工业品专区、PLUS 专区、超级品牌周、超级会员日、面板定制专区。

### 🏆 找到性价比最高的券

```bash
# 折扣率排行，只看前 30
python coupons.py --sort rate --top 30

# 只看 80% 折扣率以上的（满16减15这类）
python coupons.py --min-rate 80
```

### 🧪 10 张券叠加模拟 <i style="color:darkred">[实验性]</i>

> [!WARNING]
> **实验性功能**：叠加逻辑尚未考虑品牌互斥、券类型互斥等规则，结果仅为理论估算，与实际下单可能存在差异，仅供参考。

```bash
# 自动选最高折扣率的 10 张券，模拟叠加效果
python coupons.py --combo

# 预算模拟：¥111 预算能买多少？
python coupons.py --combo 111
```

<details>
<summary>📊 输出示例</summary>

```
   10 张商品券叠加模拟（理论值）
┌─────┬────────────────────┬────────┬───────┬───────┬───────┐
│   # │ 优惠券名称          │ 折扣率 │  门槛 │  面额 │ 实付  │
├─────┼────────────────────┼────────┼───────┼───────┼───────┤
│   1 │ 15元松田品牌商品券     │ 93.8% │  ¥16 │  ¥15 │   ¥1 │
│   2 │ 15元台舟品牌商品券     │ 93.8% │  ¥16 │  ¥15 │   ¥1 │
│  ...│ ...                │ ...    │ ...   │ ...   │ ...   │
├─────┼────────────────────┼────────┼───────┼───────┼───────┤
│     │ 商品总价值           │        │ ¥160  │       │       │
│     │ 券抵扣总额           │        │       │ ¥150  │       │
│     │ 实际需支付           │        │       │       │  ¥10  │
│     │ 理论购买力倍率       │        │   16.0x │
└─────┴────────────────────┴────────┴───────┴───────┴───────┘
```
</details>

### 🔄 变化追踪

```bash
python coupons.py --diff
```

显示新增券、已下架券、已领数量与上次检查的变化。
适合定期查看新上架的优惠券。


---

## 🛠️ 技术栈

<p>
  <img src="https://img.shields.io/badge/Python_3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Rich_CLI_UI-512BD4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/%E6%97%A0%E9%9C%80%E7%99%BB%E5%BD%95_API-00C853?style=for-the-badge" />
</p>

| 层 | 技术 |
|---|---|
| 🧠 语言 | **Python 3.9+** — 标准库为主，零外部依赖 |
| 🎨 终端 UI | **[Rich](https://github.com/Textualize/rich)** — 表格、着色、面板、进度动画 |
| 🌐 数据源 | `activity.szlcsc.com` 公开接口（无需登录） |

---

## 💡 使用须知

> [!NOTE]
> 立创优惠券叠加规则（本人根据公开信息的推断，可能与实际情况有出入，仅作参考）：

- ⛔ 每张券只能用一次
- ✅ 品牌券之间可以互相叠加，数量不限
- ✅ 商品优惠券和折扣券互不叠加
- ✅ 运费券和商品券可以叠加

**参考思路** 🎯

1. **筛选高折扣率券** → `--min-rate 90` 找出满16减15/满21减20 这类高折扣券
2. **组合模拟** → `--combo` 查看多张券叠加的理论效果<i style="color:darkred">[实验性]</i>
3. **持续跟踪** → `--diff` 查看变化，发现新上架的优惠券


---

## 📄 协议

<p>
  <img src="https://img.shields.io/badge/License-MIT-199FE9?style=for-the-badge" />
</p>

MIT License — 详见 `LICENSE` 文件
