# Timeline and room controls

## Create or change a block

Choose a room and open the block editor on its timeline. Set the times and target, then save. To change an existing block, double-click it. The [desktop editing guide](../../getting-started/quick-start.md#edit-a-scheduled-block) shows a morning block changing from 21 to 23 degrees. To remove a period, open the same editor and choose **Delete**.

## Defaults and automatic control

Choose a default temperature for gaps. For an 18-degree default and a 21-degree block from 06:00 to 09:00, the thermostat targets 21 during the block and returns to 18 at its end if no other rule applies. Enable shared storage and auto-apply for control with the dashboard closed. Check the target in Home Assistant when the block starts or ends.

## Room labels and external thermometers

Use the room settings to give the thermostat a display name, show its current temperature and optionally select an external sensor. The Home office bubble shows the thermometer reading while each block displays its scheduled target.

[![Home office row showing measured temperature and two scheduled targets](../../images/room-display-result.png)](../../images/room-display-result.png)

## Merged radiators and power commands

Choose a primary thermostat and add the other radiators under its room merge. Schedule the primary row once. Check both climate entities when the block starts. Each should receive the same target. If a model needs an explicit power command, enable its turn-on option and choose whether to send it before or after the target. See the [configuration example](../examples.md) for a two-radiator room.

## Schedule a number helper

Add an `input_number` helper to the card's entities and choose a default or add blocks. With auto-apply on, open the helper in Home Assistant to read its scheduled value. Here **Guest target** has changed to 19. An automation can use that value to drive another device.

[![Home Assistant number helper showing a scheduled value of 19 degrees](../../images/number-helper-result.png)](../../images/number-helper-result.png)

## Time, units and language

Choose Celsius or Fahrenheit, a 12- or 24-hour clock, and the time source in the card settings. For a wall dashboard in a different time zone, select Home Assistant time so the current-time marker follows the installation. See [language selection](../internationalization.md) and the [display settings](../configuration.md#rooms-and-basics).
