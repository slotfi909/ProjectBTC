import pandas as pd
import numpy as np
import math
from bingX import BingX
import time
from bingX.spot import types
from enum import Enum
from datetime import date
import sys
###
DEBUG_MODE = False
old_date = ''
logFile = ''
###
###############################
# todo
# total usdt is wrong if multiple currencies exist
# add log for each day
# add stop price for market trades
# add buy% and sell % in constractor of pair
# add file to read pais from it
# add futures!
# change functions to get interval as interval not interval.value
# search for changing stdout to a file in python
# ssh log when using python??
# add max tries function for communication
# add audit
# create code way more modular for strategy, each strategy is defined by 
# certain rules, like condtion for three white soldier
###############################


engulfing_body_condition = 2
engulfing_first_candle_color_dont_care = True
threesoldiers_body_condition = [1.01,1.02]

communication_max_tries = 5
buy_percentage_init = 10
sell_percentage_init = 13
learning_rate = 1.3
buyPositionsNumber = 0
sellPositionsNumber = 0
PAIR_MIN_TRADE_USDT = 5

        

class Strategy(Enum):
    THREESOLDIERS = 3 + 1
    ENGULFING = 2 + 1

class Pair:
    # attributes
        # pairName: str
        # buy_percentage_current: float
        # sell_percentage_current: float
        # strategies: list (contains multiple Strategy)

    def __init__(self) -> None:
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS]

    def __init__(self, pairName: str) -> None:
        self.pairName = pairName
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS]

    def setPairName(self,pairName: str) -> None:
        self.pairName = pairName

    def setStrategies(self, strategies: list) -> None:
        self.strategies = strategies

    def appendStrategies(self, strategy: Strategy) -> None:
        self.strategies.append(strategy)

    def setBuyPercentage(self, new_buy_percentage: float) -> None:
        self.buy_percentage_current = new_buy_percentage

    def setSellPercentage(self, new_sell_percentage: float) -> None:
        self.sell_percentage_current = new_sell_percentage

    def clearStrategies(self) -> None:
        self.strategies = []

    def popStrategy(self) -> None:
        assert len(self.strategies > 0), 'strategies does not have any member!'
        self.strategies.pop()


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

    
class Audit(Enum):
    WEEKLY = 1
    MONTHLY = 2

def readPairsFromFile(fileAddress: str) -> list:
    pairsFile = open(fileAddress, 'r')
    pairs_str = pairsFile.readlines()
    pairs = []
    for pair_str in pairs_str:
        stripped = pair_str.strip()
        pairs.append(Pair(stripped))

    return pairs

def saveToLogs():
    global old_date, logFile

    new_date = date.today()
    if old_date == '':
        old_date = new_date
        logFile = open(f'./logs/log-{new_date}.txt','a')

    elif old_date != new_date:
        logFile.close()
        old_date = new_date
        logFile = open(f'./logs/log-{new_date}.txt','a')
        
    sys.stdout = logFile



def get_total_balance(bingx_client) -> float:
    total_balance = float(0)
    res = bingx_client.spot.trade.get_assets()
    for record in res['balances']:
        currency_name = record['asset']
        if currency_name == 'USDT':
            total_balance += float(record['free'])
            continue
        if currency_name == 'VST':
            continue
        pairName = currency_name + '-USDT'
        klineData = bingx_client.perpetual_v2.market.get_k_line_data(pairName,Interval.MINUTELY_ONEMINUTE.value)
        pair_lastPrice = float(klineData['close'])
        total_balance += float(record['free']) * pair_lastPrice
    
    return total_balance


def get_account_info(bingx_client: BingX,pair: str) -> float | np.longdouble:
    for index in range(len(pair)):
        if pair[index] == '-':
            dash_index = index
            break
    currency = pair[0:dash_index]

    res = bingx_client.spot.trade.get_assets()
    
    pair_balance = 0
    for record in res['balances']:
        if record['asset'] == 'USDT':
            usdt_balance = float(record['free'])
        if record['asset'] == currency:
            pair_balance = float(record['free'])

    print(f'usdt balance: {usdt_balance}\n')
    print(f'pair balance: {pair_balance}')
    return usdt_balance, pair_balance

def get_pair_value(bingx_client: BingX,pair: str,usdt_balance,pair_balance: np.longdouble) -> float | float:
    res = bingx_client.perpetual_v2.market.get_k_line_data(pair,Interval.MINUTELY_ONEMINUTE.value)
    pair_balance_as_usdt = pair_balance * float(res['close'])
    print(f'pair_balance_as_usdt: {pair_balance_as_usdt}')
    return pair_balance_as_usdt

def getIntervalAsMiliSeconds(interval):
    oneMinuteAsMiliSeconds = 1 * 60 * 1000
    oneHourAsMiliSeconds = 60 * oneMinuteAsMiliSeconds
    oneDayAsMiliSeconds = 24 * oneHourAsMiliSeconds
    oneWeekAsMiliSeconds = 7 * oneDayAsMiliSeconds
    oneMonthAsMiliSeconds = 30 * oneDayAsMiliSeconds

    VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if interval not in VALID_INTERVALS:
            raise ValueError("[!] INVALID INTERVAL VALUE. Valid Intervals are: ", str(VALID_INTERVALS))


    interval_prefix = int(interval[:len(interval) - 1])
    interval_suffix = interval[-1]

    if interval_suffix == 'm':
        timeOffset = interval_prefix * oneMinuteAsMiliSeconds
    elif interval_suffix == 'h':
        timeOffset = interval_prefix * oneHourAsMiliSeconds
    elif interval_suffix == 'd':
        timeOffset = interval_prefix * oneDayAsMiliSeconds
    elif interval_suffix == 'w':
        timeOffset = interval_prefix * oneWeekAsMiliSeconds
    elif interval_suffix == 'M':
        timeOffset = interval_prefix * oneMonthAsMiliSeconds

    return timeOffset

def get_times(strategy,interval):
    timeOffset = getIntervalAsMiliSeconds(interval)

    start_time = round(time.time() * 1e3) - timeOffset * (strategy)
    end_time = round(time.time() * 1e3)
    print(f'difference(ms): {end_time - start_time}')
    print(f'difference(hour): {(end_time - start_time) / 1e3 / 60 / 60}')
    print(f'number of candles: {(end_time - start_time) / timeOffset - 1}')
    print(f'\tcurrent interval -> {interval}')
    return start_time, end_time,timeOffset

def getPairHistoryAsDataFrame(bingx_client,pair,interval,start_time,end_time):
    klineDataHistory = bingx_client.perpetual_v2.market.get_k_line_data(pair,interval,start_time,end_time)
    import warnings
    warnings.filterwarnings('ignore')

    df = pd.DataFrame(klineDataHistory)
    cdf = df.iloc[::-1]

    cdf['open'] = pd.to_numeric(cdf['open'])
    cdf['high'] = pd.to_numeric(cdf['high'])
    cdf['low'] = pd.to_numeric(cdf['low'])
    cdf['close'] = pd.to_numeric(cdf['close'])

    cdf['isGreen'] = cdf["close"]
    cdf['bodyLen'] = abs(cdf["close"] - cdf["open"])

    cdf = cdf.reset_index()
    del cdf['index']

    for i in range(len(cdf)):
        tmp = cdf.loc[i,cdf.columns.values]
        if tmp['open'] <= tmp['close']:
            tmp['isGreen'] = 1
        else:
            tmp['isGreen'] = 0

        cdf.loc[i] = tmp.values


    # for debug
        # threesoldiers
            # buy
    # cdf.at[0,'isGreen'] = 1.0
    # cdf.at[1,'isGreen'] = 1.0
    # cdf.at[2,'isGreen'] = 1.0
    # cdf.at[0,'bodyLen'] = 100
    # cdf.at[1,'bodyLen'] = 10
    # cdf.at[2,'bodyLen'] = 1
#           # sell
    # cdf.at[0,'isGreen'] = 0.0
    # cdf.at[1,'isGreen'] = 0.0
    # cdf.at[2,'isGreen'] = 0.0
    # cdf.at[0,'bodyLen'] = 100
    # cdf.at[1,'bodyLen'] = 10
    # cdf.at[2,'bodyLen'] = 1
#     # engulfing
#       # sell
    # cdf.at[0,'isGreen'] = 0.0
    # cdf.at[1,'isGreen'] = 1.0
    # cdf.at[0,'bodyLen'] = 100
    # cdf.at[1,'bodyLen'] = 10
#        # buy
    # cdf.at[0,'isGreen'] = 1.0
    # cdf.at[1,'isGreen'] = 0.0
    # cdf.at[0,'bodyLen'] = 100
    # cdf.at[1,'bodyLen'] = 10
    
    return cdf

class StrategyChecker:
    class ENGLUFING:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:
            if cdf.loc[0]['isGreen'] == 0.0:
                if cdf.loc[1]['isGreen'] == 1.0 or engulfing_first_candle_color_dont_care:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
                            self.suitableForSell = True
                
            if cdf.loc[0]['isGreen'] == 1.0:
                if cdf.loc[1]['isGreen'] == 0.0 or engulfing_first_candle_color_dont_care:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
                            self.suitableForBuy = True 
            
            return self.suitableForBuy, self.suitableForSell

    class THREESOLDIERS:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False
        def checkData(self,cdf) -> bool | bool:
            if cdf.loc[0]['isGreen'] == 1.0:
                if cdf.loc[1]['isGreen'] == 1.0:
                    if cdf.loc[2]['isGreen'] == 1.0:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
                            if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
                                self.suitableForBuy = True
                    
            if cdf.loc[0]['isGreen'] == 0.0:
                if cdf.loc[1]['isGreen'] == 0.0:
                    if cdf.loc[2]['isGreen'] == 0.0:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
                            if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
                                self.suitableForSell = True

            return self.suitableForBuy, self.suitableForSell
            
        
            
def checkPosition(cdf,strategy,interval):
    # suitableForBuy = False
    # suitableForSell = False
    
    if strategy == Strategy.THREESOLDIERS.value:
        strategyChecker = StrategyChecker.THREESOLDIERS()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)
        
        # if cdf.loc[0]['isGreen'] == 1.0:
        #     if cdf.loc[1]['isGreen'] == 1.0:
        #         if cdf.loc[2]['isGreen'] == 1.0:
        #             if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
        #                 if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
        #                     suitableForBuy = True
                
        # if cdf.loc[0]['isGreen'] == 0.0:
        #     if cdf.loc[1]['isGreen'] == 0.0:
        #         if cdf.loc[2]['isGreen'] == 0.0:
        #             if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= threesoldiers_body_condition[1]:
        #                 if cdf.loc[1]['bodyLen'] / cdf.loc[2]['bodyLen'] >= threesoldiers_body_condition[0]:
        #                     suitableForSell = True
                            
    if strategy == Strategy.ENGULFING.value:
        strategyChecker = StrategyChecker.ENGLUFING()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)
        # if cdf.loc[0]['isGreen'] == 0.0:
        #     if cdf.loc[1]['isGreen'] == 1.0 or engulfing_first_candle_color_dont_care:
        #             if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
        #                 suitableForSell = True
                
        # if cdf.loc[0]['isGreen'] == 1.0:
        #     if cdf.loc[1]['isGreen'] == 0.0 or engulfing_first_candle_color_dont_care:
        #             if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
        #                 suitableForBuy = True 
    
    print(f'suitableForBuy: {suitableForBuy}')
    print(f'suitableForSell: {suitableForSell}')
    return suitableForBuy, suitableForSell

def calculateAmount(total_balance,usdt,current_price,trade_percentage_current):
    amount_usdt = total_balance * trade_percentage_current / 100
    if amount_usdt > usdt:
        amount_usdt = usdt
    amount = amount_usdt / current_price
    return amount

    
def buyPair(bingx_client: BingX,pair,interval,total_balance,usdt_balance,buy_percentage_current):
    global buyPositionsNumber,PAIR_MIN_TRADE_USDT
    print("\033[92m \033[1m{}\033[00m" .format(f"buy opportunity!\n"))

    buyPositionsNumber += 1
    res = bingx_client.perpetual_v2.market.get_k_line_data(pair,interval)
    last_price = float(res['close'])
    amountToBuy = calculateAmount(total_balance,usdt_balance,last_price,buy_percentage_current)
       
    if amountToBuy * last_price > PAIR_MIN_TRADE_USDT:

        print(f'current buy percentage: {buy_percentage_current}')
        order = types.Order(symbol=pair,side=types.Side.BUY,type=types.OrderType.MARKET,quote_order_qty=amountToBuy,quantity=amountToBuy)
        print(f'created order: {order.to_dict()}')
        if DEBUG_MODE == False:
           res = bingx_client.spot.trade.create_order(order)
        buy_percentage_current *= learning_rate
        return res, buy_percentage_current

    else:
            print("\tUSDT balance lower than minimum for buying!")
            return 0, buy_percentage_current
        

def sellPair(bingx_client,pair,interval,total_balance,pair_balance,sell_percentage_current):
    global sellPositionsNumber,PAIR_MIN_TRADE_USDT,DEBUG_MODE
    print("\033[92m \033[1m{}\033[00m" .format(f"sell opportunity!\n"))  

    print(f'current sell percentage: {sell_percentage_current}')
    res = bingx_client.perpetual_v2.market.get_k_line_data(pair,interval)
    last_price = float(res['close'])
    pair_value_as_usdt = pair_balance * last_price
    amountToSell = calculateAmount(total_balance,pair_value_as_usdt,last_price,sell_percentage_current)


    if amountToSell * last_price > PAIR_MIN_TRADE_USDT:
        order = types.Order(symbol=pair,side=types.Side.SELL,type=types.OrderType.MARKET,quote_order_qty=amountToSell,quantity=amountToSell)
        print(f'created order: {order.to_dict()}')
        if DEBUG_MODE == False:
            res = bingx_client.spot.trade.create_order(order)
        sell_percentage_current *= learning_rate
        return res, sell_percentage_current
    else:
            print("\tpair balance lower than minumum for selling!")
            return 0, sell_percentage_current

def calibreTime(interval):
    current_time = time.time()
    print(f'current time: {time.ctime(current_time)}')
    current_time *= 1000
    intervalAsMiliSeconds = getIntervalAsMiliSeconds(interval)
    timePassed = current_time % intervalAsMiliSeconds # also as miliseconds
    sleep_time = intervalAsMiliSeconds + 1000 - timePassed
    print(f'need to sleep {sleep_time:.2f} miliseconds ({sleep_time / 1e3 // 60} minutes\
 and {(sleep_time / 1e3) % 60:.2f} seconds) to get in line with correct time!')
    print('\nsleeping...\n')
    print('======================================================')
    print('======================================================')
    time.sleep(sleep_time / 1e3)