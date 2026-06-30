#!/usr/bin/env python3
"""
立创商城优惠券数据浏览工具 — LCSC Coupon Data Viewer

从 activity.szlcsc.com 公开 API 获取优惠券数据，按专区分组展示。
仅供学习研究使用。
"""

import argparse
import csv
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from typing import Any

__version__ = "1.0.1"
_UNLIMITED = object()  # sentinel for --combo without budget

# 请求间隔限制（秒），防止频繁调用 API
_MIN_REFRESH_INTERVAL = 600  # 10 分钟

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "latest_data.json")
CACHE_FILE = os.path.join(HERE, ".coupon_cache.json")
HISTORY_FILE = os.path.join(HERE, ".coupon_history.json")

API_URL = "https://activity.szlcsc.com/activity/coupon"

SECTION_NAMES: dict[int | str, str] = {
    1:  "综合专区",
    2:  "品牌推广专区",
    3:  "超级品牌周",
    4:  "PLUS 会员专区",
    5:  "工业品专区",
    12: "超级会员日",
    13: "面板定制 & 移动端",
}

# ── rich 导入及降级 ──────────────────────────────────────────
try:
    from rich import print as rprint
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.box import ROUNDED
    from rich.style import Style
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn

    _HAS_RICH = True
    console = Console()
except ImportError:
    _HAS_RICH = False

    class Console:
        @staticmethod
        def print(*a, **kw):
            print(*a)

    console = Console()


# ── 数据获取 ──────────────────────────────────────────────────
def fetch_coupons(max_retries: int = 3) -> dict[str, Any]:
    """调用 API 获取全部优惠券数据（带自动重试、请求间隔限制）"""
    # 检查请求间隔
    _last_fetch = getattr(fetch_coupons, "_last_ts", 0)
    since_last = time.time() - _last_fetch
    if since_last < _MIN_REFRESH_INTERVAL:
        wait = _MIN_REFRESH_INTERVAL - since_last
        console.print(
            f"[yellow]⚠ 请求过于频繁，请等待 {wait:.0f}s 后重试。[/]"
        )
        raise RuntimeError(f"请求间隔限制: 每 {_MIN_REFRESH_INTERVAL}s 最多一次")
    ctx = ssl.create_default_context()
    last_exc = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(API_URL, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.szlcsc.com/huodong.html",
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                fetch_coupons._last_ts = time.time()  # type: ignore[attr-defined]
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                console.print(f"[yellow]API 请求失败，{wait}s 后重试 ({attempt+1}/{max_retries})...[/]")
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _save_data_file(data: dict[str, Any]):
    """将数据写入 latest_data.json（仓库跟踪，带缩进以支持 git diff）"""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_cache(data: dict[str, Any]):
    """写入 5 分钟临时缓存"""
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def _git_pull_data() -> bool:
    """尝试 git pull --ff-only 拉取远程最新数据"""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def _ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    """交互式询问 Y/N，非交互环境返回 default_yes"""
    try:
        suffix = " [Y/N]: " if default_yes else " [y/N]: "
        answer = input(prompt + suffix).strip().lower()
        if default_yes:
            return answer in ("", "y", "yes")
        return answer in ("y", "yes")
    except (EOFError, OSError):
        return default_yes


def load_coupons(
    use_cache: bool = True,
    refresh: bool = False,
    max_age_hr: float = 24,
) -> dict[str, Any]:
    """
    获取优惠券数据，按优先级:

    1. --refresh → 直打 szlcsc API，写入 DATA_FILE
    2. 5min CACHE_FILE 有效 → 直接用（快速反复运行）
    3. DATA_FILE 存在且未过期 → 直接用
    4. DATA_FILE 过期 → 询问用户:
       a. Y → git pull → 成功则用，否则 fallback API
       b. N → 继续用旧文件
    5. DATA_FILE 不存在 → 直打 API
    """
    # ── 1. 直打 API（--refresh）──
    if refresh:
        console.print("[dim]来源: 立创 API (--refresh)[/]")
        data = fetch_coupons()
        _save_data_file(data)
        _save_cache(data)
        return data

    # ── 2. 5min 临时缓存 ──
    if use_cache and os.path.exists(CACHE_FILE):
        mtime = os.path.getmtime(CACHE_FILE)
        if time.time() - mtime < 300:
            console.print("[dim]来源: 临时缓存 (5min)[/]")
            with open(CACHE_FILE) as f:
                return json.load(f)

    # ── 3. DATA_FILE 存在 ──
    if os.path.exists(DATA_FILE):
        age = time.time() - os.path.getmtime(DATA_FILE)
        age_hr = age / 3600

        if age_hr < max_age_hr:
            # 未过期
            console.print(f"[dim]来源: 本地数据 ({age_hr:.1f}h 前更新)[/]")
            with open(DATA_FILE) as f:
                return json.load(f)

        # 已过期 → 询问
        console.print(f"[yellow]本地数据已 {age_hr:.1f}h 未更新（阈值 {max_age_hr}h）[/]")
        if _ask_yes_no("是否从远程仓库拉取最新数据?"):
            if _git_pull_data() and os.path.exists(DATA_FILE):
                new_age = time.time() - os.path.getmtime(DATA_FILE)
                if new_age < age:  # 文件确有更新
                    console.print("[dim]来源: git pull 远程仓库[/]")
                    with open(DATA_FILE) as f:
                        return json.load(f)

            # git pull 失败 → 直打 API
            console.print("[yellow]远程拉取失败，尝试直接从立创商城获取...[/]")
            try:
                data = fetch_coupons()
                _save_data_file(data)
                _save_cache(data)
                console.print("[dim]来源: 立创 API (git pull 失败后降级)[/]")
                return data
            except Exception as exc:
                console.print(f"[red]API 请求也失败: {exc}[/]")
                console.print("[yellow]使用本地旧数据。[/]")
                with open(DATA_FILE) as f:
                    return json.load(f)

        # 用户选 N
        console.print("[dim]使用本地数据。[/]")
        with open(DATA_FILE) as f:
            return json.load(f)

    # ── 5. DATA_FILE 不存在 → 直打 API ──
    console.print("[dim]来源: 立创 API (无本地数据)[/]")
    data = fetch_coupons()
    _save_data_file(data)
    _save_cache(data)
    return data


# ── 数据处理 ──────────────────────────────────────────────────
def parse_coupons(data: dict[str, Any]) -> list[dict[str, Any]]:
    """拍平所有专区的优惠券，并清洗字段"""
    result = data.get("result", {})
    section_map = result.get("couponModelVOListMap", {})
    coupons: list[dict[str, Any]] = []
    for section_id, clist in section_map.items():
        for c in clist:
            c["_section_id"] = section_id
            coupons.append(c)
    return coupons


def compute_discount_rate(c: dict[str, Any]) -> float:
    """计算折扣率（百分比），如 满16减15 → 93.75"""
    ctype = c.get("couponType", "")
    amount = c.get("couponAmount") or 0
    threshold = c.get("minOrderMoney") or 0

    if ctype == "discount":
        discount = c.get("couponDiscount") or 10
        if discount > 10:
            discount /= 10
        elif 0 < discount <= 1:
            discount *= 10
        return round((10 - discount) / 10 * 100, 2)
    if amount and threshold and threshold > 0:
        raw = amount / threshold * 100
        return min(round(raw, 2), 100.0)
    if amount > 0:
        return 100.0
    return 0.0


def format_amount(c: dict[str, Any]) -> str:
    """格式化金额/折扣信息"""
    ctype = c.get("couponType", "")
    if ctype == "discount":
        disc = c.get("couponDiscount", 100) or 100
        if disc > 10:
            disc /= 10
        elif 0 < disc <= 1:
            disc *= 10
        return f"{disc:.0f}折"
    amount = c.get("couponAmount")
    if amount and amount > 0:
        return f"¥{amount:.0f}"
    return "-"


def classify_section(c: dict[str, Any]) -> int | str:
    """返回所属专区的 key（用于分组），统一返回 int"""
    fp = c.get("frontPartition")
    sid = c.get("_section_id")
    if fp is not None:
        return fp
    if sid == "plus":
        return 4
    if isinstance(sid, str) and sid.isdigit():
        return int(sid)
    return sid


def group_coupons(coupons: list[dict[str, Any]]) -> dict[int | str, list[dict[str, Any]]]:
    """按专区分组"""
    groups: dict[int | str, list[dict[str, Any]]] = defaultdict(list)
    for c in coupons:
        sec = classify_section(c)
        groups[sec].append(c)
    return dict(groups)


# ── 终端输出（Rich） ────────────────────────────────────────
def style_discount_rate(rate: float) -> Text:
    """折扣率样式"""
    if rate >= 90:
        return Text(f"{rate:.1f}%", style="bold green")
    if rate >= 70:
        return Text(f"{rate:.1f}%", style="green")
    if rate >= 50:
        return Text(f"{rate:.1f}%", style="yellow")
    if rate >= 30:
        return Text(f"{rate:.1f}%", style="cyan")
    return Text(f"{rate:.1f}%", style="dim white")


def style_received(count: int) -> Text:
    """已领人数样式"""
    if count >= 10000:
        return Text(f"{count:,}", style="bold bright_red")
    if count >= 1000:
        return Text(f"{count:,}", style="bright_yellow")
    if count >= 100:
        return Text(f"{count:,}", style="white")
    return Text(f"{count:,}", style="dim white")


def build_section_table(
    coupons: list[dict[str, Any]],
    section_name: str,
    sort_by: str = "received",
    min_rate: float = 0,
    brand_filter: str | None = None,
) -> Table | None:
    """为一个专区生成 Rich Table"""
    # 过滤
    filtered = list(coupons)
    if brand_filter:
        keyword = brand_filter.lower()
        filtered = [
            c for c in filtered
            if keyword in (c.get("couponName") or "").lower()
            or keyword in (c.get("couponTypeName") or "").lower()
            or keyword in (c.get("brandNames") or "").lower()
        ]
    if min_rate > 0:
        filtered = [c for c in filtered if compute_discount_rate(c) >= min_rate]

    if not filtered:
        return None

    # 排序
    if sort_by == "received":
        filtered.sort(key=lambda c: -(c.get("receiveCustomerNum") or 0))
    elif sort_by == "rate":
        filtered.sort(key=lambda c: -compute_discount_rate(c))
    elif sort_by == "amount":
        filtered.sort(key=lambda c: -(c.get("couponAmount") or 0))
    elif sort_by == "threshold":
        filtered.sort(key=lambda c: (c.get("minOrderMoney") or 0))

    table = Table(
        title=f"[bold]{section_name}[/]  ({len(filtered)} 张券)",
        box=ROUNDED,
        title_style="bold #199FE9",
        border_style="#56657F",
        header_style="bold white on #199FE9",
        padding=0,
        expand=True,
    )

    table.add_column("#", style="dim", width=3, no_wrap=True)
    table.add_column("优惠券名称", style="white", no_wrap=False, ratio=2, min_width=18)
    table.add_column("已领", justify="right", no_wrap=True, width=8)
    table.add_column("门槛", justify="right", no_wrap=True, width=7)
    table.add_column("面额", justify="right", no_wrap=True, width=7)
    table.add_column("折扣率", justify="right", no_wrap=True, width=7)
    table.add_column("限领", justify="right", no_wrap=True, width=5)
    table.add_column("有效期", style="dim", no_wrap=True, width=20)

    for idx, c in enumerate(filtered, 1):
        name = c.get("couponName") or "-"
        received = c.get("receiveCustomerNum") or 0
        threshold = c.get("minOrderMoney")
        threshold_str = f"¥{threshold:.0f}" if threshold and threshold > 0 else "-"
        amount_str = format_amount(c)
        rate = compute_discount_rate(c)
        limit = c.get("customerMaxNum") or "-"
        begin = (c.get("couponValidBeginTime") or "")[:10]
        end = (c.get("couponValidEndTime") or "")[:10]
        valid = f"{begin} ~ {end}" if begin and end else "-"

        table.add_row(
            str(idx),
            name,
            style_received(received),
            threshold_str,
            amount_str,
            style_discount_rate(rate),
            str(limit),
            valid,
        )

    return table


def print_all_sections(
    groups: dict[int | str, list[dict[str, Any]]],
    sort_by: str = "received",
    min_rate: float = 0,
    brand_filter: str | None = None,
):
    """打印所有专区的表格"""
    display_order = [1, 2, 3, 4, 5, 12, 13]
    printed = 0

    for sec_id in display_order:
        clist = groups.get(sec_id, [])
        if not clist:
            continue
        name = SECTION_NAMES.get(sec_id, f"专区 {sec_id}")
        table = build_section_table(
            clist, name, sort_by, min_rate, brand_filter
        )
        if table is not None:
            if printed > 0:
                console.print()
            console.print(table)
            printed += 1

    # 显示未知专区（API 新加的）
    known = set(display_order)
    for sec_id in groups:
        if sec_id not in known:
            clist = groups[sec_id]
            name = SECTION_NAMES.get(sec_id, f"专区 {sec_id}")
            table = build_section_table(clist, name, sort_by, min_rate, brand_filter)
            if table is not None:
                if printed > 0:
                    console.print()
                console.print(table)
                printed += 1


def print_best_value_ranking(
    all_coupons: list[dict[str, Any]],
    top_n: int = 20,
):
    """打印折扣率最高的券（全局）"""
    scored = []
    for c in all_coupons:
        rate = compute_discount_rate(c)
        received = c.get("receiveCustomerNum") or 0
        amount = c.get("couponAmount") or 0
        threshold = c.get("minOrderMoney") or 0
        scored.append((rate, received, amount, threshold, c))

    scored.sort(key=lambda x: (-x[0], -x[1]))

    table = Table(
        title=f"[bold]📊 折扣率排行榜 TOP {top_n}[/]",
        box=ROUNDED,
        title_style="bold #199FE9",
        border_style="#56657F",
        header_style="bold white on #0093E6",
        padding=0,
        expand=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("优惠券名称", ratio=2, min_width=18)
    table.add_column("折扣率", justify="right", width=7)
    table.add_column("已领", justify="right", width=8)
    table.add_column("门槛", justify="right", width=7)
    table.add_column("面额", justify="right", width=7)
    table.add_column("专区", style="dim", width=12)

    for idx, (rate, received, amount, threshold, c) in enumerate(scored[:top_n], 1):
        name = c.get("couponName") or "-"
        amount_str = format_amount(c)
        threshold_str = f"¥{threshold:.0f}" if threshold else "-"
        sid = classify_section(c)
        sec_name = SECTION_NAMES.get(sid, f"专区 {sid}")
        table.add_row(
            str(idx),
            name,
            style_discount_rate(rate),
            style_received(received),
            threshold_str,
            amount_str,
            sec_name,
        )

    console.print()
    console.print(table)


def print_combo_analysis(
    all_coupons: list[dict[str, Any]],
    budget: float | None = None,
    coupon_count: int = 10,
):
    """
    [实验性] 组合分析：找 discount_rate 最高的 N 张商品券，模拟叠加效果。
    排除运费券（对商品无意义），单张优惠不超门槛。待完善：品牌互斥、券类型互斥等规则。
    """
    scored = []
    for c in all_coupons:
        ctype = c.get("couponType", "")
        tname = (c.get("couponTypeName") or "").lower()
        # 排除运费券
        if ctype == "freight" or "运费" in tname:
            continue
        rate = compute_discount_rate(c)
        amount = c.get("couponAmount") or 0
        threshold = c.get("minOrderMoney") or 0
        if amount <= 0 or threshold <= 0:
            continue
        received = c.get("receiveCustomerNum") or 0
        scored.append((rate, received, amount, threshold, c))

    scored.sort(key=lambda x: (-x[0], -x[1]))
    top = scored[:coupon_count]

    total_threshold = sum(item[3] for item in top)
    total_amount = sum(min(item[2], item[3]) for item in top)  # 优惠不超过门槛
    actual_pay = max(total_threshold - total_amount, 1)  # 至少付 ¥1
    multiplier = total_threshold / actual_pay

    table = Table(
        title=f"[bold]💰 {coupon_count} 张商品券叠加模拟（理论值）[/]",
        box=ROUNDED,
        title_style="bold #199FE9",
        border_style="#56657F",
        header_style="bold white on #0093E6",
        padding=0,
        expand=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("优惠券名称", ratio=2, min_width=18)
    table.add_column("折扣率", justify="right", width=7)
    table.add_column("门槛", justify="right", width=7)
    table.add_column("面额", justify="right", width=7)
    table.add_column("实付", justify="right", width=7)

    for idx, (rate, recv, amt, thr, c) in enumerate(top, 1):
        pay = max(thr - min(amt, thr), 1)
        table.add_row(
            str(idx),
            c.get("couponName", "-"),
            style_discount_rate(rate),
            f"¥{thr:.0f}",
            format_amount(c),
            f"¥{pay:.0f}",
        )

    summary_text = (
        f"[bold]商品总价值[/]: [green]¥{total_threshold:,.0f}[/]\n"
        f"[bold]券抵扣总额 (上限门槛)[/]: [bright_yellow]¥{total_amount:,.0f}[/]\n"
        f"[bold]实际需支付[/]: [bold green]¥{actual_pay:,.0f}[/]\n"
        f"[bold]理论购买力倍率[/]: [bold bright_red]{multiplier:.1f}x[/]  "
        f"(付 ¥1 约抵 ¥{multiplier:.1f} 的元件价值，仅理论估算)\n"
    )

    if budget:
        estimate_items = int(budget * multiplier)
        summary_text += (
            f"\n[bold]你的预算 ¥{budget:,.0f}[/] → 可购买约 "
            f"[bold bright_green]¥{estimate_items:,}[/] 的电子元件"
        )

    console.print()
    console.print(Panel(
        "[yellow]⚠ 实验性功能[/] — 叠加逻辑尚未考虑品牌互斥、券类型互斥等规则，"
        "结果仅供参考。",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print()
    console.print(table)
    console.print()
    console.print(Panel(summary_text, title="📈 叠加效果", border_style="#199FE9"))


def print_diff(coupons: list[dict[str, Any]]):
    """对比上次运行结果，显示变化"""
    if not os.path.exists(HISTORY_FILE):
        console.print("[yellow]⚠ 没有历史数据，本次将作为基线保存。[/]")
        _save_history(coupons)
        return

    with open(HISTORY_FILE) as f:
        old = json.load(f)

    old_map = {c["couponId"]: c for c in old if c.get("couponId")}
    new_map = {c["couponId"]: c for c in coupons if c.get("couponId")}

    added = [c for cid, c in new_map.items() if cid not in old_map]
    removed = [c for cid, c in old_map.items() if cid not in new_map]
    changed = []
    for cid, new_c in new_map.items():
        old_c = old_map.get(cid)
        if old_c:
            old_recv = old_c.get("receiveCustomerNum") or 0
            new_recv = new_c.get("receiveCustomerNum") or 0
            if old_recv != new_recv:
                changed.append((new_c, old_recv, new_recv))

    if not (added or removed or changed):
        console.print("[green]✅ 与上次相比无变化。[/]")
        return

    if added:
        t = Table(title="🆕 新增优惠券", box=ROUNDED, border_style="green", padding=0, expand=True)
        t.add_column("名称", ratio=3)
        t.add_column("面额", justify="right", width=7)
        t.add_column("专区", width=16)
        for c in added:
            sid = classify_section(c)
            sec_name = SECTION_NAMES.get(sid, f"专区 {sid}")
            t.add_row(c.get("couponName", "-"), f"¥{c.get('couponAmount') or 0:.0f}", sec_name)
        console.print(t)
        console.print()

    if removed:
        t = Table(title="🗑️ 已下架优惠券", box=ROUNDED, border_style="red", padding=0, expand=True)
        t.add_column("名称", ratio=3)
        t.add_column("面额", justify="right", width=7)
        for c in removed:
            t.add_row(c.get("couponName", "-"), f"¥{c.get('couponAmount') or 0:.0f}")
        console.print(t)
        console.print()

    if changed:
        t = Table(
            title="📈 已领数量变化",
            box=ROUNDED,
            border_style="yellow",
            header_style="bold white on #CC7700",
            padding=0,
            expand=True,
        )
        t.add_column("名称", ratio=3)
        t.add_column("原先", justify="right", width=10)
        t.add_column("现在", justify="right", width=10)
        t.add_column("变化", justify="right", width=10)
        for c, old_r, new_r in sorted(changed, key=lambda x: -(x[2] - x[1])):
            diff = new_r - old_r
            diff_str = (
                Text(f"+{diff:,}", style="green")
                if diff > 0
                else Text(f"{diff:,}", style="red")
            )
            t.add_row(
                c.get("couponName", "-"),
                f"{old_r:,}",
                f"{new_r:,}",
                diff_str,
            )
        console.print(t)

    _save_history(coupons)


def export_csv(coupons: list[dict[str, Any]], filepath: str):
    """导出全部数据为 CSV"""
    fieldnames = [
        "couponId", "couponName", "couponTypeName", "couponActivityName",
        "receiveCustomerNum", "minOrderMoney", "couponAmount",
        "discountRate", "customerMaxNum",
        "couponValidBeginTime", "couponValidEndTime",
        "section", "frontPartition",
    ]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in coupons:
            row = {
                "couponId": c.get("couponId", ""),
                "couponName": c.get("couponName", ""),
                "couponTypeName": c.get("couponTypeName", c.get("couponType", "")),
                "couponActivityName": c.get("couponActivityName", ""),
                "receiveCustomerNum": c.get("receiveCustomerNum", 0),
                "minOrderMoney": c.get("minOrderMoney", ""),
                "couponAmount": c.get("couponAmount", ""),
                "discountRate": compute_discount_rate(c),
                "customerMaxNum": c.get("customerMaxNum", ""),
                "couponValidBeginTime": c.get("couponValidBeginTime", ""),
                "couponValidEndTime": c.get("couponValidEndTime", ""),
                "section": SECTION_NAMES.get(classify_section(c), ""),
                "frontPartition": c.get("frontPartition", ""),
            }
            writer.writerow(row)
    console.print(f"[green]✅ 已导出 {len(coupons)} 条数据到 [bold]{filepath}[/][/]")


def _save_history(coupons: list[dict[str, Any]]):
    """保存快照用于 diff"""
    with open(HISTORY_FILE, "w") as f:
        json.dump(coupons, f, ensure_ascii=False)


def print_summary_stats(all_coupons: list[dict[str, Any]]):
    """打印汇总统计信息"""
    total = len(all_coupons)
    if total == 0:
        console.print("[yellow]无数据。[/]")
        return

    now = datetime.now()
    active = 0
    total_received = 0
    total_discount_value = 0.0
    weighted_rate = 0.0
    type_counts: dict[str, int] = {}
    section_counts: dict[str, int] = {}

    for c in all_coupons:
        received = c.get("receiveCustomerNum") or 0
        total_received += received
        amount = c.get("couponAmount") or 0
        threshold = c.get("minOrderMoney") or 0
        if amount > 0 and threshold > 0:
            total_discount_value += min(amount, threshold)

        rate = compute_discount_rate(c)
        weighted_rate += rate * received

        raw_type = c.get("couponType") or ""
        type_name_map = {
            "freight": "运费券",
            "product": "商品券",
            "discount": "折扣券",
            "plus": "PLUS会费券",
        }
        tname = type_name_map.get(raw_type, c.get("couponTypeName") or raw_type or "未知")
        type_counts[tname] = type_counts.get(tname, 0) + 1

        sid = classify_section(c)
        sname = SECTION_NAMES.get(sid, f"专区 {sid}")
        section_counts[sname] = section_counts.get(sname, 0) + 1

        end_str = c.get("couponValidEndTime")
        if end_str:
            try:
                end_dt = datetime.strptime(end_str[:10], "%Y-%m-%d")
                if end_dt > now:
                    active += 1
            except ValueError:
                active += 1
        else:
            active += 1

    avg_rate = weighted_rate / total_received if total_received else 0

    most_popular = max(all_coupons, key=lambda c: c.get("receiveCustomerNum") or 0)

    table = Table(
        title="📊 优惠券汇总统计",
        box=ROUNDED,
        border_style="#199FE9",
        padding=0,
        expand=True,
    )
    table.add_column("指标", style="bold white")
    table.add_column("数值", ratio=2)

    table.add_row("优惠券总数", f"{total:,}")
    table.add_row("有效期内", f"{active:,}")
    table.add_row("总领取人次", f"{total_received:,}")
    table.add_row("券面总价值（上限门槛）", f"¥{total_discount_value:,.0f}")
    table.add_row("加权平均折扣率", f"{avg_rate:.1f}%")
    table.add_row(
        "最热门的券",
        f"{most_popular.get('couponName', '-')} "
        f"({most_popular.get('receiveCustomerNum') or 0:,} 人已领)"
    )

    console.print()
    console.print(table)

    # 类型分布
    type_table = Table(
        title="📂 优惠券类型分布",
        box=ROUNDED,
        border_style="#56657F",
        padding=0,
        expand=True,
    )
    type_table.add_column("类型")
    type_table.add_column("数量", justify="right")
    for tname, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        type_table.add_row(tname, f"{cnt:,}")
    console.print()
    console.print(type_table)


# ── 主入口 ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="立创商城优惠券数据浏览与比较工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python coupons.py                           # 完整展示所有专区
  python coupons.py --stats                  # 汇总统计
  python coupons.py --sort rate               # 按折扣率排序
  python coupons.py --min-rate 80             # 只看 80%% 以上折扣
  python coupons.py --brand 捷而瑞             # 按品牌名搜索（支持部分匹配），仅显示该品牌
  python coupons.py --combo                   # [实验性] 10 张券叠加模拟
  python coupons.py --diff                    # 与上次对比变化
  python coupons.py --export data.csv         # 导出 CSV
  python coupons.py --refresh                 # 从立创 API 拉取最新数据
  python coupons.py --max-age-hr 48           # 48 小时内不提示更新
        """,
    )
    parser.add_argument("--sort", choices=["received", "rate", "amount", "threshold"],
                        default="received", help="排序方式 (默认: 已领数量)")
    parser.add_argument("--min-rate", type=float, default=0,
                        help="最低折扣率筛选 (如 80 表示 80%% 以上)")
    parser.add_argument("--brand", type=str, default=None,
                        help="按品牌名搜索（支持部分名称匹配），仅显示匹配该品牌的券")
    parser.add_argument("--section", type=str, default=None,
                        help="只显示指定专区 (id 或名称关键词)")
    parser.add_argument("--combo", type=float, nargs="?", const=_UNLIMITED, default=None,
                        help="[实验性] N 张券叠加模拟（可选预算金额，如 --combo 100）")
    parser.add_argument("--diff", action="store_true",
                        help="与上次运行对比变化")
    parser.add_argument("--export", type=str, default=None, metavar="FILE",
                        help="导出全部数据为 CSV")
    parser.add_argument("--no-cache", action="store_true",
                        help="忽略 5 分钟临时缓存")
    parser.add_argument("--refresh", action="store_true",
                        help="忽略缓存，从立创 API 拉取最新数据")
    parser.add_argument("--max-age-hr", type=float, default=24,
                        help="本地数据过期阈值（小时），默认 24")
    parser.add_argument("--top", type=int, nargs="?", const=20, default=None,
                        help="仅显示折扣率排行榜 (默认 20 名)")
    parser.add_argument("--version", action="store_true",
                        help="显示版本信息")
    parser.add_argument("--stats", action="store_true",
                        help="仅显示汇总统计信息")

    args = parser.parse_args()

    if args.version:
        console.print(f"[bold]szlcsc-coupons[/] [dim]v{__version__}[/]")
        return

    # ── 加载数据 ──
    if args.refresh:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="正在从立创 API 拉取最新数据...", total=None)
            data = load_coupons(refresh=True)
    else:
        data = load_coupons(
            use_cache=not args.no_cache,
            max_age_hr=args.max_age_hr,
        )

    all_coupons = parse_coupons(data)
    groups = group_coupons(all_coupons)

    if not all_coupons:
        console.print("[red]❌ 未获取到优惠券数据，请稍后重试。[/]")
        sys.exit(1)

    # ── 免责声明 ──
    console.print()
    console.print(Panel(
        "[bold yellow]⚠ 第三方工具声明[/]\n"
        "本工具是个人开发的立创商城优惠券数据分析工具，与立创商城（szlcsc.com）无任何关联。\n"
        "数据来源于 activity.szlcsc.com 公开 API。\n"
        "\n"
        "推荐个人电子爱好者为学习研究使用。\n"
        "不推荐集体/公司/组织使用——小额券对组织价值不大，大额券价格亦常高于其他渠道。\n"
        "\n"
        "请遵守立创商城服务条款，合理控制请求频率。",
        border_style="yellow",
        padding=(1, 2),
    ))

    # ── 欢迎 ──
    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = Panel(
        f"[bold white]📋 立创商城优惠券数据浏览[/]    "
        f"[dim]{len(all_coupons)} 张券 | {dt}[/]",
        border_style="#199FE9",
        padding=(1, 2),
    )
    console.print()
    console.print(header)

    # ── 执行动作 ──
    if args.stats:
        print_summary_stats(all_coupons)
        return

    if args.diff:
        print_diff(all_coupons)
        return

    if args.export:
        export_csv(all_coupons, args.export)
        return

    if args.combo is not None:
        budget = None if args.combo is _UNLIMITED else args.combo
        print_combo_analysis(all_coupons, budget=budget)
        return

    if args.section:
        # 按专区ID或名称关键词筛选
        sec_id = None
        try:
            sec_id = int(args.section)
        except ValueError:
            query = args.section.lower()
            for sid, sname in SECTION_NAMES.items():
                if query in sname.lower():
                    sec_id = sid
                    break
        if sec_id is not None and sec_id in groups:
            name = SECTION_NAMES.get(sec_id, f"专区 {sec_id}")
            table = build_section_table(
                groups[sec_id], name, args.sort, args.min_rate, args.brand
            )
            if table:
                console.print(table)
            else:
                console.print("[yellow]⚠ 该专区无匹配的优惠券。[/]")
        else:
            console.print(f"[red]❌ 未找到专区: {args.section}[/]")
            console.print(f"  可用专区: {', '.join(f'{k}={v}' for k, v in SECTION_NAMES.items())}")
        return

    # ── 默认: 打印所有专区 ──
    if args.top is not None:
        console.print()
        print_best_value_ranking(all_coupons, top_n=args.top)
    else:
        print_all_sections(groups, args.sort, args.min_rate, args.brand)

        if args.min_rate == 0 and args.brand is None:
            console.print()
            console.print("─" * console.width)
            print_best_value_ranking(all_coupons, top_n=20)

    # 底部提示
    tips = Text()
    tips.append("\n💡 ", style="dim")
    tips.append("提示: 使用 ", style="dim")
    tips.append("python coupons.py --help", style="bold cyan")
    tips.append(" 查看全部功能", style="dim")
    console.print(tips)
    console.print()


if __name__ == "__main__":
    main()
