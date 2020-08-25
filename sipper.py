"""Class for loading sipper data."""

import os
import warnings

import numpy as np
import pandas as pd

class SipperError(Exception):
    """Class for sipper errors"""

class SipperWarning(Warning):
    """Class for sipper warnings"""

def date_filter_okay(df, start, end):
    check = df[(df.index >= start) &
            (df.index <= end)].copy()
    return not check.empty

def groupby_convertcontent(gr, content, out='Count', opposite=False):
    output = []
    for i, (n, d) in enumerate(gr):
        if content in d['LeftContents'].values:
            col = 'Left' + out if not opposite else 'Right' + out
        else:
            col = 'Right' + out if not opposite else 'Left' + out
        if output:
            start_from = np.nanmax(output[-1].values)
            to_append = d[col] + (start_from - np.nanmin(d[col].values))
        else:
            to_append = d[col]
        output.append(to_append)
    output = pd.concat(output)
    return output - np.nanmin(output)

def groupby_getcontentdict(d):
    t1 = d.index.min()
    t2 = d.index.max()
    s1 = d['LeftContents'].unique()[0]
    s2 = d['RightContents'].unique()[0]
    return {(t1, t2):(s1, s2)}

def is_concatable(sippers):
    """
    Determines whether or not Sipper files can be concatenated,
    (based on whether their start and end times overlap).

    Parameters
    ----------
    sippers : array
        an array of Sipper files

    Returns
    -------
    bool

    """
    sorted_sips = sorted(sippers, key=lambda x: x.start_date)
    for i, file in enumerate(sorted_sips[1:], start=1):
        if file.start_date <= sorted_sips[i-1].end_date:
            return False
    return True

def sipper_concat(sippers):
    if not is_concatable(sippers):
        raise SipperError('File dates overlap; cannot concatenate')
    output=[]
    columns = ['Elapsed Time', 'Device', 'LeftCount', 'LeftDuration',
               'RightCount', 'RightDuration', 'BatteryVoltage',
               'LeftContents', 'RightContents']
    offsets = {}
    sorted_sippers = sorted(sippers, key=lambda x: x.start_date)
    for i, s in enumerate(sorted_sippers):
        df = s.data.copy().loc[:,columns]
        if i==0:
            output.append(df)
            for col in['LeftCount', 'LeftDuration',
                       'RightCount', 'RightDuration']:
                if col in df.columns:
                    offsets[col] = df[col].max()
        else:
            for name, offset in offsets.items():
                df[name] += offset
                offsets[name] = df[name].max()
            output.append(df)
    output = pd.concat(output)
    return output

class Sipper():
    def __init__(self, path):
        self.path = path
        print('Loading {}...'.format(path))
        try:
            self.basename = os.path.basename(path)
            self.filename, self.extension = os.path.splitext(self.basename)
            if self.extension == '.xlsx':
                warnings.warn('Excel files can take siginficantly longer to load than .csv')
            self.extension = self.extension.lower()
            read_opts = {'.csv':pd.read_csv, '.xlsx':pd.read_excel}
            func = read_opts[self.extension]
            self.data = func(path)
            self.data.columns = self.data.columns.str.strip()
            og_columns = ['MM:DD:YYYY hh:mm:ss', 'Elapsed Time', 'Device',
                          'LeftCount', 'LeftDuration', 'RightCount',
                          'RightDuration', 'BatteryVoltage']
            sipviz_columns = og_columns + ['LeftContents', 'RightContents']
            if list(self.data.columns) == og_columns:
                self.version = 'Raw'
            elif list(self.data.columns) == sipviz_columns:
                self.version = 'SipperViz'
            else:
                raise SipperError('Column names do not match sipper data')
        except FileNotFoundError as error:
            raise error
        except pd.errors.EmptyDataError as error:
            raise error

        #data editing and attributes
        # keep battery before dropping duplicates
        self.battery = self.data['BatteryVoltage']
        self.data.drop_duplicates(subset=['LeftCount','LeftDuration',
                                          'RightCount','RightDuration'],
                                  inplace=True)
        self.data['MM:DD:YYYY hh:mm:ss'] = pd.to_datetime(self.data['MM:DD:YYYY hh:mm:ss'])
        try:
            self.data['Elapsed Time'] = pd.to_timedelta(self.data['Elapsed Time'])
        except:
            pass
        self.data = self.data.set_index('MM:DD:YYYY hh:mm:ss')
        if 'LeftContents' not in self.data.columns:
            self.data['LeftContents'] = np.nan
        if 'RightContents' not in self.data.columns:
            self.data['RightContents'] = np.nan

        #informational attributes
        self.basename = os.path.basename(path)
        if len(set(self.data['Device'])) == 1:
            self.device_no = self.data['Device'][0]
        else:
            self.device_no = None
        self.left_name = 'Left'
        self.right_name = 'Right'
        self.start_date = self.data.index[0]
        self.end_date = self.data.index[-1]
        self.duration = self.end_date - self.start_date
        self.contents_dict = self.get_contents_dict()
        self.contents = self.set_of_contents()
        self.groups = []
        self.sipperviz_assigned = False
        # ^ extra steps for plot code must be added if True
        self.duplicate_index = any(self.data.index.duplicated())
        self.unduplicated = False
        # ^ flag to show whether removal of duplicates has been done

    def __repr__(self):
        """Shows the directory used to make the file."""
        return 'Sipper("' + self.path + '")'

    def assign_contents(self, d):
        self.contents = []
        for (start, end), (left, right) in d.items():
            if not date_filter_okay(self.data, start, end):
                continue
            else:
                self.contents_dict[(start,end)] = (left,right)
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

    def get_content_values(self, content, out, df=pd.DataFrame(), opposite=False):
        if df.empty:
            df = self.data
        if out not in ['Count','Duration']:
            raise SipperError('method get_content_values() can only ' +
                              'use out = "Count" or out = "Duration"')
        if content not in self.contents:
            warnings.warn('Content "' + content + '" not found in ' + self.filename,
                          SipperWarning)
            return pd.Series()
        subset = df[(df['LeftContents'].isin([content])) |
                    (df['RightContents'].isin([content]))]
        changes = subset['LeftContents'].ne(subset['LeftContents'].shift().bfill())
        changes = changes.astype(int).cumsum()
        gr = subset.groupby(changes)
        name = content+out
        if opposite:
            name = 'Opposite' + name
        return groupby_convertcontent(gr, content=content, out=out,
                                      opposite=opposite).rename(name)

    def get_contents_dict(self, df=pd.DataFrame()):
        if df.empty:
            df = self.data
        df = df.dropna(subset=['LeftContents', 'RightContents']).copy()
        l = df['LeftContents'].ne(df['LeftContents'].shift().bfill())
        r = df['RightContents'].ne(df['RightContents'].shift().bfill())
        changes = (l|r).astype(int).cumsum()
        groupdict = df.groupby(changes).apply(groupby_getcontentdict).to_dict()
        output = {}
        for i in groupdict.values():
            output.update(i)
        return output

    def clear_contents(self, df=pd.DataFrame()):
        if df.empty:
            df = self.data
        df['LeftContents'] = np.nan
        df['RightContents'] = np.nan
        self.contents = []
        self.contents_dict = {}

    def unduplicate_index(self, method='keeplast'):
        if method=='keeplast':
            self.data = self.data[~self.data.index.duplicated(keep='last')]
        elif method=='fromelapsed':
            if any(self.data['Elapsed Time'].diff() < pd.Timedelta(0)):
                raise SipperError('Elapsed Times are not always increasing')
            t0 = self.data.index[0] - pd.Timedelta(seconds=10)
            self.data.index = self.data['Elapsed Time'] + t0
        self.unduplicated = True
        self.duplicate_index = False