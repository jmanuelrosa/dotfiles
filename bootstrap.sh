#!/usr/bin/env bash

HOMEBREW_INSTALL_COMMIT="8ab1549dfa1189fd4d818a2116592d8f0ee06d8c"
HOMEBREW_INSTALL_SHA256="5f333bbe53bc490e51e7ccb1df8779b3dd6ee73a1a7379efda216edb08ccb148"

echo "$(dirname "${BASH_SOURCE}")";

printf "\e[1;34m  [i]\e[0m Downloading jmanuelrosa's dotfiles ...\e[0m\n"
git clone https://github.com/jmanuelrosa/dotfiles.git . &> /dev/null

printf "\e[1;34m  [⬇️]\e[0m Downloading and installing dependencies ...\e[0m\n"
# The installer picks its prefix from the CPU and never exports it to this shell, so the
# same choice is made here to find brew afterwards.
if [[ "$(uname -m)" == "arm64" ]]; then
  homebrew_prefix="/opt/homebrew"
else
  homebrew_prefix="/usr/local"
fi

if [[ ! -x "${homebrew_prefix}/bin/brew" ]]; then
  homebrew_installer="$(mktemp -d)/install.sh" || exit 1
  if ! curl -fsSL -o "${homebrew_installer}" "https://raw.githubusercontent.com/Homebrew/install/${HOMEBREW_INSTALL_COMMIT}/install.sh" \
    || ! printf "%s  %s\n" "${HOMEBREW_INSTALL_SHA256}" "${homebrew_installer}" | shasum -a 256 -c --status -; then
    printf "\e[1;35m  [✗]\e[0m Homebrew installer at %s did not download or failed its checksum, aborting\e[0m\n" "${HOMEBREW_INSTALL_COMMIT}" >&2
    exit 1
  fi
  if ! /bin/bash "${homebrew_installer}"; then
    printf "\e[1;35m  [✗]\e[0m Homebrew installer failed, aborting\e[0m\n" >&2
    exit 1
  fi
fi

eval "$("${homebrew_prefix}/bin/brew" shellenv bash)"
brew install git ansible

printf "\e[1;34m  [⬇️]\e[0m Installing pinned ansible collections ...\e[0m\n"
ansible-galaxy collection install -r requirements.yml

printf "\e[1;33m  [⬇️]\e[0m Installing dotfiles ...\e[0m\n"
ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml

printf "\e[1;32m  [✔]\e[0m Dotfiles installed successfully\e[0m\n"
