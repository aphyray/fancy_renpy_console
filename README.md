<img width="2236" height="1074" alt="image" src="https://github.com/user-attachments/assets/51246442-6389-4341-8dda-4f7537dc9a8f" />

This console runs overtop of the main game loop and will not interupt or restart interactions.

It can be repositioned and minimized to just the input line if you just want to execute commands.

There are a few convenience features, noted in the image above.

not noted:
* clicking on a command will copy it to the clipboard
* clicking on output will copy both the command and output to the clipboard
* shift-enter is a newline
* tab is a double-space
* shift-up/down moves up and down when there are multiple lines
* when you click the reticle in the top left there it changes modes - notify or watch

This also overwrites the watch and notify screens.

watch:
* a prettier stack
* scrollable with mouse wheel
* repeated expressions don't repeat
* click to clear expressions

notify:
* behaves like a queue now
* click to dismiss
* lingers based on cps preference, or using a default of 60 cps
* pretty
