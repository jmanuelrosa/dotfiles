$GUI = ENV.fetch("GUI", false)

Vagrant.configure("2") do |config|
  # from https://vagrantcloud.com/search.
  config.vm.box = "archlinux/archlinux"

  config.vm.provider "virtualbox" do |v|
    v.name = "archlinux"
  end

  config.vm.provider :virtualbox do |vb|
    vb.gui = $GUI
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "vagrant.yml"
    ansible.limit = "all"
    ansible.ask_vault_pass = true
    ansible.verbose = true
    ansible.extra_vars = { ansible_python_interpreter: "/usr/bin/python3" }
  end
end

