# Summer and winter schedules

1. Open the settings gear on the card and turn on **Enable summer/winter schedules**. Save the settings.

   You will find the switch on the first settings tab.

   [![Season switch on the first settings tab](../../images/season-setting.png)](../../images/season.gif)

   [Play walkthrough](../../images/season.gif) | [Full-size GIF](../../images/season.gif)
2. Use the season selector to choose **Summer** or **Winter** before editing a room's blocks.
3. Switch seasons to inspect the other timetable. Leave the intended season selected for normal operation.

The season selects which timetable applies. To suspend schedule updates for a single room, use its [room pause](pause.md). Selecting Summer alone does not send an HVAC off command.

The stored settings are `seasonal_enabled` and `seasonal_mode` (`summer` or `winter`).

## Enable summer and winter schedules

Open the settings gear and stay on the first tab. Enable **summer/winter schedules** and save when you are ready to use separate timetables.

[![Enable summer and winter schedules in Home Assistant](../../images/season-view.png)](../../images/season.gif)

[Play walkthrough](../../images/season.gif) | [Full-size GIF](../../images/season.gif)

## Read the summer plan

Select Summer and save a short morning block. Here Summer calls for 19 degrees from 07:00 to 08:00. Select Winter to inspect the other timetable. Leave the season that should control the thermostat selected.

[![Office using a short summer block](../../images/summer-plan-result.png)](../../images/season.gif)

[Play walkthrough](../../images/season.gif) | [Full-size GIF](../../images/season.gif)

## Follow a season sensor

Open **Settings** and enable **summer/winter schedules**. Turn on **Follow a season sensor** and select the Home Assistant sensor that reports `spring`, `summer`, `autumn` and `winter`. Choose a schedule for spring and autumn independently and save.

Summer selects your summer plan and winter selects your winter plan. For example, mapping spring to Summer lets the office switch from its winter target of 21 °C to its summer target of 17 °C when spring begins. The season button shows the active plan. With shared storage and automatic temperature control enabled, the integration applies the change even with the dashboard closed.

An unavailable sensor keeps the last known plan. Until the first valid reading, the manual season is used. Disable **Follow a season sensor** and save to use the manual selector again.

[![Follow a season sensor in Home Assistant](../../images/season-sensor-result.png)](../../images/season-sensor.gif)

[Play walkthrough](../../images/season-sensor.gif) | [Full-size GIF](../../images/season-sensor.gif)

## Switch a thermostat off in summer

In **Settings**, enable summer/winter schedules. Under **Switch thermostats off in summer**, select the rooms to switch off and save. The list includes configured climate rooms whose thermostats support the HVAC `off` mode. Leave a room unchecked to run its summer timetable as usual. Automatic temperature control must be enabled.

Select **Summer** on the timeline, or let your configured season sensor select it. In the recording, Office switches to **Off** while Hall continues heating to its summer target of 18 degrees. Later blocks cannot turn Office back on. A selected room contributes no boiler demand while summer shutoff applies.

When winter begins or you deselect the room, Timeline restores the previous supported HVAC mode for a thermostat it switched off and resumes normal scheduling. With shared storage, this also works with the dashboard closed and after a Home Assistant restart. With browser storage, keep the same dashboard open for transitions. Room and global pauses still take precedence.

[![Switch a thermostat off in summer in Home Assistant](../../images/summer-off-result.png)](../../images/summer-off.gif)

[Play walkthrough](../../images/summer-off.gif) | [Full-size GIF](../../images/summer-off.gif)
