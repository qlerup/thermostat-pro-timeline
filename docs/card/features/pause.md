# Room pauses and manual targets

![Timeline with the room pause beside the Office toggle and global pause in the header](../../images/office-dashboard.png)

**Pause one room.** On the room row, select the small pause-circle beside the schedule toggle. Choose one hour, five hours, a custom duration or an indefinite pause. Other rooms can continue following their schedules.

![Duration choices in the Office pause menu](../../images/room-pause-menu.png)

**Resume a room.** Open the same room's pause menu and select resume. A global pause still applies. To pause the entire schedule, use the pause button in the header beside the settings gear.

**Adjust a thermostat manually.** With background auto-apply enabled, a detected manual change to a climate target creates a timed room pause. For example, a change from 21 to 22.5 degrees during a block lasts until the room’s next effective block start or end, or until midnight. Returning to the scheduled target cancels the generated hold. An explicit room pause takes precedence.

**After a restart.** Timeline saves the hold. The thermostat integration restores its own temperature. Opening an existing shared dashboard in v3.3.3 reads the shared schedule without saving the browser’s copy over it.
