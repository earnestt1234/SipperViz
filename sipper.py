"""Class for loading sipper data."""

from collections import OrderedDict
import os

import numpy as np
import pandas as pd

def date_filter_okay(df, start, end):
    check = df[(df.index >= start) &
            (df.index <= end)].copy()
    return not check.empty

def groupby_convertcontent(gr, content, out='Count'):
    output = []
    for i, (n, d) in enumerate(gr):
        if content in d['LeftContents'].values:
            col = 'Left' + out
        else:
            col = 'Right' + out
        if output:
            start_from = np.nanmax(output[-1].values)
            to_append = d[col] + (start_from - np.nanmin(d[col].values))
        else:
            to_append = d[col]
        output.append(to_append)
    output = pd.concat(output)
    return output - np.nanmin(output)

class SipperError(Exception):
    """Class for sipper errors"""

class Sipper():
    def __init__(self, path):
        self.path = path
        try:
            self.data = pd.read_csv(path)
            self.data.columns = self.data.columns.str.strip()
            passed = False
            og_columns = ['MM:DD:YYYY hh:mm:ss', 'Elapsed Time', 'Device',
                          'LeftCount', 'LeftDuration', 'RightCount',
                          'RightDuration', 'BatteryVoltage']
            sipviz_columns = og_columns[:-1] + ['LeftContents', 'RightContents']
            if list(self.data.columns) == og_columns:
                passed = True
                self.version = 'Raw'
            elif list(self.data.columns) == sipviz_columns:
                passed = True
                self.version = 'SipperViz'
            else:
                raise SipperError('Column names do not match sipper data')
        except FileNotFoundError as error:
            raise error
        except pd.errors.EmptyDataError as error:
            raise error

        #data editing and attributes
        if 'BatteryVoltage' in self.data.columns:
            self.battery = self.data['BatteryVoltage']
            self.data.drop(['BatteryVoltage'], axis=1, inplace=True)
        else:
            self.battery = None
        self.data.drop_duplicates(subset=['LeftCount','LeftDuration',
                                          'RightCount','RightDuration'],
                                  inplace=True)
        self.data['MM:DD:YYYY hh:mm:ss'] = pd.to_datetime(self.data['MM:DD:YYYY hh:mm:ss'])
        self.data['Elapsed Time'] = pd.to_timedelta(self.data['Elapsed Time'])
        self.data = self.data.set_index('MM:DD:YYYY hh:mm:ss')
        if 'LeftContents' not in self.data.columns:
            self.data['LeftContents'] = np.nan
        if 'RightContents' not in self.data.columns:
            self.data['RightContents'] = np.nan
        self.start_date = self.data.index[0]

        #informational attributes
        self.basename = os.path.basename(path)
        self.filename, self.extension = os.path.splitext(self.basename)
        self.device_no = self.data['Device'][0]
        self.left_name = 'Left'
        self.right_name = 'Right'
        self.end_date = self.data.index[-1]
        self.duration = self.end_date - self.start_date
        self.contents_dates = OrderedDict()
        self.contents = self.set_of_contents()

    def __repr__(self):
        """Shows the directory used to make the file."""
        return 'Sipper("' + self.path + '")'

    def assign_contents(self, d):
        self.contents = []
        for (start, end), (left, right) in d.items():
            if not date_filter_okay(self.data, start, end):
                continue
            else:
                self.contents_dates[(start,end)] = (left,right)
                if start not in self.data.index:
                    before = self.data.index[self.data.index < start].max()
                    if not pd.isna(before):
                        self.data.loc[start, :] = np.nan
                        self.data.loc[start, :] = self.data.loc[before,:]
                self.data.loc[(self.data.index >= start) &
                              (self.data.index < end), 'LeftContents'] = left
                self.data.loc[(self.data.index >= start) &
                              (self.data.index < end), 'RightContents'] = right
        self.data.sort_index(inplace=True)
        self.contents = self.set_of_contents()

    def set_of_contents(self):
        all_left = pd.Series(self.data['LeftContents'].unique()).dropna()
        all_right = pd.Series(self.data['RightContents'].unique()).dropna()
        return list(np.unique(np.concatenate([all_left,all_right])))

    def get_content_values(self, content, out, df=pd.DataFrame()):
        if df.empty:
            df = self.data
        if out not in ['Count','Duration']:
            raise SipperError('method get_content_values() can only ' +
                              'use out = "Count" or out = "Duration"')
        subset = df[(df['LeftContents'].isin([content])) |
                    (df['RightContents'].isin([content]))]
        changes = subset['LeftContents'].ne(subset['LeftContents'].shift().bfill())
        changes = changes.astype(int).cumsum()
        gr = subset.groupby(changes)
        name = content+out
        return groupby_convertcontent(gr, content=content, out=out).rename(name)