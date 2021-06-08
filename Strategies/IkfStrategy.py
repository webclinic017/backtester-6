
import backtrader as bt
from .BaseStrategy import BaseStrategy
from backtrader.utils.autodict import AutoDictList
import itertools
from iknowfirst.IkfIndicator import IkfIndicator
from iknowfirst.iknowfirst import retrieve_forecasts_data

class IkfStrategy(BaseStrategy):
    """
    buy the top data in the 7days forecast.
    sell after 7 days or until it's not in the 7days table anymore - according to the latest
    """

    def __init__(self):
        forecasts = retrieve_forecasts_data()
        self.forecasts = forecasts.stack().unstack(level=2, ).unstack().fillna(0)
        self.test_forecasts = retrieve_forecasts_data(filter_friday=False).stack().unstack(level=2,).unstack().fillna(0)
        super().__init__()

    
    def prepare(self, stock):
        stock.forecast = self.forecasts[stock._name]
        stock.indicator1 = IkfIndicator(stock, forecast='3days')
        stock.indicator2 = IkfIndicator(stock, forecast='7days')
        stock.indicator3 = IkfIndicator(stock, forecast='14days')
        stock.indicator4 = IkfIndicator(stock, forecast='1months')
        stock.indicator5 = IkfIndicator(stock, forecast='3months')
        stock.indicator6 = IkfIndicator(stock, forecast='12months')


    def check_signals(self, data):
        if self.open_signal(data):
            self.open_position(data)
    
    def open_signal(self, data):
        try:
            if data._name in list(self.forecasts.loc[str(data.datetime.date()),'7days'].index):
                return True
        except KeyError as e:
            pass # todo avoid the KeyError by quring the df differently. something like self.forecasts.loc[('2020-12-03','7days'),:].index

    def open_position(self, data):
        self.buy(data=data, exectype=bt.Order.Limit, price=data.open[0])


    def manage_position(self, data):
        trades : AutoDictList = self._trades[self.data]  # self._trades[data] is {data: {order_id: [trades]}}
        open_trades = [t for t in itertools.chain(*self._trades[self.data].values()) if t.isopen]
        for t in open_trades:
            if (data.datetime.date() - t.open_datetime().date()).days >= 7 and not self.open_position(data):
                self.sell(data=data, exectype=bt.Order.Limit, price=data.open[0])  # todo consider closing directly on the trade -  t.update()
        if len(open_trades) > 1:
            self.log(data, 'Warning - more than one open position!')


    def next(self):
        pass
        self.validate_date()

    def validate_date(self):
        for d in self.datas:
            date = d.datetime.date()
            try:
                raw_value = self.forecasts.loc[str(date), d.indicator2.p.forecast][d._name].strength
                assert raw_value == d.indicator2[0]
            except AssertionError as e:
                print('Indicator values mistmatch of %s or date %s', d._name, str(date))

""""
TODO create unit test
r = forecasts['BEZQ.TA'].loc[:,'7days',:]
n = 0
def validate_data(self):
    try:
        assert not self.forecasts.loc[str(self.data0.datetime.date())].empty
    except AssertionError as e:
        print('Error for date %s' % self.data0.datetime.date())

    try:
        assert not r.loc[str(r.index[n])[:-9]].empty
    except AssertionError as e:
        print('Indicator Error for date %s' % str(self.r.index[self.n])[:-9])
    n = n+1
"""


