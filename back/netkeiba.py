import requests
from bs4 import BeautifulSoup
import time
import csv
#取得開始年
year_start = 2024
#取得終了年
year_end = 2025

for year in range(year_start, year_end):
    race_data_all = []
    #取得するデータのヘッダー情報を先に追加しておく
    race_data_all.append(['race_id','馬','騎手','馬番','走破時間','オッズ','通過順','着順','体重','体重変化','性','齢','斤量','上がり','人気','レース名','日付','開催','クラス','芝・ダート','距離','回り','馬場','天気','場id','場名'])
    List=[]
    #競馬場
    l=["01"]
    for w in range(len(l)):
        place = ""
        if l[w] == "01":
            place = "札幌"
        # elif l[w] == "02":
        #     place = "函館"
        # elif l[w] == "03":
        #     place = "福島"
        # elif l[w] == "04":
        #     place = "新潟"
        # elif l[w] == "05":
        #     place = "東京"
        # elif l[w] == "06":
        #     place = "中山"
        # elif l[w] == "07":
        #     place = "中京"
        # elif l[w] == "08":
        #     place = "京都"
        # elif l[w] == "09":
        #     place = "阪神"
        # elif l[w] == "10":
        #     place = "小倉"

        #開催回数分ループ（6回）
        for z in range(7):
            continueCounter = 0  # 'continue'が実行された回数をカウントするためのカウンターを追加
            #開催日数分ループ（12日）
            for y in range(13):
                race_id = ''
                if y<9:
                    race_id = str(year)+l[w]+"0"+str(z+1)+"0"+str(y+1)
                    url1="https://db.netkeiba.com/race/"+race_id
                else:
                    race_id = str(year)+l[w]+"0"+str(z+1)+str(y+1)
                    url1="https://db.netkeiba.com/race/"+race_id
                #yの更新をbreakするためのカウンター
                yBreakCounter = 0
                #レース数分ループ（12R）
                for x in range(12):
                    if x<9:
                        url=url1+str("0")+str(x+1)
                        current_race_id = race_id+str("0")+str(x+1)
                    else:
                        url=url1+str(x+1)
                        current_race_id = race_id+str(x+1)
                    try:
                        r=requests.get(url)
                    #リクエストを投げすぎるとエラーになることがあるため
                    #失敗したら10秒待機してリトライする
                    except requests.exceptions.RequestException as e:
                        print(f"Error: {e}")
                        print("Retrying in 10 seconds...")
                        time.sleep(10)  # 10秒待機
                        r=requests.get(url)
                    #バグ対策でdecode
                    soup = BeautifulSoup(r.content.decode("euc-jp", "ignore"), "html.parser")
                    soup_span = soup.find_all("span")
                    #馬の数
                    allnum=(len(soup_span)-6)/3
                    #urlにデータがあるか判定
                    if allnum < 1:
                        yBreakCounter+=1
                        print('continue: ' + url)
                        continue
                    allnum=int(allnum)
                    race_data = []
                    for num in range(allnum):
                        #馬の情報
                        soup_txt_l=soup.find_all(class_="txt_l")
                        soup_txt_r=soup.find_all(class_="txt_r")
                        #走破時間
                        runtime=''
                        try:
                            runtime=soup_txt_r[2+5*num].contents[0]
                        except IndexError:
                            runtime = ''
                        soup_nowrap = soup.find_all("td",nowrap="nowrap",class_=None)
                        #通過順
                        pas = ''
                        try:
                            pas = str(soup_nowrap[3*num].contents[0])
                        except:
                            pas = ''
                        weight = 0
                        weight_dif = 0
                        #体重
                        var = soup_nowrap[3*num+1].contents[0]
                        try:
                            weight = int(var.split("(")[0])
                            weight_dif = int(var.split("(")[1][0:-1])
                        except ValueError:
                            weight = 0
                            weight_dif = 0
                        weight = weight
                        weight_dif = weight_dif

                        soup_tet_c = soup.find_all("td",nowrap="nowrap",class_="txt_c")
                        #上がり
                        last = ''
                        try:
                            last = soup_tet_c[6*num+3].contents[0].contents[0]
                        except IndexError:
                            last = ''
                        #人気
                        pop = ''
                        try:
                            pop = soup_span[3*num+10].contents[0]
                        except IndexError:
                            pop = ''
                        
                        #レースの情報
                        try:
                            var = soup_span[8]
                            sur=str(var).split("/")[0].split(">")[1][0]
                            rou=str(var).split("/")[0].split(">")[1][1]
                            dis=str(var).split("/")[0].split(">")[1].split("m")[0][-4:]
                            con=str(var).split("/")[2].split(":")[1][1]
                            wed=str(var).split("/")[1].split(":")[1][1]
                        except IndexError:
                            try:
                                var = soup_span[7]
                                sur=str(var).split("/")[0].split(">")[1][0]
                                rou=str(var).split("/")[0].split(">")[1][1]
                                dis=str(var).split("/")[0].split(">")[1].split("m")[0][-4:]
                                con=str(var).split("/")[2].split(":")[1][1]
                                wed=str(var).split("/")[1].split(":")[1][1]
                            except IndexError:
                                var = soup_span[6]
                                sur=str(var).split("/")[0].split(">")[1][0]
                                rou=str(var).split("/")[0].split(">")[1][1]
                                dis=str(var).split("/")[0].split(">")[1].split("m")[0][-4:]
                                con=str(var).split("/")[2].split(":")[1][1]
                                wed=str(var).split("/")[1].split(":")[1][1]
                        soup_smalltxt = soup.find_all("p",class_="smalltxt")
                        detail=str(soup_smalltxt).split(">")[1].split(" ")[1]
                        date=str(soup_smalltxt).split(">")[1].split(" ")[0]
                        clas=str(soup_smalltxt).split(">")[1].split(" ")[2].replace(u'\xa0', u' ').split(" ")[0]
                        title=str(soup.find_all("h1")[1]).split(">")[1].split("<")[0]

                        race_data = [
                            current_race_id,
                            soup_txt_l[4*num].contents[1].contents[0],#馬の名前
                            soup_txt_l[4*num+1].contents[1].contents[0],#騎手の名前
                            soup_txt_r[1+5*num].contents[0],#馬番
                            runtime,#走破時間
                            soup_txt_r[3+5*num].contents[0],#オッズ,
                            pas,#通過順
                            num+1,#着順
                            weight,#体重
                            weight_dif,#体重変化
                            soup_tet_c[6*num].contents[0][0],#性
                            soup_tet_c[6*num].contents[0][1],#齢
                            soup_tet_c[6*num+1].contents[0],#斤量
                            last,#上がり
                            pop,#人気,
                            title,#レース名
                            date,#日付
                            detail,
                            clas,#クラス
                            sur,#芝かダートか
                            dis,#距離
                            rou,#回り
                            con,#馬場状態
                            wed,#天気
                            w,#場
                            place]
                        race_data_all.append(race_data)
                    
                    print(detail+str(x+1)+"R")#進捗を表示
                    
                if yBreakCounter == 12:#12レース全部ない日が検出されたら、その開催中の最後の開催日と考える
                    break
    #1年毎に出力
    #出力先とファイル名は修正してください
    with open('data/'+str(year)+'.csv', 'w', newline='',encoding="SHIFT-JIS") as f:
        csv.writer(f).writerows(race_data_all)
    print("終了")