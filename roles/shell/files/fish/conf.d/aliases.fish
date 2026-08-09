# Shortcuts
alias c="clear && printf '\e[3J'"
alias dl='cd ~/Downloads'
alias dt='cd ~/Desktop'

# system
alias rm='rm -i'
alias grep=rg
alias cat=bat
alias less=bat
alias find=fd

# fish
alias please-clean-history='history clear'

# control
alias please=sudo
alias restart='sudo shutdown -r now'
alias shutdown='sudo shutdown now'

#navigation
alias ..='cd ..' # Exists by default in fish
alias l='eza --color=auto --icons=auto --long --git --group-directories-first --all --sort=name'
alias lt="eza --tree --level=2 --color=auto --icons=auto --long --all --git --ignore-glob node_modules"

# NPM
alias p=pnpm

# apps
alias chrome='open -a google\ chrome'

# git
alias g='git'
alias lg='lazygit'

alias brew:update='brew update --force && brew upgrade --greedy --force && brew autoremove && brew cleanup --prune=all --scrub'

# Clean
alias clean:brew='brew autoremove && brew cleanup --prune=all --scrub'
alias clean:docker=clean_docker
alias clean:node=clean_node
alias clean:claude='clean_claude project'
alias clean:claude:skills='clean_claude skills'
alias clean:claude:agents='clean_claude agents'
alias clean:claude:purge='clean_claude purge'
alias clean:system='mo clean; mo optimize'
alias clean:all=clean_all

# docker. The engine is a colima VM, so starting "docker" means starting colima;
# DOCKER_HOST points at that VM's socket in conf.d/exports.fish.
alias docker:start='colima start'
alias docker:stop='colima stop'

# Dev environments. Caddy fronts the per-project *.localhost domains and binds :80, so
# it needs root. `run` rather than `start` is what keeps it off the boot path: start
# writes a LaunchDaemon into /Library/LaunchDaemons, run bootstraps the keg's own plist
# and leaves nothing behind. HOME is passed through because Homebrew derives its cache
# from it, and root's own cache holds no packages API JSON, so brew aborts without it.
alias lokl:start='sudo --preserve-env=HOME brew services run caddy'
alias lokl:stop='sudo --preserve-env=HOME brew services stop caddy'
alias lokl:status='sudo --preserve-env=HOME brew services info caddy'
alias lokl:validate='caddy validate --config /opt/homebrew/etc/Caddyfile'

# claude-kit. Functions rather than aliases: fish's alias builtin appends $argv to the
# body unconditionally, so an alias holding $argv passes every argument twice.
function claude:skill --wraps claude-kit
    claude-kit $argv --type skill
end

function claude:agent --wraps claude-kit
    claude-kit $argv --type agent
end

function claude:plugin --wraps claude-kit
    claude-kit $argv --type plugin
end
