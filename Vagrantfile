Vagrant.configure("2") do |config|
  # from https://vagrantcloud.com/search.
  config.vm.box = "archlinux/archlinux"

  config.vm.provider :virtualbox do |v|1
    v.name = "archlinux"
    # v.gui = $GUI
    v.gui = true

    # Amount of memory RAM on the VM:
    v.memory = 8000

    # Amount of cpus on the VM:
    v.cpus = 2
    v.customize ["modifyvm", :id, "--cpuexecutioncap", "50"]

    # Set the video memory to 128Mb and VMSVGA
    v.customize ["modifyvm", :id, "--vram", "256"]
    v.customize ['modifyvm', :id, '--graphicscontroller', 'vmsvga']

    # Enable 3D acceleration:
    v.customize ["modifyvm", :id, "--accelerate3d", "on"]

    v.customize ["setextradata", :id, "GUI/LastGuestSizeHint", "1920,1080"]
  end

  config.vm.provision "shell", inline: "pacman --sync --quiet --refresh"
  config.vm.provision "shell", inline: "pacman --sync --quiet --noconfirm linux-headers base-devel"

  config.vm.provision "ansible_local" do |ansible|
    ansible.install = true
    ansible.limit = "all"
    ansible.verbose = false
    ansible.playbook = "dotfiles.yml"
    ansible.vault_password_file = "vault_pass"
    ansible.extra_vars = { ansible_python_interpreter: "/usr/bin/python3" }
  end
end

