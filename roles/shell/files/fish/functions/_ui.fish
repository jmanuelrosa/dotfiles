function _ui --description "Shared output vocabulary for dotfiles scripts: one palette, one set of glyphs"
    # The palette claude-kit uses (lib/python/dotkit/ui.py is the
    # python half of this file, kind for kind and glyph for glyph). Two rules hold the
    # whole style together:
    #
    #   status is a coloured glyph   ✓ green, ⚠ yellow, ✗ magenta, · dim, → cyan
    #   topic is an emoji            and only ever on a `title` or a `done` line
    #
    # Emoji are double-width in most terminals, so one used as a row marker knocks
    # every following column out of alignment. Keeping them on the two line kinds that
    # start at column zero is what lets a listing stay a listing.
    #
    # Colour is decided per stream, unlike a bare `set_color`: piping a command into a
    # file yields plain text, NO_COLOR wins over FORCE_COLOR, and FORCE_COLOR wins over
    # the tty check. Same order as ui.py, so both halves agree in a test harness.
    #
    #   _ui title  "🧹 Removing Claude artifacts"   bold heading, emoji supplied here
    #   _ui step   "Fetching upstream"              → an action being taken
    #   _ui ok     "Linked 'commit'"                ✓ it worked
    #   _ui warn   "3 were git-tracked"             ⚠ worth reading, not fatal
    #   _ui err    "Not a directory"                ✗ a refusal, printed to stderr
    #   _ui item   "~/dev/api/.claude"              · one entry of a list
    #   _ui note   "restore it with make run-role"  dim aside under the line above
    #   _ui done   "Removed 3 of 3"                 ✨ the closing summary
    #   _ui blank                                   an empty line
    #
    # Indent defaults to 0, or 2 for `item` and `note`; -i/--indent overrides it.
    # Three helpers compose rather than print, and one answers a question:
    #
    #   _ui color cyan          the escape sequence alone, for building a line by hand
    #   _ui paint cyan "text"   that text, wrapped and reset
    #   _ui path ~/dev/api      a path with $HOME collapsed back to ~
    #   _ui color-enabled       status 0 when this stdout wants colour
    #
    # The two colouring helpers are only ever useful inside a command substitution, and
    # fish gives one a pipe for stdout, so their own fd 1 is never the terminal however
    # the command was run: an isatty check there is false every time, which is what left
    # every `lns` arrow and every `clean_claude` marker uncoloured. They therefore state
    # intent, silenced by NO_COLOR alone, and the printing kind resolves it by stripping
    # the escapes its stream does not want, as dotkit's colors.for_stream does. A script
    # printing a row with `echo` has no printing kind to resolve it, so it asks
    # `_ui color-enabled` first, while fd 1 is still its own stdout.
    #
    # -s so that `_ui err "-x is unknown"` prints rather than parsing -x as a flag.
    argparse -s -n _ui 'i/indent=' -- $argv
    or return 1

    if test (count $argv) -eq 0
        echo "_ui: missing line kind" >&2
        return 1
    end

    set -l kind $argv[1]
    set -l rest $argv[2..-1]

    # These return text, or an answer, rather than printing a line, so they are served
    # before any of the layout below applies.
    switch $kind
        case color
            set -l stream $rest[2]
            test -n "$stream"; or set stream compose
            _ui_code "$rest[1]" "$stream"
            return 0
        case color-enabled
            # Asked as a bare command, so fd 1 is the caller's real stdout rather than
            # the pipe a command substitution would have handed it.
            _ui_colour_on "$rest[1]"
            return $status
        case paint
            # Every command substitution here is assigned first and then quoted:
            # with colour off `(_ui_code x)` is an empty *list*, which would shift
            # printf's arguments one place to the left rather than print nothing.
            set -l code (_ui_code "$rest[1]" compose)
            set -l reset (_ui_code reset compose)
            set -l body (string join ' ' -- $rest[2..-1])
            printf '%s%s%s' "$code" "$body" "$reset"
            return 0
        case path
            string replace -r '^'(string escape --style=regex -- $HOME)'(/|$)' '~$1' -- "$rest[1]"
            return 0
        case blank
            echo
            return 0
    end

    set -l text (string join ' ' -- $rest)

    set -l width 0
    contains -- $kind item note; and set width 2
    set -q _flag_indent; and set width $_flag_indent
    set -l pad ""
    test $width -gt 0; and set pad (string repeat -n $width ' ')

    # Glyph and colour per kind, then one printf. `title` and `note` paint their whole
    # text; every other kind paints only the glyph, so the message itself stays the
    # terminal's default colour and stays readable on any theme.
    set -l glyph ""
    set -l colour ""
    set -l stream stdout
    switch $kind
        case title
            set colour bold
        case note
            set colour dim
        case step
            set glyph →
            set colour cyan
        case ok
            set glyph ✓
            set colour green
        case warn
            set glyph ⚠
            set colour yellow
        case err
            set glyph ✗
            set colour magenta
            # Its colour is decided against stderr: `cmd 2>log` from a terminal
            # should not write escape codes into the log.
            set stream stderr
        case item
            set glyph ·
            set colour dim
        case done
            set glyph ✨
        case '*'
            echo "_ui: unknown line kind '$kind'" >&2
            return 1
    end

    set -l c (_ui_code $colour $stream)
    set -l r (_ui_code reset $stream)

    # Colour composed upstream is intent, not a decision, so this is where it is
    # resolved: the line lands here, and nothing before here could see where.
    if not _ui_colour_on $stream
        set text (string replace -ra '\e\[[0-9;]*m' '' -- "$text" | string collect)
    end

    switch $kind
        case title note
            printf '%s%s%s%s\n' "$pad" "$c" "$text" "$r"
        case done
            printf '%s%s %s\n' "$pad" "$glyph" "$text"
        case err
            printf '%s%s%s%s %s\n' "$pad" "$c" "$glyph" "$r" "$text" >&2
        case '*'
            printf '%s%s%s%s %s\n' "$pad" "$c" "$glyph" "$r" "$text"
    end
end

function _ui_code --description "The escape sequence for one palette colour, or nothing when colour is off" --argument-names name stream
    test -n "$stream"; or set stream stdout
    _ui_colour_on $stream; or return 0

    switch $name
        case reset
            set_color normal
        case dim
            # brblack, as every de-emphasised suffix in a listing uses.
            set_color brblack
        case bold
            set_color --bold
        case ''
            return 0
        case '*'
            set_color $name
    end
end

function _ui_colour_on --description "True when escape codes should be emitted for a stream" --argument-names stream
    # NO_COLOR beats FORCE_COLOR: someone who asked for no colour anywhere means it,
    # and a tool overriding that is a bug rather than a feature. Emptiness counts as
    # unset, so `NO_COLOR= cmd` does not silently strip colour.
    test -n "$NO_COLOR"; and return 1
    test -n "$FORCE_COLOR"; and return 0
    # `compose` is not a stream: it is `_ui color` / `_ui paint` saying they cannot know
    # where their text lands. Optimistic, because the printing kind strips what its own
    # stream refuses, and no check here could tell a substitution's pipe from a real one.
    test "$stream" = compose; and return 0
    isatty $stream
end
