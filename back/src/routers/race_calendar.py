from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from time import sleep
import requests
from bs4 import BeautifulSoup

calendar_router = APIRouter()

class DateRequest(BaseModel):
    racecourse: str
    selectedDate: str
    race_num:str

# 競馬場コード対応表
racecourse_codes = {
    "札幌": "01", "函館": "02", "福島": "03", "新潟": "04",
    "東京": "05", "中山": "06", "中京": "07", "京都": "08",
    "阪神": "09", "小倉": "10"
}

@calendar_router.post("/date_result")
def get_kaisai_date_url(request: DateRequest):
    racecourse_code = racecourse_codes.get(request.racecourse)
    selectedDate = request.selectedDate
    race_num = request.race_num + "R"
    print(f"Selected Date: {selectedDate}")
    year, month, date = selectedDate.split("-")
    url = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"
    header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
    print(f"URL: {url}")
    sleep(2)

    response = requests.get(url, headers=header)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="データ取得に失敗しました。")
    
    soup = BeautifulSoup(response.content, "html.parser")

    kaisai_date = None
    for a in soup.find_all('a'):
        # sleep(1)
        if f"../top/race_list.html?kaisai_date={year}{month}{date}" in a.get('href'):
            kaisai_date = a
            break

    if kaisai_date:
        print(kaisai_date)
        load_list_url = kaisai_date['href']
        load_list_url = load_list_url.replace("../top/race_list.html?", "https://race.sp.netkeiba.com/?pid=race_list&")+ f"&jyo_cd={racecourse_code}"
    else:
        print(kaisai_date)
        raise HTTPException(status_code=404, detail="指定された日付の開催データが見つかりませんでした。")

    print(load_list_url)
    responses = requests.get(load_list_url, headers=header)
    if responses.status_code != 200:
        raise HTTPException(status_code=500, detail="データ取得に失敗しました。")
    
    soup = BeautifulSoup(responses.content, "html.parser")

    for race_list in soup.find_all(class_ = "Race_Num Race_Fixed"):
        race_number = race_list.find("span")
        if race_number and race_number.text == race_num:
            race_id = race_list.find("span", class_="MyRaceCheck")["id"]
            race_code = race_id.replace("myrace_","")
            print(race_code)
            return race_code
