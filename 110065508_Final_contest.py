class Strategy(StrategyBase):
    def __init__(self):
        # strategy property of MACD
        self.subscribed_books = {}
        #self.period = 4*60*60
        self.options = {}

        self.last_type = 'sell'
        self.fast_period = 12*8 # 配合DMI的週期,因為MACD週期是DMI的8倍
        self.slow_period = 26*8
        self.signal_period = 9*8
        self.proportion = 0.99

        # strategy attributes of DMI
        self.period = 30 * 60
        self.time_period = 14
        self.adx_bound = 25
 

    def on_order_state_change(self,  order):
        pass

    # called every self.period
    def trade(self, candles):
        exchange, pair, base, quote = CA.get_exchange_pair()
        
        close_price_history = [candle['close'] for candle in candles[exchange][pair]]
        high_price_history = [candle['high'] for candle in candles[exchange][pair]]
        low_price_history = [candle['low'] for candle in candles[exchange][pair]]

        # convert to chronological order for talib
        close_price_history.reverse()
        high_price_history.reverse()
        low_price_history.reverse()

        # convert np.array
        close_price_history = np.array(close_price_history)
        high_price_history = np.array(high_price_history)
        low_price_history = np.array(low_price_history)

        if len(close_price_history) < 2:
            return []

        ### obtain DMI ###
        # Plus Directional Indicator
        pdi = talib.PLUS_DI(high_price_history, low_price_history, close_price_history, timeperiod=self.time_period)
        # Minus Directional Indicator
        mdi = talib.MINUS_DI(high_price_history, low_price_history, close_price_history, timeperiod=self.time_period)
        # Average Directional Movement Index
        adx = talib.ADX(high_price_history, low_price_history, close_price_history, timeperiod=self.time_period)

        if len(pdi) < 2:
            return

        # current indicators
        curr_pdi = pdi[-1]
        curr_mdi =mdi[-1]
        curr_adx = adx[-1]

        # previous ones
        prev_pdi = pdi[-2]
        prev_mdi = mdi[-2]

        ### get MACD ###
        # get macd from talib
        macd, macdsignal, macdhist = talib.MACD(close_price_history, fastperiod=self.fast_period, slowperiod=self.slow_period, signalperiod=self.signal_period)
        
        curr_macd = macdhist[-1]
        prev_macd = macdhist[-2]

        macd_now = macd[-1]
        signal_now = macdsignal[-1]

        ### Strategy: Combine MACD and DMI ###
        # signal of DMI
        # buy, signal_DMI = 1, sell, signal_DMI = -1
        signal_DMI = 0

        if curr_adx > self.adx_bound:
            if curr_pdi > curr_mdi and prev_pdi < prev_mdi:
                signal_DMI = 1

            if curr_pdi < curr_mdi and prev_pdi > prev_mdi:
                signal_DMI = -1

        # signal of MACD
        signal_MACD = 0
        # MACD crosses the zero line from below - buy signal
        #if prev_macd < 0 and curr_macd > 0:
        #    signal_MACD = 1
        if prev_macd < curr_macd and curr_macd < 0:
            signal_MACD = 1
        
        # MACD crosses the zero line from above - sell signal
        #elif prev_macd > 0 and curr_macd < 0:
        #    signal_MACD = -1
        elif prev_macd > curr_macd and curr_macd > 0:
            signal_MACD = -1

        ### Assemble learning ###
        signal = 0
        if signal_DMI==1 and signal_MACD==1:
            signal = 1
        elif  signal_DMI==-1 and signal_MACD==-1:
            signal = -1

        # get available balance
        base_balance = CA.get_balance(exchange, base)
        quote_balance = CA.get_balance(exchange, quote)
        available_base_amount = base_balance.available
        available_quote_amount = quote_balance.available

        # place buy order
        if self.last_type == 'sell' and signal == 1:
            amount = np.around((available_quote_amount /  close_price_history[-1]) * self.proportion, 5)
            CA.log('Buy ' + base)
            self.last_type = 'buy'
            CA.buy(exchange, pair, amount, CA.OrderType.MARKET)
           
        # place sell order
        elif self.last_type == 'buy' and signal == -1:
            CA.log('Sell ' + base)
            self.last_type = 'sell'
            CA.sell(exchange, pair, available_base_amount, CA.OrderType.MARKET)
        
        return