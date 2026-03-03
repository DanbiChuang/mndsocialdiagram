"""
社群網路拓撲圖 JSON 生成器
重構自 SigmaJSONGenerationGoogleColab.py，移除 Colab 依賴
"""
import json
import random
import uuid
import re
import os
from datetime import datetime

import google.generativeai as genai
from tavily import TavilyClient

# --- 1. 核心配置 (從環境變數讀取) ---
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3-pro-preview"

# genai.configure(api_key=GEMINI_API_KEY)  # 移除全局配置，改為動態
# tavily = TavilyClient(api_key=TAVILY_API_KEY)

# --- 2. 戰略資料庫 (Entity Library) ---

# [EVIL] 紅色供應鏈預設名單
EVIL_MEDIA_DEFAULTS = [
    "CCTV", "人民日報", "環球時報", "新華社", "解放軍報", "台海網",
    "大公報", "文匯報", "中評社", "旺報", "中國時報", "中時新聞網",
    "中天新聞", "哏傳媒", "海峽導報"
]

# [ANGEL] 友台防衛預設名單
ANGEL_MEDIA_DEFAULTS = [
    "MyGoPen", "Watchout(沃草)", "報導者", "德國之聲中文網", "美國之音中文網",
    "自由亞洲電台", "黑熊學院", "敏迪選讀", "矢板明夫俱樂部", "TaiwanPlus"
]

# [PARTY CONFIG] 政黨權重配置
EVIL_PARTY_WEIGHTS = {
    "names": ["中國國民黨", "親民黨", "新黨", "中華統一促進黨"],
    "weights": [34.58, 0.51, 0.29, 0.13]
}

ANGEL_PARTY_WEIGHTS = {
    "names": ["民主進步黨", "時代力量", "綠黨", "台灣基進", "台灣團結聯盟"],
    "weights": [36.16, 2.57, 0.85, 0.69, 0.31]
}

# [PLATFORM CONFIG] 平台白名單
CHINA_PLATFORMS = ["Weibo", "Tiktok", "中國抖音"]
GENERAL_PLATFORMS = ["X", "Instagram", "Facebook", "PTT", "YouTube", "Threads"]

STRATEGIC_PERSONA = """
你是中華民國國防部政治作戰局「心理作戰大隊」首席情報官。
任務：針對當前台海局勢，模擬各方勢力的「認知戰論述」與「媒體佈局」。
要求：
1. 嚴格區分立場：Evil (中共/協力), Angel (友台/澄清), Neutral (一般視角)。
2. 分析必須基於提供的搜尋情報，找出具體的媒體名稱。
"""

# --- 3. 第一階段：情報獵殺 ---
def get_realtime_intel(topic, tavily_api_key=None):
    api_key = tavily_api_key or TAVILY_API_KEY
    if not api_key:
        return "近期台海周邊軍事活動頻繁，網路流傳多種未經證實的撤僑與軍演訊息。"

    print(f"[*] 鎖定議題：{topic}，正在進行全網情報獵殺...")
    search_query = f"{topic} 媒體報導 評論 兩岸 認知作戰"
    try:
        client = TavilyClient(api_key=api_key)
        search_result = client.search(query=search_query, search_depth="advanced", max_results=10)
        context = "\n".join([f"- Source: {r['title']} ({r['url']})\n  Content: {r['content'][:150]}..." for r in search_result['results']])
        return context
    except Exception as e:
        print(f"[!] 搜尋失敗，使用預設背景: {e}")
        return "近期台海周邊軍事活動頻繁，網路流傳多種未經證實的撤僑與軍演訊息。"

# --- 4. 第二階段：Gemini 動態媒體與論述生成 ---
def generate_strategic_data(topic, context, gemini_api_key=None):
    api_key = gemini_api_key or GEMINI_API_KEY
    if not api_key:
        return {
            "detected_sources": [],
            "generic_narratives": {
                "evil": ["台灣當局倚美謀獨"], "angel": ["這是認知作戰"], "neutral": ["觀望中"]
            },
            "summary_analysis": "缺少 API Key，使用備用數據。"
        }

    print(f"[*] {MODEL_NAME} 正在進行媒體佈局分析與論述生成...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=STRATEGIC_PERSONA)
    # ... 其餘 logic 不變

    prompt = f"""
    情報背景：
    {context}

    目標議題：{topic}

    請完成兩項任務並回傳 JSON：
    1. **媒體識別與模擬**：根據情報背景或你的知識庫，列出 10-15 個可能參與此議題討論的「具體媒體/粉專名稱」。
       - 包含 Evil (中共官媒/在地協力)、Angel (國際/友台)、Neutral (主流媒體)。
       - 為每個媒體生成一條符合其風格的「特定報導標題」(headline)。
    2. **通用論述生成**：為大量水軍生成通用的短評 (Argument)。

    嚴格回傳 JSON 格式：
    {{
        "detected_sources": [
            {{ "name": "媒體名稱A", "standpoint": "evil", "headline": "該媒體的具體報導標題" }},
            {{ "name": "媒體名稱B", "standpoint": "angel", "headline": "該媒體的具體報導標題" }},
            ...
        ],
        "generic_narratives": {{
            "evil": ["水軍論述1", "水軍論述2", "水軍論述3"],
            "angel": ["澄清論述1", "澄清論述2", "澄清論述3"],
            "neutral": ["一般民眾論述1", "一般民眾論述2"]
        }},
        "summary_analysis": "針對此議題的認知戰攻防總結 (200字內)"
    }}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        raw_json = json_match.group(0) if json_match else text
        return json.loads(raw_json)
    except Exception as e:
        print(f"[!] 生成失敗: {e}")
        return {
            "detected_sources": [],
            "generic_narratives": {
                "evil": ["台灣當局倚美謀獨"], "angel": ["這是認知作戰"], "neutral": ["觀望中"]
            },
            "summary_analysis": "生成失敗，使用備用數據。"
        }

# --- 5. 第三階段：數據擴張與網路構建 (包含同溫層分配) ---
def build_influence_network(ai_data, topic, node_count=2000):
    nodes = []
    account_name_map = {}

    evil_authority_names = []
    angel_authority_names = []

    stats = {
        "all_cib": 0,
        "all_social_platforms": 0,
        "all_official_medias": 0
    }

    print(f"[*] 正在構建認知戰網絡，目標節點：{node_count}...")
    print(f"[*] 套用聲量與同溫層 (Community) 分配邏輯...")

    # --- A. 建立核心媒體 (Layer 0) ---
    detected_sources = ai_data.get("detected_sources", [])
    existing_names = set()

    def create_media_node(name, standpoint, headline):
        if name in existing_names: return

        vol = random.randint(150000, 400000)
        repost = random.randint(5000, 20000)
        node_id = f"Media@{name}"

        account_name_map[name] = node_id
        existing_names.add(name)

        if standpoint == "evil":
            evil_authority_names.append(name)
            community = str(random.randint(1, 3)) # Evil 媒體分配至 1-3 同溫層
        elif standpoint == "angel":
            angel_authority_names.append(name)
            community = str(random.randint(4, 6)) # Angel 媒體分配至 4-6 同溫層
        else:
            community = str(random.randint(7, 10)) # Neutral 分配至 7-10 鬆散層

        if standpoint == "evil":
            plat = random.choice(CHINA_PLATFORMS + GENERAL_PLATFORMS)
        else:
            plat = random.choice(GENERAL_PLATFORMS)

        node = {
            "id": node_id,
            "Community": community,
            "alert": True if standpoint == "evil" else False,
            "name": name,
            "symbolSize": 100,
            "category": 0,
            "info": {
                "social_platform": plat,
                "social_account": name,
                "category_name": "官方媒體/KOL",
                "role_attribute": "源頭",
                "standpoint": standpoint,
                "volume": vol,
                "be_reposted": repost,
                "social_narrative": headline,
                "party": "CCP" if standpoint == "evil" else ("Taiwan" if standpoint == "angel" else "Media"),
                "be_reposted_accounts": []
            }
        }
        nodes.append(node)
        stats["all_official_medias"] += vol
        stats["all_social_platforms"] += vol

    # 1. AI 偵測媒體
    for src in detected_sources:
        create_media_node(src['name'], src['standpoint'], src['headline'])

    # 2. 補足機制
    narratives = ai_data.get("generic_narratives", {})
    for name in EVIL_MEDIA_DEFAULTS:
        if name not in existing_names and random.random() < 0.5:
            headline = random.choice(narratives.get("evil", ["兩岸統一勢在必行"]))
            create_media_node(name, "evil", headline)
    for name in ANGEL_MEDIA_DEFAULTS:
        if name not in existing_names and random.random() < 0.5:
            headline = random.choice(narratives.get("angel", ["堅守民主防線"]))
            create_media_node(name, "angel", headline)

    # --- B. 建立傳播者與大眾 (Layer 1) ---
    evil_super_spreader_count = 0

    for i in range(node_count):
        is_spreader = random.random() < 0.3

        # 1. 決定立場
        rand_stand = random.random()
        if rand_stand < 0.35:
            standpoint = "evil"
            narrative = random.choice(narratives.get("evil", ["..."]))
            community = str(random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]) if is_spreader else str(random.randint(1, 3))
        elif rand_stand < 0.6:
            standpoint = "angel"
            narrative = random.choice(narratives.get("angel", ["..."]))
            community = str(random.choices([4, 5, 6], weights=[0.5, 0.3, 0.2])[0]) if is_spreader else str(random.randint(4, 6))
        else:
            standpoint = "neutral"
            narrative = random.choice(narratives.get("neutral", ["..."]))
            community = str(random.randint(7, 10))

        # 2. 決定類別與政黨
        category_name = "協同群" if is_spreader else "一般民眾"
        party_val = "N/A"

        if category_name == "協同群":
            if standpoint == "evil":
                party_val = random.choices(EVIL_PARTY_WEIGHTS["names"], weights=EVIL_PARTY_WEIGHTS["weights"])[0]
            elif standpoint == "angel":
                party_val = random.choices(ANGEL_PARTY_WEIGHTS["names"], weights=ANGEL_PARTY_WEIGHTS["weights"])[0]

        # 3. 決定平台
        if standpoint == "evil":
            if random.random() < 0.6:
                plat = random.choice(CHINA_PLATFORMS)
            else:
                plat = random.choice(GENERAL_PLATFORMS)
        elif standpoint == "angel":
            if random.random() < 0.03:
                plat = random.choice(CHINA_PLATFORMS)
            else:
                plat = random.choice(GENERAL_PLATFORMS)
        else:
            if random.random() < 0.07:
                plat = random.choice(CHINA_PLATFORMS)
            else:
                plat = random.choice(GENERAL_PLATFORMS)

        # 4. 聲量與轉發邏輯
        if is_spreader:
            if standpoint == "evil" and evil_super_spreader_count < 3:
                volume = random.randint(500000, 1200000)
                evil_super_spreader_count += 1
                be_reposted = int(volume * 0.5)
            else:
                volume = random.randint(10000, 150000)
                be_reposted = int(volume * random.uniform(0.1, 0.4))
            cat_id = 1
            stats["all_cib"] += volume
        else:
            volume = random.randint(100, 5000)
            be_reposted = random.randint(0, 500)
            cat_id = 2

        stats["all_social_platforms"] += volume

        # 5. 轉發目標生成
        repost_target_names = []
        if standpoint == "evil":
            if random.random() < 0.8 and evil_authority_names:
                count = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
                targets = random.sample(evil_authority_names, min(len(evil_authority_names), count))
                repost_target_names.extend(targets)
        elif standpoint == "neutral":
            if random.random() < 0.5 and evil_authority_names:
                repost_target_names.append(random.choice(evil_authority_names))
            elif random.random() < 0.2 and angel_authority_names:
                repost_target_names.append(random.choice(angel_authority_names))
        elif standpoint == "angel":
             if random.random() < 0.8 and angel_authority_names:
                repost_target_names.append(random.choice(angel_authority_names))

        uid = str(uuid.uuid4())[:8]
        user_account_name = f"u_{uid}"
        node_id = f"{plat}@{uid}"
        account_name_map[user_account_name] = node_id

        node = {
            "id": node_id,
            "Community": community,
            "alert": True if standpoint == "evil" else False,
            "name": f"User_{uid}",
            "symbolSize": 50 if is_spreader else 15,
            "category": cat_id,
            "info": {
                "social_platform": plat,
                "social_account": user_account_name,
                "category_name": category_name,
                "role_attribute": "傳播者" if is_spreader else "一般使用者",
                "standpoint": standpoint,
                "volume": volume,
                "be_reposted": be_reposted,
                "social_narrative": narrative,
                "attack_5d": "Distort" if standpoint == "evil" else "None",
                "party": party_val,
                "be_reposted_accounts": repost_target_names
            }
        }
        nodes.append(node)

    # --- C. 建立 Links ---
    print(f"[*] 正在生成連結 (Links)...")
    links = []
    for node in nodes:
        targets = node['info'].get('be_reposted_accounts', [])
        for target_name in targets:
            if target_name in account_name_map:
                links.append({
                    "source": account_name_map[target_name],
                    "target": node['id'],
                    "value": 1
                })

    return nodes, links, stats


def generate_social_graph(topic, node_count=2000, gemini_api_key=None, tavily_api_key=None):
    """
    主入口：給定議題，回傳完整 social_graph JSON dict
    """
    intel_context = get_realtime_intel(topic, tavily_api_key=tavily_api_key)
    ai_data = generate_strategic_data(topic, intel_context, gemini_api_key=gemini_api_key)
    nodes, links, stats = build_influence_network(ai_data, topic, node_count)
# ...

    return {
        "type": "social_graph",
        "observation_day": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": f"【預警】{topic} 認知戰網絡分析報告",
        "summary": ai_data.get('summary_analysis', '無摘要'),
        "all_cib": stats["all_cib"],
        "all_social_platforms": stats["all_social_platforms"],
        "all_official_medias": stats["all_official_medias"],
        "data": {
            "nodes": nodes,
            "links": links
        }
    }
