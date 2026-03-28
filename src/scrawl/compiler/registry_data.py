"""Data-driven block definitions for full Scratch 3.0 coverage.

~129 blocks across 10 categories (Events, Motion, Looks, Sound, Control,
Data, Operators, Sensing, Pen, Music).
Adding a new block = adding one BlockDef entry here.
"""

from __future__ import annotations

from scrawl.compiler.registry import (
    BlockDef,
    BlockShape,
    FieldSpec,
    InputSpec,
    MenuSpec,
)

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

EVENT_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="when flag clicked",
        opcode="event_whenflagclicked",
        shape=BlockShape.HAT,
        has_next=True,
    ),
    BlockDef(
        pattern="when I receive [BROADCAST_OPTION v]",
        opcode="event_whenbroadcastreceived",
        shape=BlockShape.HAT,
        fields=[FieldSpec("BROADCAST_OPTION", "broadcast")],
        has_next=True,
    ),
    BlockDef(
        pattern="when this sprite clicked",
        opcode="event_whenthisspriteclicked",
        shape=BlockShape.HAT,
        has_next=True,
    ),
    BlockDef(
        pattern="broadcast [BROADCAST_INPUT v]",
        opcode="event_broadcast",
        shape=BlockShape.STACK,
        inputs=[InputSpec("BROADCAST_INPUT", "broadcast", "", 11)],
    ),
    BlockDef(
        pattern="broadcast [BROADCAST_INPUT v] and wait",
        opcode="event_broadcastandwait",
        shape=BlockShape.STACK,
        inputs=[InputSpec("BROADCAST_INPUT", "broadcast", "", 11)],
    ),
    # Phase 2 additions
    BlockDef(
        pattern="when [KEY_OPTION v] key pressed",
        opcode="event_whenkeypressed",
        shape=BlockShape.HAT,
        fields=[FieldSpec("KEY_OPTION", "key_option")],
        has_next=True,
    ),
    BlockDef(
        pattern="when backdrop switches to [BACKDROP v]",
        opcode="event_whenbackdropswitchesto",
        shape=BlockShape.HAT,
        fields=[FieldSpec("BACKDROP", "backdrop")],
        has_next=True,
    ),
    BlockDef(
        pattern="when [WHENGREATERTHANMENU v] > (VALUE)",
        opcode="event_whengreaterthan",
        shape=BlockShape.HAT,
        inputs=[InputSpec("VALUE", "number", "10", 4)],
        fields=[FieldSpec("WHENGREATERTHANMENU", "greater_than_menu")],
        has_next=True,
    ),
]

# ---------------------------------------------------------------------------
# Motion
# ---------------------------------------------------------------------------

MOTION_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="move (STEPS) steps",
        opcode="motion_movesteps",
        shape=BlockShape.STACK,
        inputs=[InputSpec("STEPS", "number", "10", 4)],
    ),
    BlockDef(
        pattern="turn right (DEGREES) degrees",
        opcode="motion_turnright",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DEGREES", "number", "15", 4)],
    ),
    BlockDef(
        pattern="turn left (DEGREES) degrees",
        opcode="motion_turnleft",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DEGREES", "number", "15", 4)],
    ),
    BlockDef(
        pattern="go to x: (X) y: (Y)",
        opcode="motion_gotoxy",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("X", "number", "0", 4),
            InputSpec("Y", "number", "0", 4),
        ],
    ),
    BlockDef(
        pattern="set x to (X)",
        opcode="motion_setx",
        shape=BlockShape.STACK,
        inputs=[InputSpec("X", "number", "0", 4)],
    ),
    BlockDef(
        pattern="set y to (Y)",
        opcode="motion_sety",
        shape=BlockShape.STACK,
        inputs=[InputSpec("Y", "number", "0", 4)],
    ),
    BlockDef(
        pattern="change x by (DX)",
        opcode="motion_changexby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DX", "number", "10", 4)],
    ),
    BlockDef(
        pattern="change y by (DY)",
        opcode="motion_changeyby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DY", "number", "10", 4)],
    ),
    BlockDef(
        pattern="point in direction (DIRECTION)",
        opcode="motion_pointindirection",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DIRECTION", "angle", "90", 8)],
    ),
    BlockDef(
        pattern="glide (SECS) secs to x: (X) y: (Y)",
        opcode="motion_glidesecstoxy",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("SECS", "number", "1", 4),
            InputSpec("X", "number", "0", 4),
            InputSpec("Y", "number", "0", 4),
        ],
    ),
    # Reporters
    BlockDef(
        pattern="x position",
        opcode="motion_xposition",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="y position",
        opcode="motion_yposition",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="direction",
        opcode="motion_direction",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="go to [TO v]",
        opcode="motion_goto",
        shape=BlockShape.STACK,
        menu=MenuSpec("motion_goto_menu", "TO", "TO"),
    ),
    BlockDef(
        pattern="glide (SECS) secs to [TO v]",
        opcode="motion_glideto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("SECS", "number", "1", 4)],
        menu=MenuSpec("motion_glideto_menu", "TO", "TO"),
    ),
    BlockDef(
        pattern="point towards [TOWARDS v]",
        opcode="motion_pointtowards",
        shape=BlockShape.STACK,
        menu=MenuSpec("motion_pointtowards_menu", "TOWARDS", "TOWARDS"),
    ),
    BlockDef(
        pattern="if on edge, bounce",
        opcode="motion_ifonedgebounce",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="set rotation style [STYLE v]",
        opcode="motion_setrotationstyle",
        shape=BlockShape.STACK,
        fields=[FieldSpec("STYLE", "rotation_style")],
    ),
]

# ---------------------------------------------------------------------------
# Looks
# ---------------------------------------------------------------------------

LOOKS_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="say [MESSAGE] for (SECS) seconds",
        opcode="looks_sayforsecs",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("MESSAGE", "string", "Hello!", 10),
            InputSpec("SECS", "number", "2", 4),
        ],
    ),
    BlockDef(
        pattern="say [MESSAGE]",
        opcode="looks_say",
        shape=BlockShape.STACK,
        inputs=[InputSpec("MESSAGE", "string", "Hello!", 10)],
    ),
    BlockDef(
        pattern="think [MESSAGE] for (SECS) seconds",
        opcode="looks_thinkforsecs",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("MESSAGE", "string", "Hmm...", 10),
            InputSpec("SECS", "number", "2", 4),
        ],
    ),
    BlockDef(
        pattern="think [MESSAGE]",
        opcode="looks_think",
        shape=BlockShape.STACK,
        inputs=[InputSpec("MESSAGE", "string", "Hmm...", 10)],
    ),
    BlockDef(
        pattern="show",
        opcode="looks_show",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="hide",
        opcode="looks_hide",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="switch costume to [COSTUME v]",
        opcode="looks_switchcostumeto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("COSTUME", "string", "", 10)],
        menu=MenuSpec("looks_costume", "COSTUME", "COSTUME"),
    ),
    BlockDef(
        pattern="set size to (SIZE) %",
        opcode="looks_setsizeto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("SIZE", "number", "100", 4)],
    ),
    # Reporters
    BlockDef(
        pattern="costume number",
        opcode="looks_costumenumbername",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("NUMBER_NAME", "costume_number_name", default_value="number")],
        has_next=False,
    ),
    BlockDef(
        pattern="costume name",
        opcode="looks_costumenumbername",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("NUMBER_NAME", "costume_number_name", default_value="name")],
        has_next=False,
    ),
    BlockDef(
        pattern="size",
        opcode="looks_size",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="change [EFFECT v] effect by (CHANGE)",
        opcode="looks_changeeffectby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("CHANGE", "number", "25", 4)],
        fields=[FieldSpec("EFFECT", "looks_effect")],
    ),
    BlockDef(
        pattern="set [EFFECT v] effect to (VALUE)",
        opcode="looks_seteffectto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "0", 4)],
        fields=[FieldSpec("EFFECT", "looks_effect")],
    ),
    BlockDef(
        pattern="clear graphic effects",
        opcode="looks_cleargraphiceffects",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="change size by (CHANGE)",
        opcode="looks_changesizeby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("CHANGE", "number", "10", 4)],
    ),
    BlockDef(
        pattern="next costume",
        opcode="looks_nextcostume",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="switch backdrop to [BACKDROP v]",
        opcode="looks_switchbackdropto",
        shape=BlockShape.STACK,
        menu=MenuSpec("looks_backdrops", "BACKDROP", "BACKDROP"),
    ),
    BlockDef(
        pattern="next backdrop",
        opcode="looks_nextbackdrop",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="go to [FRONT_BACK v] layer",
        opcode="looks_gotofrontback",
        shape=BlockShape.STACK,
        fields=[FieldSpec("FRONT_BACK", "front_back")],
    ),
    BlockDef(
        pattern="go [FORWARD_BACKWARD v] (NUM) layers",
        opcode="looks_goforwardbackwardlayers",
        shape=BlockShape.STACK,
        inputs=[InputSpec("NUM", "number", "1", 4)],
        fields=[FieldSpec("FORWARD_BACKWARD", "forward_backward")],
    ),
    BlockDef(
        pattern="backdrop number",
        opcode="looks_backdropnumbername",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("NUMBER_NAME", "backdrop_number_name", default_value="number")],
        has_next=False,
    ),
    BlockDef(
        pattern="backdrop name",
        opcode="looks_backdropnumbername",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("NUMBER_NAME", "backdrop_number_name", default_value="name")],
        has_next=False,
    ),
]

# ---------------------------------------------------------------------------
# Sound
# ---------------------------------------------------------------------------

SOUND_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="play sound [SOUND_MENU v] until done",
        opcode="sound_playuntildone",
        shape=BlockShape.STACK,
        menu=MenuSpec("sound_sounds_menu", "SOUND_MENU", "SOUND_MENU"),
    ),
    BlockDef(
        pattern="start sound [SOUND_MENU v]",
        opcode="sound_play",
        shape=BlockShape.STACK,
        menu=MenuSpec("sound_sounds_menu", "SOUND_MENU", "SOUND_MENU"),
    ),
    BlockDef(
        pattern="stop all sounds",
        opcode="sound_stopallsounds",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="change [EFFECT v] sound effect by (VALUE)",
        opcode="sound_changeeffectby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "10", 4)],
        fields=[FieldSpec("EFFECT", "sound_effect")],
    ),
    BlockDef(
        pattern="set [EFFECT v] sound effect to (VALUE)",
        opcode="sound_seteffectto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "100", 4)],
        fields=[FieldSpec("EFFECT", "sound_effect")],
    ),
    BlockDef(
        pattern="clear sound effects",
        opcode="sound_cleareffects",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="set volume to (VOLUME) %",
        opcode="sound_setvolumeto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VOLUME", "number", "100", 4)],
    ),
    BlockDef(
        pattern="change volume by (VOLUME)",
        opcode="sound_changevolumeby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VOLUME", "number", "-10", 4)],
    ),
    BlockDef(
        pattern="volume",
        opcode="sound_volume",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
]

# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------

CONTROL_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="forever",
        opcode="control_forever",
        shape=BlockShape.C_BLOCK,
        substacks=1,
        has_next=False,  # forever is a cap-C block
    ),
    BlockDef(
        pattern="if <CONDITION> then",
        opcode="control_if",
        shape=BlockShape.C_BLOCK,
        inputs=[InputSpec("CONDITION", "boolean", None, None)],
        substacks=1,
    ),
    # Note: control_if_else is handled by the parser upgrading control_if
    # when it encounters "else". No separate pattern needed.
    BlockDef(
        pattern="repeat (TIMES)",
        opcode="control_repeat",
        shape=BlockShape.C_BLOCK,
        inputs=[InputSpec("TIMES", "positive_integer", "10", 6)],
        substacks=1,
    ),
    BlockDef(
        pattern="repeat until <CONDITION>",
        opcode="control_repeat_until",
        shape=BlockShape.C_BLOCK,
        inputs=[InputSpec("CONDITION", "boolean", None, None)],
        substacks=1,
    ),
    BlockDef(
        pattern="wait (DURATION) seconds",
        opcode="control_wait",
        shape=BlockShape.STACK,
        inputs=[InputSpec("DURATION", "positive_number", "1", 5)],
    ),
    BlockDef(
        pattern="stop [STOP_OPTION v]",
        opcode="control_stop",
        shape=BlockShape.CAP,
        fields=[FieldSpec("STOP_OPTION", "stop_option")],
        has_next=False,
    ),
    BlockDef(
        pattern="create clone of [CLONE_OPTION v]",
        opcode="control_create_clone_of",
        shape=BlockShape.STACK,
        inputs=[InputSpec("CLONE_OPTION", "string", "", 10)],
        menu=MenuSpec(
            "control_create_clone_of_menu",
            "CLONE_OPTION",
            "CLONE_OPTION",
        ),
    ),
    BlockDef(
        pattern="delete this clone",
        opcode="control_delete_this_clone",
        shape=BlockShape.CAP,
        has_next=False,
    ),
    BlockDef(
        pattern="when I start as a clone",
        opcode="control_start_as_clone",
        shape=BlockShape.HAT,
        has_next=True,
    ),
    # Phase 2 addition
    BlockDef(
        pattern="wait until <CONDITION>",
        opcode="control_wait_until",
        shape=BlockShape.STACK,
        inputs=[InputSpec("CONDITION", "boolean", None, None)],
    ),
]

# ---------------------------------------------------------------------------
# Data (variables and lists)
# ---------------------------------------------------------------------------

DATA_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="set [VARIABLE v] to (VALUE)",
        opcode="data_setvariableto",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "string", "0", 10)],
        fields=[FieldSpec("VARIABLE", "variable")],
    ),
    BlockDef(
        pattern="change [VARIABLE v] by (VALUE)",
        opcode="data_changevariableby",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "1", 4)],
        fields=[FieldSpec("VARIABLE", "variable")],
    ),
    BlockDef(
        pattern="add [ITEM] to [LIST v]",
        opcode="data_addtolist",
        shape=BlockShape.STACK,
        inputs=[InputSpec("ITEM", "string", "thing", 10)],
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="delete all of [LIST v]",
        opcode="data_deletealloflist",
        shape=BlockShape.STACK,
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="delete (INDEX) of [LIST v]",
        opcode="data_deleteoflist",
        shape=BlockShape.STACK,
        inputs=[InputSpec("INDEX", "positive_integer", "1", 7)],
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="insert [ITEM] at (INDEX) of [LIST v]",
        opcode="data_insertatlist",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("ITEM", "string", "thing", 10),
            InputSpec("INDEX", "positive_integer", "1", 7),
        ],
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="replace item (INDEX) of [LIST v] with [ITEM]",
        opcode="data_replaceitemoflist",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("INDEX", "positive_integer", "1", 7),
            InputSpec("ITEM", "string", "thing", 10),
        ],
        fields=[FieldSpec("LIST", "list")],
    ),
    # Reporters
    BlockDef(
        pattern="item (INDEX) of [LIST v]",
        opcode="data_itemoflist",
        shape=BlockShape.REPORTER,
        inputs=[InputSpec("INDEX", "positive_integer", "1", 7)],
        fields=[FieldSpec("LIST", "list")],
        has_next=False,
    ),
    BlockDef(
        pattern="item # of [ITEM] in [LIST v]",
        opcode="data_itemnumoflist",
        shape=BlockShape.REPORTER,
        inputs=[InputSpec("ITEM", "string", "thing", 10)],
        fields=[FieldSpec("LIST", "list")],
        has_next=False,
    ),
    BlockDef(
        pattern="length of list [LIST v]",
        opcode="data_lengthoflist",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("LIST", "list")],
        has_next=False,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="show variable [VARIABLE v]",
        opcode="data_showvariable",
        shape=BlockShape.STACK,
        fields=[FieldSpec("VARIABLE", "variable")],
    ),
    BlockDef(
        pattern="hide variable [VARIABLE v]",
        opcode="data_hidevariable",
        shape=BlockShape.STACK,
        fields=[FieldSpec("VARIABLE", "variable")],
    ),
    BlockDef(
        pattern="show list [LIST v]",
        opcode="data_showlist",
        shape=BlockShape.STACK,
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="hide list [LIST v]",
        opcode="data_hidelist",
        shape=BlockShape.STACK,
        fields=[FieldSpec("LIST", "list")],
    ),
    BlockDef(
        pattern="[LIST v] contains [ITEM]?",
        opcode="data_listcontainsitem",
        shape=BlockShape.BOOLEAN,
        inputs=[InputSpec("ITEM", "string", "thing", 10)],
        fields=[FieldSpec("LIST", "list")],
        has_next=False,
    ),
]

# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

OPERATOR_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="(NUM1) + (NUM2)",
        opcode="operator_add",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("NUM1", "number", "", 4),
            InputSpec("NUM2", "number", "", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(NUM1) - (NUM2)",
        opcode="operator_subtract",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("NUM1", "number", "", 4),
            InputSpec("NUM2", "number", "", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(NUM1) * (NUM2)",
        opcode="operator_multiply",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("NUM1", "number", "", 4),
            InputSpec("NUM2", "number", "", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(NUM1) / (NUM2)",
        opcode="operator_divide",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("NUM1", "number", "", 4),
            InputSpec("NUM2", "number", "", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(OPERAND1) = (OPERAND2)",
        opcode="operator_equals",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("OPERAND1", "string", "", 10),
            InputSpec("OPERAND2", "string", "", 10),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(OPERAND1) > (OPERAND2)",
        opcode="operator_gt",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("OPERAND1", "string", "", 10),
            InputSpec("OPERAND2", "string", "", 10),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="(OPERAND1) < (OPERAND2)",
        opcode="operator_lt",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("OPERAND1", "string", "", 10),
            InputSpec("OPERAND2", "string", "", 10),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="<OPERAND1> and <OPERAND2>",
        opcode="operator_and",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("OPERAND1", "boolean", None, None),
            InputSpec("OPERAND2", "boolean", None, None),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="<OPERAND1> or <OPERAND2>",
        opcode="operator_or",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("OPERAND1", "boolean", None, None),
            InputSpec("OPERAND2", "boolean", None, None),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="not <OPERAND>",
        opcode="operator_not",
        shape=BlockShape.BOOLEAN,
        inputs=[InputSpec("OPERAND", "boolean", None, None)],
        has_next=False,
    ),
    BlockDef(
        pattern="pick random (FROM) to (TO)",
        opcode="operator_random",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("FROM", "number", "1", 4),
            InputSpec("TO", "number", "10", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="join [STRING1] [STRING2]",
        opcode="operator_join",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("STRING1", "string", "apple ", 10),
            InputSpec("STRING2", "string", "banana", 10),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="length of [STRING]",
        opcode="operator_length",
        shape=BlockShape.REPORTER,
        inputs=[InputSpec("STRING", "string", "apple", 10)],
        has_next=False,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="(NUM1) mod (NUM2)",
        opcode="operator_mod",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("NUM1", "number", "", 4),
            InputSpec("NUM2", "number", "", 4),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="round (NUM)",
        opcode="operator_round",
        shape=BlockShape.REPORTER,
        inputs=[InputSpec("NUM", "number", "", 4)],
        has_next=False,
    ),
    BlockDef(
        pattern="[OPERATOR v] of (NUM)",
        opcode="operator_mathop",
        shape=BlockShape.REPORTER,
        inputs=[InputSpec("NUM", "number", "", 4)],
        fields=[FieldSpec("OPERATOR", "mathop")],
        has_next=False,
    ),
    BlockDef(
        pattern="[STRING1] contains [STRING2]?",
        opcode="operator_contains",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("STRING1", "string", "apple", 10),
            InputSpec("STRING2", "string", "a", 10),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="letter (LETTER) of [STRING]",
        opcode="operator_letter_of",
        shape=BlockShape.REPORTER,
        inputs=[
            InputSpec("LETTER", "positive_integer", "1", 6),
            InputSpec("STRING", "string", "apple", 10),
        ],
        has_next=False,
    ),
]

# ---------------------------------------------------------------------------
# Sensing
# ---------------------------------------------------------------------------

SENSING_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="touching [TOUCHINGOBJECTMENU v]?",
        opcode="sensing_touchingobject",
        shape=BlockShape.BOOLEAN,
        menu=MenuSpec(
            "sensing_touchingobjectmenu",
            "TOUCHINGOBJECTMENU",
            "TOUCHINGOBJECTMENU",
        ),
        has_next=False,
    ),
    BlockDef(
        pattern="mouse down?",
        opcode="sensing_mousedown",
        shape=BlockShape.BOOLEAN,
        has_next=False,
    ),
    BlockDef(
        pattern="key [KEY_OPTION v] pressed?",
        opcode="sensing_keypressed",
        shape=BlockShape.BOOLEAN,
        menu=MenuSpec(
            "sensing_keyoptions",
            "KEY_OPTION",
            "KEY_OPTION",
        ),
        has_next=False,
    ),
    BlockDef(
        pattern="mouse x",
        opcode="sensing_mousex",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="mouse y",
        opcode="sensing_mousey",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="ask [QUESTION] and wait",
        opcode="sensing_askandwait",
        shape=BlockShape.STACK,
        inputs=[InputSpec("QUESTION", "string", "What's your name?", 10)],
    ),
    BlockDef(
        pattern="answer",
        opcode="sensing_answer",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="timer",
        opcode="sensing_timer",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="reset timer",
        opcode="sensing_resettimer",
        shape=BlockShape.STACK,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="touching color (COLOR)?",
        opcode="sensing_touchingcolor",
        shape=BlockShape.BOOLEAN,
        inputs=[InputSpec("COLOR", "color", "#0000ff", 9)],
        has_next=False,
    ),
    BlockDef(
        pattern="color (COLOR) is touching (COLOR2)?",
        opcode="sensing_coloristouchingcolor",
        shape=BlockShape.BOOLEAN,
        inputs=[
            InputSpec("COLOR", "color", "#0000ff", 9),
            InputSpec("COLOR2", "color", "#00ff00", 9),
        ],
        has_next=False,
    ),
    BlockDef(
        pattern="distance to [DISTANCETOMENU v]",
        opcode="sensing_distanceto",
        shape=BlockShape.REPORTER,
        menu=MenuSpec(
            "sensing_distancetomenu",
            "DISTANCETOMENU",
            "DISTANCETOMENU",
        ),
        has_next=False,
    ),
    BlockDef(
        pattern="current [CURRENTMENU v]",
        opcode="sensing_current",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("CURRENTMENU", "date_component")],
        has_next=False,
    ),
    BlockDef(
        pattern="days since 2000",
        opcode="sensing_dayssince2000",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="username",
        opcode="sensing_username",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="loudness",
        opcode="sensing_loudness",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
    BlockDef(
        pattern="set drag mode [DRAG_MODE v]",
        opcode="sensing_setdragmode",
        shape=BlockShape.STACK,
        fields=[FieldSpec("DRAG_MODE", "drag_mode")],
    ),
    BlockDef(
        pattern="[PROPERTY v] of [OBJECT v]",
        opcode="sensing_of",
        shape=BlockShape.REPORTER,
        fields=[FieldSpec("PROPERTY", "sensing_of_property")],
        menu=MenuSpec("sensing_of_object_menu", "OBJECT", "OBJECT"),
        has_next=False,
    ),
]

# ---------------------------------------------------------------------------
# Pen extension
# ---------------------------------------------------------------------------

PEN_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="erase all",
        opcode="pen_clear",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="pen down",
        opcode="pen_penDown",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="pen up",
        opcode="pen_penUp",
        shape=BlockShape.STACK,
    ),
    BlockDef(
        pattern="set pen color to (COLOR)",
        opcode="pen_setPenColorToColor",
        shape=BlockShape.STACK,
        inputs=[InputSpec("COLOR", "color", "#0000ff", 9)],
    ),
    BlockDef(
        pattern="set pen size to (SIZE)",
        opcode="pen_setPenSizeTo",
        shape=BlockShape.STACK,
        inputs=[InputSpec("SIZE", "number", "1", 4)],
    ),
    BlockDef(
        pattern="change pen size by (SIZE)",
        opcode="pen_changePenSizeBy",
        shape=BlockShape.STACK,
        inputs=[InputSpec("SIZE", "number", "1", 4)],
    ),
    BlockDef(
        pattern="stamp",
        opcode="pen_stamp",
        shape=BlockShape.STACK,
    ),
    # Phase 2 additions
    BlockDef(
        pattern="change pen [COLOR_PARAM v] by (VALUE)",
        opcode="pen_changePenColorParamBy",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "10", 4)],
        fields=[FieldSpec("COLOR_PARAM", "pen_color_param")],
    ),
    BlockDef(
        pattern="set pen [COLOR_PARAM v] to (VALUE)",
        opcode="pen_setPenColorParamTo",
        shape=BlockShape.STACK,
        inputs=[InputSpec("VALUE", "number", "50", 4)],
        fields=[FieldSpec("COLOR_PARAM", "pen_color_param")],
    ),
]

# ---------------------------------------------------------------------------
# Music extension
# ---------------------------------------------------------------------------

MUSIC_BLOCKS: list[BlockDef] = [
    BlockDef(
        pattern="play drum [DRUM v] for (BEATS) beats",
        opcode="music_playDrumForBeats",
        shape=BlockShape.STACK,
        inputs=[InputSpec("BEATS", "number", "0.25", 4)],
        menu=MenuSpec("music_menu_DRUM", "DRUM", "DRUM"),
    ),
    BlockDef(
        pattern="play note (NOTE) for (BEATS) beats",
        opcode="music_playNoteForBeats",
        shape=BlockShape.STACK,
        inputs=[
            InputSpec("NOTE", "number", "60", 4),
            InputSpec("BEATS", "number", "0.25", 4),
        ],
    ),
    BlockDef(
        pattern="rest for (BEATS) beats",
        opcode="music_restForBeats",
        shape=BlockShape.STACK,
        inputs=[InputSpec("BEATS", "number", "0.25", 4)],
    ),
    BlockDef(
        pattern="set tempo to (TEMPO)",
        opcode="music_setTempo",
        shape=BlockShape.STACK,
        inputs=[InputSpec("TEMPO", "number", "60", 4)],
    ),
    BlockDef(
        pattern="tempo",
        opcode="music_getTempo",
        shape=BlockShape.REPORTER,
        has_next=False,
    ),
]


# ---------------------------------------------------------------------------
# All blocks combined
# ---------------------------------------------------------------------------

ALL_BLOCKS: list[BlockDef] = (
    EVENT_BLOCKS
    + MOTION_BLOCKS
    + LOOKS_BLOCKS
    + SOUND_BLOCKS
    + CONTROL_BLOCKS
    + DATA_BLOCKS
    + OPERATOR_BLOCKS
    + SENSING_BLOCKS
    + PEN_BLOCKS
    + MUSIC_BLOCKS
)
