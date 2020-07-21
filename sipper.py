"""Class for loading sipper data."""

import numpy as np
import os
import pandas as pd

class SipperError(Exception):
    """Class for sipper errors"""

class Sipper():
    def __init__(self, path):
        self.path = path
        try:
            self.data = pd.read_csv(path)
            self.data.columns = self.data.columns.str.strip()
            if list(self.data.columns) != ['MM:DD:YYYY hh:mm:ss',
                                           'Elapsed Time', 'Device',
                                           'LeftCount', 'LeftDuration',
                                           'RightCount', 'RightDuration',
                                           'BatteryVoltage']:
                raise SipperError('Column names do not match sipper data')
        except FileNotFoundError as error:
            raise error
        except pd.errors.EmptyDataError as error:
            raise error

        #data attributes
        self.battery = self.data['BatteryVoltage']
        self.data.drop(['BatteryVoltage'], axis=1, inplace=True)
        self.data.drop_duplicates(subset=['LeftCount','LeftDuration',
                                          'RightCount','RightDuration'],
                                  inplace=True)
        self.data['MM:DD:YYYY hh:mm:ss'] = pd.to_datetime(self.data['MM:DD:YYYY hh:mm:ss'])
        self.data['Elapsed Time'] = pd.to_timedelta(self.data['Elapsed Time'])
        self.data = self.data.set_index('MM:DD:YYYY hh:mm:ss')
        self.data['LeftContents'] = np.nan
        self.data['RightContents'] = np.nan
        self.start_date = self.data.index[0]
        self.end_date = self.data.index[-1]
        self.duration = self.end_date - self.start_date

        #information attributes
        self.basename = os.path.basename(path)
        self.filename, self.extension = os.path.splitext(self.basename)
        self.device_no = self.data['Device'][0]
        self.left_name = 'Left'
        self.right_name = 'Right'
        self.contents = []

    def __repr__(self):
        """Shows the directory used to make the file."""
        return 'Sipper("' + self.path + '")'

    def assign_contents(self, d):
        self.contents = []
        for (start, end), (left, right) in d.items():
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
        all_left = self.data['LeftContents'].unique()
        all_right = self.data['RightContents'].unique()
        self.contents = list(np.unique(np.concatenate([all_left,all_right])))

    def get_drinkcount(self, content):
        subset = self.data[(content in self.data['LeftContents']) |
                           (content in self.data['RightContents'])]

