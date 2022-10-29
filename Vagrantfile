$GUI = ENV.fetch("GUI", false)

Vagrant.configure("2") do |config|
  # from https://vagrantcloud.com/search.
  config.vm.box = "generic/arch"

  config.vm.provider "virtualbox" do |v|
    v.name = "archlinux"
  end

  config.vm.provider :virtualbox do |vb|
    vb.gui = $GUI
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "setup.yml"
  end
end

