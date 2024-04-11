import pandas as pd
import numpy as np
import math
from bingX import BingX
import time
from bingX.spot import types
from aenum import Enum, NoAlias
from datetime import date
import sys
###
DEBUG_MODE = False
old_date = ''
logFile = ''
###
###############################
# todo
# do all the selling first the do the buy
# add option to buy all market or half market half limit
# add option to do buy and sell in different intervals
# add stop price for market trades
# add buy% and sell % in constractor of pair
# add futures!
# add max tries function for communication
# add audit
# create code way more modular
###############################


engulfing_body_condition = 2
engulfing_first_candle_color_dont_care_buy = False
engulfing_first_candle_color_dont_care_sell = True
hammer_candle_color_dont_care = False
shooting_star_candle_color_dont_care = True
threesoldiers_body_condition = [1.01,1.02]
hammer_tail_to_body_ratio = 6
shooting_star_head_to_body_ratio = 6

communication_max_tries = 5
buy_percentage_init = 10
sell_percentage_init = 13
learning_rate_buy = 0.9
learning_rate_sell = 1.1
buyPositionsNumber = 0
sellPositionsNumber = 0
PAIR_MIN_TRADE_USDT = 5

        

class Strategy(Enum):
    _settings_ = NoAlias
    THREESOLDIERS = 3 + 1
    ENGULFING = 2 + 1
    SHOOTINGSTAR = 1 + 1 
    HAMMER = 1 + 1

class Pair:
    # attributes
        # pairName: str
        # buy_percentage_current: float
        # sell_percentage_current: float
        # strategies: list (contains multiple Strategy)

    def __init__(self) -> None:
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS, Strategy.SHOOTINGSTAR, Strategy.HAMMER]

    def __init__(self, pairName: str) -> None:
        self.pairName = pairName
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS, Strategy.SHOOTINGSTAR, Strategy.HAMMER]

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
    sys.stderr = logFile



def get_total_balance(bingx_client: BingX) -> float:
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
        klineData = bingx_client.spot.market.get_k_line_data(pairName,Interval.MINUTELY_ONEMINUTE.value)
        # pair_lastPrice = float(klineData['close'])
        pair_lastPrice = float(klineData[0][1])
        total_balance += float(record['free']) * pair_lastPrice
    
    return total_balance


def get_account_info(bingx_client: BingX,pair: Pair) -> float | np.longdouble:
    for index in range(len(pair.pairName)):
        if pair.pairName[index] == '-':
            dash_index = index
            break
    currency = pair.pairName[0:dash_index]

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

def get_pair_value(bingx_client: BingX,pair: Pair,usdt_balance,pair_balance: np.longdouble) -> float | float:
    res = bingx_client.spot.market.get_k_line_data(pair.pairName,Interval.MINUTELY_ONEMINUTE.value)
    # pair_balance_as_usdt = pair_balance * float(res['close'])
    pair_balance_as_usdt = pair_balance * res[0][1]
    print(f'pair_balance_as_usdt: {pair_balance_as_usdt}')
    return pair_balance_as_usdt

def getIntervalAsMiliSeconds(interval: Interval):
    oneMinuteAsMiliSeconds = 1 * 60 * 1000
    oneHourAsMiliSeconds = 60 * oneMinuteAsMiliSeconds
    oneDayAsMiliSeconds = 24 * oneHourAsMiliSeconds
    oneWeekAsMiliSeconds = 7 * oneDayAsMiliSeconds
    oneMonthAsMiliSeconds = 30 * oneDayAsMiliSeconds

    VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if interval.value not in VALID_INTERVALS:
        raise ValueError("[!] INVALID INTERVAL VALUE. Valid Intervals are: ", str(VALID_INTERVALS))


    interval_prefix = int(interval.value[:len(interval.value) - 1])
    interval_suffix = interval.value[-1]

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

def get_times(strategy: Strategy, interval: Interval):
    timeOffset = getIntervalAsMiliSeconds(interval)

    start_time = round(time.time() * 1e3) - timeOffset * (strategy.value)
    end_time = round(time.time() * 1e3)
    print(f'difference(ms): {end_time - start_time}')
    print(f'difference(hour): {(end_time - start_time) / 1e3 / 60 / 60}')
    print(f'number of candles: {(end_time - start_time) / timeOffset - 1}')
    print(f'\tcurrent interval -> {interval}')
    return start_time, end_time,timeOffset

def getPairHistoryAsDataFrame(bingx_client: BingX, pair: Pair, interval: Interval, start_time, end_time, strategy: Strategy):
    klineDataHistory = bingx_client.spot.market.get_k_line_data(pair.pairName,interval.value,start_time,end_time,strategy.value)
    import warnings
    warnings.filterwarnings('ignore')

    df = pd.DataFrame(klineDataHistory)
    # cdf = df.iloc[::-1]

    # cdf['open'] = pd.to_numeric(cdf['open'])
    # cdf['high'] = pd.to_numeric(cdf['high'])
    # cdf['low'] = pd.to_numeric(cdf['low'])
    # cdf['close'] = pd.to_numeric(cdf['close'])
    ###
    del df[6],df[7]
    df.columns = ['time','open','high','low','close','volume']
    cdf = df.drop(0) if len(df) == strategy.value else df
    # cdf = df
    ###
    cdf['isGreen'] = cdf["close"]
    cdf['headLen'] = cdf['close']
    cdf['tailLen'] = cdf['close']
    cdf['bodyLen'] = abs(cdf["close"] - cdf["open"])

    cdf = cdf.reset_index()
    del cdf['index']

    for i in range(len(cdf)):
        tmp = cdf.loc[i,cdf.columns.values]
        if tmp['open'] <= tmp['close']: # is green
            tmp['isGreen'] = 1
            tmp['headLen'] = tmp['high'] - tmp['close']
            tmp['tailLen'] = tmp['open'] - tmp['low']
        else:
            tmp['isGreen'] = 0
            tmp['headLen'] = tmp['high'] - tmp['open']
            tmp['tailLen'] = tmp['close'] - tmp['low']

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
        # hammer
    cdf.at[0,'isGreen'] = 1.0
    cdf.at[0,'bodyLen'] = 1
    cdf.at[0,'tailLen'] = 10
        # shootingstar
    cdf.at[0,'bodyLen'] = 1
    cdf.at[0,'headLen'] = 10
    
    return cdf

class StrategyChecker:
    class ENGLUFING:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:
            if cdf.loc[0]['isGreen'] == 0.0:
                if cdf.loc[1]['isGreen'] == 1.0 or engulfing_first_candle_color_dont_care_sell:
                        if cdf.loc[0]['bodyLen'] / cdf.loc[1]['bodyLen'] >= engulfing_body_condition:
                            self.suitableForSell = True
                
            if cdf.loc[0]['isGreen'] == 1.0:
                if cdf.loc[1]['isGreen'] == 0.0 or engulfing_first_candle_color_dont_care_buy:
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
            
    class HAMMER:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:               
            if cdf.loc[0]['isGreen'] == 1.0 or hammer_candle_color_dont_care:
                if cdf.loc[0]['tailLen'] / cdf.loc[0]['bodyLen'] >= hammer_tail_to_body_ratio:
                    self.suitableForBuy = True 
            
            return self.suitableForBuy, self.suitableForSell
 
    class SHOOTINGSTAR:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:               
            if cdf.loc[0]['isGreen'] == 0.0 or shooting_star_candle_color_dont_care:
                if cdf.loc[0]['headLen'] / cdf.loc[0]['bodyLen'] >= shooting_star_head_to_body_ratio:
                    self.suitableForSell = True 
            
            return self.suitableForBuy, self.suitableForSell
        
            
def checkPosition(cdf : pd.DataFrame, strategy: Strategy):
    # suitableForBuy = False
    # suitableForSell = False
    
    if strategy == Strategy.THREESOLDIERS:
        strategyChecker = StrategyChecker.THREESOLDIERS()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)
                                   
    elif strategy == Strategy.ENGULFING:
        strategyChecker = StrategyChecker.ENGLUFING()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)

    elif strategy == Strategy.SHOOTINGSTAR:
        strategyChecker = StrategyChecker.SHOOTINGSTAR()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)

    elif strategy == Strategy.HAMMER:
        strategyChecker = StrategyChecker.HAMMER()
        suitableForBuy, suitableForSell = strategyChecker.checkData(cdf)

    
    print(f'suitableForBuy: {suitableForBuy}')
    print(f'suitableForSell: {suitableForSell}')
    return suitableForBuy, suitableForSell

def calculateAmount(total_balance,usdt,current_price,trade_percentage_current):
    amount_usdt = total_balance * trade_percentage_current / 100
    if amount_usdt > usdt:
        amount_usdt = usdt
    amount = amount_usdt / current_price
    return amount

    
def buyPair(bingx_client: BingX, pair: Pair, interval: Interval, total_balance, usdt_balance):
    global buyPositionsNumber,PAIR_MIN_TRADE_USDT
    print("\033[92m \033[1m{}\033[00m" .format(f"buy opportunity!\n"))

    buyPositionsNumber += 1
    res = bingx_client.spot.market.get_k_line_data(pair.pairName, interval.value)
    # last_price = float(res['close'])
    last_price = res[0][1]
    amountToBuy = calculateAmount(total_balance,usdt_balance,last_price,pair.buy_percentage_current)
       
    if amountToBuy * last_price > PAIR_MIN_TRADE_USDT:

        print(f'current buy percentage: {pair.buy_percentage_current}')
        order = types.Order(symbol=pair.pairName, side=types.Side.BUY,type=types.OrderType.MARKET,quote_order_qty=amountToBuy,quantity=amountToBuy)
        print(f'created order: {order.to_dict()}')
        if DEBUG_MODE == False:
           res = bingx_client.spot.trade.create_order(order)
        pair.buy_percentage_current *= learning_rate_buy
        return res, pair.buy_percentage_current

    else:
            print("\tUSDT balance lower than minimum for buying!\n")
            return 0, pair.buy_percentage_current
        

def sellPair(bingx_client: BingX, pair: Pair, interval: Interval, total_balance,pair_balance):
    global sellPositionsNumber,PAIR_MIN_TRADE_USDT,DEBUG_MODE
    print("\033[92m \033[1m{}\033[00m" .format(f"sell opportunity!\n"))  

    print(f'current sell percentage: {pair.sell_percentage_current}')
    res = bingx_client.spot.market.get_k_line_data(pair.pairName, interval.value)
    # last_price = float(res['close'])
    last_price = res[0][1]
    pair_value_as_usdt = pair_balance * last_price
    amountToSell = calculateAmount(total_balance, pair_value_as_usdt, last_price, pair.sell_percentage_current)


    if amountToSell * last_price > PAIR_MIN_TRADE_USDT:
        order = types.Order(symbol=pair.pairName, side=types.Side.SELL,type=types.OrderType.MARKET,quote_order_qty=amountToSell,quantity=amountToSell)
        print(f'created order: {order.to_dict()}')
        if DEBUG_MODE == False:
            res = bingx_client.spot.trade.create_order(order)
        pair.sell_percentage_current *= learning_rate_sell
        return res, pair.sell_percentage_current
    else:
        print("\tpair balance lower than minumum for selling!\n")
        return 0, pair.sell_percentage_current

def calibreTime(interval: Interval):
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
    sys.stdout.flush()
    time.sleep(sleep_time / 1e3)
