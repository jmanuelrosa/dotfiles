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

# Dev environments. The five lokl: aliases that lived here are gone: `lokl` is a real
# command now (roles/apps/files/scripts/lokl), and it owns the domains as well as the
# proxy, because a domain is a hosts entry and a Caddy site file that have to agree.
#
#   lokl add my-custom-project       lokl list      lokl start
#   lokl remove my-custom-project    lokl sync      lokl status
#
# A project with several services nests them under one parent, so all of them share the
# registrable domain and therefore the cookie jar:
#
#   lokl add my-project --sub app --sub api    # my-project.localhost, app.my-project.localhost, ...
#   lokl remove my-project --tree              # the parent and every subdomain under it
#
# The port is derived from the working directory when `add` is given none, and
# `lokl port <name>` prints it for a dev script to read. No `--host`: that binds every
# interface, and Caddy already dials loopback.
#
#   astro dev --port (lokl port my-custom-project)

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


alias pi:debug=pi_debug
alias pi:log=pi_last_error
