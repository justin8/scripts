#!/bin/bash
echo "Please enter the new (short) hostname for this server:"

# Fix hostname entries
read hostname
sed -i "s/new-arch-vm/$hostname/g" /etc/hosts
sed -i "s/new-arch-vm/$hostname/g" /etc/hostname
hostname "$hostname"

# Regen sshd keys
rm -f /etc/ssh/ssh_host*
ssh-keygen -A

# Rename root filesystem / rebuild mkinitcpio
btrfs filesystem label "/" "${hostname}-btrfs"
e2label "/dev/disk/by-label/boot" "${hostname}-boot"
sed -i "s/LABEL=btrfs/LABEL=${hostname}-btrfs/g" /etc/fstab
sed -i "s/LABEL=boot/LABEL=${hostname}-boot/g" /etc/fstab
sed -i "s/LABEL=btrfs/LABEL=${hostname}-btrfs/g" /boot/syslinux/syslinux.cfg
syslinux-install_update -iam
mkinitcpio -p linux

# Configure snapper
snapper -c root create-config /

# Configure puppet
systemctl stop puppet
rm -rf /var/lib/puppet/ssl
puppet agent -t --no-noop
systemctl enable puppet
systemctl start puppet

# Enable collectd
systemctl enable collectd

# Remove firstboot script.
sed -i "s#/firstboot.sh##g" /root/.zshrc-addon
mv /firstboot.sh /tmp

echo "Press enter to reboot now, or ctrl+c to exit"
read
reboot
