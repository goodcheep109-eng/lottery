"""
台灣大樂透 歷史開獎資料爬蟲
資料來源：台灣彩券官方 API
API: https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto649Result
"""

import requests
import pandas as pd
import os
import time
import urllib3
from datetime import datetime

# 關閉 SSL 憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "lotto649.csv")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

API_URL = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto649Result"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.taiwanlottery.com/",
    "Origin": "https://www.taiwanlottery.com",
}


def fetch_month(year, month):
    """抓取單月開獎資料"""
    month_str = f"{year}-{month:02d}"
    params = {
        "period": "",
        "month": month_str,
        "endMonth": month_str,
        "pageNum": 1,
        "pageSize": 20,
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        data = resp.json()
        if data.get("rtCode") != 0:
            return []
        items = data.get("content", {}).get("lotto649Res", [])
        records = []
        for item in items:
            nums = item.get("drawNumberSize", [])
            if len(nums) < 7:
                continue
            # drawNumberSize: [號碼1~6排序後, 特別號]
            lottery_date = item.get("lotteryDate", "")[:10]
            period = str(item.get("period", ""))
            records.append({
                "期別": period,
                "開獎日期": lottery_date,
                "號碼1": nums[0],
                "號碼2": nums[1],
                "號碼3": nums[2],
                "號碼4": nums[3],
                "號碼5": nums[4],
                "號碼6": nums[5],
                "特別號": nums[6],
            })
        return records
    except Exception as e:
        return []


def fetch_history(start_year=2013, end_year=None):
    """抓取歷史開獎資料（API 支援第四屆起，約 2013 年）"""
    if end_year is None:
        end_year = datetime.now().year

    all_records = []
    for year in range(start_year, end_year + 1):
        year_records = []
        end_month = 12 if year < end_year else datetime.now().month
        for month in range(1, end_month + 1):
            records = fetch_month(year, month)
            year_records.extend(records)
            time.sleep(0.15)
        all_records.extend(year_records)
        print(f"  ✓ {year} 年：抓到 {len(year_records)} 筆")

    return all_records


def save_data(df):
    """儲存資料到 CSV"""
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ 資料已儲存：{DATA_FILE}（共 {len(df)} 筆）")


def load_data():
    """載入本地 CSV 資料"""
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    df["開獎日期"] = pd.to_datetime(df["開獎日期"], errors="coerce")
    return df


def update_data():
    """智慧更新：只抓缺少的月份"""
    existing = load_data()
    current_year = datetime.now().year
    current_month = datetime.now().month

    if existing.empty:
        print("📥 首次匯入，抓取歷史資料（2013 年至今）...")
        print("   （台灣彩券 API 支援第四屆起，約 2013 年開始）")
        records = fetch_history(2013, current_year)
    else:
        last_date = existing["開獎日期"].max()
        if pd.isna(last_date):
            start_year, start_month = 2013, 1
        else:
            start_year = last_date.year
            start_month = last_date.month

        print(f"🔄 更新資料，從 {start_year}/{start_month:02d} 開始補抓...")
        records = []
        for year in range(start_year, current_year + 1):
            sm = start_month if year == start_year else 1
            em = 12 if year < current_year else current_month
            for month in range(sm, em + 1):
                r = fetch_month(year, month)
                records.extend(r)
                time.sleep(0.15)
            print(f"  ✓ {year} 年更新完成")

    if not records and existing.empty:
        print("⚠️  未抓到任何資料")
        return pd.DataFrame()

    if records:
        new_df = pd.DataFrame(records)
        new_df["開獎日期"] = pd.to_datetime(new_df["開獎日期"], errors="coerce")
        if not existing.empty:
            df = pd.concat([existing, new_df]).drop_duplicates(subset=["期別"]).sort_values("開獎日期").reset_index(drop=True)
        else:
            df = new_df.sort_values("開獎日期").reset_index(drop=True)
        save_data(df)
        return df
    else:
        return existing


if __name__ == "__main__":
    print("🎰 台灣大樂透資料爬蟲")
    print("=" * 40)
    df = update_data()
    if not df.empty:
        print(f"\n最新 5 筆開獎紀錄：")
        print(df.tail(5).to_string(index=False))
