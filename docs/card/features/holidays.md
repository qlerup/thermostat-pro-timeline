# Holidays

- holidays_enabled: true/false
- holidays_source: calendar | manual
- holidays_entity: calendar.* or a binary sensor that is on during holidays
- holidays_dates: [ "YYYY-MM-DD", ... ] manual date list when using manual source

## Choose a holiday source

Open **Settings > Holidays** and enable holiday schedules. Use a calendar for recurring holidays, or enter specific dates manually. Save the selected source before editing the holiday timetable.

[![Choose a holiday source in Home Assistant](../../images/holidays-view.png)](../../images/holidays.gif)

[Play walkthrough](../../images/holidays.gif) | [Full-size GIF](../../images/holidays.gif)

## Schedule a range of dates

For consecutive days, switch to the manual source and add a range using its first and last dates. Save the settings, then edit the holiday timetable to set the temperatures for those days. For an on/off holiday calendar, keep the calendar as the source and maintain the dates in Home Assistant.
