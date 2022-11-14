$GUI = ENV.fetch("GUI", false)

Vagrant.configure("2") do |config|
  # from https://vagrantcloud.com/search.
  config.vm.box = "archlinux/archlinux"

  config.vm.provider :virtualbox do |v|
    v.name = "archlinux"
    v.gui = $GUI
    v.memory = 8000
    v.cpus = 4
    v.customize ["modifyvm", :id, "--vram", "128"]
  end

  config.vm.provision "shell", inline: "pacman -Syu --quiet --noconfirm"

  config.vm.provision "ansible_local" do |ansible|
    ansible.install = true
    ansible.limit = "all"
    ansible.verbose = false
    ansible.playbook = "vagrant.yml"
    ansible.vault_password_file = "vault_pass"
    ansible.extra_vars = { ansible_python_interpreter: "/usr/bin/python3" }
  end
end

