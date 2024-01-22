#!/usr/bin/env bash

echo "$(dirname "${BASH_SOURCE}")";

printf "\e[1;34m  [i]\e[0m Downloading jmanuelrosa's dotfiles ...\e[0m\n"
git clone https://github.com/jmanuelrosa/dotfiles.git . &> /dev/null

printf "\e[1;34m  [⬇️]\e[0m Downloading and installing dependencies ...\e[0m\n"
sudo pacman -Sy --noconfirm git ansible ansible-galaxy &> /dev/null
ansible-galaxy collection install community.general

printf "\e[1;33m  [⬇️]\e[0m Installing dotfiles ...\e[0m\n"
ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass setup.yml

printf "\e[1;32m  [✔]\e[0m Dotfiles installed successfully\e[0m\n"
