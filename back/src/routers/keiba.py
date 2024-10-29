# routers/keiba.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

keiba_router = APIRouter()

# フロントエンドからの入力モデル
class RaceRequest(BaseModel):
    racecourse: str
    count: str
    race_date: str
    race_num: str

# 競馬場コード対応表
racecourse_codes = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10"
}

# リンク生成とスクレイピング
@keiba_router.post("/race_result")
async def get_race_results(request: RaceRequest):
    racecourse_code = racecourse_codes.get(request.racecourse)
    if not racecourse_code:
        raise HTTPException(status_code=400, detail="無効な競馬場名です。")
    
    load_url = f"https://race.netkeiba.com/race/result.html?race_id=2024{racecourse_code}{request.count}{request.race_date}{request.race_num}&rf=race_list"
    response = requests.get(load_url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="レース結果ページにアクセスできません。")
    
    soup = BeautifulSoup(response.content, "html.parser")
    race_result = soup.find(id="tab_ResultSelect_1_con")
    if not race_result:
        raise HTTPException(status_code=404, detail="レース結果が見つかりませんでした。")

    result_table = race_result.find("tbody")

    def get_text(element):
        if (_cell := element.text.replace("\n", "")):
            return _cell
        elif element and (img := element.find("img")):
            return img.get("alt")
        else:
            return ""

    row_keys = ["rank", "waku", "horse_num", "name", "age", "weight", "jockey", "time", "sa", "ninki", "odds"]
    rows = [row.find_all("td") for row in result_table.find_all("tr")]
    result = [dict(zip(row_keys, map(get_text, row))) for row in rows]
    return result