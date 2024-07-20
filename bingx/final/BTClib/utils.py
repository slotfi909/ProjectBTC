from BTClib.datatypes import *
from BTClib.constants import *
from BTClib.other import *
from BTClib.constants import _limit_orders

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

def add_limit_order_to_queue(limit_order_result: dict[str, any]):
    orderId = limit_order_result['orderId']
    orderSymbol = limit_order_result['symbol']
    order_object = order_detail(orderSymbol,orderId)
    _limit_orders.append(order_object)

def check_order_timeout(bingx_client: BingX):
    global _limit_orders
    for order in _limit_orders:
        order.timeout_counter -= 1
        if order.timeout_counter <= 0:
            cancel_result = bingx_client.spot.trade.cancel_order(order.orderId,order.symbol)
            print(f"order for symbol {order.symbol} with orderId {order.orderId} canceled.")
            print(f"cancellation result: {cancel_result}")
            _limit_orders.remove(order)

def _calculateAmount(total_balance,usdt,current_price,trade_percentage_current):
    amount_usdt = total_balance * trade_percentage_current / 100
    if amount_usdt > usdt:
        amount_usdt = usdt
    amount = amount_usdt / current_price
    return amount

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

def get_times(strategy: Strategy, interval: Interval):
    timeOffset = _getIntervalAsMiliSeconds(interval)

    start_time = round(time.time() * 1e3) - timeOffset * (strategy.value)
    end_time = round(time.time() * 1e3)
    if DEBUG_MODE:
        print(f'\tcurrent interval -> {interval}')
    return start_time, end_time,timeOffset

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

def write_spot_summary(summary_dict: dict, fileAddress: str):
    if os.path.isfile(fileAddress) == True:
        os.remove(fileAddress)

    final_string = ""
    for key, value in summary_dict.items():
        final_string += f"{key}: {value}\n"
    with open(fileAddress, 'a') as summaryFile:
        summaryFile.write(final_string)
        summaryFile.write(f"\nlast updated in {time.ctime(time.time())}")

def save_to_logs_spot():
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

