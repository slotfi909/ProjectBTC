import BTClib
import time
import sys

secret_key = "WqP5txrWtmbGcMND5GjFiBZICth5nZFIXYKEPqKitRl7xOHVGOFzNo8yNCLQUmK4guPTNgV4nwKLT0aD5iYIg"
api_key = "SbyekABHMR0SyrIQKTqU14sExh5m40sV5a6jaBenI26u5SDm8z4gGzQCLamCp6Ww2uJyVjyhJQESk4Gt5jA"
pairs = ['BTC-USDT','ETH-USDT']
interval = BTClib.Interval.HOURLY_ONEHOUR
test = "BTC-USDT"

strategy = BTClib.Strategy.ENGULFING
buy_percentage_current = BTClib.buy_percentage_init
sell_percentage_current = BTClib.sell_percentage_init

bingx_client = BTClib.BingX(api_key=api_key, secret_key=secret_key)
while(True):
    
    BTClib.calibreTime(interval.value)

    for pair in pairs:

        print(f"\nnew try at {time.ctime(time.time())} for pair {pair}:\n")

        usdt_balance, pair_balance = BTClib.get_account_info(bingx_client,pair)

        pair_balance_as_usdt, total_balance = BTClib.update_balance_info(bingx_client,pair,interval.value,usdt_balance,pair_balance)

        start_time, end_time,intervalAsMillisecond = BTClib.get_times(strategy.value,interval.value)

        cdf = BTClib.getPairHistoryAsDataFrame(bingx_client,pair,interval.value,start_time,end_time)

        print(f'current pair data:\n{cdf}\n')

        suitableForBuy, suitableForSell = BTClib.checkPosition(cdf,strategy.value,interval.value)

        res = 0
        if suitableForBuy:
            res, buy_percentage_current = BTClib.buyPair(bingx_client,pair,interval.value,total_balance,usdt_balance,buy_percentage_current)

        if suitableForSell:
            res, sell_percentage_current = BTClib.sellPair(bingx_client,pair,interval.value,total_balance,pair_balance,sell_percentage_current)

        if res != 0:
            print(f"order result:\n{res}\n")
            if suitableForBuy:
                sell_percentage_current = BTClib.sell_percentage_init
                print('sell percentage successfully reset')
            if suitableForSell:
                buy_percentage_current = BTClib.buy_percentage_init
                print('buy percentage successfully reset')

        print("\n====================\n")
        