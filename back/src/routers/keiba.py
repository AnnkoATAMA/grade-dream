from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

from .race_calendar import DateRequest, get_kaisai_date_url

keiba_router = APIRouter()

class RaceRequest(BaseModel):
    racecourse: str
    selectedDate: str
    race_num: str


# リンク生成とスクレイピング
@keiba_router.post("/race_result")
def get_race_results_handler(request: RaceRequest):
    date_request = DateRequest(
        racecourse=request.racecourse,
        selectedDate=request.selectedDate,
        race_num=request.race_num
    )
    race_code = get_kaisai_date_url(date_request)
    # レース場のコードを計算
    if not (results := get_race_results(race_code)):
        raise HTTPException(status_code=404, detail="レース結果が見つかりませんでした。")
    return results

def get_race_results(race_code):
    load_url = f"https://race.netkeiba.com/race/result.html?race_id={race_code}&rf=race_list"
    header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
    response = requests.get(load_url,  headers=header)
    print(load_url)
    
    soup = BeautifulSoup(response.content, "html.parser")
    race_result = soup.find(id="tab_ResultSelect_1_con")
    

    if not race_result:
        print("レース結果が見つかりません (race_result is None).")
        return None

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