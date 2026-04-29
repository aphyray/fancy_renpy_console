# It's A Fancy Ren'Py Console!

<img width="2236" height="1074" alt="image" src="https://github.com/user-attachments/assets/f1f09a8b-7016-44a6-9f63-3bec031cda62" />

## Overview
This console runs overtop of the main game loop and will not interupt or restart interactions.

It can be repositioned and minimized to just the input line if you just want to execute commands.

There are a few convenience features, noted in the image above.

## Other Features
* Clicking on a command will copy it to the clipboard
* Clicking on output will copy both the command and output to the clipboard
* `Shift-Enter` is a newline
* `Tab` is a double-space
* `Shift-Up/Down` moves up and down when there are multiple lines
* When you click the reticle in the top left there it changes modes - notify or watch

## Watch and Notify
This also overwrites the watch and notify screens.

### Watch
* A prettier stack
* Scrollable with the mouse wheel
* Repeated expressions don't repeat
* Click to clear expressions
* Pretty prints by default. Wrap expression in nopf() to prevent that

### Notify
* Behaves like a queue now
* Click to dismiss
* Lingers based on cps preference, or using a default of 60 cps
* Pretty

## Any AI Used in This?
No. The only intelligence I need to tap into is that of the fine folks in the Ren'Py Discord. Thanks to the lot of them for enduring my mad questions.

## Disclaimer

Provided without warranty. Full of jank and over-writing of functions in modules.

Pretty functional as of 8.5.3.
