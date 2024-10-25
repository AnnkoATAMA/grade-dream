import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup


app = FastAPI()

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
@app.post("/race_result")
async def get_race_results(request: RaceRequest):
    racecourse_code = racecourse_codes.get(request.racecourse)
    if not racecourse_code:
        raise HTTPException(status_code=400, detail="無効な競馬場名です。")
    
    load_url = f"https://race.netkeiba.com/race/result.html?race_id=2024{racecourse_code}{request.count}{request.race_date}{request.race_num}&rf=race_list"
    print(load_url)
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

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
