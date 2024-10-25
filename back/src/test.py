import requests
from bs4 import BeautifulSoup

load_url = "https://www.jra.go.jp/JRADB/accessS.html?CNAME=pw01sde1008202405061120241020/ED"
html = requests.get(load_url)
soup = BeautifulSoup(html.content, "html.parser")

# print(soup.find("tbody").text)
race_result = soup.find(id="race_result")
result_table = race_result.find("tbody")

# for tr in result_table.find_all("tr"):
#     saerch_td = tr.find_all("td")[:8]
#     for td in saerch_td:
#         print(td.text)
#     print("***********")

# datas = []

# for tr in result_table.find_all("tr"):
#     data = {}
#     for search_td in tr.find_all("td")[:8]:
#         data[search_td.text] = search_td.parent.findNext("td").text.strip()
#     datas.append(data)

# print(datas)


def get_text(element):
  if(_cell:=element.text.replace("\n", "")):
    return _cell
  elif (element is not None and (img:=element.find("img"))):
    return img.get("alt")
  else:
    return ""

row_keys = ["rank", "waku", "horse_num", "name", "age", "weight", "jockey", "time"]
rows = [row.find_all("td") for row in result_table.find_all("tr")]
result = [dict(zip(row_keys, map(get_text, row))) for row in rows]

print(result)

# {key : value}