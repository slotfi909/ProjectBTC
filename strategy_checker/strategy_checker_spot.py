#!/usr/bin/env python
# coding: utf-8

# In[12]:


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
from enum import Enum

class Strategy(Enum):
    THREESOLDIERS = 1
    ENGULFING = 2
    
class Audit(Enum):
    WEEKLY = 1
    MONTHLY = 2
    
class Interval(Enum):
    MINUTELY_ONEMINUTE = '1m'
    MINUTELY_THREEMINUTE = '3m'
    MINUTELY_FIVEMINUTE = '5m'
    MINUTELY_FIFTEENMINUTE = '15m'
    MINUTELY_THIRTYMINUTE = '30m'

    HOURLY_ONEHOUR = '1h'
    HOURLY_TWOHOUR = '2h'
    HOURLY_FOURHOUR = '4h'
    HOURLY_SIXHOUR = '6h'
    HOURLY_EIGHTHOUR = '8h'
    HOURLY_TWELVEHOUR = '12h'

    DAILY_ONEDAY = '1d'

    WEEKLY_ONEWEEK = '1w'

    MONTHLY_ONEMONTH = '1M'
    
engulfing_body_condition = 2
threesoldiers_body_condition = [1.01,1.02]
#march and nov 21 and march 24 almost same price (all high)
# 3         11           3


# In[13]:


file = "../../data/csv/Binance_BTCUSDT_2024_minute_2024_04_02.csv"
# enums
strategy = Strategy.ENGULFING
audit = Audit.MONTHLY
interval = Interval.MINUTELY_ONEMINUTE
strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS]

usdt_balance = 45000
buy_percentage_init = 10
sell_percentage_init = 13
learning_rate = 1.3
bitcoin_balance: np.longdouble = 0
period = 1 * 24 * 60 # as candles
drop_rows = True
row_upper_limit = 1 * 7 * 24 * 26 # datas upper than
row_lower_limit = 0 # datas lower than
add_each_month = 0 #20 # dollars
period_counter = 1 # add money after n periods

total_balance = usdt_balance + bitcoin_balance
buyPositionsNumber = 0
sellPositionsNumber = 0
buyDuplicateChecker = 0
sellDuplicateChecker = 0
buy_percentage_current = buy_percentage_init
sell_percentage_current = sell_percentage_init
usdt_balance_init = usdt_balance

print(f'chosen strategy: {strategy.name}')


# In[14]:


# if columns are not set properly, open the file one time and save it under .csv format
# and try again
if drop_rows:
    if row_lower_limit != 0:
        df = pd.read_csv(file,skiprows=row_lower_limit,nrows=(row_upper_limit - row_lower_limit + 1),names = ['Unix' ,'Date' ,'Symbol' ,'Open' ,'High' ,'Low' ,'Close' ,'Volume BTC','Volume USDT','tradecount'])
    else:
        df = pd.read_csv(file,skiprows=row_lower_limit,nrows=(row_upper_limit - row_lower_limit + 1))
       
else:
    df = pd.read_csv(file)

df.head()


# In[15]:


df.describe()


# In[16]:


df.columns


# In[17]:


df.iloc[0]


# In[18]:


if row_lower_limit == 0 and drop_rows:
    df.columns = df.iloc[0]
    df = df.drop(0)
    df.head()


# In[19]:


cdf = df[['Date','Open','High','Low','Close']]
cdf.head()


# In[20]:


cdf.describe()


# In[21]:


print(type(cdf['Open'][1]))
print(type(cdf['High'][1]))


# In[22]:


import warnings
warnings.filterwarnings('ignore')

cdf['Open'] = pd.to_numeric(cdf['Open'])
cdf['High'] = pd.to_numeric(cdf['High'])
cdf['Low'] = pd.to_numeric(cdf['Low'])
cdf['Close'] = pd.to_numeric(cdf['Close'])

print(type(cdf['Open'][1]))
print(type(cdf['High'][1]))


# In[23]:


cdf['isGreen'] = cdf["Close"]
cdf['bodyLen'] = abs(cdf["Close"] - cdf["Open"])
cdf['bodyLen_normalised'] = abs(cdf["Close"] - cdf["Open"]) / cdf['Open']
cdf = cdf.reset_index()
del cdf['index']
cdf.head()


# In[24]:


cdf.describe()


# In[25]:


del cdf['High']
del cdf['Low']

for i in range(len(cdf)):
    tmp = cdf.loc[i,cdf.columns.values]
    if tmp['Open'] <= tmp['Close']:
        tmp['isGreen'] = 1
    else:
        tmp['isGreen'] = 0

    cdf.loc[i] = tmp.values
        
cdf.head(10)


# In[26]:


cdf.tail()


# In[27]:


def updateTotalBalance(i):
    global usdt_balance, bitcoin_balance, total_balance
    total_balance = usdt_balance + bitcoin_balance * cdf.loc[i]["Close"]


# In[28]:


def buyBTC(i):
    global usdt_balance, bitcoin_balance, total_balance,buyPositionsNumber, sellPositionsNumber
    global buyDuplicateChecker,sellDuplicateChecker, learning_rate, buy_percentage_current
    global buy_percentage_init, sell_percentage_current, sell_percentage_init
   
    buyDuplicateChecker += 1
    sellDuplicateChecker = 0
    # if buyDuplicateChecker != 3:
    #     return
    
    buyDuplicateChecker = 0
    buyDuplicateChecker = 0
    print("\033[92m \033[1m{}\033[00m" .format(f"buy opportunity!\n"))        

    if usdt_balance > 0:
        buyPositionsNumber += 1
        
        print(f'current buy percentage: {buy_percentage_current}')
        amountToBuy_usdt = total_balance * buy_percentage_current / 100
        buy_percentage_current *= learning_rate
        sell_percentage_current = sell_percentage_init
        
        if amountToBuy_usdt > usdt_balance:
            amountToBuy_usdt = usdt_balance
            
        addedBitcoinAmount = np.longdouble(amountToBuy_usdt / cdf.loc[i]["Close"])
        usdt_balance -= amountToBuy_usdt
        bitcoin_balance += addedBitcoinAmount
        updateTotalBalance(i)
        print(f'\tbought {amountToBuy_usdt} $ BTC ({addedBitcoinAmount} BTCs) in {cdf.loc[i]["Date"]}')
        print(f"\tnew usdt balance: {usdt_balance}")
        print(f'\tnew bitcoin balance: {bitcoin_balance} ({bitcoin_balance * cdf.loc[i]["Close"]} $)')
        
    else:
        print(f"\tthere isn't any usdt to buy BTC with it!")
        print(f'\tcurrent BTC balance: {bitcoin_balance} ({bitcoin_balance * cdf.loc[i]["Close"]} $)')


# In[29]:


def sellBTC(i):
    global usdt_balance, bitcoin_balance, total_balance,buyPositionsNumber, sellPositionsNumber
    global sellDuplicateChecker,buyDuplicateChecker, buy_percentage_current, buy_percentage_init
    global sell_percentage_current, sell_percentage_init, learning_rate
    
    sellDuplicateChecker += 1
    buyDuplicateChecker = 0
    # if sellDuplicateChecker != 3:
    #     return
    
    buyDuplicateChecker = 0
    sellDuplicateChecker = 0
    print("\033[91m \033[1m{}\033[00m" .format(f"sell opportunity!\n"))        
    if bitcoin_balance > 0:
        sellPositionsNumber += 1
        
        currentValueOfAllBitcoins = bitcoin_balance * cdf.loc[i]["Close"]
        
        print(f'current sell percentage: {sell_percentage_current}')
        amountToSell_usdt = total_balance * sell_percentage_current / 100
        sell_percentage_current *= learning_rate
        buy_percentage_current = buy_percentage_init
        
        if amountToSell_usdt > currentValueOfAllBitcoins:
            amountToSell_usdt = currentValueOfAllBitcoins
        
        amountToSell_bitcoin = amountToSell_usdt / cdf.loc[i]["Close"]
        usdt_balance += amountToSell_usdt
        bitcoin_balance -= amountToSell_bitcoin
        updateTotalBalance(i)
        print(f'\tsold {amountToSell_usdt} $ of BTC ({amountToSell_usdt} $) in {cdf.loc[i]["Date"]}')
        print(f"\tnew usdt balance: {usdt_balance}")
        print(f'\tnew bitcoin balance: {bitcoin_balance} ({bitcoin_balance * cdf.loc[i]["Close"]} $)')
        
    else:
        print(f"\tthere isn't any bitcoin to sell!")
        print(f'\tcurrent USDT balance: {usdt_balance} $')


# In[43]:


def checkForPosition(i,strategy):
    if strategy == Strategy.THREESOLDIERS:
        if i >= len(cdf) - 2:
            return
        suitableForBuy = False
        suitableForSell = False
    #     print(f'i = {i}:')

        if cdf.loc[0 + i]['isGreen'] == 1.0:
            if cdf.loc[1 + i]['isGreen'] == 1.0:
                if cdf.loc[2 + i]['isGreen'] == 1.0:
                    if cdf.loc[1 + i]['bodyLen'] / cdf.loc[0 + i]['bodyLen'] >= threesoldiers_body_condition[0]:
                        if cdf.loc[2 + i]['bodyLen'] / cdf.loc[1 + i]['bodyLen'] >= threesoldiers_body_condition[1]:
                            suitableForBuy = True
                
        if cdf.loc[0 + i]['isGreen'] == 0.0:
            if cdf.loc[1 + i]['isGreen'] == 0.0:
                if cdf.loc[2 + i]['isGreen'] == 0.0:
                    if cdf.loc[1 + i]['bodyLen'] / cdf.loc[0 + i]['bodyLen'] >= threesoldiers_body_condition[0]:
                        if cdf.loc[2 + i]['bodyLen'] / cdf.loc[1 + i]['bodyLen'] >= threesoldiers_body_condition[1]:
                            suitableForSell = True
                
    if strategy == Strategy.ENGULFING:
        if i >= len(cdf) - 1:
            return
        suitableForBuy = False
        suitableForSell = False
    #     print(f'i = {i}:')

        if cdf.loc[0 + i]['isGreen'] == 1.0:
            if cdf.loc[1 + i]['isGreen'] == 0.0:
#                     if cdf.loc[1 + i]['bodyLen'] / cdf.loc[0 + i]['bodyLen'] >= engulfing_body_condition:
                    if cdf.loc[0 + i]['bodyLen'] / cdf.loc[1 + i]['bodyLen'] >= engulfing_body_condition:
                        suitableForBuy = True
                
        if cdf.loc[0 + i]['isGreen'] == 0.0:
            if cdf.loc[1 + i]['isGreen'] == 1.0:
#                 if cdf.loc[2 + i]['isGreen'] == 0.0: # not sure if this line is neceesary?
#                 if cdf.loc[1 + i]['bodyLen'] / cdf.loc[0 + i]['bodyLen'] >= engulfing_body_condition:
                if cdf.loc[0 + i]['bodyLen'] / cdf.loc[1 + i]['bodyLen'] >= engulfing_body_condition:
                    suitableForSell = True
                

        if suitableForBuy:
    #         print(f'{i} is suitable for buy!')
            buyBTC(i)

        if suitableForSell:
    #         print(f"{i} is suitable for sell!")
            sellBTC(i)

    #     if not (suitableForBuy or suitableForSell):
    #         print(f'{i} is not suitable for buy nor sell!')


# In[44]:


def timeout(i):
    global usdt_balance, bitcoin_balance, total_balance,buyPositionsNumber, sellPositionsNumber, counter
    updateTotalBalance(i)
    print("\033[91m \033[1m{}\033[00m" .format(f"\n\t\tCOUNTER REACHER IT'S MAXIMUM!\n"))
    print("\033[91m \033[1m{}\033[00m" .format(f"\t\topened {buyPositionsNumber} buypositions and {sellPositionsNumber} sell positions!\n"))
    print("\033[91m \033[1m{}\033[00m" .format(f"\t\tcurrent usdt balance: {usdt_balance}\n"))
    print("\033[91m \033[1m{}\033[00m" .format(f"\t\tcurrent bitcoin balance: {bitcoin_balance} ({bitcoin_balance * cdf.loc[i]['Close']} $)\n"))
    print("\033[91m \033[1m{}\033[00m" .format(f"\t\tcurrent total balance: {total_balance}\n"))
    counter = 0
    buyPositionsNumber = 0
    sellPositionsNumber = 0
    return total_balance


# In[45]:


def calculatePeriod():
    global audit, interval, period
    if audit == Audit.MONTHLY:
        if interval == Interval.DAILY_ONEDAY:
            period = 30
        if interval == Interval.HOURLY_FOURHOUR:
            period = 6 * 30
        if interval == Interval.HOURLY_ONEHOUR:
            period = 24 * 30
            
    if audit == Audit.WEEKLY:
        if interval == Interval.DAILY_ONEDAY:
            period = 7
        if interval == Interval.HOURLY_FOURHOUR:
            period = 6 * 7
        if interval == Interval.HOURLY_ONEHOUR:
            period = 24 * 7


# In[46]:


totals = []
counter = 0
total_counter = 0

calculatePeriod()
for i in range(len(cdf) -1, -1, -1):
    
    for strategy in strategies:
#         print(f'i = {i}, strategy = {strategy}')
        checkForPosition(i,strategy)
        counter += 1
        if counter == period:
            totals.append(timeout(i))
            total_counter += 1
        if total_counter == period_counter:
            print(f"new month!,\n\t{add_each_month} $ added to USDT balance.")
            usdt_balance += add_each_month
            total_counter = 0


# In[47]:


print("totals:")
for i in totals:
    print(i)
print(f"min: {min(totals)}, max: {max(totals)}")
# print(f"all buy and no change: {usdt_balance_init * (cdf.iloc[0]['Close'] / cdf.iloc[len(cdf) - 1]['Close'])}")


# ### ############################################################

# 
# 

# In[25]:


min(totals)


# In[ ]:




