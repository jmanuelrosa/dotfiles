function pi_debug --description "Launch pi with Cursor SDK failure detail capture enabled: message and stack instead of a generic '... did not complete'"
    env PI_CURSOR_SDK_EVENT_DEBUG=1 PI_CURSOR_SDK_EVENT_DEBUG_DIR="$HOME/.pi/agent/cursor-sdk-debug" pi $argv
end
