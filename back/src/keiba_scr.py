import datetime
import itertools
import re
import time
from typing import Dict, List, Union

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import relativedelta
from tqdm import tqdm

from base import SoupScraperBase


class NetkeibaSoupScraperBase(SoupScraperBase):
    '''Netkeibaの静的サイトのスクレイピングに使うベースクラス'''

    def __init__(self, base_url: str, user_id: str = None, password: str = None):
        """
        Parameters
        ----------
        base_url : str
            対象ページのURL。レースIDによって制御できる形式にする。
        user_id : str, default None
            ログインする場合に指定するユーザID
        password : str, default None
            ログインする場合に指定するパスワード
        """
        url, info = None, None
        if (user_id is not None) and (password is not None):
            url = "https://regist.netkeiba.com/account/?pid=login&action=auth"
            info = {'login_id': user_id, 'pswd': password}
        super().__init__(login_url=url, login_info=info)
        self.base_url = base_url
        self.soup = None
        self.race_id = None

    def get_soup(self, race_id: Union[str, int]):
        """ページの情報をBeautifulSoup形式で保持する。

        Parameters
        ----------
        race_id : str or int
            8桁のレースID
        """
        self.soup = self._get_soup(
            self.base_url.format(race_id), encoding='EUC-JP')
        self.race_id = race_id
        return self.soup

class DatabaseScraper(NetkeibaSoupScraperBase):
    '''入力されたレースIDに従ってNetkeibaのDatabaseページから情報を取得するクラス'''
    MAIN_DF_COLUMNS = [
        '着順', '枠番', '馬番', '性齢', '斤量', 'タイム',
        '上り', '単勝', '人気', '馬体重', '賞金(万円)']
    PLEMIUS_COLUMNS = ['ﾀｲﾑ指数', '調教ﾀｲﾑ', '厩舎ｺﾒﾝﾄ', '備考']
    RACECOURSE_DICT = {
        1: '札幌', 2: '函館', 3: '福島', 4: '新潟', 5: '東京',
        6: '中山', 7: '中京', 8: '京都', 9: '阪神', 10: '小倉'}

    def __init__(self, user_id=None, password=None):
        super().__init__(
            base_url="https://db.netkeiba.com/race/{}",
            user_id=user_id, password=password)

    def get_main_df(self, race_id: Union[int, str] = None) -> pd.DataFrame:
        """馬ごとの情報をスクレイピングする"""
        if race_id is not None:
            self.get_soup(race_id)
        assert self.soup is not None
        rows = self.soup.find(
            'table', attrs={"class": "race_table_01"}).find_all('tr')
        data = [[col.text.replace('\n', '') for col in row.findAll(
            ['td', 'th'])] for row in rows]
        cols = self.MAIN_DF_COLUMNS + \
            self.PLEMIUS_COLUMNS if self.login else self.MAIN_DF_COLUMNS
        main_df = pd.DataFrame(data[1:], columns=data[0])[cols]
        main_df['race_id'] = self.race_id
        main_df['horse_id'] = self.__get_horse_id_list()
        main_df['jockey_id'] = self.__get_jockey_id_list()
        main_df['trainer_id'] = self.__get_trainer_id_list()
        main_df['owner_id'] = self.__get_owner_id_list()
        return main_df

    def __get_horse_id_list(self) -> List[int]:
        """DataBaseページに掲載されている馬のIDリストを取得する"""
        return self.__get_id_list('horse')

    def __get_jockey_id_list(self) -> List[int]:
        """DataBaseページに掲載されている騎手のIDリストを取得する"""
        return self.__get_id_list('jockey')

    def __get_trainer_id_list(self) -> List[int]:
        """DataBaseページに掲載されている調教師のIDリストを取得する"""
        return self.__get_id_list('trainer')

    def __get_owner_id_list(self) -> List[int]:
        """DataBaseページに掲載されている馬主のIDリストを取得する"""
        return self.__get_id_list_from_col(19)

    def __get_id_list(self, id_type: str) -> List[str]:
        atag_list = self.soup.find("table", attrs={"summary": "レース結果"}).find_all(
            "a", attrs={"href": re.compile(f"^/{id_type}")})
        id_list = [re.findall(r"\d+", atag["href"])[0] for atag in atag_list]
        return id_list

    def __get_id_list_from_col(self, col_idx: int) -> List[str]:
        id_list = list()
        tr_list = self.soup.find(
            'table', attrs={'class': 'race_table_01'}).find_all('tr')[1:]
        for tr in tr_list:
            atag = tr.find_all('td')[col_idx].find('a')
            if atag is None:
                id_list.append('')
            else:
                id_list.append(re.findall(r"\d+", atag["href"])[0])
        return id_list

    def get_race_info(self, race_id: Union[int, str] = None) -> dict:
        """レースの基本情報を取得する"""
        if race_id is not None:
            self.get_soup(race_id)
        assert self.soup is not None
        info = {'race_id': int(self.race_id)}
        # レース情報のスクレイピング
        race_name = self.soup.find(
            "dl", attrs={"class": "racedata fc"}).find('h1').text
        data_intro = self.soup.find(
            "div", attrs={"class": "data_intro"}).find_all("p")
        # 情報の整理
        info.update(self.__parse_racename(race_name))
        info.update(self.__parse_race_id(self.race_id))
        info.update(self.__parse1(data_intro[0].find("span").text))
        info.update(self.__parse2(data_intro[1].text))
        return info

    def __defaultfind(self, pattern, s, default=''):
        cont = re.findall(pattern, s)
        if len(cont) > 0:
            return cont[0]
        return default

    def __parse_racename(self, race_name: str):
        gn = self.__defaultfind("\(G\d\)", race_name)
        d = {'G123': '-'}
        if '1' in gn:
            d['G123'] = 'G1'
        elif '2' in gn:
            d['G123'] = 'G2'
        elif '3' in gn:
            d['G123'] = 'G3'
        return d

    def __parse_race_id(self, race_id: Union[str, int]):
        d = dict()
        d['馬場'] = self.RACECOURSE_DICT[int(str(race_id)[4:6])]
        d['開催'] = int(str(race_id)[6:8])
        d['N日目'] = int(str(race_id)[8:10])
        d['Nレース目'] = int(str(race_id)[10:12])
        return d

    def __parse1(self, text: str):
        d = dict()
        d['レース種別'] = self.__defaultfind('[ダ芝障]', text)
        d['周回方向'] = self.__defaultfind('[左右]', text, '無')
        d['コース長'] = int(self.__defaultfind(
            '\d{3,4}m', text, default='-1 ')[:-1])
        d['天気'] = self.__defaultfind('[晴曇雨小雪]{1,2}', text)
        d['コース状態'] = self.__defaultfind('[良稍重不]{1,2}', text)
        d['出走時間'] = self.__defaultfind('\d{2}:\d{2}', text)
        return d

    def __parse2(self, text: str):
        d = {'年': '', '月': '', '日': ''}
        cont = self.__defaultfind('\d{4}年\d{1,2}月\d{1,2}日', text, default=None)
        if cont is not None:
            date = datetime.datetime.strptime(cont, '%Y年%m月%d日')
            d['日付'] = datetime.datetime.strftime(date, '%Y-%m-%d')
            d['年'] = date.year
            d['月'] = date.month
            d['日'] = date.day
        pattern = '|'.join(['[新馬未勝利出走オープン]{2,4}', '\d+万', '\d勝クラス'])
        d['レースランク'] = self.__defaultfind(pattern, text)
        d['地方'] = self.__defaultfind('[特指]{1,2}', text, default='無')
        d['外国'] = self.__defaultfind('[国際混]{1,2}', text, default='無')
        d['条件'] = self.__defaultfind('[ハンデ馬齢別定量]{2,3}', text, default='無')
        return d

    def get_pay_df(self, race_id: Union[int, str] = None) -> pd.DataFrame:
        """レースの払い戻し情報を取得する"""
        if race_id is not None:
            self.get_soup(race_id)
        assert self.soup is not None
        tables = self.soup.find_all('table', attrs={"class": "pay_table_01"})
        rows = tables[0].find_all('tr') + tables[1].find_all('tr')
        data = [[re.sub(r"\<.+?\>", "", str(col).replace('<br/>', 'br')).replace(
            '\n', '') for col in row.findAll(['td', 'th'])] for row in rows]
        pay_df = pd.DataFrame(data)
        cols = ['券種', '馬番号', '払戻', '人気']
        l = list()
        for row in pay_df.values:
            for i in range(len(row[1].split('br'))):
                d = {'race_id': self.race_id}
                for col_idx, key in enumerate(cols):
                    if key == '券種':
                        d[key] = row[col_idx].split('br')[0]
                    else:
                        d[key] = row[col_idx].split('br')[i]
                l.append(d)
        return pd.DataFrame(l)

    def get_corner_df(self, race_id: Union[int, str] = None):
        if race_id is not None:
            self.get_soup(race_id)
        assert self.soup is not None
        df = pd.read_html(
            str(self.soup.find('table', attrs={"summary": 'コーナー通過順位'})))[0]
        df.columns = ['コーナー', '通過順']
        return df

    def get_laptime_df(self, race_id: Union[int, str] = None):
        if race_id is not None:
            self.get_soup(race_id)
        assert self.soup is not None
        df = pd.read_html(
            str(self.soup.find('table', attrs={"summary": 'ラップタイム'})))[0].T
        df.columns = ['ラップ', 'ペース']
        df = df.iloc[1:].reset_index(drop=True)
        return df


    '''過去の情報を含まずに、今回のレース情報だけを馬柱から抽出する。
    DatabaseScraperのmain_dfなどと照合できるようにレースIDと馬番号だけは残し、
    main_dfやrace_infoなどに含まれている情報は抽出しない。
    '''

    def __init__(self):
        super().__init__(login_url=None, login_info=None)
        self.base_url = 'http://jiro8.sakura.ne.jp/index.php?code={}'
        self.cols = [
            'race_id', '馬番', 'ペース脚質3F', 'コーナー順位',
            '先行指数', 'ペース指数', '上がり指数', 'スピード指数',
            '本紙)独自指数', 'SP指数補正後']

    def get_umabashira(self, race_id: Union[str, int]) -> pd.DataFrame:
        code = str(race_id)[2:]
        soup = self._get_soup(self.base_url.format(code))
        table = soup.find('table', attrs={"class": 'c1'})
        df = pd.read_html(str(table))[0]
        df = df.T.iloc[:-1, :20]
        df.columns = [
            '枠番', '馬番', '馬名', '性齢', '斤量', '騎手', '調教師', '着順',
            'オッズ(人気)', 'タイム', 'ペース脚質3F', 'コーナー順位', '体重(増減)',
            '先行指数', 'ペース指数', '上がり指数', 'スピード指数',
            '本紙)独自指数', 'SP指数補正後', '前走の指数']
        df['race_id'] = race_id
        return df[self.cols].copy

class RaceidScraper(NetkeibaSoupScraperBase):
    def __init__(self):
        super().__init__(base_url="https://db.netkeiba.com/race/list/{}")

    def get_raceID_list_from_date(self, date: datetime.date) -> List[int]:
        """指定した日付に開催されたレースのレースID

        Parameters
        ----------
        date : datetime.date
            レースIDを取得する日付。
            直近1週間だとレース情報が存在しない可能性があるため警告が表示される。

        Returns
        -------
        List[str]
            レースIDのリスト
        """
        # today = datetime.datetime.today()
        # assert date <= today, '未来の日付が入力されています'
        # oneweekago = today - datetime.timedelta(days=7)
        # if oneweekago < date <= today:
        #     warnings.warn('直近のレースは情報が更新されていない場合があります')
        date = f'{date.year:04}{date.month:02}{date.day:02}'
        self.get_soup(date)
        race_list = self.soup.find('div', attrs={"class": 'race_list fc'})
        if race_list is None:
            return list()
        a_tag_list = race_list.find_all('a')
        href_list = [a_tag.get('href') for a_tag in a_tag_list]
        race_id_list = list()
        for href in href_list:
            for s in re.findall('[0-9]{12}', href):
                race_id_list.append(int(s))
        return list(set(race_id_list))
