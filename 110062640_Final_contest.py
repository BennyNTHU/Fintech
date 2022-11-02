#!/usr/bin/env python
# coding: utf-8

# In[ ]:


class Strategy(StrategyBase):
    def __init__(self):
        # strategy attributes
        self.period = 70 * 60
        self.subscribed_books = {}
        self.options = {}

        # define your attributes here
        self.long_window_size = 10
        self.short_window_size = 5

    def on_order_state_change(self,  order):
        pass

    def trade(self, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()

        # get the latest 10 candles
        if len(candles[exchange][pair]) < self.long_window_size + 1:
            return
        candles[exchange][pair] = candles[exchange][pair][:self.long_window_size + 1]
        # use close price
        close_price_history = [candle['close'] for candle in candles[exchange][pair]]

        # convert to chronological order for talib
        close_price_history.reverse()
        # convert np.array
        close_price_history = np.array(close_price_history)
        long_ma_history = talib.SMA(close_price_history, self.long_window_size)
        short_ma_history = talib.SMA(close_price_history, self.short_window_size)

        # get available balance
        base_balance = CA.get_balance(exchange, base)
        quote_balance = CA.get_balance(exchange, quote)
        available_base_amount = base_balance.available
        available_quote_amount = quote_balance.available

        if short_ma_history[-2] < long_ma_history[-2] and short_ma_history[-1] > long_ma_history[-1]:
            CA.log('黃金交叉')
            amount = 0.1
            if available_quote_amount >= amount * close_price_history[-1]:
                CA.log('買入 ' + base)
                CA.buy(exchange, pair, amount, CA.OrderType.MARKET)
            else:
                CA.log('資產不足')
        elif short_ma_history[-2] > long_ma_history[-2] and short_ma_history[-1] < long_ma_history[-1]:
            CA.log('死亡交叉')
            if available_base_amount > 0:
                CA.log('賣出 ' + base)
                CA.sell(exchange, pair, available_base_amount, CA.OrderType.MARKET)
            else:
                CA.log('資產不足')

