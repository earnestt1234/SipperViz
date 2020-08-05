# -*- coding: utf-8 -*-
"""
Created on Wed Aug  5 13:24:18 2020

@author: earne
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from sipperplots import get_any_idi

def drinkcount_cumulative(sipper, show_left=True, show_right=True,
                          show_content=[], **kwargs):
    output = pd.DataFrame()
    df = sipper.data
    if 'date_filter' in kwargs:
        s, e = kwargs['date_filter']
        df = df[(df.index >= s) &
                (df.index <= e)].copy()
    if show_left:
        l = pd.DataFrame({'LeftCount' : df['LeftCount']}, index=df.index)
        output = output.join(l, how='outer')
    if show_right:
        r = pd.DataFrame({'RightCount' : df['RightCount']}, index=df.index)
        output = output.join(r, how='outer')
    if show_content:
        for c in show_content:
            count = sipper.get_content_values(c, out='Count', df=sipper.data)
            if not count.empty:
                temp = pd.DataFrame({c +'Count' : count}, index=count.index)
                output = output.join(temp, how='outer')
    return output

def drinkcount_binned(sipper, binsize='1H', show_left=True, show_right=True,
                       show_content=[], **kwargs):
    output = pd.DataFrame()
    df = sipper.data
    if 'date_filter' in kwargs:
        s, e = kwargs['date_filter']
        df = df[(df.index >= s) &
                (df.index <= e)].copy()
    if show_left:
        binned = df['LeftCount'].diff().resample(binsize).sum()
        l = pd.DataFrame({'LeftCount' : binned}, index=binned.index)
        output = output.join(l, how='outer')
    if show_right:
        binned = df['RightCount'].diff().resample(binsize).sum()
        r = pd.DataFrame({'RightCount' : binned}, index=binned.index)
        output = output.join(r, how='outer')
    if show_content:
        for c in show_content:
            count = sipper.get_content_values(c, out='Count', df=sipper.data)
            binned = count.diff().resample(binsize).sum()
            if not count.empty:
                temp = pd.DataFrame({c+'Count' : binned}, index=binned.index)
                output = output.join(temp, how='outer')
    return output

def drinkduration_cumulative(sipper, show_left=True, show_right=True,
                          show_content=[], **kwargs):
    output = pd.DataFrame()
    df = sipper.data
    if 'date_filter' in kwargs:
        s, e = kwargs['date_filter']
        df = df[(df.index >= s) &
                (df.index <= e)].copy()
    if show_left:
        l = pd.DataFrame({'LeftDuration' : df['LeftDuration']}, index=df.index)
        output = output.join(l, how='outer')
    if show_right:
        r = pd.DataFrame({'RightDuration' : df['RightDuration']}, index=df.index)
        output = output.join(r, how='outer')
    if show_content:
        for c in show_content:
            count = sipper.get_content_values(c, out='Count', df=sipper.data)
            if not count.empty:
                temp = pd.DataFrame({c+'Duration' : count}, index=count.index)
                output = output.join(temp, how='outer')
    return output

def drinkduration_binned(sipper, binsize='1H', show_left=True, show_right=True,
                       show_content=[], **kwargs):
    output = pd.DataFrame()
    df = sipper.data
    if 'date_filter' in kwargs:
        s, e = kwargs['date_filter']
        df = df[(df.index >= s) &
                (df.index <= e)].copy()
    if show_left:
        binned = df['LeftDuration'].diff().resample(binsize).sum()
        l = pd.DataFrame({'LeftDuration' : binned}, index=binned.index)
        output = output.join(l, how='outer')
    if show_right:
        binned = df['RightDuration'].diff().resample(binsize).sum()
        r = pd.DataFrame({'RightDuration' : binned}, index=binned.index)
        output = output.join(r, how='outer')
    if show_content:
        for c in show_content:
            count = sipper.get_content_values(c, out='Count', df=sipper.data)
            binned = count.diff().resample(binsize).sum()
            if not count.empty:
                temp = pd.DataFrame({c+'Duration' : binned}, index=binned.index)
                output = output.join(temp, how='outer')
    return output

def interdrink_intervals(sippers, kde=True, logx=True,
                         combine=False, **kwargs):
    if combine:
        output = idi_onecurve(sippers, kde, logx, **kwargs)
    else:
        output = idi_multicurve(sippers, kde, logx, **kwargs)
    return output

def idi_onecurve(sippers, kde, logx, **kwargs):
    bar_df = pd.DataFrame()
    kde_df = pd.DataFrame()
    combined = []
    for sipper in sippers:
        fig = plt.figure()
        plt.clf()
        df = sipper.data.copy()
        if 'date_filter' in kwargs:
            s, e = kwargs['date_filter']
            df = df[(df.index >= s) &
                    (df.index <= e)].copy()
        y = get_any_idi(df)
        if logx:
            y = [np.log10(val) for val in y if not pd.isna(val)]
            bins = np.round(np.arange(-2, 5, .1), 2)
        else:
            bins = np.linspace(0, 900, 50)
        combined += list(y)
    plot = sns.distplot(combined, bins=bins, norm_hist=False, kde=kde)
    if kde:
        if plot.get_lines():
            line = plot.get_lines()[0]
            x, y = line.get_data()
            kde_df = kde_df.reindex(x)
            kde_df['Values'] = y
    bar_x = [v.get_x() for v in plot.patches]
    bar_h = [v.get_height() for v in plot.patches]
    bar_df = bar_df.reindex(bar_x)
    bar_df['Values'] = bar_h
    bar_df.index.name = 'log10(minutes)' if logx else 'minutes'
    kde_df.index.name = 'log10(minutes)' if logx else 'minutes'
    plt.close()
    return bar_df, kde_df

def idi_multicurve(sippers, kde, logx, **kwargs):
    bar_df = pd.DataFrame()
    kde_df = pd.DataFrame()
    for sipper in sippers:
        fig = plt.figure()
        plt.clf()
        df = sipper.data.copy()
        if 'date_filter' in kwargs:
            s, e = kwargs['date_filter']
            df = df[(df.index >= s) &
                    (df.index <= e)].copy()
        y = get_any_idi(df)
        if logx:
            y = [np.log10(val) for val in y if not pd.isna(val)]
            bins = np.round(np.arange(-2, 5, .1), 2)
        else:
            bins = np.linspace(0, 900, 50)
        plot = sns.distplot(y, bins=bins, norm_hist=False, kde=kde)
        bar_x = [v.get_x() for v in plot.patches]
        bar_h = [v.get_height() for v in plot.patches]
        btemp = pd.DataFrame({sipper.filename : bar_h}, index=bar_x)
        bar_df = bar_df.join(btemp, how='outer')
        if kde:
            if plot.get_lines():
                line = plot.get_lines()[0]
                x, y = line.get_data()
                ktemp = pd.DataFrame({sipper.filename : y}, index=x)
                kde_df = kde_df.join(ktemp, how='outer')
        plt.close()
    bar_df.index.name = 'log10(minutes)' if logx else 'minutes'
    kde_df.index.name = 'log10(minutes)' if logx else 'minutes'
    return bar_df, kde_df
