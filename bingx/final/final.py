import BTClib
import time
import sys
import os

secret_key = "WqP5txrWtmbGcMND5GjFiBZICth5nZFIXYKEPqKitRl7xOHVGOFzNo8yNCLQUmK4guPTNgV4nwKLT0aD5iYIg"
api_key = "SbyekABHMR0SyrIQKTqU14sExh5m40sV5a6jaBenI26u5SDm8z4gGzQCLamCp6Ww2uJyVjyhJQESk4Gt5jA"

# prepairing pairs
pairs = BTClib.readPairsFromFile('./pairs.txt')

# set interval
interval = BTClib.Interval.HOURLY_ONEHOUR

bingx_client = BTClib.BingX(api_key=api_key, secret_key=secret_key)

###############
##playground
###############
while(True):
    
    BTClib.saveToLogs()

    BTClib.calibreTime(interval)

    for pair in pairs:

        print(f"\nnew try at {time.ctime(time.time())} for pair {pair.pairName}:\n")

        balances_changed = True
        for strategy in pair.strategies:

            if balances_changed:

                usdt_balance, pair_balance = BTClib.get_account_info(bingx_client,pair)

                pair_balance_as_usdt = BTClib.get_pair_value(bingx_client,pair,usdt_balance,pair_balance)

            total_balance = BTClib.get_total_balance(bingx_client)

            start_time, end_time,intervalAsMillisecond = BTClib.get_times(strategy,interval)

            cdf = BTClib.getPairHistoryAsDataFrame(bingx_client,pair,interval,start_time,end_time,strategy)

            print(f'\ncurrent pair data for strategy {strategy}:\n{cdf}\n')

            suitableForBuy, suitableForSell = BTClib.checkPosition(cdf,strategy)

            res = 0
            balances_changed = False
            if suitableForBuy:
                res, pair.buy_percentage_current = BTClib.buyPair(bingx_client,pair,interval,total_balance,usdt_balance)
                balances_changed = True

            if suitableForSell:
                res, pair.sell_percentage_current = BTClib.sellPair(bingx_client,pair,interval,total_balance,pair_balance)
                balances_changed = True

            if res != 0:
                print(f"order result:\n{res}\n")
                if suitableForBuy:
                    pair.sell_percentage_current = BTClib.sell_percentage_init
                    print('sell percentage successfully reset')
                if suitableForSell:
                    pair.buy_percentage_current = BTClib.buy_percentage_init
                    print('buy percentage successfully reset')

        print("\n====================\n")
        sys.stdout.flush()
        