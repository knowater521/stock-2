#!/usr/bin/env python
# -*- coding:utf-8 -*-
#       FileName:  stockdata.py
#
#    Description:
#
#        Version:  1.0
#        Created:  2019-06-18 16:07:49
#  Last Modified:  2019-09-10 15:00:14
#       Revision:  none
#       Compiler:  gcc
#
#         Author:  zt ()
#   Organization:

import pickle
import time
import datetime
import zlib
import redis
import pandas as pd
import tushare as ts


class stockdata:
    def __init__(self):
        with open('tk.pkl', 'rb') as f:
            tk = pickle.load(f)
            ts.set_token(tk)
        self.pro = ts.pro_api()
        self.redis = redis.Redis(host='127.0.0.1', password='zt@123456', port=6379)

    def get_today_date(self):
        return datetime.datetime.now().strftime("%Y%m%d")

    def get_trade_cal(self, st):
        todaydate = self.get_today_date()
        df = self.pro.query('trade_cal', start_date=st, end_date=todaydate)
        df = df[df.is_open == 1]
        df = df.reset_index(drop=True)
        return df

    # 000001.SH 399001.SZ 399006.SZ
    def get_index_daily_start_end_date_save(self, code, date):
        df = self.pro.index_daily(ts_code=code, trade_date=date)
        re = self.redis.hexists(date, code[0:-3])
        if re == 0:
            print("downloading: ", date, code[0:-3])
            self.redis.hset(date, code[0:-3], zlib.compress(pickle.dumps(df), 5))
        return df

    def get_index_daily_start_end_date_save_all(self, date):
        self.get_index_daily_start_end_date_save('000001.SH', date)
        self.get_index_daily_start_end_date_save('399001.SH', date)
        self.get_index_daily_start_end_date_save('399006.SH', date)

    def get_stock_number_start_end_date(self, code, st, end):
        return self.pro.daily(ts_code=code, start_date=st, end_date=end)

    def get_stock_number_date_last_ndays(self, code, date, ndays):
        end = datetime.datetime.now()
        st = end - datetime.timedelta(days=ndays * 2)
        st = st.strftime("%Y%m%d")
        end = end.strftime("%Y%m%d")
        df = self.get_stock_number_start_end_date(code, st, end)
        if df.shape[0] <= ndays:
            return df
        return df[0:ndays]

    def get_stock_basics(self):
        return self.pro.get_stock_basics()

    def get_date_stock_info(self, date):
        return self.pro.daily(trade_date=date)

    def get_date_limitup(self, date):
        dfd = self.pro.daily(trade_date=date)
        dfd = dfd[['ts_code', 'close', 'pct_chg']]
        dfs = self.pro.stk_limit(trade_date=date)
        dfs = dfs[['ts_code', 'up_limit']]
        df = pd.merge(dfd, dfs, on='ts_code')
        df = df[(df.close == df.up_limit) & (df.pct_chg > 6.0) & (df.pct_chg < 12.0)]
        df = df['ts_code']
        df = df.reset_index(drop=True)
        return df

    def get_top_list_save(self, date):
        df = self.pro.top_list(trade_date=date)
        re = self.redis.hexists(date, 'top_list')
        if re == 0:
            print("downloading: ", date, "top_list")
            self.redis.hset(date, 'top_list', zlib.compress(pickle.dumps(df), 5))
        return df

    def get_top_inst_save(self, date):
        df = self.pro.top_inst(trade_date=date)
        re = self.redis.hexists(date, 'top_inst')
        if re == 0:
            print("downloading: ", date, "top_inst")
            self.redis.hset(date, 'top_inst', zlib.compress(pickle.dumps(df), 5))
        return df

    def get_one_day_data_save(self, date):
        df_tscode = self.get_date_limitup(date)
        for i in df_tscode.index:
            c = df_tscode.loc[i]
            re = self.redis.hexists(date, c)

            if (re == 0):
                print("downloading: ", date, c)
                df = self.get_stock_number_date_last_ndays(c, date, 40)
                self.redis.hset(date, c, zlib.compress(pickle.dumps(df), 5))
                time.sleep(0.1)

    def get_all_data_save(self):
        ds = "20170101"

        rd = self.redis.keys("20*")
        if rd:
            rd.sort()
            ds = rd[-1].decode()

        ds_date = self.get_trade_cal(ds)
        ds_date = ds_date['cal_date']
        ds_date = ds_date.reset_index(drop=True)

        print(" start_date: ", ds_date[0], "end_date: ", ds_date[ds_date.shape[0] - 1])

        for i in ds_date.index:
            d = ds_date.loc[i]
            self.get_top_list_save(d)
            self.get_top_inst_save(d)
            self.get_index_daily_start_end_date_save_all(d)
            self.get_one_day_data_save(d)
            # self.redis.save()


A = stockdata()
startTime = datetime.datetime.now()
d = A.get_top_inst_save('20190906')
# d = A.get_stock_number_date_last_ndays("600818.SH", "20180101", 40)
# d = A.get_index_daily_start_end_date_save_all("20190906")
A.get_all_data_save()
# A.get_one_day_data_save('20190906')
# d = A.get_date_limitup('20190909')
# print(d)
# d = A.get_trade_cal("20190901")
print("Time taken:", datetime.datetime.now() - startTime)
'''
r.hset('20190903', 'limitup', zlib.compress(pickle.dumps(a), 5))
df = pickle.loads(zlib.decompress(r.hget('20190903', 'limitup')))

d1 = r.hget('20190901', 'limitup')
if (d1 is None):
    print('none data')
else:
    print(d1)
'''
