from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from time import sleep
import requests
from bs4 import BeautifulSoup

calendar_router = APIRouter()

class DateRequest(BaseModel):
    selectedDate: str

@calendar_router.post("/date_result")
def get_kaisai_date(request: DateRequest):
    selectedDate = request.selectedDate
    print(selectedDate)
    year, month, date = selectedDate.split("-")
    url = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"
    print(url)
    sleep(2)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tbody_tag = soup.find(class_ = "Calendar_Table")
    a_tag = tbody_tag.find_all('a')
    kaisai_date = a_tag.find(href = f"../top/race_list.html?kaisai_date={year}{month}{date}")
    print(kaisai_date)
    if kaisai_date:
        return {"url": kaisai_date['href'], "text": kaisai_date.text.strip()}
    else:
        raise HTTPException(status_code=404, detail="指定された日付の開催データが見つかりませんでした。")
