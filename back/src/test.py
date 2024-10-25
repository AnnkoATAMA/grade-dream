import requests
from bs4 import BeautifulSoup

load_url = "https://race.netkeiba.com/race/result.html?race_id=202408050611&rf=race_list"
html = requests.get(load_url)
soup = BeautifulSoup(html.content, "html.parser")

race_result = soup.find(id="tab_ResultSelect_1_con")
result_table = race_result.find("tbody")

def get_text(element):
  if(_cell:=element.text.replace("\n", "")):
    return _cell
  elif (element is not None and (img:=element.find("img"))):
    return img.get("alt")
  else:
    return ""

row_keys = ["rank", "waku", "horse_num", "name", "age", "weight", "jockey", "time", "sa", "ninki", "odds"]
rows = [row.find_all("td") for row in result_table.find_all("tr")]
result = [dict(zip(row_keys, map(get_text, row))) for row in rows]

print(result)
