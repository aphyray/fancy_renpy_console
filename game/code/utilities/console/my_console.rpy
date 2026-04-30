# allows the console to appears even in menues
define config.top_layers = config.top_layers + [
    "console",
    "notify",
]

define config.interface_layer = "console"

define config.console_history_size = 50

default _console.reticle_callback = notify_tag_attributes
default _console.reticle_callback_alternate = watch_tag_attributes
default _console.verbose = False
default _console.autocomplete_on = True
default _console.suppressed_error_patterns = [
    "Exception: Cannot start an interaction in the middle of an interaction, without creating a new context.",
    # "TypeError: exec() arg 1 must be a string, bytes or code object",
]
default persistent.reticle_watch_on = False
default persistent.console_minimized = False
default persistent.console_bounds = (absolute(1200.0), absolute(80.0), absolute(600.0), absolute(800.0))
default persistent.console_history_display_limit = 100
default persistent.text_size_adjustment = 0

default persistent.console_image_summary_layers = dict(zip(renpy.display.scenelists.ordered_layers, [True for i in range(0, len(renpy.display.scenelists.ordered_layers))]))

define config.label_overrides = {
    "_console": "_my_console",
    "_console_return": "_my_console_return",
    }


# Console styles.
init -1500:

    style _console is _default:
        xpadding gui._scale(20)
        ypadding gui._scale(10)
        xfill True
        yfill True
        color "#FFF"
        background "#000C"

    style _console_vscrollbar is _vscrollbar

    style _console_text is _default:
        color "#FFF"
        size 18
        font "code/utilities/console/fonts/AzeretMono-Regular.ttf"
        adjust_spacing False
        antialias False
        font_features { "liga": False, "clig" : False }
        language "anywhere" # where to split words. anywhere is... as it says on the box. will event split words in the middle
        yalign 0.5

    style _console_input is _default:
        xfill True

    style _console_input_text is _console_text:
        color "#FFF"
        size 18
        layout "greedy"
        language "anywhere"
        adjust_spacing "vertical"
        antialias False
        yalign 1.0
        xalign 0.0

    style _console_history is _default:
        xfill True
        color "#FFF"

    style _console_command_text is _console_text:
        color "#FFFC"
        font "code/utilities/console/fonts/AzeretMono-Italic.ttf"
        # italic True

    style _console_result_text is _console_text

    style _console_error_text is _console_text:
        color "#f98a8aff"
        font "code/utilities/console/fonts/AzeretMono-SemiBold.ttf"

    style _console_trace is _default:
        background "#0004"
        color "#FFF"
        xalign 1.0
        top_margin 20
        right_margin 20
        xpadding 2
        ypadding 2

    style _console_trace_text is _default:
        color "#FFF"
        font "code/utilities/console/fonts/AzeretMono-Regular.ttf"
        size 16

    style _console_trace_var is _console_trace_text:
        color "#FFF9"
        font "code/utilities/console/fonts/AzeretMono-Italic.ttf"
        bold False
        
    style _console_trace_value is _console_trace_text

init -1400 python in _console:

    import traceback

    class MyScriptErrorHandler:
        """
        Handles error in Ren'Py script.
        """

        def __init__(self):
            self.target_depth = renpy.call_stack_depth()

        def __call__(self, traceback_exception):
            he = console.history[-1]
            he.result = traceback_exception.format_exception_only(_ExceptionPrintContext(filter_private=False))
            he.is_error = True

    @command(_("jump <label>: jumps to label"))
    def jump(l):
        label = l.label_name()

        if label is None:
            raise Exception("Could not parse label. (Unqualified local labels are not allowed.)")

        if not console.can_renpy():
            raise Exception("Ren'Py script not enabled. Not jumping.")

        if not renpy.has_label(label):
            raise Exception("Label %s not found." % label)

        # renpy.pop_call()
        renpy.jump(label)

    @command(_("watch <expression>: watch a python expression\n watch short: makes the representation of traced expressions short (default)\n watch long: makes the representation of traced expressions as is"))
    def watch(l):
        expr = l.rest()
        expr = expr.strip()

        if expr == "short":
            persistent._console_traced_short = True
            return

        if expr == "long":
            persistent._console_traced_short = False
            return

        try:
            renpy.python.py_compile(expr, 'eval')

            traced_expressions.append(expr)

            if "_trace_screen" not in config.always_shown_screens:
                config.always_shown_screens.append("_trace_screen")

        except Exception as e:
            error = ""
            if verbose:
                error = str("\n".join(traceback.format_exception(e)))
            else:
                error = str(e)

            renpy.notify("{}{}{}".format("{color=#F00}", error, "{/color}"))

            pass

    def is_renpy_statement(line):
        rv = len(renpy.parser.parse_block(renpy.lexer.lex_string(line, advance=False))) > 0
        return rv

    # stolen wholecloth from script.py > Script() > update_bytecode()
    def give_python_node_bytecode(python_node):
        pycode_node = python_node.code
        pycode_node.bytecode = renpy.python.py_compile(
                    pycode_node.source,
                    pycode_node.mode,
                    filename=pycode_node.filename,
                    lineno=pycode_node.linenumber,
                    py=pycode_node.py,
                    hashcode=pycode_node.hashcode,
                    column=pycode_node.col_offset,
                )

    def execute_renpy_in_current_context(line, include_return=False):
        """
        Rather than using call(), which goes back to the beginning of the interaction
        This sews the statement into the context's node chain and allows it to run immediately
        """
        error = None

        parsed = renpy.parser.parse_block(renpy.lexer.lex_string(line, advance=False))

        try:
            if len(parsed) > 0:
                # remove Return nodes, or the current context gets nuked
                nodes = [
                    node
                    for node in parsed
                    if include_return or type(node) != renpy.ast.Return
                ]

                for i, node in enumerate(nodes[0:-1]):
                    nodes[i].chain(nodes[i+1])
                nodes[-1].chain(renpy.game.context().next_node)

                for node in nodes:
                    if type(node) == renpy.ast.Python:
                        give_python_node_bytecode(node) # need to manually set this for python statements invoked from strings it seems
                    node.execute()

        except Exception as e:
            error = e
            # if verbose:
            #     error = str("\n".join(traceback.format_exception(e)))
            # else:
            #     error = str(e)

        # some errors can be ignored
        if len([ pattern for pattern in suppressed_error_patterns if pattern in str("\n".join(traceback.format_exception(error)))]) > 0:
            return None

        return error

    def run(self, lines):
        
        line_count = len(lines)
        code = "\n".join(lines)

        he = ConsoleHistoryEntry(code)
        if code != "exit":
            self.history.append(he)
        else:
            code = "renpy.hide_screen('_console')"

        try:

            # If we have 1 line, try to parse it as a command.
            if line_count == 1:
                block = [ ( "<console>", 1, code, [ ]) ]
                l = renpy.parser.Lexer(block)
                l.advance()

                # Command can be None, but that's okay, since the lookup will fail.
                command = l.word()

                command_fn = config.console_commands.get(command, None)

                if command_fn is not None: # and command != "jump":
                    he.result = command_fn(l)
                    he.update_lines()
                    # return

            error = None

            # print("trying to renpy")


            if he.result is None:

                # Try to run it as Ren'Py.
                if self.can_renpy():

                    if is_renpy_statement(code):
                        error = execute_renpy_in_current_context(code)
                        if error is None:
                            return
                        # else:
                        #     name = renpy.load_string(code + "\nreturn")
                        #     if name is not None:
                        #         renpy.game.context().exception_handler = MyScriptErrorHandler()
                        #         # modifying this so running renpy statements won't advance the script
                        #         renpy.call(name, from_current=True)
                        #     else:
                        #         error = "\n\n".join(renpy.get_parse_errors())

            
            if he.result is None:

                # Try to eval it.
                try:
                    renpy.python.py_compile(code, 'eval')
                except Exception:
                    pass
                else:
                    try:
                        result = renpy.python.py_eval(code)
                        if persistent._console_short and not getattr(result, "_console_always_long", False):
                            he.result = aRepr.repr(result)

                            if not self.did_short_warning and he.result != repr(result):
                                self.did_short_warning = True
                                he.result += "\n\n" + __("The console is using short representations. To disable this, type 'long', and to re-enable, type 'short'")
                        else:
                            he.result = repr(result)

                        he.update_lines()
                        # return

                    except Exception as e:
                        error = e
                        # if verbose:
                        #     error = str("\n".join(traceback.format_exception(e)))
                        # else:
                        #     error = str(e)

            # print("trying to exec")

            if he.result is None:

                # Try to exec it.
                try:
                    renpy.python.py_compile(code, "exec")
                except Exception as e:
                    if error is None:
                        error = e

                else:
                    try:
                        renpy.python.py_exec(code)
                        # return
                    except Exception as e:
                        if error is None:
                            error = e

            if he.result is None:

                if error is not None:
                    error_string = ""
                    if verbose:
                        error_string = str("\n".join(traceback.format_exception(error))) # the whole traceback
                    else:
                        error_string = str(traceback.format_exception_only(error)[-1]) # just the final line of the error is fine
                    error_lines = error_string.split("\n")
                    # error_lines = [ l for l in error_lines if not l or l.strip(" ~^") ] # remove ^/~ only lines.

                    # renpy.notify(str(error_lines))

                    if error_lines[-1] == "":
                        error_lines.pop()

                    # he.result = "\n".join( error_lines ).replace("{", "{{")
                    he.result = "\n".join( error_lines )
                    he.update_lines()
                    he.is_error = True

        except renpy.game.CONTROL_EXCEPTIONS:
            raise

        except Exception as e:
            he.result = self.format_exception(e)
            he.update_lines()
            he.is_error = True

        if persistent.console_minimized:
            renpy.notify(he.result)

    def enter():
        """
        Called to enter the debug console.
        """

        if console is None:
            return

        if renpy.get_screen("_console") is None:
            renpy.show_screen("_console")
            renpy.restart_interaction()

        # # if rollback is available, it means we're in the main game loop, so we can open in the current context
        # if renpy.game.context().rollback:
        #     try:
        #         renpy.rollback(checkpoints=0, force=True, greedy=False, current_label="_console")
        #         # renpy.rollback(checkpoints=0, force=True, greedy=True, defer=True, abnormal=False, label="_console")
        #     except renpy.game.CONTROL_EXCEPTIONS:
        #         raise
        #     except Exception:
        #         pass

        # # if rollback is *not* available, it *probably* means we're in menus, so we should open in a new context.
        # renpy.call_in_new_context("_console")

    
    # for some reason the default method of pulling the history out of the console wasn't working for my screen, so I've adapted it here 
    def console_restore_from_persistent(console):

        console.history = BoundedList(config.console_history_size, config.console_history_lines + config.console_history_size)
        console.line_history = BoundedList(config.console_history_size)
        console.line_index = 0

        if persistent._console_history is not None:
            for i in persistent._console_history:
                he = ConsoleHistoryEntry(i[0], i[1], i[2])
                he.update_lines()
                console.history.append(he)

        if persistent._console_line_history is not None:
            console.line_history.extend(persistent._console_line_history)

init python:
    import itertools
    import linecache

    def dragged_console(drags=None, drop=None):
        # persistent.console_bounds = (absolute(drags[0].x), absolute(drags[0].y), absolute(drags[0].w), absolute(drags[0].h))
        persistent.console_bounds = (absolute(drags[0].x), absolute(drags[0].y), absolute(persistent.console_bounds[2]), absolute(persistent.console_bounds[3]))
        # renpy.restart_interaction()
        return None


    def dragged_console_resizer(drags=None, drop=None):
        persistent.console_bounds = (absolute(persistent.console_bounds[0]), absolute(persistent.console_bounds[1]), absolute(max(400, persistent.console_bounds[2] + drags[0].x)), absolute(max(300, persistent.console_bounds[3] + drags[0].y)))
        drags[0].snap(0, 0, 0, _warper.easein_elastic)
        # Scroll("history_viewport", "vertical increase", 20000.0, 0.01).__call__()
        renpy.restart_interaction()
        return None


    def dragged_reticle(drags=None, drop=None):
        global watch_variable
        watch_variable = drags
        mouse_x, mouse_y = renpy.get_mouse_pos()
        layer = "master"
        tags = [(tag_and_order[0], tag_and_order[1], renpy.get_image_bounds(tag_and_order[0])) for tag_and_order in renpy.get_zorder_list(layer)]
        overlapping_tags = [
            tag_details
            for tag_details in tags
            # doesn't work when we're using relative positions
            # if (drags[0].x+drags[0].w/2 > tag_details[2][0] and drags[0].x+drags[0].w/2 < tag_details[2][0]+tag_details[2][2]
            #     and drags[0].y+drags[0].h/2 > tag_details[2][1] and drags[0].y+drags[0].h/2 < tag_details[2][1]+tag_details[2][3]
            # )
            if (mouse_x > tag_details[2][0] and mouse_x < tag_details[2][0]+tag_details[2][2]
                and mouse_y > tag_details[2][1] and mouse_y < tag_details[2][1]+tag_details[2][3]
            )
        ]

        if overlapping_tags:
            overlapping_tags = overlapping_tags[-1]        
        else:
            overlapping_tags = None

        if renpy.get_screen_variable("reticle_alternate_on"):
            _console.reticle_callback_alternate(None if overlapping_tags is None else overlapping_tags[0], layer)
        else:
            _console.reticle_callback(None if overlapping_tags is None else overlapping_tags[0], layer)

        # drags[0].snap(drags[0].start_x, drags[0].start_y, 0.25, _warper.easein_elastic)
        drags[0].snap(0, 0, 0.25, _warper.easein_elastic)

        return None

    def notify_tag_attributes(tag, layer="master"):
        renpy.notify("None" if tag is None else str(list(itertools.chain([tag], renpy.get_attributes(tag, layer)))))
        return None

    def watch_tag(tag, layer="master"):
        return "None" if tag is None else " ".join(list(itertools.chain([tag], renpy.get_attributes(tag, layer))))

    def watch_tag_attributes(tag, layer="master"):
        if tag is None:
            return None
        renpy.watch("watch_tag('{}', '{}')".format(tag, layer))
        renpy.watch("get_all_transform_properties('{}', '{}')".format(tag, layer))
        renpy.restart_interaction()
        return None

    def watch_at_list(tag, layer="master"):
        return renpy.get_at_list(tag, layer)

    def get_all_transform_properties(tag, layer="master"):
        
        default_transform = renpy.display.transform.TransformState()
        transform = renpy.get_screen(tag, layer=layer)
        new_adjustments = default_transform.diff(transform.state)
        adjustments = {x: [new_adjustments[x][1]] for x in new_adjustments}

        while new_adjustments and hasattr(transform, "child") and hasattr(transform.child, "state"):
            new_adjustments = default_transform.diff(transform.child.state)
            adjustments = {
                x: ([new_adjustments[x][1]] if new_adjustments.get(x) else []) + (adjustments[x] if adjustments.get(x) else [])
                for x in set(list(new_adjustments)).union(list(adjustments))
            }
            transform = transform.child
        
        return adjustments


    def get_image_attributes_summary():

        output_strings = []

        for layer in renpy.display.scenelists.ordered_layers:
            hidden = renpy.get_hidden_tags(layer)
            showing = renpy.get_showing_tags(layer, sort=True)
            transforms = renpy.layer_has_transforms(layer)
            transform_list = []

            if transforms.at_list:
                transform_list.append("show layer")
            if transforms.camera:
                transform_list.append("camera")
            if transforms.config_layer_transforms:
                transform_list.append("config.layer_transforms")

            if not hidden and not showing:
                continue

            if layer in renpy.config.context_clear_layers:
                continue

            output_strings.append(
                "layer {}".format(layer)
            )

            if transform_list:
                output_strings.append(
                    "(transforms: {})".format(', '.join(transform_list))
                )

            for name in hidden:
                attributes = " ".join(renpy.get_attributes(name, layer=layer))
                output_strings.append(
                    "> {} {} (hidden)".format(name, attributes)
                )

            for name in showing:
                attributes = " ".join(renpy.get_attributes(name, layer=layer))
                output_strings.append(
                    "> {} {}".format(name, attributes)
                )

            output_strings.append(" ")

        return output_strings


    def image_attributes():
        return "\n".join(get_image_attributes_summary())

    def get_image_summary(layers=None):

        output_strings = []

        if layers is None:
            layers = [ layer_name for layer_name in persistent.console_image_summary_layers if persistent.console_image_summary_layers[layer_name] ]

        for layer in layers:
            hidden = renpy.get_hidden_tags(layer)
            showing = renpy.get_showing_tags(layer, sort=True)
            transforms = renpy.layer_has_transforms(layer)
            transform_list = []

            if transforms.at_list:
                transform_list.append("show layer")
            if transforms.camera:
                transform_list.append("camera")
            if transforms.config_layer_transforms:
                transform_list.append("config.layer_transforms")

            if not hidden and not showing:
                continue

            if layer in renpy.config.context_clear_layers:
                continue

            output_strings.append(
                "layer {}".format(layer)
            )

            if transform_list:
                output_strings.append(
                    "(transforms: {})".format(', '.join(transform_list))
                )

            for name in hidden:
                attributes = " ".join(renpy.get_attributes(name, layer=layer))
                output_strings.append(
                    "> {} {} (hidden)".format(name, attributes)
                )

            for name in showing:
                attributes = " ".join(renpy.get_attributes(name, layer=layer))
                transforms = ", ".join(get_transforms_on_tag(name, layer))
                output_strings.append(
                    "> {}{}{}{}{}".format(name, " " if len(attributes) > 0 else "", attributes, " at " if len(transforms) > 0 else "", transforms)
                )

            output_strings.append(" ")

        return output_strings


    def image_summary(layers=None):
        return "\n".join(get_image_summary(layers))


    def get_script_lines(filename):

        filename = renpy.exports.unelide_filename(filename)

        data_io = open(filename, "r", encoding="utf-8")

        with data_io:
            data = data_io.read()

        if filename.endswith("_ren.py"):
            data = ren_py_to_rpy(data, filename)
        
        return data

    # loc is a tuple with (path, line_number)
    def get_line_from_loc(loc):
        return get_script_lines(loc[0]).splitlines()[loc[1]]

    def get_console_input_text():

        try:
            return renpy.get_screen_variable("console_input", "_console").content
        except:
            return ""

    def set_console_input_text(string=""):

        try:
            input_object = renpy.get_screen_variable("console_input", "_console")
        except:
            return

        # line = input_object.content
        input_object.caret_pos = len(string)
        input_object.old_care_pos = len(string)
        input_object.update_text(string, True)
        input_object.per_interact()

    def set_console_autocomplete_text(string=""):

        try:
            input_object = renpy.get_screen_variable("console_autocomplete_input", "_console")
        except:
            return

        line = input_object.content
        input_object.caret_pos = len(string)
        input_object.old_care_pos = len(string)
        input_object.update_text(string, True)
        input_object.per_interact()


    def set_input_text(input_object, content=""):

        input_object.caret_pos = len(string)
        input_object.old_care_pos = len(string)
        input_object.update_text(string, True)
        input_object.per_interact()

    def console_watch_current_input():

        text_value = get_console_input_text()
        
        # if the input field is empty, watch the previous command
        if text_value == "":
            text_value = _console.console.line_history[-1][0] if len(_console.console.line_history) > 0 else ""

        if text_value != "":
            renpy.watch(text_value)
            set_console_input_text()

    def console_process_input(console):

        # input_object = renpy.get_screen_variable("console_input", "_console")

        # line = input_object.content
        # input_object.caret_pos = 0
        # input_object.old_care_pos = 0
        # input_object.update_text("", True)
        # input_object.per_interact()

        line = get_console_input_text()

        if line == "":
            return

        set_console_input_text()

        # line = value.get_text()
        # value.set_text("")

        console.lines.pop()
        console.lines.append(line)

        lines = console.lines
        if not console.line_history or console.line_history[-1] != lines:
            console.line_history.append(lines)

        console.reset()

        if config.console_callback is not None:
            lines = config.console_callback(lines)

            if not lines:
                return

        try:
            _console.run(console, lines)
        finally:
            console.backup()
            renpy.game.context().force_checkpoint = True
            renpy.exports.checkpoint(hard="not_greedy")
        
        return None

    def console_save_state(console):
        console.backup()

    def console_handle_escape(exit_action):
        if len(persistent.autocomplete_list) > 0:
            console_clear_autocomplete()
        elif get_console_input_text() != "":
            set_console_input_text()
        else:
            for action in [] + exit_action:
                action.__call__()
    
    def console_recall_line(console, offset):

        setattr(console, "line_index", min(max(console.line_index + offset, 0), max(len(console.line_history), 0)))

        line_value = ""

        if console.line_index != len(console.line_history):
            line_value = console.line_history[console.line_index][0]

        set_console_input_text(line_value)


    def toggle_reticle_mode():
        renpy.set_screen_variable("reticle_alternate_on", not renpy.get_screen_variable("reticle_alternate_on"))
        renpy.restart_interaction()
        return None 

    
    def unwatch_thoroughly(expression):
        while expression in _console.traced_expressions:
            renpy.unwatch(expression)

    
    def get_lines_from_text_displayable(text_displayable, width=500):
        
        text_displayable.update() # creates tokens, which Layout requires

        layout = renpy.text.text.Layout(text_displayable, width, 0, None, drawable_res=False)

        lines = []

        for line in layout.lines:
            lines.append("".join([ chr(g.character) for g in line.glyphs ]))
        
        return lines

    # def refresh_console():
    #     if renpy.get_screen("_console"):
    #         _console.console.show_stdio() 
    #         renpy.hide_screen("_console")
    #         renpy.show_screen("_console")

    # config.stdout_callbacks.append(refresh_console)
    # config.stderr_callbacks.append(refresh_console)

    # used for fuzzy matching and sorting with .ratio()
    from difflib import SequenceMatcher

    def fuzzy_match_sorter(big_string, small_string):
        big_string = str.casefold(big_string)
        small_string = str.casefold(small_string)
        # "00000big_string" when there's a partial match right at the start
        # "00009big_string" when there's a 0.9 fuzzy ratio - x10 to group into rough categories and then alphabetically 
        return "00000" + big_string if big_string.startswith(small_string) else "{:05d}{}".format(10 - int(10*SequenceMatcher(None, small_string, big_string).ratio()), big_string)

    def fuzzy_match_sorter(big_string, small_string):
        lower_big_string = str.casefold(big_string)
        lower_small_string = str.casefold(small_string)

        ranked_partial_match_string = "{:05d}{}".format(0, lower_big_string)

        ranked_fuzzy_string = "{:05d}{}".format(
            int(8*max(SequenceMatcher(None, lower_small_string, lower_big_string).ratio(), SequenceMatcher(None, lower_big_string, lower_small_string).ratio())),
            lower_big_string
        )

        # "Abig_string" when there's a partial match right at the start
        # "[B..]big_string" when there's a 0.9 fuzzy ratio - x10 to group into rough categories and then alphabetically 
        return ranked_partial_match_string if lower_big_string.startswith(lower_small_string) else ranked_fuzzy_string


    # s1 = ' It was a dark and stormy night. I was all alone sitting on a red chair. I was not completely alone as I had three cats.'
    # s2 = ' It was a murky and stormy night. I was all alone sitting on a crimson chair. I was not completely alone as I had three felines.'
    # SM(None, s1, s2).ratio()

    def handle_input_change(content):

        # include_renpy_statements = False

        persistent.console_input_text = content

        persistent.autocomplete_list.clear()
        persistent.autocomplete_selection_index = 0
        update_autocomplete_list_position_and_text()

        if not _console.autocomplete_on:
            return        
        
        if persistent.autocomplete_on and persistent.console_input_text != "":
            subject = re.split(r'[^\w\.]', persistent.console_input_text)[-1]
            current_leaf = subject.split('.')[-1]
            if re.match(r'^.*\w.*$', subject):
                try:
                    subject_object = eval('.'.join(("store." + subject).split('.')[0:-1]))
                    # available_variables = list(set(dir(subject_object) + ([] if include_renpy_statements and subject != current_leaf else list(set([i for sub in list(renpy.statements.registry.keys()) for i in sub ]))))) # all the renpy commands, but only if this is the first item
                    available_variables = list(set(dir(subject_object) + ([] if subject != current_leaf else list(config.console_commands))))
                    persistent.autocomplete_list = sorted(
                                [
                                    item for item in available_variables
                                    if not item[0:2] == "__" and (current_leaf == "" or item.lower().startswith(current_leaf.lower()) or SequenceMatcher(None, current_leaf.lower(), item.lower()).ratio() > 0.65 )
                                ],
                                key=renpy.partial(fuzzy_match_sorter, small_string=current_leaf)
                            )
                except:
                    pass

        persistent.autocompleting = len(persistent.autocomplete_list) > 0

        if persistent.autocompleting:
            set_console_autocomplete_text(get_autocomplete_list_with_highlight())
        else:
            set_console_autocomplete_text("")

    def get_branch_and_leaf_from_incomplete_statement(statement):
        split_by_nonwords = re.split(r'(\W)', statement)
        leaf = split_by_nonwords[-1]
        branch = ''.join(split_by_nonwords[0:-1])

        return {"branch": branch, "leaf": leaf}

    def get_autocomplete_list_with_highlight(offset_by=0):
        max_length = 5
        
        persistent.autocomplete_selection_index += offset_by
        persistent.autocomplete_selection_index = min(max(0, persistent.autocomplete_selection_index), len(persistent.autocomplete_list)-1)
        index = persistent.autocomplete_selection_index

        offset = int(
            max(
                0,
                min(
                    len(persistent.autocomplete_list)-max_length,
                    max(0, index - max_length/2 + 1)
                )
            )
        )

        items = [
            "{}{}".format(
                "> " if i == index-offset else "  ",
                item
            )
            for i, item in enumerate(persistent.autocomplete_list[offset:offset+max_length])
        ]

        if offset > 0:
            items.insert(0, "  ... {} ...".format(offset))
        
        if offset + max_length < len(persistent.autocomplete_list):
            items.append("  ... {} ...".format(len(persistent.autocomplete_list) - offset - max_length))

        return '\n'.join(items)

    def update_autocomplete_list_position_and_text(offset_by=0):
        if _console.autocomplete_on and len(persistent.autocomplete_list) > 0:
            set_console_autocomplete_text(get_autocomplete_list_with_highlight(offset_by=offset_by))
        elif offset_by != 0:
            console_recall_line(_console.console, offset_by)
            console_clear_autocomplete()

    def console_clear_autocomplete():
        persistent.autocomplete_list.clear()
        update_autocomplete_list_position_and_text()
        set_console_autocomplete_text("")

    def console_handle_tab_keypress():
        if len(persistent.autocomplete_list) > 0:
        
            input_text = get_console_input_text()
            branch_and_leaf = get_branch_and_leaf_from_incomplete_statement(input_text)

            set_console_input_text(branch_and_leaf["branch"] + persistent.autocomplete_list[persistent.autocomplete_selection_index])
        
            console_clear_autocomplete()
        else:
            _TouchKeyboardTextInput('  ').__call__()


    def console_handle_return_keypress():
        if len(persistent.autocomplete_list) > 0:
        
            input_text = get_console_input_text()
            branch_and_leaf = get_branch_and_leaf_from_incomplete_statement(input_text)
            completed_statement = branch_and_leaf["branch"] + persistent.autocomplete_list[persistent.autocomplete_selection_index]

            set_console_input_text(completed_statement)

            if(input_text == completed_statement):
                console_process_input(_console.console)
                _console.console.show_stdio()
        
            console_clear_autocomplete()

        else:
        
            console_process_input(_console.console)
            _console.console.show_stdio()

            # Function(console_process_input, _console.console),
            # Function(_console.console.show_stdio), # grabs any stdio output in the buffer
            # Scroll("history_viewport", "vertical increase", -100000000.0, 0.0),
            

screen autocomplete_widget():
    layer config.interface_layer
    zorder 100000

    $ autocomplete_list = persistent.autocomplete_list

    frame:

        align (0.5, 0.5)

        has vbox

        for entry in autocomplete_list:
            button:
                text entry style "_console_text"



default persistent.console_input_text = ""
default persistent.autocomplete_on = True
default persistent.autocomplete_list = []
default persistent.autocompleting = False
default persistent.autocomplete_selection_index = 0

# the console

screen _console(lines=_console.console.lines[:-1], indent="  ", default=_console.console.lines[-1], history=_console.console.history, _transient=False):
    # This screen takes as arguments:
    #
    # lines
    #    The current set of lines in the input buffer.
    # indent
    #    Indentation to apply to the new line.
    # history
    #    A list of (command, result, is_error) tuples.

    layer config.interface_layer
    zorder 1500
    modal False
    roll_forward True

    on "show" action SetVariable(
        "persistent.console_image_summary_layers",
        dict(zip(renpy.display.scenelists.ordered_layers, [True for i in range(0, len(renpy.display.scenelists.ordered_layers))])) if len(persistent.console_image_summary_layers) != len(renpy.display.scenelists.ordered_layers) else persistent.console_image_summary_layers
    )

    # default autocomplete_list = []

    python:
        # autocomplete_list = [] if (get_console_input_text() == "") else sorted(
        #             [
        #                 item for item in autocomplete_options
        #                 if item.lower().startswith(current_leaf.lower())
        #             ],
        #             key=str.casefold
        #         )

        exit_action = [Function(console_save_state, _console.console), Hide()] #, Function(renpy.end_interaction, 0)

        minimized = persistent.console_minimized
        maximized = persistent.console_maximized

        history = _console.console.history

        line_height = int((style["_console_text"].size + persistent.text_size_adjustment)*1.1 + 5)
        history_limit = persistent.console_history_display_limit
        lines_per_row = 25
        lines_to_print = [] # (line_text, "command"/"result"/"error", clipboard_text)

        history_scroll_adjustment = ui.adjustment(step=-line_height)

        text_size_adjustment = persistent.text_size_adjustment

    default reticle_alternate_on = False

    default scroll_needed = True

    on "show" action [
        Function(_console.console.show_stdio), # grabs any stdio output in the buffer
    ]

    default default = (_console.console.line_history[_console.console.line_index][0] if _console.console.line_index < len(_console.console.line_history) else "")  
    default console_input_line = default
    default line = ""

    # default console_input_adjust_spacing = False

    # default console_input_value = ScreenVariableInputValue("console_input_line")
    
    draggroup:
        at transform:
            subpixel True
        drag as console_window:
            dragged dragged_console
            draggable (not maximized)
            drag_offscreen True
            xpos (persistent.console_bounds[0] if not maximized else 0)
            ypos (persistent.console_bounds[1] if not maximized else 0)
            xsize (persistent.console_bounds[2] if not maximized else config.screen_width)
            if not minimized:
                ysize (persistent.console_bounds[3] if not maximized else config.screen_height-50)

            frame as outer_frame:
                style "_console"
                padding (0, 0)
                background "#110019AA"
                yfill False
                xfill False

                vbox:

                    fixed as titlebar_fixed:
                        fit_first True
                        frame:
                            padding (0, 0)
                            background "#2139"
                            yalign 0.5
                            hbox as hb:
                                spacing 10
                                xalign 1.0
                                yalign 0.5
                                xfill True
                                yfill False
                                box_align 1.0
                                null:
                                    xfill True
                                button:
                                    action IncrementVariable("persistent.text_size_adjustment", -2)
                                    padding (16, 16)
                                    xsize 42
                                    ysize 42
                                    xalign 0.5
                                    yalign 0.5
                                    text "-":
                                        style "_console_text"
                                        size 20
                                        outlines [ (absolute(1.0), "#FFF", absolute(0), absolute(0)) ]
                                button:
                                    action IncrementVariable("persistent.text_size_adjustment", 2)
                                    padding (16, 16)
                                    xsize 42
                                    ysize 42
                                    xalign 0.5
                                    yalign 0.5
                                    text "+":
                                        style "_console_text"
                                        size 20
                                        outlines [ (absolute(1.0), "#FFF", absolute(0), absolute(0)) ]
                                button:
                                    action ToggleVariable("persistent.console_minimized")
                                    padding (16, 16)
                                    xsize 42
                                    ysize 42
                                    xalign 0.5
                                    yalign 0.5
                                    text "⌤":
                                        style "_console_text"
                                        at transform:
                                            yzoom (-1.0 if minimized else 1.0)
                                        font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                        size 20
                                        outlines [ (absolute(1.0), "#FFF", absolute(0), absolute(0)) ]
                                button:
                                    action ToggleVariable("persistent.console_maximized")
                                    padding (16, 16)
                                    xsize 42
                                    ysize 42
                                    xalign 0.5
                                    yalign 0.5
                                    text ("🗗" if maximized else "🗖"):
                                        style "_console_text"
                                        at transform:
                                            yoffset 4
                                        font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                        size 20
                                button:
                                    action exit_action
                                    padding (16, 16)
                                    xsize 42
                                    ysize 42
                                    xalign 0.5
                                    yalign 0.5
                                    text "❌":
                                        style "_console_text"
                                        at transform:
                                            xoffset -5
                                        size 16

                        # putting the drag inside a button/frame so that its relavtive position is (0, 0)
                        # was having issues referring to drags[0].start_x and such
                        button:
                            padding (0, 0)
                            xpos 5
                            ypos 0
                            yfill False
                            xfill False
                            drag:
                                dragged dragged_reticle
                                clicked toggle_reticle_mode
                                drag_offscreen True                        

                                has button:
                                    background None
                                    padding (16, 16)
                                    xysize(42, 42)
                                    at transform:
                                        matrixtransform Matrix.rotate(0,0,45*reticle_alternate_on)

                                text "⌖":
                                    xalign 0.5
                                    yalign 0.5
                                    yoffset 6
                                    style "_console_text"
                                    font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                    size 36
                                    outlines [ (absolute(1.25), "#000", absolute(0), absolute(0)), (absolute(0.75), "#FFF", absolute(0), absolute(0)) ]

                        drag:
                            draggable False

                            xpos 50
                            ypos 0

                            has button:
                                # unwatch first because we don't want to fill the trace screen with dupes of this
                                action If("nopf(image_summary())" in _console.traced_expressions, Function(unwatch_thoroughly, "nopf(image_summary())"), Function(renpy.watch, "nopf(image_summary())"))
                                alternate Show("layer_picker")
                                background None
                                padding (16, 16)
                                xysize(42, 42)

                            text "🖽":
                                xalign 0.5
                                yalign 0.5
                                yoffset 4
                                prefer_emoji False
                                style "_console_text"
                                font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                size 28

                        drag:
                            draggable False
                            clicked [
                                ToggleVariable("_console.verbose"),
                                Notify("verbose errors are now {}".format("on" if not _console.verbose else "off")), # the value lags behind one update
                            ]

                            xpos 100
                            ypos 0

                            has button:
                                background None
                                padding (16, 16)
                                xysize(42, 42)

                            text ("🗏" if _console.verbose else "🗉"):
                                xalign 0.5
                                yalign 0.5
                                yoffset 4
                                prefer_emoji False
                                style "_console_text"
                                font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                size 28
                                outlines [ (absolute(0.75), "#FFF", absolute(0), absolute(0)) ]

                        drag:
                            draggable False
                            clicked [
                                # add reshowing/hiding autocomplete panel
                                ToggleVariable("_console.autocomplete_on"),
                                Function(update_autocomplete_list_position_and_text),
                                Notify("tab completion is now {}".format("on" if not _console.autocomplete_on else "off")), # the value lags behind one update
                            ]

                            xpos 150
                            ypos 0

                            has button
                            background None
                            padding (16, 16)
                            xysize(42, 42)

                            text "💡":
                                at transform:
                                    alpha (1.0 if _console.autocomplete_on else 0.4)
                                    matrixcolor ColorizeMatrix("#FFF", "#FFF")
                                xalign 0.5
                                yalign 0.5
                                yoffset 2
                                xoffset -2
                                prefer_emoji False
                                style "_console_text"
                                font "code/utilities/console/fonts/NotoSansSymbols-Regular.ttf"
                                size 24

                        $ clear_function = config.console_commands.get("clear", None)

                        if not minimized:
                            drag:
                                draggable False
                                clicked [
                                    Function(clear_function, renpy.parser.Lexer([])),
                                ]

                                xpos 200
                                ypos 0

                                has button:
                                    background None
                                    padding (16, 16)
                                    xysize(42, 42)

                                text "⎚":
                                    xalign 0.5
                                    yalign 0.5
                                    yoffset -4
                                    prefer_emoji False
                                    style "_console_text"
                                    font "code/utilities/console/fonts/NotoSansSymbols-Regular.ttf"
                                    size 28


                    fixed as history_fixed:
                        fit_first True
                        if minimized:
                            vpgrid:
                                id "history_viewport" # need a dummy placeholder for this when vpgrid is hidden
                                cols 1
                        else:
                            vpgrid as history_vpgrid:

                                id "history_viewport"
                                cols 1

                                at transform:
                                    yzoom -1.0 # because viewport scrolling is weird

                                yalign 1.0
                                xfill True
                                yfill True

                                mousewheel True
                                scrollbars "vertical"
                                yinitial 0.0
                                yadjustment history_scroll_adjustment

                                vscrollbar_thumb "#50297799"
                                vscrollbar_hover_thumb "#502977cc"
                                vscrollbar_base_bar "#17062866"
                                vscrollbar_bar_vertical True
                                vscrollbar_bar_invert True


                                # limit display to prevent horrendous lag

                                for i, he in enumerate(history[-min(history_limit, len(history)):]):
                                    # each individual item
                                    python:
                                        command_lines = None if he.command is None else "{{".join(he.command.split("{"))
                                        result_lines = None if he.result is None or he.is_error else "{{".join(he.result.split("{"))
                                        error_lines = None if he.result is None or not he.is_error else "{{".join(he.result.split("{"))
                                        history_width = absolute((persistent.console_bounds[2] if not maximized else config.screen_width)-30)
                                    
                                        if command_lines is not None:
                                            style["current_style"] = Style("_console_command_text", properties={"size":style["_console_command_text"].size + persistent.text_size_adjustment})
                                            broken_lines = get_lines_from_text_displayable(
                                                Text(command_lines, substitute=False, style="current_style"),
                                                width=history_width
                                            )
                                            for broken_line in broken_lines:
                                                if broken_line.strip() != "":
                                                    lines_to_print.append((broken_line, "command", command_lines))

                                        if result_lines is not None:
                                            # Style("_console_command_text", properties={"size":50}, name="current_style").inspect()
                                            # Style("_console_command_text", properties={"size":500}, name=["current_style"]).inspect()
                                            style["current_style"] = Style("_console_result_text", properties={"size":style["_console_result_text"].size + persistent.text_size_adjustment})
                                            
                                            broken_lines = get_lines_from_text_displayable(
                                                Text(result_lines, substitute=False, style="current_style"),
                                                width=history_width
                                            )
                                            for broken_line in broken_lines:
                                                if broken_line.strip() != "":
                                                    lines_to_print.append((broken_line, "result", "{}{}".format(command_lines + "\n\n" if command_lines is not None else "", result_lines)))

                                        if error_lines is not None:
                                            # Style("_console_command_text", properties={"size":style["_console_command_text"].size + persistent.text_size_adjustment}, name="current_style")
                                            style["current_style"] = Style("_console_error_text", properties={"size":style["_console_error_text"].size + persistent.text_size_adjustment})
                                            broken_lines = get_lines_from_text_displayable(
                                                Text(error_lines, substitute=False, style="current_style"),
                                                width=history_width
                                            )
                                            for broken_line in broken_lines:
                                                if broken_line.strip() != "":
                                                    lines_to_print.append((broken_line, "error", "{}{}".format(command_lines + "\n\n" if command_lines is not None else "", error_lines)))

                                        lines_to_print.append(("", "space", ""))
                                


                                #### no partitioning. seems to work just as fast

                                for line, kind, clipboard_text in lines_to_print[-1:-history_limit:-1]:
                                    python:
                                        line_style = "_console_{}_text".format(kind)
                                        copy_message = "copied {}".format(
                                            "command" if kind == "command"
                                            else "command and result"
                                        )
                                    fixed:
                                        ysize line_height
                                        at transform:
                                            yzoom -1.0 # because viewport scrolling is weird
                                        if kind == "space":
                                            null
                                        else:
                                            button:
                                                action [
                                                    CopyToClipboard("{".join(clipboard_text.split("{{"))),
                                                    Notify(copy_message)
                                                ]
                                                ysize line_height
                                                xfill True
                                                background None
                                                # hover_background "#0003" # slows things down when enabled
                                                padding (4, 0)

                                                text "[line!q]" style line_style layout "nobreak":
                                                    size absolute(getattr(style, line_style).size + text_size_adjustment)

                                #### partitioning strategy

                                # # ["5 + 7", "12", "8-3", "5", "b", "Bob"]
                                # $ lines_to_print.reverse()
                                # # ["Bob", "b", "5", "8-3", "12", "5 + 7"]
                                # $ partitioned_lines = [lines_to_print[i:i + lines_per_row] for i in range(0, len(lines_to_print), lines_per_row)]
                                # # $ partitioned_lines = [lines_to_print[-i-1:-i-1-lines_per_row:-1] for i in range(0, len(lines_to_print), lines_per_row)]
                                # # [["Bob", "b", "5", "8-3", "12"], ["5 + 7"]]
                                # # $ partitioned_lines.reverse()
                                # # [["5 + 7"], ["Bob", "b", "5", "8-3", "12"]]

                                # for row in partitioned_lines[0:int(history_limit/lines_per_row)]:
                                #     # $ row.reverse()
                                #     # [["12", "8-3", "5", "b", "Bob"]]
                                #     vbox:
                                #         at transform:
                                #             yzoom -1.0
                                #         frame:
                                #             background None
                                #             padding (0,0)
                                #             ysize lines_per_row * line_height
                                #             vbox:
                                #                 yalign 1.0
                                #                 for line, kind, clipboard_text in row[::-1]:
                                #                     python:
                                #                         line_style = "_console_{}_text".format(kind)
                                #                         copy_message = "copied {}".format(
                                #                             "command" if kind == "command"
                                #                             else "command and result"
                                #                         )
                                #                     button:
                                #                         action [
                                #                             CopyToClipboard(clipboard_text),
                                #                             Notify(copy_message)
                                #                         ]
                                #                         ysize line_height
                                #                         xfill True
                                #                         background None
                                #                         hover_background "#0003"
                                #                         padding (0, 0)
                                #                         text "[line!q]" style line_style

                                # # ["5 + 7", "12", "8-3", "5", "b", "Bob"]
                                # $ lines_to_print.reverse()
                                # # ["Bob", "b", "5", "8-3", "12", "5 + 7"]
                                # $ partitioned_lines = [lines_to_print[i:i + lines_per_row] for i in range(0, len(lines_to_print), lines_per_row)]
                                # # $ partitioned_lines = [lines_to_print[-i-1:-i-1-lines_per_row:-1] for i in range(0, len(lines_to_print), lines_per_row)]
                                # # [["Bob", "b", "5", "8-3", "12"], ["5 + 7"]]
                                # # $ partitioned_lines.reverse()
                                # # [["5 + 7"], ["Bob", "b", "5", "8-3", "12"]]

                    $ autocomplete_on = _console.autocomplete_on

                    if _console.autocomplete_on:
                        fixed as console_autocomplete_frame: # my dream is to make this whole thing disappear when the autocomplete text is empty, but alas, that requires restart_interaction(), and I ain't living that life
                            yalign 1.0
                            ysize 0
                            frame:
                                background None
                                yalign 1.0
                                padding (5, 5)
                                frame:
                                    background "#213C"
                                    yalign 1.0
                                    padding (-1, -1) # this manages to get rid of the weird border artefact
                                    input as console_autocomplete_input:
                                        yalign 1.0
                                        style "_console_input_text"
                                        caret Null()


                    fixed as input_fixed:
                        yalign 1.0
                        ysize 2*absolute(style._console_input_text.size + text_size_adjustment)

                        frame:
                            yalign 1.0
                            background "#2136"
                            padding (0, 0)
                            has hbox
                            yalign 1.0
                            button:
                                action Function(console_watch_current_input)
                                background "#213C"
                                xalign 0.5
                                yalign 1.0
                                xysize(2*absolute(style._console_input_text.size + text_size_adjustment), 2*absolute(style._console_input_text.size + text_size_adjustment))
                                padding (0,0)
                                text "👁":
                                    yoffset 4
                                    xoffset 2
                                    xalign 0.5
                                    yalign 0.5
                                    color "#FFF"
                                    font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                    prefer_emoji False
                                    size absolute((style._console_input_text.size + text_size_adjustment))

                            frame as console_input_frame:
                                style "_console_input"
                                padding (10, 5)
                                yalign 1.0
                                yminimum 2*absolute(style._console_input_text.size + text_size_adjustment)
                                input as console_input:
                                    default default
                                    style "_console_input_text"

                                    changed handle_input_change

                                    exclude ""
                                    copypaste True
                                    multiline True
                                    caret_blink False
                                    caret Fixed(Solid("#fff", xsize=2, yoffset=1), xsize=0)
                                    size absolute(style._console_input_text.size + text_size_adjustment)

                        button:
                            padding (0, 0)
                            xalign 1.0
                            yalign 1.0
                            ysize 0
                            yoffset -32
                            xoffset 4

                            drag:
                                dragged dragged_console_resizer
                                drag_offscreen ((-1000000,36,1000000,36) if minimized else True)                       

                                has button:
                                    background None
                                    xysize(36, 36)

                                text "◿":
                                    xalign 0.5
                                    yalign 0.5
                                    xoffset -4
                                    style "_console_text"
                                    color "#FFFFFF"
                                    font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                    prefer_emoji False
                                    size 36
                                    outlines [ (absolute(0.75), "#FFF", absolute(0), absolute(0)) ]

                                text "◿":
                                    xalign 0.5
                                    yalign 0.5
                                    xoffset 2
                                    yoffset 3
                                    style "_console_text"
                                    color "#FFFFFF"
                                    font "code/utilities/console/fonts/NotoSansSymbols2-Regular.ttf"
                                    prefer_emoji False
                                    size 18
                                    outlines [ (absolute(0.5), "#FFF", absolute(0), absolute(0)) ]

    # key "ctrl_K_TAB" action _TouchKeyboardTextInput('  ')
    key "K_TAB" action Function(console_handle_tab_keypress)

    # watch whatever's in the input box
    key "ctrl_K_RETURN" action Function(console_watch_current_input)

    key "noshift_K_RETURN" action [
        Function(console_handle_return_keypress),
        # Function(console_process_input, _console.console),
        # Function(_console.console.show_stdio), # grabs any stdio output in the buffer
        # Scroll("history_viewport", "vertical increase", -100000000.0, 0.0),
    ]

    key "console_exit" action Function(console_handle_escape, exit_action)
    key "K_PAGEDOWN" action Function(console_recall_line, _console.console, +100000000)

    key "anyrepeat_K_UP" action Function(update_autocomplete_list_position_and_text, offset_by=-1, _update_screens=False)
    key "anyrepeat_K_DOWN" action Function(update_autocomplete_list_position_and_text, offset_by=1, _update_screens=False)

    # key "console_older" action Function(console_recall_line, _console.console, -1)
    # key "console_newer" action Function(console_recall_line, _console.console, +1)

init python:
    # allows shift-arrowkeys to move around the multiline input
    config.keymap["console_older"] = [ 'noshift_anyrepeat_K_UP', 'noshift_anyrepeat_KP_UP' ],
    config.keymap["console_newer"] = [ 'noshift_anyrepeat_K_DOWN', 'noshift_anyrepeat_KP_DOWN' ]
    # prevent right-click from exiting. not sure why that's even an option frankly
    config.keymap["console_exit"] = [ 'K_ESCAPE', 'K_MENU', 'K_PAUSE' ],# 'mouseup_3' ],

    def toggle_image_summary_layer(layer):
        # initialize if layer count is off
        if len(persistent.console_image_summary_layers) != len(renpy.display.scenelists.ordered_layers):
            persistent.console_image_summary_layers = dict(zip(renpy.display.scenelists.ordered_layers, [True for i in range(0, len(renpy.display.scenelists.ordered_layers))]))

        persistent.console_image_summary_layers.update({layer: not persistent.console_image_summary_layers[layer]})

screen layer_picker():

    tag layer_picker
    layer config.interface_layer
    zorder 2500
    modal True

    key "K_ESCAPE" action Hide() capture True
    key "K_TAB" action Hide() capture True
    key "dismiss" action Hide() capture True
    key "game_menu" action Hide() capture True

    default top_left_corner = renpy.get_mouse_pos()

    nearrect:
        rect (top_left_corner[0], top_left_corner[1], 1, 1)
        frame:
            padding (0, 0)
            background "#0009"
            vbox:
                align (0.5, 0.5)
                spacing 2
                for layer_name in persistent.console_image_summary_layers:
                    button:
                        xfill False
                        background None
                        hbox:
                            align (0.0, 0.5)
                            spacing 10

                            text layer_name:
                                style "_console_text"
                                align (0.0, 0.5)

                            button:
                                xsize 50
                                ysize 30
                                text ("✔️" if persistent.console_image_summary_layers[layer_name] else " "):
                                    at transform:
                                        matrixcolor ColorizeMatrix("#FFF", "#FFF")
                                    # style "_console_text" # errors out? ??
                                    size style._console_text.size
                                    align (0.0, 0.5)

                        action [Function(toggle_image_summary_layer, layer_name)]


# invisible button that eats console show commands
# (to prevent jumping to the _console label)

screen show_console_button():
    layer config.interface_layer

    zorder 10000

    $ button_action = Show("_console")

    if renpy.get_screen("_console") is None:
        key "shift_K_O" action NullAction() capture True
        key "console" action button_action capture True

# init python:
#     config.overlay_screens.append("show_console_button")

# the watch screen

init python:
    from pprint import pprint
    from pprint import pformat

screen _trace_screen():

    layer "notify"
    zorder 1501

    if _console.traced_expressions:

        viewport:
            mousewheel True
            xmaximum 0.33
            frame style "_console_trace":
                background None
                pos (0, 0)
                anchor (0, 0)
                padding (20, 0, 0, 20)

                vbox:
                    spacing 20
                    python:
                        expressions = []
                        for item in _console.traced_expressions:
                            if item not in expressions:
                                expressions.append(item)
                    for expr in expressions:
                        python:
                            # if persistent._console_traced_short:
                            #     repr_func = _console.traced_aRepr.repr
                            # else:
                            #     repr_func = repr

                            nopf = False
                            new_expr = expr

                            if new_expr.startswith("nopf"):
                                new_expr = new_expr[5:-1]
                                nopf = True

                            try:
                                if nopf:
                                    value = eval(new_expr)
                                else:
                                    value = pformat(eval(new_expr))
                            except Exception:
                                value = "eval failed"
                            # del repr_func

                        button:
                            background "#0009"
                            vbox:
                                text "[new_expr!q]: " style "_console_trace_var"
                                text "[value!q]" style "_console_trace_value"
                            action Function(unwatch_thoroughly, expr)


### The keybind screen actually intercepts the show_console event, so this never actually get called

# The label that is called by _console.enter to actually run the console.
# This can be called in the current context (for normal Ren'Py code) or
# in a new context (in menus).
label _my_console:

    python:
        _console.console_restore_from_persistent(_console.console)
        # _console.console.show_stdio()
        renpy.show_screen("_console")

    return

label _my_console_return:

    return







init python:
    import datetime

    def sayer(character_name):
        """Used to dynamically assign a speaker to say something. like sayer(character_name_variable) 'Thing to say.'"""
        return getattr(store, character_name.lower())

    def snapshot_character(character, file_name=None, layer="master"):
        image_tag = character.image_tag
        if file_name is None:
            file_name = "{}_snapshot_{}.png".format(character.name, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        d = renpy.get_screen(image_tag, layer)
        renpy.render_to_file(d, file_name)
        return file_name

    def snapshot_tag(image_tag, file_name=None, layer="master"):
        if file_name is None:
            file_name = "{}_snapshot_{}.png".format(image_tag, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        d = renpy.get_screen(image_tag, layer)
        renpy.render_to_file(d, file_name)
        return file_name    

    def draw_from(deck, stock=[]):
        """
        Treats a list like a deck of cards.
        When empty, assigns the list variable to the default stock and shuffles it.
        Pops one element per draw.

        "Draw from deck, replenish with stock."

        Pattern is generally:
        default deck = []
        default stock = ["option 1", "option 2", "option 3"]
        draw_from(deck, stock)
        """

        # shuffle options into the deck
        if len(deck) < 1:
            deck.extend(stock.copy())
            # using renpy.random so this is compatible with rollbacks and such
            renpy.random.shuffle(deck)
        # draw an option
        return deck.pop()

    # gets a placement object from an image tag, presuming it to be on the master layer
    # a placement object has the following properties
    # xpos, ypos, xanchor, yanchor, xoffset, yoffset, and subpixel
    # because of my use of yoffset in the definition of the image, trying to copy every item in this list duplicates the yoffset for some reason
    # fun fact, `show image_tag` makes screens, apparently
    def get_placement_by_tag(tag, layer="master"):
        return renpy.get_placement(renpy.get_screen(tag, layer=layer))

    def get_tag(tag, layer="master"):
        return renpy.get_screen(tag, layer=layer)

    def get_all_named_transform_names(use_store=store):
        return [ var_name for var_name in vars(store) if type(getattr(store, var_name)) == type(reset) ] # reset is a transform

    def get_all_named_transforms(use_store=store):
        # this returns a dict of transform variable names -> transform objects
        return { transform_name: (use_store, getattr(use_store, transform_name)) for transform_name in get_all_named_transform_names() if hasattr(use_store, transform_name) }

    def get_references_to_transform(transform_object, use_store=store):
        all_named_transforms = get_all_named_transforms(use_store)
        return [ name for name in all_named_transforms if transform_object == all_named_transforms[name][1] ]

    def get_transforms_on_tag(tag, layer='master', use_store=store):
        tag_transform_object_locs = [ at.atl.loc for at in get_at_list_recursively(tag, layer) if hasattr(at, "atl") ]
        if tag_transform_object_locs is None:
            return None
        all_named_transforms = get_all_named_transforms(use_store)
        return [ transform_name for transform_name in all_named_transforms if all_named_transforms[transform_name][1].atl.loc in tag_transform_object_locs ]

    def get_at_list_recursively(tag, layer='master'):
        transforms = renpy.get_at_list(tag, layer)
        transform = renpy.get_screen(tag, layer)
        while hasattr(transform, "child"):
            transform = getattr(transform, "child")
            transforms.append(transform)

        return transforms


    def get_all_stores():
        return [ getattr(store, var_name) for var_name in vars(store) if type(getattr(store, var_name)) == type(store) ]
