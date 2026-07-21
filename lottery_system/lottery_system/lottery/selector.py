"""
台灣大樂透 多條件選號篩選模組
功能：根據各種統計條件智慧推薦號碼組合
"""

import random
import pandas as pd
import numpy as np
from analyzer import frequency_analysis, hot_cold_analysis, interval_analysis, sum_analysis


def filter_combinations(candidates, conditions):
    """
    對候選號碼組合套用多重篩選條件
    conditions 範例：
    {
        "奇偶比": (2, 4),        # 奇數個數範圍 (min, max)
        "大小比": (2, 4),        # 大號(>25)個數範圍
        "和值範圍": (100, 180),  # 6碼總和範圍
        "連號上限": 2,           # 最多幾組連號
        "重複上限": 2,           # 與上期重複號碼上限
        "間隔下限": 3,           # 號碼最少間隔幾期才納入
    }
    """
    result = []
    for combo in candidates:
        nums = sorted(combo)

        # 奇偶比篩選
        if "奇偶比" in conditions:
            odd_min, odd_max = conditions["奇偶比"]
            odd_count = sum(1 for n in nums if n % 2 == 1)
            if not (odd_min <= odd_count <= odd_max):
                continue

        # 大小比篩選
        if "大小比" in conditions:
            big_min, big_max = conditions["大小比"]
            big_count = sum(1 for n in nums if n > 25)
            if not (big_min <= big_count <= big_max):
                continue

        # 和值範圍篩選
        if "和值範圍" in conditions:
            s_min, s_max = conditions["和值範圍"]
            total = sum(nums)
            if not (s_min <= total <= s_max):
                continue

        # 連號上限篩選
        if "連號上限" in conditions:
            max_consec = conditions["連號上限"]
            consec = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
            if consec > max_consec:
                continue

        result.append(tuple(nums))

    return result


def score_combination(combo, freq_dict, interval_dict, weights=None):
    """
    對一組號碼評分（分數越高越推薦）
    weights: {"頻率": 0.4, "間隔": 0.4, "隨機": 0.2}
    """
    if weights is None:
        weights = {"頻率": 0.4, "間隔": 0.4, "隨機": 0.2}

    nums = list(combo)
    total_draws = max(interval_dict.values()) if interval_dict else 1

    # 頻率分數（出現越多越高）
    max_freq = max(freq_dict.values()) if freq_dict else 1
    freq_score = sum(freq_dict.get(n, 0) for n in nums) / (6 * max_freq)

    # 間隔分數（間隔越長越高，代表「欠出現」）
    interval_score = sum(interval_dict.get(n, 0) for n in nums) / (6 * total_draws)

    # 隨機分數
    random_score = random.random()

    score = (
        weights["頻率"] * freq_score +
        weights["間隔"] * interval_score +
        weights["隨機"] * random_score
    )
    return round(score, 4)


def recommend_numbers(df, mode="綜合", n_recommend=5, conditions=None, recent_n=50):
    """
    主推薦函式
    mode:
        "熱號優先"  - 優先選近期高頻號碼
        "冷號優先"  - 優先選久未出現號碼
        "綜合"      - 熱冷號平衡
        "隨機"      - 純隨機（對照組）
        "歷史最強"  - 全期出現最多的號碼
    n_recommend: 推薦幾組
    conditions: 篩選條件 dict
    recent_n: 冷熱號分析期數
    """
    if df.empty:
        return []

    freq_all = frequency_analysis(df)
    hot_cold = hot_cold_analysis(df, recent_n)
    interval = interval_analysis(df)

    # 依模式決定候選號碼池
    if mode == "熱號優先":
        # 近期熱號優先，從出現頻率前20名中選
        pool = [n for n, _ in sorted(hot_cold["全部頻率"].items(), key=lambda x: x[1], reverse=True)[:25]]
        weights = {"頻率": 0.7, "間隔": 0.1, "隨機": 0.2}

    elif mode == "冷號優先":
        # 久未出現的號碼優先
        pool = [n for n, _ in sorted(interval.items(), key=lambda x: x[1], reverse=True)[:25]]
        weights = {"頻率": 0.1, "間隔": 0.7, "隨機": 0.2}

    elif mode == "歷史最強":
        pool = [n for n, _ in sorted(freq_all.items(), key=lambda x: x[1], reverse=True)[:25]]
        weights = {"頻率": 0.8, "間隔": 0.1, "隨機": 0.1}

    elif mode == "隨機":
        pool = list(range(1, 50))
        weights = {"頻率": 0.0, "間隔": 0.0, "隨機": 1.0}

    else:  # 綜合
        pool = list(range(1, 50))
        weights = {"頻率": 0.4, "間隔": 0.4, "隨機": 0.2}

    # 產生候選組合
    candidates = set()
    attempts = 0
    max_attempts = 5000

    while len(candidates) < max(200, n_recommend * 20) and attempts < max_attempts:
        attempts += 1
        if len(pool) >= 6:
            combo = tuple(sorted(random.sample(pool, 6)))
        else:
            combo = tuple(sorted(random.sample(range(1, 50), 6)))
        candidates.add(combo)

    candidates = list(candidates)

    # 套用篩選條件
    if conditions:
        filtered = filter_combinations(candidates, conditions)
        if len(filtered) >= n_recommend:
            candidates = filtered
        else:
            # 條件太嚴，放寬後重試
            candidates = filtered if filtered else candidates

    # 評分排序
    scored = []
    for combo in candidates:
        score = score_combination(combo, hot_cold["全部頻率"], interval, weights)
        scored.append((combo, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # 取前 N 組，確保組合間差異夠大
    result = []
    for combo, score in scored:
        if len(result) >= n_recommend:
            break
        # 確保與已選組合重複號碼不超過3個
        too_similar = False
        for existing, _ in result:
            overlap = len(set(combo) & set(existing))
            if overlap >= 4:
                too_similar = True
                break
        if not too_similar:
            result.append((combo, score))

    return result


def format_recommendation(recommendations):
    """格式化推薦結果"""
    output = []
    for i, (combo, score) in enumerate(recommendations, 1):
        nums_str = "  ".join(f"{n:02d}" for n in sorted(combo))
        output.append({
            "組別": f"第 {i} 組",
            "號碼": list(sorted(combo)),
            "號碼顯示": nums_str,
            "評分": score,
            "奇數個數": sum(1 for n in combo if n % 2 == 1),
            "大號個數": sum(1 for n in combo if n > 25),
            "和值": sum(combo),
        })
    return output


if __name__ == "__main__":
    from scraper import load_data

    df = load_data()
    if df.empty:
        print("⚠️  無資料，請先執行 scraper.py 匯入資料")
    else:
        print("🎯 台灣大樂透智慧選號系統")
        print("=" * 50)

        # 設定篩選條件
        conditions = {
            "奇偶比": (2, 4),       # 2~4個奇數
            "大小比": (2, 4),       # 2~4個大號
            "和值範圍": (90, 180),  # 和值在合理範圍
            "連號上限": 2,          # 最多2組連號
        }

        for mode in ["綜合", "熱號優先", "冷號優先", "歷史最強"]:
            print(f"\n📌 模式：{mode}")
            recs = recommend_numbers(df, mode=mode, n_recommend=3, conditions=conditions)
            formatted = format_recommendation(recs)
            for r in formatted:
                print(f"  {r['組別']}：{r['號碼顯示']}  "
                      f"（和值:{r['和值']} 奇:{r['奇數個數']}偶:{6-r['奇數個數']} "
                      f"大:{r['大號個數']}小:{6-r['大號個數']}）")
