import backtrader as bt
from tests.test_common import *
import test_common
from database.data_loader import IBLoader
from datetime import datetime
import pytest
from __init__test import TEST_DATA_DIR
from backtrader import date2num, num2date
from utils.backtrader_helpers import convert_to_dataframe
from database import diff_data_feed


def assert_prices(feed, datetime, open, high, low, close, ago=0):
    assert feed.datetime.date(-ago) == datetime.date()
    assert feed.open[-ago] == open
    assert feed.high[-ago] == high
    assert feed.low[-ago] == low
    assert feed.close[-ago] == close

def get_feed_file_path_mock(symbol):
    return TEST_DATA_DIR + symbol + '.csv'
    
class TestHistoricalLoader:
    """IB Gateway or TWS must be connected prior to these tests"""
        
    @pytest.fixture
    def loader(self, cerebro):
        return IBLoader(cerebro)

    # maybe redundant TODO
    def test_request_feed_data(self, cerebro, loader):
        """Request data of specific stock and date and verify the prices received """
        loader.load_feeds(['ZION'], datetime(2020,7,31), datetime(2020,8,1), backfill_from_database=False)
        cerebro.addstrategy(test_common.DummyStrategy)
        cerebro.run()
        assert_prices(cerebro.datas[0], datetime(2020,7,31), 32.6, 32.69, 31.94, 32.47), 'Data mismatch'
    

    # @pytest.mark.parametrize('start, end', [('2020-06-02', '2020-07-31'), ('2020-10-20', '2020-11-10'), ('2021-01-20', '2021-02-10')])
    @pytest.mark.parametrize('start, end', [('2020-11-02', '2021-03-19')])
    def test_request_feed_data_for_period(self, cerebro, loader, start, end):
        loader.load_feeds(['ZION'], start_date=datetime.fromisoformat(start), end_date=datetime.fromisoformat(end), backfill_from_database=False, store=True)
        cerebro.addstrategy(test_common.DummyStrategy)
        cerebro.run()
        requested_data = cerebro.datas[0]
        df = pd.read_csv(TEST_DATA_DIR+'ZION_BATS_TRADINGVIEW_1D.csv', index_col=0, converters={0:lambda long_date:long_date[:10]}, parse_dates=[0])
        requested_df = convert_to_dataframe(requested_data)
        requested_df.index = requested_df.index.map(lambda dt: dt.date)
        diffs = diff_data_feed(requested_df, df.loc[requested_df.index[0]:requested_df.index[-1]])
        assert diffs.empty, f'There are differences between the requested data and the static data:\n{diffs.to_string(index=True)}\n'

    # TODO test to compare volumes of requested feed and static

    #TODO delete ZION.csv from the test folder
        
    def test_request_feed_data_on_weekend(self, cerebro, loader):
        """Request data over the weekend when there is no trading of the contract"""
        weekend_start = datetime(2021,11,13)
        assert weekend_start.isoweekday() == 6  # making sure it's Saturday
        weekend_end = datetime(2021, 11,15)
        assert weekend_end.isoweekday() == 1
        loader.load_feeds(['ZION'], weekend_start, weekend_end, backfill_from_database=False)
        loader.load_feeds(['NVDA'], datetime(2021,11,15), datetime(2021,11,22), backfill_from_database=False)
        cerebro.addstrategy(test_common.DummyStrategy)
        cerebro.run()
        assert len(cerebro.datas[0]) == 0, 'data should be empty - since it\'s weekend'
        assert len(cerebro.datas[1]) == 5, 'data should have full business week - 5 days'
        
    def test_backfill_one_bar(self, cerebro, loader, mocker):
        """Load data feed from file, fill missing bar from live data server"""
        mocker.patch.object(loader.source, 'get_feed_path', return_value=TEST_DATA_DIR + 'backfill_test.csv')
        loader.load_feeds(['NVDA'], start_date=datetime(2021, 11, 19), end_date=datetime(2021, 11, 23), backfill_from_database=True, store=False)
        cerebro.addstrategy(DummyStrategy)
        cerebro.run()
        assert len(cerebro.datas[0]) == 2
        assert_prices(cerebro.datas[0], datetime(2021, 11, 19), 44.44, 66.66, 33.33, 55.55, ago=1), 'Mismatch with data from file'
        assert_prices(cerebro.datas[0], datetime(2021, 11, 22), 335.17, 346.47, 319.0, 319.56, ago=0), 'Mismatch with data from server'