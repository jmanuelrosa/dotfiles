#!/usr/bin/env bash

echo "$(dirname "${BASH_SOURCE}")";

printf "\e[1;34m  [i]\e[0m Downloading jmanuelrosa's dotfiles ...\e[0m\n"
git clone https://github.com/jmanuelrosa/dotfiles.git . &> /dev/null

printf "\e[1;34m  [⬇️]\e[0m Downloading and installing dependencies ...\e[0m\n"
if [ "$(uname)" == "Darwin" ]; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  brew install git ansible
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  sudo pacman -Sy --noconfirm git ansible
fi

printf "\e[1;34m  [⬇️]\e[0m Updating ansible ...\e[0m\n"
ansible-galaxy collection install community.general

printf "\e[1;33m  [⬇️]\e[0m Installing dotfiles ...\e[0m\n"
ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml

printf "\e[1;32m  [✔]\e[0m Dotfiles installed successfully\e[0m\n"
