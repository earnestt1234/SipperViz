"""Functions for plotting sipper data."""

import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def date_filter_okay(df, start, end):
    check = df[(df.index >= start) &
            (df.index <= end)].copy()
    return not check.empty

def convert_dt64_to_dt(dt64):
    """Converts numpy datetime to standard datetime (needed for shade_darkness
    function in most cases)."""
    new_date = ((dt64 - np.datetime64('1970-01-01T00:00:00'))/
                np.timedelta64(1, 's'))
    new_date = datetime.datetime.utcfromtimestamp(new_date)
    return new_date

def hours_between(start, end, convert=True):
    """
    Create a range of hours between two dates.

    Parameters
    ----------
    start, end : datetime-like object
        When to begin and end the data range
    convert : bool, optional
        Whether to convert the start/end arguments from numpy datetime to
        standard datetime. The default is True.

    Returns
    -------
    pandas DateTimeIndex
        Index array of all hours between start and end.
    """
    if convert:
        start = convert_dt64_to_dt(start)
        end = convert_dt64_to_dt(end)
    rounded_start = datetime.datetime(year=start.year,
                                      month=start.month,
                                      day=start.day,
                                      hour=start.hour)
    rounded_end = datetime.datetime(year=end.year,
                                    month=end.month,
                                    day=end.day,
                                    hour=end.hour)
    return pd.date_range(rounded_start,rounded_end,freq='1H')

def is_day_or_night(time, period, lights_on=7, lights_off=19):
    """
    Check if a datetime occured at day or night

    Parameters
    ----------
    time : datetime or pandas.Timestamp
        time to check
    period : str
        'day' or 'night', which period to check if the date is part of,
        based on the lights_on and lights_off arguments
    lights_on : int, optional
        Hour of the day (0-23) when lights turn on. The default is 7.
    lights_off : int, optional
         Hour of the day (0-23) when lights turn off. The default is 19.

    Returns
    -------
    Bool
    """
    lights_on = datetime.time(hour=lights_on)
    lights_off = datetime.time(hour=lights_off)
    val = False
    #defaults to checking if at night
    if lights_off > lights_on:
        val = time.time() >= lights_off or time.time() < lights_on
    elif lights_off < lights_on:
        val = time.time() >= lights_off and time.time() < lights_on
    #reverses if period='day'
    return val if period=='night' else not val

def get_daynight_count(start_time, end_time, lights_on=7, lights_off=9):
    """
    Compute the (fractional) number of completed light and dark periods
    between two dates.  Used for normalizing values grouped by day & nightime.

    Parameters
    ----------
    start_time : datetime
        starting time
    end_time : datetime
        ending time
    lights_on : int, optional
        Hour of the day (0-23) when lights turn on. The default is 7.
    lights_off : int, optional
        Hour of the day (0-23) when lights turn off. The default is 19.

    Returns
    -------
    dict
        dictionary with keys "day" and "night", values are the
        number of completed periods for each key.
    """
    cuts = []
    cuts.append(start_time)
    loop_time = start_time.replace(minute=0,second=0)
    while loop_time < end_time:
        loop_time += pd.Timedelta(hours=1)
        if loop_time.hour == lights_on:
            cuts.append(loop_time)
        elif loop_time.hour == lights_off:
            cuts.append(loop_time)
    cuts.append(end_time)
    days = []
    nights = []
    if lights_off > lights_on:
        day_hours = lights_off - lights_on
        night_hours = 24 - day_hours
    else:
        night_hours = lights_on - lights_off
        day_hours = 24 - night_hours
    day_hours = pd.Timedelta(hours = day_hours)
    night_hours = pd.Timedelta(hours = night_hours)
    for i, t in enumerate(cuts[:-1]):
        if is_day_or_night(t, 'day', lights_on, lights_off):
            days.append((cuts[i+1] - t)/day_hours)
        else:
            nights.append((cuts[i+1] - t)/night_hours)
    return {'day':sum(days),'night':sum(nights)}

def night_intervals(array, lights_on, lights_off, instead_days=False):
    """
    Find intervals of a date-array corresponding to night time.

    Parameters
    ----------
    array : array-like
        Array of datetimes (e.g. generated by hours_between).
    lights_on : int
        Integer between 0 and 23 representing when the light cycle begins.
    lights_off : int
        Integer between 0 and 23 representing when the light cycle ends.
    instead_days : bool, optional
        Return intervals during daytime instead of nighttime.
        The default is False.

    Returns
    -------
    night_intervals : list
        List of tuples with structure (start of nighttime, end of nighttime).
    """
    night_intervals = []
    lights_on = datetime.time(hour=lights_on)
    lights_off = datetime.time(hour=lights_off)
    if lights_on == lights_off:
        return night_intervals
    else:
        at_night = [is_day_or_night(i, 'night') for i in array]
    if instead_days:
        at_night = [not i for i in at_night]
    night_starts = []
    night_ends = []
    if at_night[0] == True:
        night_starts.append(array[0])
    for i, _ in enumerate(at_night[1:],start=1):
        if at_night[i] == True and at_night[i-1] == False:
            night_starts.append(array[i])
        elif at_night[i] == False and at_night[i-1] == True:
            night_ends.append(array[i])
    if at_night[-1] == True:
        night_ends.append(array[-1])
    night_intervals = list(zip(night_starts, night_ends))
    return night_intervals

def shade_darkness(ax, min_date, max_date, lights_on, lights_off,
                   convert=True):
    """
    Shade the night periods of a matplotlib Axes with a datetime x-axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Plot Axes.
    min_date : datetime
        Earliest date to shade.
    max_date : datetime
        Latest date to shade.
    lights_on : int
        Integer between 0 and 23 representing when the light cycle begins.
    lights_off : int
        Integer between 0 and 23 representing when the light cycle ends.
    convert : bool, optional
        Whether to convert the start/end arguments from numpy datetime to
        standard datetime. The default is True.

    Returns
    -------
    None.
    """
    hours_list = hours_between(min_date, max_date,convert=convert)
    nights = night_intervals(hours_list, lights_on=lights_on,
                             lights_off=lights_off)
    if nights:
        for i, interval in enumerate(nights):
            start = interval[0]
            end = interval[1]
            if start != end:
                ax.axvspan(start,
                           end,
                           color='gray',
                           alpha=.2,
                           label='_'*i + 'lights off',
                           zorder=0)

def date_format_x(ax, start, end):
    """
    Format the x-ticks of datetime plots created by FED3 Viz.  Handles various
    incoming dates by lowering the (time) frequency of ticks with longer
    date ranges.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Graph Axes
    start : datetime
        Earliest x-position of the graph
    end : datetime
        Latest x-position of the graph

    Returns
    -------
    None.
    """
    quarter_hours = mdates.MinuteLocator(byminute=[0,15,30,45])
    all_hours = mdates.HourLocator()
    quarter_days = mdates.HourLocator(byhour=[0,6,12,18])
    days = mdates.DayLocator()
    two_days = mdates.DayLocator(interval=2)
    three_days = mdates.DayLocator(interval=3)
    months = mdates.MonthLocator()
    d8_span = end - start
    if d8_span < datetime.timedelta(hours=12):
        xfmt = mdates.DateFormatter('%H:%M')
        major = all_hours
        minor = quarter_hours
    elif ((d8_span >= datetime.timedelta(hours=12))
          and (d8_span < datetime.timedelta(hours=24))):
        xfmt = mdates.DateFormatter('%b %d %H:%M')
        major = quarter_days
        minor = all_hours
    elif ((d8_span >= datetime.timedelta(hours=24))
          and (d8_span < datetime.timedelta(days=3))):
        xfmt = mdates.DateFormatter('%b %d %H:%M')
        major = days
        minor = quarter_days
    elif (d8_span >= datetime.timedelta(days=3)
          and (d8_span < datetime.timedelta(days=6))):
        xfmt = mdates.DateFormatter('%b %d %H:%M')
        major = two_days
        minor = days
    elif ((d8_span >= datetime.timedelta(days=6))
          and (d8_span < datetime.timedelta(days=20))):
        xfmt = mdates.DateFormatter('%b %d')
        major = three_days
        minor = days
    elif d8_span >= datetime.timedelta(days=20):
        xfmt = mdates.DateFormatter("%b '%y")
        major = months
        minor = three_days
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax.xaxis.set_major_locator(major)
    ax.xaxis.set_major_formatter(xfmt)
    ax.xaxis.set_minor_locator(minor)

def drinkcount_cumulative(sipper, show_left_count=True, show_right_count=True,
                          shade_dark=True, show_content_count=[],
                          lights_on=7, lights_off=19, **kwargs):
    if 'ax' in kwargs:
        ax = kwargs['ax']
    else:
        fig, ax = plt.subplots()
    df = sipper.data
    if show_left_count:
        ax.plot(df.index, df['LeftCount'], drawstyle='steps', color='red',
                label=sipper.left_name)
    if show_right_count:
        ax.plot(df.index, df['RightCount'], drawstyle='steps', color='blue',
                label=sipper.right_name)
    if show_content_count:
        for c in show_content_count:
            count = sipper.get_content_values(c, out='Count', df=sipper.data)
            if not count.empty:
                ax.plot(count.index, count, drawstyle='steps', label=c)
    date_format_x(ax, df.index[0], df.index[-1])
    ax.set_title('Drink Count for ' + sipper.filename)
    ax.set_ylabel('Drinks')
    ax.set_xlabel('Date')
    if shade_dark:
        shade_darkness(ax, df.index[0], df.index[-1], lights_on, lights_off)
    ax.legend()
    plt.tight_layout()
    return fig if 'ax' not in kwargs else None