# system
alias rm "rm -i"
alias cat bat
alias less bat
alias update "sudo pacman-mirrors -f 10 --method rank && yay -Sc --noconfirm && yay -Syu --noconfirm && yay -RYc"

# fish
alias please-clean-history "history clear"

# control
alias please sudo
alias restart "sudo shutdown -r now"
alias shutdown "sudo shutdown now"

#navigation
alias .. "cd .." # Exists by default in fish
alias ls 'eza --color=always --long --git --icons=always --group-directories-first --sort=name'
alias ll "eza --color=always --long --git --icons=always --group-directories-first --all --sort=name"

# NPM
alias p pnpm

# apps
alias lock "i3lock"
alias g "git"
alias chrome "open -a google\ chrome"

# docker
alias docker:start "systemctl start docker"
alias docker:stop "systemctl stop docker"