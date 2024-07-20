from BTClib.datatypes import *
from BTClib.constants import *
from BTClib.other import *
from BTClib.utils import *
from BTClib.utils import _calculateAmount
from BTClib.constants import _limit_orders

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

def create_limit_order(pair: Pair, side: types.Side, amount, price):
    created_order = types.Order(symbol=pair.pairName, side=side,type=types.OrderType.LIMIT,quote_order_qty=amount,quantity=amount, price=price)
    return created_order

def create_market_order(pair: Pair, side: types.Side, amount):

    created_order = types.Order(symbol=pair.pairName, side=side,type=types.OrderType.MARKET,quote_order_qty=amount,quantity=amount)
    return created_order

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

def get_pair_value(bingx_client: BingX,pair: Pair,pair_balance: np.longdouble) -> float:
    
    pair_balance_as_usdt = pair_balance * pair.get_latest_price()
    if DEBUG_MODE:
        print(f'pair: {pair.pairName}, pair_balance_as_usdt: {pair_balance_as_usdt}')
    return pair_balance_as_usdt

def get_account_summary(bingx_client: BingX) -> dict:
    if DEBUG_MODE:
        print("account summary: ")
    summary_dict = {}
    
    total_balance = float(0)
    res = bingx_client.spot.trade.get_assets()
    for record in res['balances']:
        currency_name = record['asset']
        if currency_name == 'USDT':
            summary_dict['USDT'] = record['free']
            total_balance += float(record['free'])
            continue
        if currency_name == 'VST':
            continue
        if float(record['free']) == 0:
            continue
        
        pairName = currency_name + '-USDT'
        pair = Pair(pairName)
        pair.update_latest_price(bingx_client)
        pair_balance_as_usdt = get_pair_value(bingx_client, pair, float(record['free']))
        summary_dict[pairName] = [float(record['free']), pair_balance_as_usdt]
        total_balance += pair_balance_as_usdt
    summary_dict['total_balance'] = total_balance
    
    return summary_dict

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

def cancel_previous_orders(bingx_client: BingX,symbol: str | None = None):
    if DEBUG_MODE == False:
            # print(f'result of cancel previous orders with arg {symbol}:\n{res}')
        if symbol is None:
            res = bingx_client.spot.trade.cancel_order_all_orders()
        else:
            res = bingx_client.spot.trade.cancel_order_all_orders(symbol)
        return res

    else:
        print("not canceling any order is debug mode is ON...")
        return
        
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
