set -gx EDITOR code
set -gx DOTFILES_DIR "$HOME/Developer/dotfiles"
set -gx DOCKER_HOST "unix://$HOME/.colima/docker.sock"

# AI exports
set -gx PI_ASK_USER_DISPLAY_MODE inline
set -gx CTX7_TELEMETRY_DISABLED 1
