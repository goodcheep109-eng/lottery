"""
台灣大樂透 選號模組（簡化版）
三大模式：下期預測、本季預測、兩年綜合
每組推薦包含 6個號碼 + 1個特別號
"""

import random
import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime


def get_freq(df):
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    all_nums = df[cols].values.flatten().tolist()
    return {i: all_nums.count(i) for i in range(1, 50)}


def get_special_freq(df):
    specials = df["特別號"].dropna().astype(int).tolist()
    return {i: specials.count(i) for i in range(1, 50)}


def get_interval(df):
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    total = len(df)
    last_seen = {}
    for idx, row in df.iterrows():
        for col in cols:
            last_seen[int(row[col])] = idx
    return {n: total - 1 - last_seen.get(n, -1) for n in range(1, 50)}


def pick_special(exclude_nums, special_freq):
    pool = [n for n in range(1, 50) if n not in exclude_nums]
    weights = [special_freq.get(n, 1) for n in pool]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    return random.choices(pool, weights=probs, k=1)[0]


def generate_combo(pool, freq, interval, mode="綜合"):
    if mode == "熱號":
        weights = [freq.get(n, 1) ** 2 for n in pool]
    elif mode == "冷號":
        weights = [interval.get(n, 1) ** 2 for n in pool]
    else:
        weights = [(freq.get(n, 1) + interval.get(n, 1)) for n in pool]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    nums = random.choices(pool, weights=probs, k=30)
    seen = set()
    result = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            result.append(n)
        if len(result) == 6:
            break
    while len(result) < 6:
        n = random.choice([x for x in pool if x not in seen])
        seen.add(n)
        result.append(n)
    return sorted(result)


def check_conditions(nums):
    odd = sum(1 for n in nums if n % 2 == 1)
    big = sum(1 for n in nums if n > 25)
    total = sum(nums)
    consec = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
    return (2 <= odd <= 4) and (2 <= big <= 4) and (80 <= total <= 200) and (consec <= 3)


def predict_next(df, n=5):
    """🔮 下期開獎號碼預測：近30期熱號 + 久未出現號碼 綜合加權"""
    recent = df.tail(30)
    freq = get_freq(recent)
    interval = get_interval(df)
    special_freq = get_special_freq(df)
    pool = list(range(1, 50))
    results = []
    attempts = 0
    while len(results) < n and attempts < 10000:
        attempts += 1
        nums = generate_combo(pool, freq, interval, "綜合")
        if not check_conditions(nums):
            continue
        if any(len(set(nums) & set(r["號碼"])) >= 4 for r in results):
            continue
        results.append({"號碼": nums, "特別號": pick_special(nums, special_freq)})
    return results


def predict_season(df, n=5):
    """🌸 本季機率預測：當前季度歷年最常出現的號碼"""
    current_quarter = (datetime.now().month - 1) // 3 + 1
    season_df = df[df["開獎日期"].dt.quarter == current_quarter]
    if len(season_df) < 10:
        season_df = df.tail(50)
    freq = get_freq(season_df)
    interval = get_interval(df)
    special_freq = get_special_freq(season_df)
    pool = [n for n, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:35]]
    results = []
    attempts = 0
    while len(results) < n and attempts < 10000:
        attempts += 1
        nums = generate_combo(pool, freq, interval, "熱號")
        if not check_conditions(nums):
            continue
        if any(len(set(nums) & set(r["號碼"])) >= 4 for r in results):
            continue
        results.append({"號碼": nums, "特別號": pick_special(nums, special_freq)})
    return results


def predict_two_years(df, n=5):
    """📅 前後兩年綜合預測：近兩年開獎資料頻率最高的號碼"""
    two_years_ago = pd.Timestamp.now() - pd.DateOffset(years=2)
    recent_df = df[df["開獎日期"] >= two_years_ago]
    if len(recent_df) < 20:
        recent_df = df.tail(100)
    freq = get_freq(recent_df)
    interval = get_interval(df)
    special_freq = get_special_freq(recent_df)
    pool = list(range(1, 50))
    results = []
    attempts = 0
    while len(results) < n and attempts < 10000:
        attempts += 1
        nums = generate_combo(pool, freq, interval, "綜合")
        if not check_conditions(nums):
            continue
        if any(len(set(nums) & set(r["號碼"])) >= 4 for r in results):
            continue
        results.append({"號碼": nums, "特別號": pick_special(nums, special_freq)})
    return results


def format_results(results, mode_name):
    output = []
    for i, r in enumerate(results, 1):
        nums = r["號碼"]
        special = r["特別號"]
        output.append({
            "組別": f"第 {i} 組",
            "模式": mode_name,
            "號碼": nums,
            "特別號": special,
            "號碼顯示": "  ".join(f"{n:02d}" for n in nums),
            "特別號顯示": f"{special:02d}",
            "和值": sum(nums),
            "奇數": sum(1 for n in nums if n % 2 == 1),
            "大號": sum(1 for n in nums if n > 25),
        })
    return output


if __name__ == "__main__":
    from scraper import load_data
    df = load_data()
    if df.empty:
        print("⚠️  無資料")
    else:
        for mode, func in [("🔮 下期預測", predict_next), ("🌸 本季預測", predict_season), ("📅 兩年綜合", predict_two_years)]:
            print(f"\n{mode}：")
            for r in format_results(func(df, 5), mode):
                print(f"  {r['組別']}：{r['號碼顯示']} ＋特別號 {r['特別號顯示']}  (和值:{r['和值']})")
