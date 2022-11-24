# jmanuelrosa's dotfiles

 A set of configurations, applications and tweaks for Arch Linux

## Packages Overview

* [System](./roles/system/tasks/main.yml) packages

## Installation

**Warning**: These dotfiles are well tested with Arch Linux and should work *ONLY* with Arch Linux. If you want to try it with another Linux distribution, you should use the packaging tool for your Linux distribution, such as the [apt module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/apt_module.html#ansible-collections-ansible-builtin-apt-module) for Debian.

### No dependencies
You don't need to do anything to install the dotfiles in this way, just run the bootstrap script and it will do the rest.

```
> mkdir dotfiles
> cd dotfiles
> bash <(curl -L https://github.com/jmanuelrosa/dotfiles/bootstrap.sh)
```

### Using Ansible and Git

If you want to manage the dotfiles by yourself, you can download and run them with Ansible. In this case, you'll need to install git, ansible, and some plugins.

```
> sudo pacman -S git ansible
> ansible-galaxy collection install community.general
> mkdir dotfiles
> cd dotfiles
> git clone git@github.com:jmanuelrosa/dotfiles.git . &> /dev/nul
> ansible-playbook --inventory inventory.yml --ask-vault-password --ask-become-pass dotfiles.yml
```

## Tools

* [yay](https://github.com/Jguer/yay): A powerful AUR Helper written in Go to use as an alternative to Pacman
* [bat](https://github.com/sharkdp/bat): A cat(1) clone with wings
* [glances](https://github.com/nicolargo/glances): A top/htop alternative for GNU/Linux, BSD, Mac OS and Windows operating systems.
* github: ... you know it
  * [gh](https://github.com/cli/cli): GitHub’s official command line tool

## Testing

Instead to run the dotfiles in your current machine all time that we change or update a config, you can test these playbooks with Vagrant. There is a Vagrant file configuration with the minimun required (an empty arch installation).

The first that you need is install the dependencies:

```
> yay -S vagrant virtualbox ansible
```

After install all dependencies, you can choose to run the GUI or not to see Sway and Wayland in action.

If you want to run vagrant in headless mode, you need to run it with:

```
> vagrant up
```

If you want to run Vagrant with the GUI and see how beautiful Sway is and how it's works in Wayland, you can run:


```
> GUI=true vagrant up
```

### Install Guest additions on vagrant

```
> vagrant ssh -c "sudo pacman --remove --noconfirm virtualbox-guest-utils-nox"
> vagrant ssh -c "sudo pacman --sync --quiet --noconfirm virtualbox-guest-utils virtualbox-guest-iso"
> vagrant reload
> vagrant ssh -c "sudo mount -t iso9660 -o loop /usr/lib/virtualbox/additions/VBoxGuestAdditions.iso /mnt"
> vagrant ssh -c "sudo yes | sudo sh /mnt/VBoxLinuxAdditions.run --accept"
> vagrant reload
> vagrant ssh -c "sudo /sbin/rcvboxadd quicksetup all"
```

## Errors

### Vagrant errors

* `VERR_VMX_MSR_ALL_VMX_DISABLED` error whrn try to run `vagrant up`, you need to active virtualization in your BIOS. You need to active
  * Intel Virtualization technology
  * Intel VT-d Feature

* If you get an error related to `vboxdrv`, run `sudo modprobe vboxdrv` to add this module to the kernel. For this, you should have installed `linux-lts-headers`.