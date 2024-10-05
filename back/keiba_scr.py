import datetime
import itertools
import re
import time
from typing import Dict, List, Union

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import relativedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from tqdm import tqdm

from .base import SeleniumScraperBase, SoupScraperBase


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


class UmabashiraScraper(object):
    '''入力されたレースIDに従って馬柱を取得するクラス'''

    def __init__(self):
        self.base_url = 'http://jiro8.sakura.ne.jp/index.php?code={}'

    def get_umabashira(self, race_id: Union[str, int]) -> pd.DataFrame:
        """馬柱情報をDataFrame形式で取得する。

        Parameters
        ----------
        race_id : str or int
            8桁のレースID
        """
        code = str(race_id)[2:]
        html = requests.get(self.base_url.format(code))
        html.encoding = 'cp932'
        dfs = pd.read_html(html.text)
        # TODO: 整形するコード書いておく
        return dfs[12]


class UmabashiraLimitedScraper(SoupScraperBase):
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
        return df[self.cols].copy()


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

    def get_monthly_raceID_list(self, year: int, month: int, sleep_time: float = 1, leave: bool = True) -> List[str]:
        """指定した年月、1ヶ月の間に開催された全レースのレースIDを取得する

        Parameters
        ----------
        year : int
        month : int
        sleep_time : float, default True
            スクレイピングの際1回ごとに発生する待機時間
        leave : bool, default True
            Falseを指定すると、終了したら進捗バーを消すようにできる

        Returns
        -------
        List[str]
            レースIDのリスト
        """
        today = datetime.date(year, month, 1)
        race_id_list = list()
        for _ in tqdm(range(31), leave=leave):
            race_id_list += self.get_raceID_list_from_date(today)
            today = today + relativedelta.relativedelta(days=1)
            time.sleep(sleep_time)
        return race_id_list

    def get_yearly_raceID_list(self, year, sleep_time, leave=True) -> list:
        race_id_list = list()
        for i in range(12):
            race_id_list += self.get_monthly_raceID_list(
                year, month=i+1, sleep_time=sleep_time, leave=leave)
        return race_id_list


class HorseResultsScraper(NetkeibaSoupScraperBase):
    '''馬の過去成績データをスクレイピングするクラス'''

    def __init__(self, user_id=None, password=None):
        super().__init__(
            base_url='https://db.netkeiba.com/horse/{}',
            user_id=user_id, password=password)

    def get_horseresults(self, horse_id):
        """
        Parameters:
        ----------
        horse_id : Union[str, int]
            馬ID

        Returns:
        ----------
        pandas.DataFrame
            馬の過去成績データのDataFrame
        """

        soup = self.get_soup(horse_id)
        table = soup.find('table', attrs={"class": "db_h_race_results"})
        df = pd.read_html(str(table), flavor="bs4")[0]
        columns = df.columns.values.tolist()
        new_columns = ['horse_id'] + columns
        df['horse_id'] = horse_id
        return df[new_columns]


class HorseDataScraper(SoupScraperBase):
    '''馬の情報をスクレイピングするクラス'''

    def get_sex(self, horse_id: Union[int, str]) -> str:
        """性別をスクレイピングするメソッド

        Parameters
        ----------
        horse_id : Union[int, str]
            _description_

        Returns
        -------
        str
            _description_
        """
        base_url = 'https://db.netkeiba.com/horse/{}/'
        soup = self._get_soup(base_url.format(horse_id), encoding='EUC-JP')
        s = soup.find('p', attrs={"class": "txt_01"})
        cont = re.findall('[セ牡牝]', s.text)
        assert len(cont) != 0, '性別が判定できませんでした'
        return cont[0]

    def get_birthday(self, horse_id: Union[int, str]) -> str:
        """誕生日をスクレイピングするメソッド

        Parameters
        ----------
        horse_id : Union[int, str]
            馬ID

        Returns
        -------
        str
            2016-07-16など、日付を表す文字列
        """
        url = f'https://db.netkeiba.com/horse/{horse_id}/'

        soup = self._get_soup(url, encoding='EUC-JP')
        html = str(soup.find('div', attrs={"class": "db_prof_area_02"}))
        s = pd.read_html(html)[0].iloc[0, 1]
        dt = datetime.datetime.strptime(s, '%Y年%m月%d日')
        return dt.strftime('%Y-%m-%d')

    def get_peds(self, horse_id: Union[int, str]):
        """血統データをスクレイピングするメソッド
        Parameters:
        ----------
        horse_id : Union[int, str]
            馬ID

        Returns:
        ----------
        peds_df : pandas.DataFrame
            全血統データをまとめてDataFrame型にしたもの
        """
        base_url = 'https://db.netkeiba.com/horse/ped/{}'

        id_list = list()
        soup = self._get_soup(base_url.format(horse_id))
        table = soup.find('table', attrs={"class": "blood_table"})
        for idx, span in enumerate(['16', '8', '4', '2', '']):
            for row in table.find_all("td", attrs={"rowspan": span}):
                for atag in row.find_all("a"):
                    ret = re.findall(r"/horse/[0-9a-zA-Z]{10}", atag["href"])
                    if len(ret) != 0:
                        d = {
                            'name': atag.text.split('\n')[0],
                            'horse_id': ret[0].split('/')[-1],
                            'gen': idx + 1}
                        id_list.append(d)
        return pd.DataFrame(id_list)


class RealTimeOddsScraper(SeleniumScraperBase):
    """
    JRA公式サイトからほぼリアルタイムのオッズ情報をスクレイピングするクラス。
    """
    RACECOURSE_DICT = {
        1: '札幌', 2: '函館', 3: '福島', 4: '新潟', 5: '東京',
        6: '中山', 7: '中京', 8: '京都', 9: '阪神', 10: '小倉'}

    def __init__(self, executable_path: str, visible: bool = False, wait_time: int = 10, select_manually: bool = False):
        """
        Parameters
        ----------
        executable_path : str
            chrome driverまでのパス
        visible : bool, default False
            ブラウザを起動して動作させるかのフラグ
        wait_time : float, default 10
            タイムアウトまでの時間

        Notes
        -----
        このクラスは`self.status`で現在のブラウザの状態を定義している。
        * 0: 初期状態。何も表示されている状態
        * 1: 今週の競馬が開催されている競馬場一覧が表示されている状態
        * 2: ある競馬場のレース(12R)一覧が表示されている状態
        * 3: レース個別ページが表示されている状態
        """
        super().__init__(executable_path=executable_path,
                         visible=visible, wait_time=wait_time)
        self.URL = 'https://www.jra.go.jp/'
        self.status = 0
        self.__index_base = True
        if select_manually:
            self.get_racecourse_list()
            print('以下の数字からレースを選択し、select_racecourseメソッドを使用してください')
            for i, race in enumerate(self.race_list):
                print(f'{i}, ', race['text'])

    def change_indexbase(self):
        '''
        馬連以降のボタンのインデックスがページによって違う（要検証）
        1だけずれるので、bool値を加算するかどうかで制御する
        '''
        self.__index_base = not self.__index_base

    def get_tansho_odds(self) -> pd.DataFrame:
        assert self.status == 3
        self._select_baken_type(0)
        dfs = self._get_odds_list()
        d = {'馬番': 'First', '単勝': 'Odds'}
        df = dfs[0][['馬番', '単勝']].rename(columns=d)
        return df

    def get_umaren_odds(self):
        assert self.status == 3
        self._select_baken_type(1 + self.__index_base)
        dfs = self._get_odds_list()
        l = list()
        for i, df in enumerate(dfs):
            df.columns = ['Second', 'Odds']
            df['First'] = i + 1
            l.append(df)
        df = pd.concat(l)[['First', 'Second', 'Odds']]
        df.reset_index(drop=True, inplace=True)
        return df

    def get_wide_odds(self):
        assert self.status == 3
        self._select_baken_type(2 + self.__index_base)
        dfs = self._get_odds_list()
        l = list()
        for i, df in enumerate(dfs):
            df.columns = ['Second', 'Odds']
            df['First'] = i + 1
            l.append(df)
        df = pd.concat(l)[['First', 'Second', 'Odds']]
        df.reset_index(drop=True, inplace=True)
        return df

    def get_umatan_odds(self):
        assert self.status == 3
        self._select_baken_type(3 + self.__index_base)
        dfs = self._get_odds_list()
        l = list()
        for i, df in enumerate(dfs):
            df.columns = ['Second', 'Odds']
            df['First'] = i + 1
            l.append(df)
        df = pd.concat(l)[['First', 'Second', 'Odds']]
        idx = df.First == df.Second
        df = df[~idx].reset_index(drop=True)
        return df

    def get_renpuku_odds(self):
        assert self.status == 3
        self._select_baken_type(4 + self.__index_base)
        element = self._get_element(By.ID, 'odds_list')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        horse_num = dfs[0].iloc[:, 0].max()
        itr = itertools.combinations([i+1 for i in range(horse_num-1)], 2)
        for i, c in enumerate(itr):
            dfs[i].columns = ['Third', 'Odds']
            dfs[i]['First'] = int(c[0])
            dfs[i]['Second'] = int(c[1])
        df = pd.concat(dfs)[['First', 'Second', 'Third', 'Odds']]
        df = df.dropna().drop_duplicates()
        return df.reset_index(drop=True)

    def get_rentan_odds(self):
        self._select_baken_type(5 + self.__index_base)
        element = self._get_element(By.ID, 'odds_list')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        horse_num = dfs[0].iloc[:, 0].max()
        itr = itertools.permutations([i+1 for i in range(horse_num)], 2)
        for i, c in enumerate(itr):
            dfs[i].columns = ['Third', 'Odds']
            dfs[i]['First'] = int(c[0])
            dfs[i]['Second'] = int(c[1])
        df = pd.concat(dfs)[['First', 'Second', 'Third', 'Odds']]
        df = df.dropna().drop_duplicates()
        return df.reset_index(drop=True)

    def _get_odds_list(self):
        assert self.status == 3
        element = self._get_element(By.ID, 'odds_list')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        return dfs

    def _select_baken_type(self, idx: int):
        assert self.status == 3
        elements = self._get_elements(By.CLASS_NAME, 'nav')
        baken_type_list = elements[1].find_elements(By.TAG_NAME, 'li')
        self._click(baken_type_list[idx])

    def get_racecourse_list(self):
        '''
        ページにアクセス&遷移し、レース一覧が存在するページを表示する。
        status any -> 1
        '''
        self.visit_race_list_page()
        self.date_info = self.get_date_info()
        self.race_list = self.get_race_list()

    def select_race(self, race_num: int):
        '''
        レース一覧(12R)が表示されているページから1レースを選択する
        status 2 -> 3
        '''
        assert self.status == 2
        assert 0 < race_num < 13
        race_num -= 1
        element = self._get_element(By.TAG_NAME, 'tbody')
        race_num_list = element.find_elements(By.CLASS_NAME, 'race_num')
        self._click(race_num_list[race_num])
        self.status = 3

    def select_racecourse(self, idx):
        '''
        get_racecourse_listメソッド後に利用して、
        レース場のその日のレース一覧(12R)を表示しているページに遷移。
        status 1 -> 2
        '''
        assert self.status == 1
        assert self.race_list is not None, 'get_racecourse_listを先に実行してください'
        self._click(self.race_list[idx]['element'])
        print('select_raceメソッドでレースを選択してください')
        self.race_list = None
        self.status = 2

    def visit_race_list_page(self):
        '''
        JRAの公式にアクセスし、オッズタブを選択し、レース一覧ページを表示する
        status any -> 1
        '''
        self._visit_page(self.URL)
        element = self._get_element(By.ID, 'quick_menu')
        element = element.find_elements(By.TAG_NAME, 'li')[2]
        self._click(element)
        self.status = 1

    def get_date_info(self) -> list:
        '''
        日付と曜日を文字列のリストとして取得する
        status 1 -> 1
        '''
        assert self.status == 1
        this_week = self._get_element(By.CLASS_NAME, 'thisweek')
        days = this_week.find_elements(By.CLASS_NAME, 'sub_header')
        return [day.get_attribute('textContent') for day in days]

    def get_race_list(self) -> list:
        '''
        その週に開催されている（されていた）レースの一覧について
        文字列（レース名など）と、elementを取得する。
        status 1 -> 1
        '''
        assert self.status == 1
        race_list = list()
        days_elements = self._get_elements(By.CLASS_NAME, 'link_list')
        for i, days_element in enumerate(days_elements):
            elements = days_element.find_elements(By.TAG_NAME, 'div')
            date_info = self.date_info[i]
            for element in elements:
                text = element.get_attribute("textContent")
                text = text.replace('\n', '').replace(' ', '')
                text = date_info + text
                race_list.append({'text': text, 'element': element})
        return race_list

    def select_race_from_race_id(self, race_id, sleep_time=0.3) -> list:
        '''
        その週に開催されている（されていた）レースの一覧について
        文字列（レース名など）と、elementを取得する。
        status any -> 3
        '''
        self.visit_race_list_page()
        time.sleep(sleep_time)

        race_id = str(race_id)
        assert len(race_id) == 12
        baba = self.RACECOURSE_DICT[int(race_id[4:6])]
        race_txt = f'{int(race_id[6:8])}回{baba}{int(race_id[8:10])}日'

        days_elements = self._get_elements(By.CLASS_NAME, 'link_list')
        for days_element in days_elements:
            elements = days_element.find_elements(By.TAG_NAME, 'div')
            for element in elements:
                text = element.get_attribute("textContent")
                text = text.replace('\n', '').replace(' ', '')
                if race_txt in text:
                    self._click(element)
                    self.status = 2
                    time.sleep(sleep_time)
                    self.select_race(int(race_id[10:12]))
                    return

    def get_odds_df_dict(self) -> Dict[str, pd.DataFrame]:
        df_dict = dict()
        # 単勝
        df_dict['TANSHO'] = self.get_tansho_odds()
        # 馬単
        df_dict['UMATAN'] = self.get_umatan_odds()
        # 3連単
        df_dict['RENTAN'] = self.get_rentan_odds()
        # 馬連
        df_dict['UMAREN'] = self.get_umaren_odds()
        # 3連複
        df_dict['RENPUKU'] = self.get_renpuku_odds()
        # ワイド
        df_dict['WIDE'] = self.get_wide_odds()
        return df_dict


class OddsScraper(SeleniumScraperBase):
    def __init__(self, executable_path, visible=False, wait_time=10):
        super().__init__(executable_path=executable_path,
                         visible=visible, wait_time=wait_time)
        self.ODDS_URL = 'https://race.netkeiba.com/odds/index.html?race_id={}&rf=race_submenu'

    def visit_page(self, race_id: Union[str, int]):
        self._visit_page(self.ODDS_URL.format(race_id))

    def get_tansho_odds(self, sleep_time=0.2) -> pd.DataFrame:
        # 単勝/複勝
        element = self._get_element(By.ID, "odds_navi_b1")
        self._click(element)
        time.sleep(sleep_time)
        tansho_df = self.__get_tanpuku_odds(0)
        return tansho_df

    def get_fukusho_odds(self, sleep_time=0.2) -> pd.DataFrame:
        # 複勝
        element = self._get_element(By.ID, "odds_navi_b1")
        self._click(element)
        time.sleep(sleep_time)
        tansho_df = self.__get_tanpuku_odds(1)
        return tansho_df

    def __get_tanpuku_odds(self, idx) -> pd.DataFrame:
        # 0なら単勝、1なら複勝のテーブルを取得
        elements = self._get_elements(
            By.CLASS_NAME, "RaceOdds_HorseList_Table")
        df = pd.read_html(elements[idx].get_attribute('outerHTML'))[0]
        cols = [col.replace(' ', '') for col in df.columns]
        df.columns = cols
        tanpuku_df = df[['馬番', 'オッズ']]
        tanpuku_df.columns = ['First', 'Odds']
        return tanpuku_df

    def get_wakuren_odds(self) -> pd.DataFrame:
        # 枠連
        element = self._get_element(By.ID, "odds_navi_b3")
        self._click(element)
        raise NotImplementedError

    def get_umaren_odds(self, sleep_time: float = 0.2) -> pd.DataFrame:
        # 馬連
        element = self._get_element(By.ID, "odds_navi_b4")
        self._click(element)
        time.sleep(sleep_time)
        element = self._get_element(By.CLASS_NAME, "GraphOdds")
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        first_list = [int(df.columns.values[0]) for df in dfs]
        umaren_df_list = [df.iloc[:, :2] for df in dfs]
        for i in range(len(umaren_df_list)):
            umaren_df_list[i].columns = ['Second', 'Odds']
            umaren_df_list[i]['First'] = first_list[i]
            umaren_df_list[i] = umaren_df_list[i][['First', 'Second', 'Odds']]
        umaren_df = pd.concat(umaren_df_list, axis=0)
        return umaren_df

    def get_wide_odds(self, sleep_time: float = 0.2) -> pd.DataFrame:
        # ワイド
        element = self._get_element(By.ID, "odds_navi_b5")
        self._click(element)
        time.sleep(sleep_time)
        element = self._get_element(By.CLASS_NAME, 'GraphOdds')
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        first_list = [int(df.columns.values[0]) for df in dfs]
        wide_df_list = [df.iloc[:, :2] for df in dfs]
        for i in range(len(wide_df_list)):
            wide_df_list[i].columns = ['Second', 'Odds']
            wide_df_list[i]['First'] = first_list[i]
            wide_df_list[i] = wide_df_list[i][['First', 'Second', 'Odds']]
        wide_df = pd.concat(wide_df_list, axis=0)
        return wide_df

    def get_umatan_odds(self, sleep_time: float = 0.2) -> pd.DataFrame:
        # 馬単
        element = self._get_element(By.ID, "odds_navi_b6")
        self._click(element)
        time.sleep(sleep_time)
        element = self._get_element(By.CLASS_NAME, "GraphOdds")
        dfs = pd.read_html(element.get_attribute('outerHTML'))
        first_list = [int(df.columns.values[0]) for df in dfs]
        batan_df_list = [df.iloc[:, :2] for df in dfs]
        for i in range(len(batan_df_list)):
            batan_df_list[i].columns = ['Second', 'Odds']
            batan_df_list[i]['First'] = first_list[i]
            batan_df_list[i] = batan_df_list[i][['First', 'Second', 'Odds']]
        batan_df = pd.concat(batan_df_list, axis=0)
        return batan_df

    def get_renpuku_odds(self, sleep_time: float = 0.2) -> pd.DataFrame:
        # 3連複
        element = self._get_element(By.ID, "odds_navi_b7")
        self._click(element)
        dropdown = self._get_element(By.ID, "list_select_horse")
        select = Select(dropdown)
        num = len(select.options)
        # スクレイピング
        dfs_list = list()
        for axis_horse_number in range(1, num):
            if axis_horse_number > 1:
                # 軸馬の選択・変更 dropdown select状態にする
                dropdown = self._get_element(By.ID, "list_select_horse")
                select = Select(dropdown)
                select.select_by_value(str(axis_horse_number))
            time.sleep(sleep_time)
            element = self._get_element(By.CLASS_NAME, "GraphOdds")
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            dfs_list.append(dfs)
        # 整形
        renpuku_concat_df_list = list()
        for uma, dfs in enumerate(dfs_list):
            uma += 1
            second_list = [int(df.columns.values[0]) for df in dfs]
            renpuku_df_list = [df.iloc[:, :2] for df in dfs]
            for i in range(len(renpuku_df_list)):
                renpuku_df_list[i].columns = ['Third', 'Odds']
                renpuku_df_list[i]['First'] = uma
                renpuku_df_list[i]['Second'] = second_list[i]
                renpuku_df_list[i] = renpuku_df_list[i][[
                    'First', 'Second', 'Third', 'Odds']]
            renpuku_concat_df_list.append(pd.concat(renpuku_df_list, axis=0))
        renpuku_df = pd.concat(renpuku_concat_df_list, axis=0)
        # 着順をソートして重複を削除
        values = renpuku_df.iloc[:, :3].values
        values.sort()
        renpuku_df[renpuku_df.columns[:3]] = values
        renpuku_df = renpuku_df.drop_duplicates().reset_index(drop=True)
        return renpuku_df

    def get_rentan_odds(self, sleep_time: float = 0.2) -> pd.DataFrame:
        # 3連単
        element = self._get_element(By.ID, "odds_navi_b8")
        self._click(element)
        dropdown = self._get_element(By.ID, "list_select_horse")
        select = Select(dropdown)
        num = len(select.options)
        # スクレイピング
        dfs_list = list()
        for axis_horse_number in range(1, num):
            if axis_horse_number > 1:
                # 軸馬の選択・変更 dropdown select状態にする
                dropdown = self._get_element(By.ID, "list_select_horse")
                select = Select(dropdown)
                select.select_by_value(str(axis_horse_number))
            time.sleep(sleep_time)
            element = self._get_element(By.CLASS_NAME, "GraphOdds")
            dfs = pd.read_html(element.get_attribute('outerHTML'))
            dfs_list.append(dfs)
        # 整形
        tan3concat_df_list = list()
        for uma, dfs in enumerate(dfs_list):
            uma += 1
            second_list = [int(df.columns.values[0]) for df in dfs]
            tan3_df_list = [df.iloc[:, :2] for df in dfs]
            for i in range(len(tan3_df_list)):
                tan3_df_list[i].columns = ['Third', 'Odds']
                tan3_df_list[i]['First'] = uma
                tan3_df_list[i]['Second'] = second_list[i]
                tan3_df_list[i] = tan3_df_list[i][[
                    'First', 'Second', 'Third', 'Odds']]
            tan3concat_df_list.append(pd.concat(tan3_df_list, axis=0))
        tan3_df = pd.concat(tan3concat_df_list, axis=0)
        return tan3_df

    def get_odds_df_dict(self, sleep_time: float = 0.2) -> Dict[str, pd.DataFrame]:
        df_dict = dict()
        # 単勝
        df_dict['TANSHO'] = self.get_tansho_odds(sleep_time)
        # 馬単
        df_dict['UMATAN'] = self.get_umatan_odds(sleep_time)
        # 3連単
        df_dict['RENTAN'] = self.get_rentan_odds(sleep_time)
        # 馬連
        df_dict['UMAREN'] = self.get_umaren_odds(sleep_time)
        # 3連複
        df_dict['RENPUKU'] = self.get_renpuku_odds(sleep_time)
        # ワイド
        df_dict['WIDE'] = self.get_wide_odds(sleep_time)
        return df_dict


