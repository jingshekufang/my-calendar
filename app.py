import streamlit as st
from streamlit_calendar import calendar
from lunarcalendar import Converter, Solar
from github import Github
import datetime
import json
import base64

# --- 設定區 ---
PAGE_TITLE = "📅 正覺精舍齋堂排程 (GitHub版)"
ADMIN_PASSWORD = "1234"

# 這裡需要您的 GitHub 資訊
# 為了安全，實際上傳到雲端時，建議把這些放在 st.secrets 裡
# 但為了您測試方便，您可以先填在這裡，或者等等教您設 Secrets
GITHUB_TOKEN = st.secrets["github_token"] 
REPO_NAME = st.secrets["repo_name"] # 格式： "您的帳號/倉庫名稱"
DATA_FILE = "events.json" # 我們要把資料存在這個檔案裡

st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# --- GitHub 存取功能 ---

def get_repo():
    """連線到 GitHub 倉庫"""
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

def get_data_from_github():
    """從 GitHub 讀取 JSON 檔案"""
    try:
        repo = get_repo()
        # 嘗試讀取檔案
        contents = repo.get_contents(DATA_FILE)
        # GitHub 回傳的是 Base64 編碼，要解碼
        json_str = base64.b64decode(contents.content).decode("utf-8")
        return json.loads(json_str), contents.sha
    except:
        # 如果檔案不存在，回傳空清單
        return [], None

def update_github_file(new_data, sha=None):
    """把新的資料寫回 GitHub"""
    repo = get_repo()
    json_str = json.dumps(new_data, ensure_ascii=False, indent=4)
    
    if sha:
        # 如果檔案存在，就更新 (Update)
        repo.update_file(DATA_FILE, "Update calendar events", json_str, sha)
    else:
        # 如果檔案不存在，就建立 (Create)
        repo.create_file(DATA_FILE, "Initial calendar events", json_str)

# --- 資料庫操作 (CRUD) ---

def add_event(date, task, description):
    # 1. 先讀取舊資料
    current_data, sha = get_data_from_github()
    
    # 2. 準備新的一筆資料
    new_item = {
        "id": str(datetime.datetime.now().timestamp()), # 用時間當 ID
        "date": str(date),
        "task": task,
        "description": description
    }
    
    # 3. 加入清單
    current_data.append(new_item)
    
    # 4. 寫回 GitHub
    update_github_file(current_data, sha)

def delete_event(target_id):
    current_data, sha = get_data_from_github()
    
    # 過濾掉要刪除的 ID
    new_data = [item for item in current_data if item["id"] != target_id]
    
    update_github_file(new_data, sha)

# --- 農曆轉換 (維持不變) ---
def get_lunar_events(year_start, year_end):
    lunar_events_list = []
    start_date = datetime.date(year_start, 1, 1)
    end_date = datetime.date(year_end, 12, 31)
    delta = datetime.timedelta(days=1)
    
    current_date = start_date
    while current_date <= end_date:
        solar = Solar(current_date.year, current_date.month, current_date.day)
        lunar = Converter.Solar2Lunar(solar)
        
        if lunar.day == 1:
            lunar_text = f"🌑{lunar.month}月"
        else:
            chinese_num = ["", "初", "二十", "三十"]
            digits = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
            if lunar.day <= 10:
                lunar_text = f"初{digits[lunar.day]}"
            elif lunar.day < 20:
                lunar_text = f"十{digits[lunar.day - 10]}"
            elif lunar.day == 20:
                lunar_text = "二十"
            elif lunar.day < 30:
                lunar_text = f"廿{digits[lunar.day - 20]}"
            elif lunar.day == 30:
                lunar_text = "三十"
            else:
                lunar_text = str(lunar.day)

        lunar_events_list.append({
            "title": lunar_text,
            "start": current_date.isoformat(),
            "allDay": True,
            "backgroundColor": "#ffffff",
            "borderColor": "#ffffff",
            "textColor": "#aaaaaa",
            "display": "block"
        })
        current_date += delta
    return lunar_events_list

# --- 介面開始 ---
st.title(PAGE_TITLE)

# 讀取資料 (放在這裡全域使用)
# 為了避免每次操作都讀取 GitHub (比較慢)，Streamlit 會自動重跑 script
try:
    events_data, _ = get_data_from_github()
except Exception as e:
    st.error(f"GitHub 連線失敗，請檢查 Token 或 Repository 名稱。\n錯誤: {e}")
    events_data = []

col1, col2 = st.columns([1, 2])

# --- 左邊：操作區 ---
with col1:
    st.subheader("管理區")
    password = st.text_input("輸入密碼管理事項", type="password")
    is_admin = (password == ADMIN_PASSWORD)

    if is_admin:
        st.success("已解鎖編輯模式")
        with st.form("my_form"):
            new_date = st.date_input("日期", datetime.date.today())
            new_task = st.text_input("標題")
            new_desc = st.text_area("詳細說明")
            
            submitted = st.form_submit_button("儲存 (寫入 GitHub)")
            
            if submitted:
                with st.spinner("正在連線 GitHub 儲存中..."):
                    add_event(new_date, new_task, new_desc)
                st.success(f"✅ 已儲存：{new_task}")
                st.rerun()
    else:
        st.info("訪客模式：只能瀏覽")

    st.divider()
    st.write("### 事項清單")
    
    # 倒序顯示
    if events_data:
        for item in reversed(events_data):
            e_id = item["id"]
            e_date = item["date"]
            e_task = item["task"]
            e_desc = item.get("description", "")
            
            with st.expander(f"{e_date} - {e_task}"):
                if e_desc:
                    st.info(e_desc)
                
                if is_admin:
                    if st.button("🗑️ 刪除", key=f"del_{e_id}", type="primary"):
                        with st.spinner("正在從 GitHub 刪除..."):
                            delete_event(e_id)
                        st.success("已刪除")
                        st.rerun()

# --- 右邊：月曆區 ---
with col2:
    st.subheader("月曆視圖")
    
    calendar_events = []
    if events_data:
        for item in events_data:
            calendar_events.append({
                "title": item["task"],
                "start": item["date"],
                "backgroundColor": "#3788d8",
                "borderColor": "#3788d8",
                "extendedProps": {"description": item.get("description", "")},
                "order": 1
            })

    today = datetime.date.today()
    lunar_events = get_lunar_events(today.year, today.year + 1)
    all_events = lunar_events + calendar_events

    calendar_options = {
        "locale": "zh-tw", 
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,listMonth"
        },
        "initialView": "dayGridMonth",
        "eventOrder": "start,-duration,allDay,title"
    }
    
    calendar(events=all_events, options=calendar_options)