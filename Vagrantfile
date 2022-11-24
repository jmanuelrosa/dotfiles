$GUI = ENV.fetch("GUI", false)

Vagrant.configure("2") do |config|
  # from https://vagrantcloud.com/search.
  config.vm.box = "archlinux/archlinux"

  # if Vagrant.has_plugin?("vagrant-vbguest")
  #   # Vagrant vagrant-vbguest plugin
  #   config.vbguest.auto_update = true
  #   config.vbguest.no_remote = false
  #   config.vbguest.no_install = false
  #   config.vbguest.auto_reboot = true
  #   config.vbguest.installer_arguments = ['--nox11']
  #   # config.vbguest.installer_hooks[:before_install] = [
  #   #   "pacman -Syu --quiet --noconfirm",
  #   #   "sudo pacman --remove --noconfirm virtualbox-guest-utils-nox",
  #   #   "sudo pacman --sync --quiet --noconfirm virtualbox-guest-utils virtualbox-guest-iso"
  #   # ]
  #   # config.vbguest.iso_pat2h = "/usr/lib/virtualbox/additions/VBoxGuestAdditions.iso"
  # end

  config.vm.provider :virtualbox do |v|
    v.name = "archlinux"
    v.gui = $GUI

    # Amount of memory RAM on the VM:
    v.memory = 8000

    # Amount of cpus on the VM:
    v.cpus = 2

    # Set the video memory to 128Mb and VMSVGA
    v.customize ["modifyvm", :id, "--vram", "128"]
    v.customize ['modifyvm', :id, '--graphicscontroller', 'vmsvga']

    # Enable 3D acceleration:
    v.customize ["modifyvm", :id, "--accelerate3d", "on"]

    v.customize ["setextradata", :id, "GUI/LastGuestSizeHint", "1920,1080"]
  end

  config.vm.provision "shell", inline: "pacman -Syu --quiet --noconfirm"
  config.vm.provision "shell", inline: "pacman --sync --quiet --noconfirm linux-headers base-devel"

  config.vm.provision "ansible_local" do |ansible|
    ansible.install = true
    ansible.limit = "all"
    ansible.verbose = false
    ansible.playbook = "vagrant.yml"
    ansible.vault_password_file = "vault_pass"
    ansible.extra_vars = { ansible_python_interpreter: "/usr/bin/python3" }
  end
end

