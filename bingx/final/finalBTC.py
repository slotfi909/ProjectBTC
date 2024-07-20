import BTClib
import time
import sys
import os

secret_key = "WqP5txrWtmbGcMND5GjFiBZICth5nZFIXYKEPqKitRl7xOHVGOFzNo8yNCLQUmK4guPTNgV4nwKLT0aD5iYIg"
api_key = "SbyekABHMR0SyrIQKTqU14sExh5m40sV5a6jaBenI26u5SDm8z4gGzQCLamCp6Ww2uJyVjyhJQESk4Gt5jA"

# prepairing pairs
pairs = BTClib.read_pairs_from_file('./pairs.txt')

# set interval
# interval = BTClib.Interval.MINUTELY_THREEMINUTE
interval = BTClib.read_interval_from_file("./interval.txt")
bingx_client = BTClib.BingX(api_key=api_key, secret_key=secret_key)


###############
##playground
# orderType = BTClib.OrderType()
# orderType = BTClib.OrderType(BTClib.OrderType.OrderTypeEnum.MARKETANDLIMIT)
###############

BTClib.cancel_previous_orders(bingx_client)

# BTClib.set_ordertype(orderType)

while(True):
    
    # BTClib.save_to_logs_spot()

    BTClib.calibre_time(interval)
    
    BTClib.check_order_timeout(bingx_client)

    total_balance = BTClib.get_total_balance(bingx_client)

    for pair in pairs:

        print(f"\nnew try at {time.ctime(time.time())} for pair {pair.pairName}:\n")

        pair.update_latest_price(bingx_client)

        balances_changed = True
        for strategy in pair.strategies:

            if balances_changed:

                usdt_balance = BTClib.get_usdt_balance(bingx_client)

                pair_balance = BTClib.get_pair_balance(bingx_client,pair)

                pair_balance_as_usdt = BTClib.get_pair_value(bingx_client,pair,pair_balance)

            start_time, end_time,interval_as_millisecond = BTClib.get_times(strategy,interval)

            cdf = BTClib.get_pair_history_as_dataframe(bingx_client,pair,interval,start_time,end_time,strategy)

            limit_price = BTClib.calculate_limit_price(cdf.loc[0])

            print(f'\ncurrent pair data for strategy {strategy}:\n{cdf}\n')

            suitableForBuy, suitableForSell = BTClib.check_position(cdf,strategy)

            print(f'suitableForBuy: {suitableForBuy}')
            print(f'suitableForSell: {suitableForSell}')

            balances_changed = False
            market_res, limit_res = False, False
            if suitableForSell:
                market_res, limit_res, pair.sell_percentage_current = BTClib.sell_pair(bingx_client,pair,interval,total_balance,pair_balance,limit_price)
                balances_changed = True

            if suitableForBuy:
                market_res, limit_res, pair.buy_percentage_current = BTClib.buy_pair(bingx_client,pair,interval,total_balance,usdt_balance,limit_price)
                balances_changed = True


            if market_res == True or limit_res == True:
                if suitableForBuy:
                    pair.sell_percentage_current = BTClib.sell_percentage_init
                    print('sell percentage successfully reset')
                if suitableForSell:
                    pair.buy_percentage_current = BTClib.buy_percentage_init
                    print('buy percentage successfully reset')

        print("\n====================\n")
        sys.stdout.flush()
    
    summary_dict = BTClib.get_account_summary(bingx_client)

    BTClib.write_spot_summary(summary_dict, './summary.txt')
    