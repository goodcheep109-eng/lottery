"""
台灣大樂透 資料分析模組
功能：頻率分析、冷熱號、間隔分析、月/季/年統計
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime


def get_all_numbers(df, include_special=False):
    """取出所有開獎號碼（攤平成一維列表）"""
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    nums = df[cols].values.flatten().tolist()
    if include_special:
        nums += df["特別號"].dropna().astype(int).tolist()
    return nums


def frequency_analysis(df, include_special=False):
    """
    全期頻率分析
    回傳：{號碼: 出現次數} 排序 dict
    """
    nums = get_all_numbers(df, include_special)
    counter = Counter(nums)
    # 補齊 1-49 所有號碼
    result = {i: counter.get(i, 0) for i in range(1, 50)}
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def hot_cold_analysis(df, recent_n=50, include_special=False):
    """
    冷熱號分析（近 N 期）
    回傳：hot（前10熱號）, cold（前10冷號）, all_freq dict
    """
    recent = df.tail(recent_n)
    freq = frequency_analysis(recent, include_special)
    sorted_nums = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    hot = sorted_nums[:10]
    cold = sorted_nums[-10:]
    return {
        "熱號": hot,
        "冷號": cold,
        "全部頻率": freq,
        "分析期數": recent_n,
    }


def interval_analysis(df):
    """
    號碼間隔分析：每個號碼距離上次出現已過幾期
    回傳：{號碼: 間隔期數}
    """
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    total = len(df)
    last_seen = {}

    for idx, row in df.iterrows():
        for col in cols:
            n = int(row[col])
            last_seen[n] = idx  # 記錄最後出現的 index

    result = {}
    for n in range(1, 50):
        if n in last_seen:
            result[n] = total - 1 - last_seen[n]
        else:
            result[n] = total  # 從未出現

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def monthly_analysis(df):
    """
    每月號碼頻率分析
    回傳：{月份(1-12): {號碼: 次數}}
    """
    result = {}
    for month in range(1, 13):
        subset = df[df["開獎日期"].dt.month == month]
        if subset.empty:
            result[month] = {}
            continue
        freq = frequency_analysis(subset)
        result[month] = freq
    return result


def quarterly_analysis(df):
    """
    每季號碼頻率分析
    回傳：{季(1-4): {號碼: 次數}}
    """
    result = {}
    for q in range(1, 5):
        subset = df[df["開獎日期"].dt.quarter == q]
        if subset.empty:
            result[q] = {}
            continue
        freq = frequency_analysis(subset)
        result[q] = freq
    return result


def yearly_analysis(df):
    """
    每年號碼頻率分析
    回傳：{年份: {號碼: 次數}}
    """
    result = {}
    years = sorted(df["開獎日期"].dt.year.dropna().unique().astype(int))
    for year in years:
        subset = df[df["開獎日期"].dt.year == year]
        freq = frequency_analysis(subset)
        result[year] = freq
    return result


def consecutive_analysis(df):
    """
    連號分析：每期有幾組連號
    回傳：統計摘要
    """
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    consec_counts = []
    for _, row in df.iterrows():
        nums = sorted([int(row[c]) for c in cols])
        count = sum(1 for i in range(len(nums)-1) if nums[i+1] - nums[i] == 1)
        consec_counts.append(count)
    return {
        "平均連號組數": round(np.mean(consec_counts), 2),
        "有連號比例": round(sum(1 for c in consec_counts if c > 0) / len(consec_counts) * 100, 1),
        "分佈": Counter(consec_counts),
    }


def odd_even_analysis(df):
    """
    奇偶比分析
    回傳：各奇偶比例的出現次數
    """
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    ratios = []
    for _, row in df.iterrows():
        nums = [int(row[c]) for c in cols]
        odd = sum(1 for n in nums if n % 2 == 1)
        even = 6 - odd
        ratios.append(f"{odd}奇{even}偶")
    return Counter(ratios)


def sum_analysis(df):
    """
    和值分析：6個號碼加總的分佈
    """
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    sums = df[cols].astype(int).sum(axis=1)
    return {
        "平均和值": round(sums.mean(), 1),
        "最小和值": int(sums.min()),
        "最大和值": int(sums.max()),
        "和值分佈": sums.value_counts().sort_index().to_dict(),
    }


def big_small_analysis(df, threshold=25):
    """
    大小號分析（預設 1-25 為小號，26-49 為大號）
    """
    cols = ["號碼1", "號碼2", "號碼3", "號碼4", "號碼5", "號碼6"]
    ratios = []
    for _, row in df.iterrows():
        nums = [int(row[c]) for c in cols]
        big = sum(1 for n in nums if n > threshold)
        small = 6 - big
        ratios.append(f"{big}大{small}小")
    return Counter(ratios)


def generate_summary(df):
    """
    產生完整分析摘要（供 Dashboard 使用）
    """
    if df.empty:
        return {}

    df = df.copy()
    df["開獎日期"] = pd.to_datetime(df["開獎日期"], errors="coerce")
    df = df.dropna(subset=["開獎日期"])

    summary = {
        "總期數": len(df),
        "最早日期": str(df["開獎日期"].min().date()),
        "最新日期": str(df["開獎日期"].max().date()),
        "全期頻率": frequency_analysis(df),
        "冷熱號_近30期": hot_cold_analysis(df, 30),
        "冷熱號_近50期": hot_cold_analysis(df, 50),
        "冷熱號_近100期": hot_cold_analysis(df, 100),
        "號碼間隔": interval_analysis(df),
        "月份分析": monthly_analysis(df),
        "季度分析": quarterly_analysis(df),
        "年度分析": yearly_analysis(df),
        "連號分析": consecutive_analysis(df),
        "奇偶分析": odd_even_analysis(df),
        "和值分析": sum_analysis(df),
        "大小號分析": big_small_analysis(df),
    }
    return summary


if __name__ == "__main__":
    from scraper import load_data
    df = load_data()
    if df.empty:
        print("⚠️  無資料，請先執行 scraper.py 匯入資料")
    else:
        summary = generate_summary(df)
        print(f"✅ 分析完成！共 {summary['總期數']} 期資料")
        print(f"   資料範圍：{summary['最早日期']} ~ {summary['最新日期']}")
        print(f"\n🔥 近50期熱號 Top 10：")
        for num, cnt in summary["冷熱號_近50期"]["熱號"]:
            print(f"   號碼 {num:2d}：出現 {cnt} 次")
        print(f"\n❄️  近50期冷號 Top 10：")
        for num, cnt in summary["冷熱號_近50期"]["冷號"]:
            print(f"   號碼 {num:2d}：出現 {cnt} 次")
