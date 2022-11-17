# Copyright (c) general_backbone. All rights reserved.
from bs4 import BeautifulSoup
from vnquant import utils
import pandas as pd
import logging as logging
import requests
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
from vnquant import configs
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

URL_VND = configs.URL_VND
URL_CAFE = configs.URL_CAFE
HEADERS = configs.HEADERS

class DataLoader():
    def __init__(self, symbols, start, end, data_source = 'CAFE', minimal = True, *arg, **karg):
        self.symbols = symbols
        self.start = start
        self.end = end
        self.data_source = data_source
        self.minimal = minimal

    def download(self):
        loader = DataLoaderCAFE(self.symbols, self.start, self.end)
        stock_data = loader.download()

        if self.minimal:
            data = stock_data[['high', 'low', 'open', 'close', 'adjust', 'volume']]
            return data
        else:
            return stock_data

class DataLoadProto():
    def __init__(self, symbols, start, end, *arg, **karg):
        self.symbols = symbols
        self.start = utils.convert_text_dateformat(start, new_type = '%d/%m/%Y')
        self.end = utils.convert_text_dateformat(end, new_type = '%d/%m/%Y')

class DataLoaderCAFE(DataLoadProto):
    def __init__(self, symbols, start, end, *arg, **karg):
        self.symbols = symbols
        self.start = start
        self.end = end
        super(DataLoaderCAFE, self).__init__(symbols, start, end)

    def download(self):
        stock_datas = []
        if not isinstance(self.symbols, list):
            symbols = [self.symbols]
        else:
            symbols = self.symbols

        for symbol in symbols:
            stock_datas.append(self.download_one(symbol))

        data = pd.concat(stock_datas, axis=1)
        return data

    def download_one(self, symbol):
        stock_data = pd.DataFrame(columns=['date', 'change_perc1', 'change_perc2',
                                           'open', 'high', 'low', 'close',
                                           'avg', 'volume_match', 'volume_reconcile'])

        for i in range(1000):
            stock_slice_batch = self.download_batch(i + 1, symbol)
            stock_data = pd.concat([stock_data, stock_slice_batch], axis=0)
            try:
                date_end_batch = stock_slice_batch.date.values[-1]
            except:
                # start date is holiday or weekend
                break
            is_touch_end = utils.convert_date(self.start, '%d/%m/%Y') == utils.convert_date(date_end_batch, '%d/%m/%Y')
            # logging.info('batch: {}; start date out range: {}; date_end_batch: {}'.format(i + 1, is_touch_end, date_end_batch))
            if is_touch_end:
                break

        stock_data['change_perc1'], stock_data['change_perc2'] = stock_data['change_perc'].apply(utils.split_change_col).str
        if 'change_perc' in stock_data.columns:
            stock_data.pop('change_perc')
        if 'avg' in stock_data.columns:
            stock_data.pop('avg')
            stock_data = stock_data.set_index('date').apply(pd.to_numeric, errors='coerce')
            stock_data.index = list(map(lambda text: utils.convert_date(text, date_type='%d/%m/%Y'), stock_data.index))
            stock_data.index.name = 'date'
            stock_data = stock_data.sort_index()
            stock_data.fillna(0, inplace=True)
            stock_data['volume'] = stock_data.volume_match + stock_data.volume_reconcile


        # Create multiple columns
        iterables = [stock_data.columns.tolist(), [symbol]]
        mulindex = pd.MultiIndex.from_product(iterables, names=['Attributes', 'Symbols'])
        stock_data.columns = mulindex


        logging.info('data {} from {} to {} have already cloned!' \
                     .format(symbol,
                             utils.convert_text_dateformat(self.start, origin_type = '%d/%m/%Y', new_type = '%Y-%m-%d'),
                             utils.convert_text_dateformat(self.end, origin_type='%d/%m/%Y', new_type='%Y-%m-%d')))

        return stock_data

    def download_batch(self, id_batch, symbol):
        form_data = {'ctl00$ContentPlaceHolder1$scriptmanager':'ctl00$ContentPlaceHolder1$ctl03$panelAjax|ctl00$ContentPlaceHolder1$ctl03$pager2',
                       'ctl00$ContentPlaceHolder1$ctl03$txtKeyword':symbol,
                       'ctl00$ContentPlaceHolder1$ctl03$dpkTradeDate1$txtDatePicker':self.start,
                       'ctl00$ContentPlaceHolder1$ctl03$dpkTradeDate2$txtDatePicker':self.end,
                       '__EVENTTARGET':'ctl00$ContentPlaceHolder1$ctl03$pager2',
                       '__EVENTARGUMENT':id_batch,
                       '__ASYNCPOST':'true'}
        url = URL_CAFE+symbol+"-1.chn"
        r = requests.post(url, data = form_data, headers = HEADERS, verify=False)
        soup = BeautifulSoup(r.content, 'html.parser')
        # print(soup)
        table = soup.find('table')
        stock_slice_batch = pd.read_html(str(table))[0].iloc[2:, :12]

        stock_slice_batch.columns = ['date', 'adjust', 'close', 'change_perc', 'avg',
                        'volume_match', 'value_match', 'volume_reconcile', 'value_reconcile',
                        'open', 'high', 'low']

        return stock_slice_batch

# loader1 = DataLoaderVND(symbols="VND", start="2021-01-01", end="2021-02-15")
# loader2 = DataLoaderCAFE(symbols="VND", start="2017-01-10", end="2019-02-15")
# loader3 = DataLoader(symbols='VND', start="2018-01-10", end="2018-02-15", minimal=False, data_source='vnd')
# loader3 = DataLoader(symbols='VND', start="2018-01-10", end="2018-02-15", minimal=True, data_source='vnd')
# loader3 = DataLoader(symbols=['VND', 'VCB'], start="2018-01-10", end="2018-02-15", minimal=True, data_source='vnd')
# loader4 = DataLoader(symbols='VND', start="2018-01-10", end="2018-02-15", minimal=False, data_source='cafe')
# loader4 = DataLoader(symbols='VND', start="2018-01-10", end="2018-02-15", minimal=True, data_source='cafe')
# loader4 = DataLoader(symbols=['VND', 'VCB'], start="2018-01-10", end="2018-02-15", minimal=True, data_source='cafe')