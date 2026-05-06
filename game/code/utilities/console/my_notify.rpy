
## Notify screen ###############################################################
##
## The notify screen is used to show the player a message. (For example, when
## the game is quicksaved or a screenshot has been taken.)
##
## https://www.renpy.org/doc/html/screen_special.html#notify-screen

init python:

    import traceback

    def add_message_to_notify_stack(message=""):
        notify.stack.append(message)
        if not renpy.get_screen("notify_stack"):
            renpy.exports.show_screen("notify_stack")
        try:
            renpy.display.tts.notify_text = renpy.text.extras.filter_alt_text(message)
            renpy.exports.restart_interaction() # could have unintended consequences...
        except:
            pass

    # renpy's default implementation
    
    # def display_notify(message):
    #     """
    #     :doc: other

    #     The default implementation of :func:`renpy.notify`.
    #     """

    #     renpy.exports.hide_screen("notify")
    #     renpy.exports.show_screen("notify", message=message)
    #     renpy.display.tts.notify_text = renpy.text.extras.filter_alt_text(message)

    #     renpy.exports.restart_interaction()

    def remove_message_from_stack(message):
        if message in notify.stack:
            notify.stack.remove(message)
        if message in notify.clear_queue:
            notify.clear_queue.remove(message)

define config.notify = add_message_to_notify_stack
default notify.stack = []
default notify.clear_queue = []

screen notify_stack():

    layer "notify"
    zorder 10000

    $ stack = notify.stack
    $ clear_queue = notify.clear_queue

    if clear_queue:
        timer 0.1 repeat True action Function(remove_message_from_stack, message)
        text str(clear_queue)

    frame:
        background None
        align (1.0, 0.0)
        padding (0.0, 0.0)
        xmaximum 0.4
        vbox:
            for message in stack:
                use notify(message) id message

screen notify(message):

    layer "notify"
    zorder 10000

    style_prefix "notify"

    default start_hiding = False
    default fade_time = 0.2

    python:
        if message is None:
            message = "None"
        
        if message == "":
            message = "<empty string>"

        # message = renpy.filter_text_tags(renpy.substitute("{{".join(renpy.last_say().what).split("{")), allow=allow=gui.history_allow_tags)

    if start_hiding:
        timer fade_time repeat True action Function(remove_message_from_stack, message)

    frame:
        background None
        padding (0, 0)
        xfill False
        yfill False
        align (1.0, 0.0)
        at transform:
            ease fade_time crop (0, 0, float(not start_hiding), float(not start_hiding))

        button style "notify_button" at notify_appear:
            action SetLocalVariable("start_hiding", True), SetLocalVariable("fade_time", 0.1)
            align (1.0, 0.0)

            python:

                formatted_message = " "

                try:

                    if config.say_menu_text_filter is not None:
                        # formatted_message = renpy.filter_text_tags("{{".join(config.say_menu_text_filter(message).split("{")), allow=gui.history_allow_tags)
                        formatted_message = renpy.filter_text_tags(config.say_menu_text_filter(message), allow=gui.history_allow_tags)
                    else:
                        # formatted_message = renpy.filter_text_tags("{{".join(renpy.substitute(message).split("{")), allow=gui.history_allow_tags)
                        formatted_message = renpy.filter_text_tags(message, allow=gui.history_allow_tags)
                
                except Exception as e:

                    formatted_message = "<a notify string is busted>"
                    print("notify failed on this message: " + message)

            text "[formatted_message]"

    # the default calculation for a string's read time uses a factor of 1.0 instead of 0.5, and no minimum.
    $ wait_time = 7.0 + 0.5/((_preferences.text_cps if _preferences.text_cps != 0 else 60) / len(message))

    timer wait_time action SetLocalVariable("start_hiding", True)


transform notify_appear:
    on show:
        alpha 0
        linear .25 alpha 1.0
    on hide:
        linear .5 alpha 0.0


style notify_text is gui_text:
    properties gui.text_properties("notify")

style notify_button_text is notify_text:
    properties gui.text_properties("notify")
    textalign 1.0

style notify_button is empty:
    background Frame("gui/notify.png", gui.notify_frame_borders, tile=gui.frame_tile)
    padding gui.notify_frame_borders.padding


    
