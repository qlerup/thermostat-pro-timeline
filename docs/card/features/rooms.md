# Timeline and room controls

## Create or change a block

Choose a room and open the block editor on its timeline. Set the times and target, then save. To change an existing block, double-click it. The [desktop editing guide](../../getting-started/quick-start.md#edit-a-scheduled-block) shows a morning block changing from 21 to 23 degrees. To remove a period, open the same editor and choose **Delete**.

## Defaults and automatic control

Choose a default temperature for gaps. For an 18-degree default and a 21-degree block from 06:00 to 09:00, the thermostat targets 21 during the block and returns to 18 at its end if no other rule applies. Enable shared storage and auto-apply for control with the dashboard closed. Check the target in Home Assistant when the block starts or ends.

[![Enable auto-apply and display per-room defaults](../../images/defaults-result.png)](../../images/defaults.gif)

[Play walkthrough](../../images/defaults.gif) | [Full-size GIF](../../images/defaults.gif)

## Room labels and external thermometers

Use the room settings to give the thermostat a display name, show its current temperature and optionally select an external sensor. The Home office bubble shows the thermometer reading while each block displays its scheduled target.

[![Home office row showing measured temperature and two scheduled targets](../../images/room-display-result.png)](../../images/room-display.gif)

[Play walkthrough](../../images/room-display.gif) | [Full-size GIF](../../images/room-display.gif)

## Merged radiators and power commands

Choose a primary thermostat and add the other radiators under its room merge. Schedule the primary row once. Check both climate entities when the block starts. Each should receive the same target. If a model needs an explicit power command, enable its turn-on option and choose whether to send it before or after the target. See the [configuration example](../examples.md) for a two-radiator room.

[![Link a second radiator and enable turn-on sequencing](../../images/merge-result.png)](../../images/merge.gif)

[Play walkthrough](../../images/merge.gif) | [Full-size GIF](../../images/merge.gif)

## Schedule a number helper

Add an `input_number` helper to the card's entities and choose a default or add blocks. With auto-apply on, open the helper in Home Assistant to read its scheduled value. The example switches the room control to **Guest target**. An automation can use that value to drive another device.

[![The Office timeline using a number helper as a room control](../../images/number-helper-result.png)](../../images/number-helper.gif)

[Play walkthrough](../../images/number-helper.gif) | [Full-size GIF](../../images/number-helper.gif)

## Time, units and language

Choose Celsius or Fahrenheit, a 12- or 24-hour clock, and the time source in the card settings. For a wall dashboard in a different time zone, select Home Assistant time so the current-time marker follows the installation. See [language selection](../internationalization.md) and the [display settings](../configuration.md#rooms-and-basics).

[![Change to a 12-hour clock and Fahrenheit](../../images/clock-result.png)](../../images/clock.gif)

[Play walkthrough](../../images/clock.gif) | [Full-size GIF](../../images/clock.gif)

## Keep a timetable without sending commands

Open **Settings > Rooms**, expand the thermostat and switch off **Apply schedule to this thermostat**. Save. The row keeps its blocks while the device can be managed independently. Turn the option back on when the room should follow Timeline again.

[![Keep a timetable without sending commands](../../images/room-apply-result.png)](../../images/room-apply.gif)

[Play walkthrough](../../images/room-apply.gif) | [Full-size GIF](../../images/room-apply.gif)

## Apply a change during the current period

In the general settings, enable **Apply on edit** for active blocks and **Apply on default change** for gaps. Save. For example, editing the current block from 20 to 21 degrees can update the thermostat immediately. Editing a block that starts tomorrow changes the future plan.

[![Apply a change during the current period](../../images/apply-edit-result.png)](../../images/apply-edit.gif)

[Play walkthrough](../../images/apply-edit.gif) | [Full-size GIF](../../images/apply-edit.gif)

## Copy a plan between rooms

Expand the source row actions and choose **Copy plan**. Open the destination row and choose **Paste plan**. Check the destination blocks and use the card header Save control for pending edits. The same copy and paste controls are available between days in the weekday view.

[![Copy a plan between rooms](../../images/copy-plan-result.png)](../../images/copy-plan.gif)

[Play walkthrough](../../images/copy-plan.gif) | [Full-size GIF](../../images/copy-plan.gif)

## Choose the HVAC mode for a block

1. Open **Settings > Rooms**, expand the thermostat, enable **Choose HVAC mode per block**, and save. The option is off by default for every room.
2. Double-click a timeline block (or add one). Under **HVAC mode**, choose what the thermostat should do while this block is active.
3. Save the block, then use **Save** in the card header if it appears. With automatic application enabled, check the thermostat's **mode** as well as its **target temperature**.

| Block setting | What Timeline sends |
| --- | --- |
| Follow room settings (default) | Uses the existing temperature and optional turn-on behavior. Existing blocks and gaps follow the room settings. |
| Temperature only | Sends the scheduled temperature without a power, preset or mode command, even if the room normally sends a turn-on command. Use this when another automation controls when the heater may start. How an off thermostat handles a temperature command depends on the device. |
| Off | Switches the thermostat off. The block sends no temperature command. |
| Heat, Cool, Auto or Heat/Cool | Selects the mode and applies the target. A transition from Off to Heat works even when both blocks have the same temperature. |
| Fan only or Dry | Selects the mode without sending a heating target. |

The mode list comes from the primary thermostat. Linked thermostats skip a block command if they do not support its selected mode. Pauses and summer shutoff still apply. After an Off block, use a Heat block when you want heating to restart explicitly. Turning the room option off makes its blocks follow the room settings again.

[![Office switched off by its active block while Hall continues its schedule](../../images/block-hvac-off.png)](../../images/block-hvac.gif)

[![Office stays off as its target changes to 23 degrees in Temperature only mode](../../images/block-hvac-temperature-only.png)](../../images/block-hvac.gif)

[![Office heating again after saving Heat for its block](../../images/block-hvac-result.png)](../../images/block-hvac.gif)

[Play walkthrough](../../images/block-hvac.gif) | [Full-size GIF](../../images/block-hvac.gif)
