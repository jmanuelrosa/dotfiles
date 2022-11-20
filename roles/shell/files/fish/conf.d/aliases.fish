# system
alias rm "rm -i"

# control
alias please sudo
alias restart 'sudo shutdown -r now'
alias shutdown 'sudo shutdown now'

# update
alias update "sudo reflector --protocol https --age 5 --number 10 --latest 10 --sort rate --save /etc/pacman.d/mirrorlist && yay -Sc --noconfirm && yay -Syu --noconfirm && yay -RYc"

#navigartion
alias .. "cd .." # Exists by default in fish
# alias ll "ls -alh" # Exists by default in fish

# apps
alias lock "i3lock"