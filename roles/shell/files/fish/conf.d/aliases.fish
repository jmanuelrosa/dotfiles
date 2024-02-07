# system
alias rm "rm -i"
alias cat bat
alias less bat

# control
alias please sudo
alias restart "sudo shutdown -r now"
alias shutdown "sudo shutdown now"

# update
alias update "sudo reflector --protocol https --age 5 --number 10 --latest 10 --sort rate --save /etc/pacman.d/mirrorlist && yay -Sc --noconfirm && yay -Syu --noconfirm && yay -RYc"

#navigation
alias .. "cd .." # Exists by default in fish
alias ll "ls -alh" # Exists by default in fish

# NPM
alias p pnpm

# apps
alias lock "i3lock"
alias g "git"
alias chrome "open -a google\ chrome"
