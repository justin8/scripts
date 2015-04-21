Vagrant.configure('2') do |config|

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
  end


  config.vm.provision "shell", inline: <<-SHELL
    apt-get install -y python-pip libav-tools libchromaprint0
    pip install -r /vagrant/requirements.txt
  SHELL

  config.vm.define :gmusicDO do |gdo|
    gdo.vm.provider :digital_ocean do |provider, override|
      override.ssh.private_key_path = '~/.ssh/vagrant_id_rsa'
      override.vm.box = 'digital_ocean'
      override.vm.box_url = "https://github.com/smdahlen/vagrant-digitalocean/raw/master/box/digital_ocean.box"

      provider.token = ENV['DIGITAL_OCEAN_TOKEN']
      provider.image = 'ubuntu-14-10-x64'
      provider.region = 'sgp1'
      provider.size = '512mb'
    end
  end

  config.vm.define :gmusicVBox do |gvb|
    gvb.vm.box = "ubuntu/trusty64"
  end

end

