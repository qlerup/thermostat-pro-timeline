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

[![Select the first and last days of a holiday](../../images/holiday-range-result.png)](../../images/holiday-range.gif)

[Play walkthrough](../../images/holiday-range.gif) | [Full-size GIF](../../images/holiday-range.gif)

## Give a holiday its own timetable

After selecting the date source, open **Edit holiday schedule**, choose Office, add a block and save. This example uses 21 degrees from 09:00 to 20:00 on matching dates. Adding a date and editing its temperature blocks are separate steps.

[![Office holiday timetable with a daytime heating block](../../images/holiday-plan-result.png)](../../images/holidays.gif)

[Play walkthrough](../../images/holidays.gif) | [Full-size GIF](../../images/holidays.gif)

## Follow a holiday calendar

Use **Settings > Holidays > Calendar** and select a dedicated holiday calendar. The holiday plan applies while the selected entity is on. An all-day event covers a whole day. Use the [holiday timetable](#give-a-holiday-its-own-timetable) to choose the actual temperatures.

[![Follow a holiday calendar](../../images/calendar-result.png)](../../images/calendar.gif)

[Play walkthrough](../../images/calendar.gif) | [Full-size GIF](../../images/calendar.gif)
