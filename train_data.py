#!/usr/bin/env python
# -*- coding:utf-8 -*-
#       FileName:  train_data.py
#
#    Description:
#
#        Version:  1.0
#        Created:  2019-09-19 10:07:56
#  Last Modified:  2019-10-09 18:22:01
#       Revision:  none
#       Compiler:  gcc #
#         Author:  zt ()
#   Organization:

import sys
import datetime
import math
import numpy as np
np.set_printoptions(threshold=np.inf)
import pandas as pd
from stockdata import stockdata


class train_data:
    def __init__(self):
        self.sd = stockdata()
        self.batch_size = 32        # 一次训练多少组数据
        self.num_input = 13         # 每组数据的每一行
        self.timesteps = 20         # 多少行
        self.num_classes = 2        # 数据集类别数
        self.test_size = 0          # 填充多少个0
        # [batch] T1 T2
        self.ndays = 2              # 几日差值
        self.epochs = 60

    def calc_delta_days(self, d1, d2):
        d = (datetime.datetime.strptime(d1, "%Y%m%d") -
             datetime.datetime.strptime(d2, "%Y%m%d")).days
        return float(d)

    def gen_train_data_from_df(self, df):
        code = df.iat[0, 0]
        df = df[::-1]
        df = df.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)

        min_len = self.timesteps + self.batch_size + self.ndays
        if df.shape[0] < min_len:
            return ()

        cnt = df.shape[0]
        cnt = cnt - min_len
        cnt = cnt // self.batch_size

        df = df.tail(cnt * self.batch_size + min_len)
        dif = self.sd.get_index_daily_by_code(code)

        dif = dif.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)
        df = pd.merge(df, dif, on='trade_date')

        df['td2'] = df['trade_date'].shift(1)
        df['td2'].iat[0] = df['trade_date'].iat[0]

        df['trade_date'] = df.apply(lambda x: self.calc_delta_days(
            x['trade_date'], x['td2']), axis=1)

        df = df.drop(['td2'], axis=1)

        datanums = df.shape[0] - self.timesteps - self.ndays

        xn = np.empty(shape=[0, self.timesteps, self.num_input, 1])
        yn = np.empty(shape=[0, self.num_classes])
        for i in range(datanums):
            dfx = df[i: i + self.timesteps]
            dfx = dfx.apply(lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)))
            xtmp = np.array(dfx).reshape(1, self.timesteps, self.num_input, 1)
            xn = np.vstack((xn, xtmp))

            yo = df['open_x'].iat[i + self.timesteps]
            yc = df['close_x'].iat[i + self.timesteps + 1]
            y = 100.0 * (yc - yo) / yo
            ytmp = np.zeros(self.num_classes)
            if y > 0.5:
                ytmp[1] = 1
            else:
                ytmp[0] = 1
            yn = np.vstack((yn, ytmp))
        return xn, yn

    def make_a_train_data_from_df(self, dfx, y):
        xn = np.array(dfx)
        xn = xn.reshape(self.num_input * self.timesteps)

        xnpad = np.zeros(self.test_size)
        xn = np.append(xn, xnpad, axis=0)

        xn = xn.reshape(1, self.num_input * self.timesteps + self.test_size)

        yn = np.zeros(self.num_classes)
        if y > 0.5:
            yn[1] = 1
        else:
            yn[0] = 1

        yn = yn.reshape(1, self.num_classes)
        return (xn, yn)

    def calc_train_data_list_from_df(self, df):
        df = df[::-1]
        df = df.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)
        df['buy'] = df['close'].shift(-1)
        df['sell'] = df['close'].shift(-1 * self.ndays)
        df.drop(df.tail(self.ndays).index, inplace=True)
        df['earn'] = 100.0 * (df['sell'] - df['buy']) / df['buy']
        df.drop(['buy', 'sell'], axis=1, inplace=True)

        lt = []
        min_len = self.timesteps + self.batch_size
        if df.shape[0] < min_len:
            return lt

        code = df.iat[0, 0]

        cnt = df.shape[0]
        cnt = cnt - min_len
        cnt = cnt // self.batch_size
        cnt = cnt * self.batch_size

        df = df.tail(cnt + min_len)

        dif = self.sd.get_index_daily_by_code(code)

        dif = dif.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)
        df = pd.merge(df, dif, on='trade_date')

        cnt = df.shape[0]

        df['td2'] = df['trade_date'].shift(1)
        df['td2'].iat[0] = df['trade_date'].iat[0]

        df['trade_date'] = df.apply(lambda x: self.calc_delta_days(
            x['trade_date'], x['td2']), axis=1)

        df = df.drop(['td2'], axis=1)
        dfy = df['earn']
        df = df.drop(['earn'], axis=1)

        self.num_input = df.shape[1]

        for i in range(cnt - self.timesteps):
            dfx = df[i: i + self.timesteps]
            dfx = dfx.apply(lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)))
            y = dfy.iat[i + self.timesteps - 1]
            xn, yn = self.make_a_train_data_from_df(dfx, y)
            lt.append((xn, yn))

        return lt

    def get_batch_data_from_list(self, ll, n):
        if len(ll) == 0:
            return None

        # full batch
        if n == -1:
            rlen = len(ll)
            xt, yt = ll[0]
        else:
            rlen = self.batch_size
            xt, yt = ll[n * self.batch_size]

        for i in range(1, rlen):
            x, y = ll[i]
            xt = np.vstack([xt, x])
            yt = np.vstack([yt, y])
        return (xt, yt)

    def get_test_data_df(self):
        pass

    def get_predict_data(self, code, date):
        df = self.sd.get_data_by_code(code)
        df = df[df.trade_date <= date]
        df = df.head(self.timesteps)
        df = df[::-1]
        df = df.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)

        dif = self.sd.get_index_daily_by_code(code)

        dif = dif.drop(['change', 'ts_code', 'pre_close', 'pct_chg'], axis=1)
        df = pd.merge(df, dif, on='trade_date')

        df['td2'] = df['trade_date'].shift(1)
        df['td2'].iat[0] = df['trade_date'].iat[0]

        df['trade_date'] = df.apply(lambda x: self.calc_delta_days(
            x['trade_date'], x['td2']), axis=1)

        df = df.drop(['td2'], axis=1)
        df = df.apply(lambda x: (x - np.min(x)) / (np.max(x) - np.min(x)))

        xn = np.array(df).reshape(1, self.timesteps, self.num_input, 1)

        return xn

    def test(self):
        ll = self.sd.get_all_code()
        for c in ll:
            d = self.sd.get_data_by_code(c)
            df = self.calc_train_data_list_from_df(d)
            print(c)
            if df is None:
                pass


if __name__ == '__main__':
    startTime = datetime.datetime.now()
    a = train_data()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'g':  # gen train data
            pass
        elif sys.argv[1] == 't':  # gen test data
            pass
        elif sys.argv[1] == 'p':  # get predict data
            pass
    else:
        # df = a.sd.get_data_by_code('600737.SH')
        df = a.sd.get_data_by_code('000058.SZ')
        # df = a.get_predict_data('600737.SH', '20190925')
        # df = a.calc_train_data_list_from_df(df)
        # df = a.gen_train_data_from_df(df)
        # df['res'] = 0.0
        print(df)
        print(df.shape)
        # print(df.shape)
        # print(df[0][0])
        # print(df[0][1])
        # d = a.test()
        # c = a.get_batch_data_from_list(d, 100)
        # print(c)
        # print(type(c))
        # print(a.calc_delta_days("20190926", "20190821"))

    print("Time taken:", datetime.datetime.now() - startTime)
