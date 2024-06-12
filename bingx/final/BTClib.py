import pandas as pd
import numpy as np
import math
from bingX import BingX
import time
from bingX.spot import types
from aenum import Enum, NoAlias
from datetime import date
import sys
import os
###
DEBUG_MODE = True

old_date = ''
logFile = ''
###
###############################
# todo
# check pair_min_trade for both market trade and limit trade
# price is queried two times, once in get_total_balance and then in 
# do all the selling first the do the buy
# add option to buy all market or half market half limit
# add option to do buy and sell in different intervals
# add option of using indicators -> MAs
# add special sell/ buy/ learning rate for each strategy
# prevent buy/sell when candles bodyLens are too small
# add stop price for market trades
# add buy% and sell % in constractor of pair
# add futures!
# add max tries function for communication
# add audit
# create code way more modular
# prevent division by zero
###############################

MARKET_BUY_PERCENTAGE = 50
LIMIT_BUY_PERCENTAGE = 100 - MARKET_BUY_PERCENTAGE
MARKET_SELL_PERCENTAGE = 50
LIMIT_SELL_PERCENTAGE = 100 - MARKET_SELL_PERCENTAGE
ORDER_TIMEOUT = 4

engulfing_body_condition = 2
engulfing_first_candle_color_dont_care_buy = True
engulfing_first_candle_color_dont_care_sell = True
hammer_candle_color_dont_care = False
shooting_star_candle_color_dont_care = True
threesoldiers_body_condition = [1.01,1.02]
hammer_tail_to_body_ratio = 6
hammer_head_to_body_ratio = 0.1
shooting_star_head_to_body_ratio = 6
shooting_star_tail_to_body_ratio = 0.1


communication_max_tries = 5
buy_percentage_init = 10
sell_percentage_init = 13
learning_rate_buy = 0.9
learning_rate_sell = 1.1
buyPositionsNumber = 0
sellPositionsNumber = 0
PAIR_MIN_TRADE_USDT = 5
_limit_orders = []

class order_detail:
    global ORDER_TIMEOUT
    def __init__(self,symbol,orderId, timeout_counter_initial = ORDER_TIMEOUT):
        self.orderId = orderId
        self.symbol = symbol
        self.timeout_counter = timeout_counter_initial

class Strategy(Enum):
    _settings_ = NoAlias
    THREESOLDIERS = 3 + 1
    ENGULFING = 2 + 1
    SHOOTINGSTAR = 1 + 1 
    HAMMER = 1 + 1

class Pair:
    '''
    # attributes
        # pairName: str
        # buy_percentage_current: float
        # sell_percentage_current: float
        # strategies: list (contains multiple Strategy)
    '''
    def __init__(self) -> None:
        self._price_updated = False
        self.buy_percentage_current = buy_percentage_init
        self.sell_percentage_current = sell_percentage_init
        self.strategies = [Strategy.ENGULFING, Strategy.THREESOLDIERS, Strategy.SHOOTINGSTAR, Strategy.HAMMER]

    def __init__(self, pairName: str) -> None:
        self._price_updated = False
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

    def extract_currency_name(self) -> str:
        for index in range(len(self.pairName)):
            if self.pairName[index] == '-':
                dash_index = index
                break

        currency = self.pairName[0:dash_index]
        return currency

    def update_latest_price(self,bingx_client: BingX):
        self._price_updated = True
        res = bingx_client.spot.market.get_k_line_data(self.pairName,Interval.MINUTELY_ONEMINUTE.value)
        self._latest_price = res[0][1]

        return

    def get_latest_price(self):
        assert self._price_updated , "latest price was never set, but there was an attempt to access it!"
        return self._latest_price
        

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

def calculate_limit_price(cdf):
    open_price = cdf['open']
    close_price = cdf['close']
    body_length = cdf['bodyLen']
    if cdf['isGreen'] == 1:
        limit_price = open_price + body_length / 2
    else:
        limit_price = close_price + body_length / 2
    
    return limit_price



def read_pairs_from_file(fileAddress: str) -> list:
    if os.path.isfile(fileAddress) == False:
        with open(fileAddress,'a') as new_pairs_file:
            new_pairs_file.write('BTC-USDT\n')

    with open(fileAddress, 'r') as pairsFile:
        pairs_str = pairsFile.readlines()
    pairs = []
    for pair_str in pairs_str:
        stripped = pair_str.strip()
        pairs.append(Pair(stripped))

    return pairs

def read_interval_from_file(fileAddress: str) -> list:
    VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]

    if os.path.isfile(fileAddress) == False:
        with open(fileAddress,'a') as new_interval_file:
            new_interval_file.write('4h\n')
 
    with open(fileAddress, 'r') as intervalFile:
        interval_str = intervalFile.readline()
    interval_stripped = interval_str.strip()
    assert (interval_stripped in VALID_INTERVALS), f"given interval in file  {fileAddress} is not a valid one"

    # iterate through each interval and see whetehr it matches
    for enum_instance in Interval:
        if enum_instance.value == interval_stripped:
            enum_result = enum_instance
            break
    
    return enum_result





def save_to_logs():
    global old_date, logFile

    new_date = date.today()
    if old_date == '': # bot just started
        old_date = new_date
        logFile = open(f'./logs/log-{new_date}.txt','a')

    elif old_date != new_date:
        logFile.close()
        old_date = new_date
        logFile = open(f'./logs/log-{new_date}.txt','a')
        
    sys.stdout = logFile
    sys.stderr = logFile

def cancel_previous_orders(bingx_client: BingX,symbol: str | None = None):
    if symbol is None:
        res = bingx_client.spot.trade.cancel_order_all_orders()
    else:
        res = bingx_client.spot.trade.cancel_order_all_orders(symbol)
    if DEBUG_MODE:
        print(f'result of cancel previous orders with arg {symbol}:\n{res}')
    return res

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
        if float(record['free']) == 0:
            continue
        
        pairName = currency_name + '-USDT'
        pair = Pair(pairName)
        pair.update_latest_price(bingx_client)
        total_balance += get_pair_value(bingx_client, pair, float(record['free']))
    
    return total_balance

def get_pair_balance(bingx_client: BingX,pair: Pair) -> np.longdouble:
    
    currency = pair.extract_currency_name()

    res = bingx_client.spot.trade.get_assets()
    
    pair_balance = 0
    for record in res['balances']:
        if record['asset'] == currency:
            pair_balance = float(record['free'])
            break

    if DEBUG_MODE:
        print(f'pair balance: {pair_balance}')
    return pair_balance

def get_usdt_balance(bingx_client: BingX) -> float:

    res = bingx_client.spot.trade.get_assets()
    
    usdt_balance = 0
    for record in res['balances']:
        if record['asset'] == 'USDT':
            usdt_balance = float(record['free'])
            break

    if DEBUG_MODE:
        print(f'usdt balance: {usdt_balance}\n')
    return usdt_balance

def get_account_info(bingx_client: BingX,pair: Pair) -> float | np.longdouble:
    '''
    unused function -> replaced with get_pair and get_usdt balance
    '''
    # for index in range(len(pair.pairName)):
        # if pair.pairName[index] == '-':
            # dash_index = index
            # break
    # currency = pair.pairName[0:dash_index]

    currency = pair.extract_currency_name()

    res = bingx_client.spot.trade.get_assets()
    
    pair_balance = 0
    for record in res['balances']:
        if record['asset'] == 'USDT':
            usdt_balance = float(record['free'])
        if record['asset'] == currency:
            pair_balance = float(record['free'])

    if DEBUG_MODE:
        print(f'usdt balance: {usdt_balance}\n')
        print(f'pair balance: {pair_balance}')
    return usdt_balance, pair_balance

def get_pair_value(bingx_client: BingX,pair: Pair,pair_balance: np.longdouble) -> float:
    
    pair_balance_as_usdt = pair_balance * pair.get_latest_price()
    if DEBUG_MODE:
        print(f'pair: {pair.pairName}, pair_balance_as_usdt: {pair_balance_as_usdt}')
    return pair_balance_as_usdt

def _getIntervalAsMiliSeconds(interval: Interval):
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
    timeOffset = _getIntervalAsMiliSeconds(interval)

    start_time = round(time.time() * 1e3) - timeOffset * (strategy.value)
    end_time = round(time.time() * 1e3)
    if DEBUG_MODE:
        print(f'\tcurrent interval -> {interval}')
    return start_time, end_time,timeOffset

def get_pair_history_as_dataframe(bingx_client: BingX, pair: Pair, interval: Interval, start_time, end_time, strategy: Strategy):
    klineDataHistory = bingx_client.spot.market.get_k_line_data(pair.pairName,interval.value,start_time,end_time,strategy.value)
    
    df = pd.DataFrame(klineDataHistory)

    del df[6],df[7]
    df.columns = ['time','open','high','low','close','volume']
    cdf = df.drop(0) if len(df) == strategy.value else df

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
    # cdf.at[0,'isGreen'] = 1.0
    # cdf.at[0,'bodyLen'] = 1
    # cdf.at[0,'tailLen'] = 10
        # shootingstar
    # cdf.at[0,'bodyLen'] = 1
    # cdf.at[0,'headLen'] = 10
    
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
                    if cdf.loc[0]['headLen'] / cdf.loc[0]['bodyLen'] <= hammer_head_to_body_ratio:
                       self.suitableForBuy = True 
            
            return self.suitableForBuy, self.suitableForSell
 
    class SHOOTINGSTAR:
        def __init__(self) -> None:
            self.suitableForBuy = False
            self.suitableForSell = False

        def checkData(self,cdf) -> bool | bool:               
            if cdf.loc[0]['isGreen'] == 0.0 or shooting_star_candle_color_dont_care:
                if cdf.loc[0]['headLen'] / cdf.loc[0]['bodyLen'] >= shooting_star_head_to_body_ratio:
                    if cdf.loc[0]['tailLen'] / cdf.loc[0]['bodyLen'] <= shooting_star_tail_to_body_ratio:
                        self.suitableForSell = True 
            
            return self.suitableForBuy, self.suitableForSell
               
def check_position(cdf : pd.DataFrame, strategy: Strategy):
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

    return suitableForBuy, suitableForSell

def _calculateAmount(total_balance,usdt,current_price,trade_percentage_current):
    amount_usdt = total_balance * trade_percentage_current / 100
    if amount_usdt > usdt:
        amount_usdt = usdt
    amount = amount_usdt / current_price
    return amount

def create_market_order(pair: Pair, side: types.Side, amount):

    created_order = types.Order(symbol=pair.pairName, side=side,type=types.OrderType.MARKET,quote_order_qty=amount,quantity=amount)
    return created_order


def create_limit_order(pair: Pair, side: types.Side, amount, price):
    created_order = types.Order(symbol=pair.pairName, side=side,type=types.OrderType.LIMIT,quote_order_qty=amount,quantity=amount, price=price)
    return created_order

def buy_pair(bingx_client: BingX, pair: Pair, interval: Interval, total_balance, usdt_balance,limit_price):
    global buyPositionsNumber,PAIR_MIN_TRADE_USDT
    print("\033[92m \033[1m{}\033[00m" .format(f"buy opportunity!\n"))
    if DEBUG_MODE == True:
        print(f'current buy percentage: {pair.buy_percentage_current}')

    buyPositionsNumber += 1
    last_price = pair.get_latest_price()
    amountToBuy = _calculateAmount(total_balance,usdt_balance,last_price,pair.buy_percentage_current)
    market_amount = amountToBuy * (MARKET_BUY_PERCENTAGE) / 100
    limit_amount = amountToBuy - market_amount

    market_order_placed, limit_order_placed = False, False
    if market_amount * last_price > PAIR_MIN_TRADE_USDT: # market order is possible
        order_market_buy = create_market_order(pair,types.Side.BUY,market_amount)
        if DEBUG_MODE == False:
            market_order_result = bingx_client.spot.trade.create_order(order_market_buy)
        market_order_placed = True
    else:
        print("USDT balance lower than minimum for market buy")

    if limit_amount * last_price > PAIR_MIN_TRADE_USDT: # limit order is possible
        order_limit_buy = create_limit_order(pair,types.Side.BUY,limit_amount,limit_price)
        if DEBUG_MODE == False:
            limit_order_result = bingx_client.spot.trade.create_order(order_limit_buy)
        limit_order_placed = True
    else:
        print("USDT balance lower than minimum for limit buy")

    if market_order_placed or limit_order_placed:
        pair.buy_percentage_current *= learning_rate_buy

    return market_order_placed, limit_order_placed, pair.buy_percentage_current
    

def check_order_timeout(bingx_client: BingX):
    global _limit_orders
    for order in _limit_orders:
        order.timeout_counter -= 1
        if order.timeout_counter <= 0:
            cancel_result = bingx_client.spot.trade.cancel_order(order.orderId,order.symbol)
            print(f"order for symbol {order.symbol} with orderId {order.orderId} canceled.")
            print(f"cancellation result: {cancel_result}")
            _limit_orders.remove(order)


def sell_pair(bingx_client: BingX, pair: Pair, interval: Interval, total_balance,pair_balance,limit_price):
    global sellPositionsNumber,PAIR_MIN_TRADE_USDT,DEBUG_MODE
    sellPositionsNumber += 1
    print("\033[92m \033[1m{}\033[00m" .format(f"sell opportunity!\n"))  

    if DEBUG_MODE:
        print(f'current sell percentage: {pair.sell_percentage_current}')
    last_price = pair.get_latest_price()
    pair_value_as_usdt = get_pair_value(bingx_client,pair,pair_balance)
    amountToSell = _calculateAmount(total_balance, pair_value_as_usdt, last_price, pair.sell_percentage_current)

    market_amount = amountToSell * (MARKET_SELL_PERCENTAGE) / 100
    limit_amount = amountToSell - market_amount
    market_order_placed, limit_order_placed = False, False
    if market_amount * last_price > PAIR_MIN_TRADE_USDT: # market order is possible
        order_market_sell = create_market_order(pair,types.Side.SELL,market_amount)
        if DEBUG_MODE == False:
            market_order_result = bingx_client.spot.trade.create_order(order_market_sell)
        market_order_placed = True
    else:
        print("pair balance lower than minimum for market sell")

    if limit_amount * last_price > PAIR_MIN_TRADE_USDT: # limit order is possible
        order_limit_sell = create_market_order(pair,types.Side.SELL,limit_amount)
        if DEBUG_MODE == False:
            limit_order_result = bingx_client.spot.trade.create_order(order_limit_sell)
        limit_order_placed = True
    else:
        print("pair balance lower than minimum for limit sell")

    if market_order_placed or limit_order_placed:
        pair.sell_percentage_current *= learning_rate_sell

    return market_order_placed, limit_order_placed, pair.sell_percentage_current

def add_limit_order_to_queue(limit_order_result: dict[str, any]):
    orderId = limit_order_result['orderId']
    orderSymbol = limit_order_result['symbol']
    order_object = order_detail(orderSymbol,orderId)
    _limit_orders.append(order_object)


def calibre_time(interval: Interval):
    current_time = time.time()
    print(f'current time: {time.ctime(current_time)}')
    current_time *= 1000
    intervalAsMiliSeconds = _getIntervalAsMiliSeconds(interval)
    timePassed = current_time % intervalAsMiliSeconds # also as miliseconds
    sleep_time = intervalAsMiliSeconds + 1000 - timePassed
    print(f'need to sleep {sleep_time:.2f} miliseconds ({sleep_time / 1e3 // 60} minutes\
 and {(sleep_time / 1e3) % 60:.2f} seconds) to get in line with correct time!')
    print('\nsleeping...\n')
    print('======================================================')
    print('======================================================')
    sys.stdout.flush()
    time.sleep(sleep_time / 1e3)
