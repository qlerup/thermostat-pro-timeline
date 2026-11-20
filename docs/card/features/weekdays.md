# Weekdays

Open the settings gear and choose the Weekdays tab. Start with weekday/weekend grouping if Monday to Friday share a routine. Choose separate Saturday and Sunday schedules when those days differ. Use all seven days for individual timetables.

Select the day or group before editing a block. Switch the view to compare one room across days, or several rooms on the same day.

## Choose a weekday grouping

Open **Settings > Weekdays** and enable weekday schedules. If **Copy main schedule** opens, choose which day group should receive a copy, or select **Don’t copy** to start separately. Group Monday through Friday together for a regular workweek, or choose individual days for different routines.

[![Choose a weekday grouping in Home Assistant](../../images/weekdays-view.png)](../../images/weekdays.gif)

[Play walkthrough](../../images/weekdays.gif) | [Full-size GIF](../../images/weekdays.gif)

## Compare days for one room

Select the view for one room across all days. Here Office warms up at 06:00 on weekdays. Saturday starts at 08:00 and reaches 23 degrees. Select the corresponding day before editing a block.

[![Office timelines with a later Saturday block](../../images/weekday-rows-result.png)](../../images/weekdays.gif)

[Play walkthrough](../../images/weekdays.gif) | [Full-size GIF](../../images/weekdays.gif)

## Settings

- weekdays_enabled: true/false to enable weekday schedules.
- weekdays_mode: weekday_weekend | weekday_sat_sun | all_7 to choose day groupings.
- weekdays_view: all_rooms_one_day | one_room_all_days to pick timeline browsing mode.
- weekdays_view_switch_in_timeline: true to show a toggle in the main header.

## Choose a plan with Workday sensors

Set up two **Workday** binary sensors in Home Assistant. Use offset **0** for today and **1** for tomorrow. Set their workweek, country and holidays to match your household. Workday supplies an on/off answer. The temperatures and times come from the weekday timetables you edit in Timeline.

In **Settings > Weekdays**, enable weekday schedules and **Use Workday sensors to choose the plan**. Select both sensors, then pick the timetable to use for each combination. Each room uses its own blocks for that weekday. Choose seven individual days if, for example, Friday evening should differ from Monday evening.

| Today | Tomorrow | Initially uses |
| --- | --- | --- |
| Work | Work | Monday |
| Work | Free | Friday |
| Free | Free | Saturday |
| Free | Work | Sunday |

Save and check the Workday timetable below the card heading. In the example, Work / Free uses Thursday instead of Friday and Office targets 22 degrees. You can reuse the same day in several combinations. When either sensor is missing or unavailable, or the option is switched off, the normal calendar weekday applies. Holiday, household presence and active profile schedules retain their existing priority.

[![Choose a plan with Workday sensors in Home Assistant](../../images/workday-plans-result.png)](../../images/workday-plans.gif)

[Play walkthrough](../../images/workday-plans.gif) | [Full-size GIF](../../images/workday-plans.gif)
