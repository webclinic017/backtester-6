import backtrader as bt
from __init__test import TEST_DATA_DIR
from test_common import *
from shutil import copy
from database.data_writer import store
from database import diff_data_feed_csv
from backtrader import num2date
    
data_path = TEST_DATA_DIR+'/writer_test.csv'


@pytest.mark.parametrize('data', [([bt.feeds.GenericCSVData(dataname=data_path, dtformat='%Y-%m-%d', 
                                                            fromdate=datetime(2020, 11, 2), todate=datetime(2020,11,14))])])
class TestStoreData:
    def test_store_and_add_new_datapoint(self, data_fixture: bt.feed.FeedBase, tmpdir):
        tmpfile = tmpdir.join("tmpfile.csv")
        store(data_fixture, tmpfile)
        diffs = diff_data_feed_csv(data_path, tmpfile)
        assert diffs.empty, f'There are differences between the files:\n{diffs.to_string(index=True)}\n'
        # add new data point and rewrite
        new_datapoint = extend_last_datapoint_by_1(data_fixture)
        store(data_fixture, tmpfile)
        diffs = diff_data_feed_csv(data_path, tmpfile)
        assert len(diffs) == 1, f'Expecting one additional datapoint'
        assert contains_datapoint(new_datapoint, tmpfile), f'Datapoint is not found in the file'

    def test_fails_store_merge_conflict(self, data_fixture: bt.feed.FeedBase, tmpdir):
        tmpfile = tmpdir.join("tmpfile.csv")
        copy(data_path, str(tmpfile))
        data_fixture.open[0] = 0  # create a conflict
        store(data_fixture, tmpfile)
        diffs = diff_data_feed_csv(data_path, tmpfile)
        assert diffs.empty, f'Manipulated data should not be written (hence no diffs with the untouched original file)\n{diffs.to_string(index=True)}\n'

    def test_fails_store_weekend_datapoint(self, data_fixture: bt.feed.FeedBase, tmpdir):
        tmpfile = tmpdir.join("tmpfile.csv")
        copy(data_path, str(tmpfile))
        initial_len = len(data_fixture)
        extend_enough_datapoints_to_reach_weekend(data_fixture)
        assert len(data_fixture) >= 5 + initial_len, 'Data was not extended enough'
        store(data_fixture, tmpfile)
        diffs = diff_data_feed_csv(tmpfile, data_path)
        assert diffs.empty, f'Manipulated data should not be written (hence no diffs with the untouched original file)\n{diffs.to_string(index=True)}\n'


def extend_last_datapoint_by_1(data_fixture):
    data_fixture.forward()
    data_point = {} 
    for alias in data_fixture.lines.getlinealiases():
        line = getattr(data_fixture.lines, alias)
        line[0] = line[-1] + 1
        data_point[alias] = line[-1] + 1
    return data_point

def extend_enough_datapoints_to_reach_weekend(data_fixture):
    [extend_last_datapoint_by_1(data_fixture) for _ in range(5)]
    
def contains_datapoint(datapoint, file):
    index_label = 'datetime'
    dataframe = pd.read_csv(file, index_col=index_label,)
    datapoint_date = str(num2date(datapoint.pop(index_label)).date())
    file_datapoint = dataframe.loc[datapoint_date]
    return pd.Series(datapoint).eq(file_datapoint).all()
    