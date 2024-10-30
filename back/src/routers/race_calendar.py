from time import sleep
from urllib import parse
from selenium.webdriver.common.by import By

def parse_url(url, search_s):
    parsed_url = parse.urlparse(url)
    params = parse.parse_qs(parsed_url.query)
    target = params.get(search_s, [None])[0]
    return target

def get_kaisai_date(driver, year, month):
    url = f"/calendar.html?year={year}&month={month}"
    driver.get(url)
    sleep(2)
    CalendarSelectMenu = driver.find_element(by=By.CLASS_NAME, value="CalendarSelectMenu")
    Race_Calendar_Main = CalendarSelectMenu.find_element(by=By.CLASS_NAME, value="Race_Calendar_Main")
    RaceCellBoxes = Race_Calendar_Main.find_elements(by=By.CLASS_NAME, value="RaceCellBox")
    ancs = []
    for RaceCellBox in RaceCellBoxes:
        _a = RaceCellBox.find_elements(by=By.TAG_NAME, value="a")
        if len(_a) == 1:
            ancs.append(_a[0].get_attribute("href"))
    kaisai_dates = [parse_url(anc, "kaisai_date") for anc in ancs]
    return kaisai_dates