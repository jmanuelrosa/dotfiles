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
alias l='eza --color=auto --icons=auto --group-directories-first'
alias ls='eza --color=auto --icons=auto --long --git --group-directories-first --sort=name'
alias ll='eza --color=auto --icons=auto --long --git --group-directories-first --all --sort=name'

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

# docker
alias docker:start='systemctl start docker'
alias docker:stop='systemctl stop docker'

alias claude:skill='claude-skill'
alias claude:mcp='claude-mcp'
alias claude:agent='claude-agent'
