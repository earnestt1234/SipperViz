"""Class for loading sipper data."""

import os
import pandas as pd

class SipperLoadError(Exception):
    """Error for sipper loading errors"""

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
                raise SipperLoadError('Column names do not match sipper data')
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
        self.start_date = self.data.index[0]
        self.end_date = self.data.index[-1]
        self.duration = self.end_date - self.start_date

        #information attributes
        self.basename = os.path.basename(path)
        self.filename, self.extension = os.path.splitext(self.basename)
        self.device_no = self.data['Device'][0]
        self.left_name = 'Left'
        self.right_name = 'Right'

    def __repr__(self):
        """Shows the directory used to make the file."""
        return 'Sipper("' + self.path + '")'

s = Sipper(r"C:\Users\earne\Box\20200313 Behavior Study sipper data\4\SIP004_021220_00.CSV")
d = s.data
