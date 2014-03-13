#!/usr/bin/env python2
from __future__ import print_function

import argparse
import json
from httplib import InvalidURL
import os
from multiprocessing.pool import ThreadPool
import re
import socket
from sys import exit
import time

import pysphere
from tendo import singleton

from racktables import client

lock = singleton.SingleInstance()


class DictDiffer(object):
    """
  Calculate the difference between two dictionaries as:
  (1) items added
  (2) items removed
  (3) keys same in both but changed values
  (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(
            current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])


def vprint(message):
    try:
        if args.verbose > 0:
            print(message)
    except NameError:
        print(message)


def vvprint(message):
    try:
        if args.verbose > 1:
            print(message)
    except NameError:
        print(message)


def get_passwords(pw_file=os.getenv('HOME') + '/.vmwrtpw'):
    """Defaults to use a password file in the home directory. Running this
    function with a different pw_file will set it for all future uses"""
    if not hasattr(get_passwords, 'passwords'):
        get_passwords.passwords = {}
        with open(pw_file) as f:
            get_passwords.passwords = json.load(f)
    return get_passwords.passwords


def racktables():
    if not hasattr(racktables, 'rt'):
        racktables.rt = client.RacktablesClient(
            'http://racktables.wotifgroup.com/api.php',
            get_passwords()['rtusername'],
            get_passwords()['rtpassword'])
        if not racktables.rt.get_chapter(13):
            print('An error has occurred while connecting to racktables! Aborting.')
            exit(1)
    return racktables.rt


def vsphere():
    if not hasattr(vsphere, 'vmwserver'):
        vsphere.vmwserver = pysphere.VIServer()
        try:
            vsphere.vmwserver.connect("vcenter.core.wotifgroup.com",
                                      get_passwords()['vmwusername'],
                                      get_passwords()['vmwpassword'])
        except pysphere.VIApiException:
            print('An error has occurred while connecting to vSphere! Aborting.')
            exit(1)
    return vsphere.vmwserver


def generate_tags(vm_props):
    tags = []
    if re.search('BNE2', vm_props['clustername']):
        tags.append('Eagle Farm')
    elif re.search('SYD2|UAT', vm_props['clustername']):
        tags.append('Global Switch')
    return tags


def get_rt_vm_by_name(name):
    rt_objs = racktables().get_objects(type_filter=1504)
    for vm in rt_objs:
        if rt_objs[vm]['name'] == name:
            return vm
    return None


def get_rt_details(rt_id):
    details = racktables().get_object(rt_id, get_attrs=True)
    return (details['attrs'], details['ipv4'])


def get_rt_attr(attrs, name):
    try:
        return attrs[name]['a_value']
    except KeyError:
        return None


def get_vmw_osname(vm):
    os_translations = {
        'win2000AdvServGuest': 'Windows 2000',
        'winXPProGuest': 'Windows XP',
        'winNetStandard64Guest': 'Windows 2003',
        'winNetStandardGuest': 'Windows 2003',
        'winLonghorn64Guest': 'Windows Server 2008',
        'winLonghornGuest': 'Windows Server 2008',
        'windows7_64Guest': 'Windows 7',
        'windows8_64Guest': 'Windows 8',
        'windows7Server64Guest': 'Windows Server 2008 R2',
        'windows8Server64Guest': 'Windows Server 2012',
        'centos64Guest': 'CentOS V5',
        'debian6Guest': 'Debian 6.0 (squeeze)',
        'rhel3Guest': 'RHEL V3',
        'rhel4Guest': 'RHEL V4',
        'rhel5_Guest': 'RHEL V5',
        'rhel5_64Guest': 'RHEL V5',
        'rhel6_64Guest': 'RHEL V6'
        }
    os_id = vm.get_property('guest_id')
    if os_id in os_translations:
        return os_translations[os_id]
    else:
        return None


def get_vmw_datastore(vm):
    path = vm.get_property('path')
    datastore = re.search('\[(.*?)\]', path)
    return datastore.groups()[0]


def get_rt_objs(type=1504):
    '''Default type filter is 1504 (VMs)'''
    if not hasattr(get_rt_objs, 'rt_objs'):
        vvprint("Creating blank rt_objs record")
        get_rt_objs.rt_objs = {}
    if type not in get_rt_objs.rt_objs:
        vvprint("Initializing rt_objs entry for type %d" % type)
        get_rt_objs.rt_objs[type] = racktables().get_objects(type_filter=type)
    return get_rt_objs.rt_objs[type]


def get_rt_vm(rt_id):
    attrs, networks = get_rt_details(rt_id)
    vm_obj = get_rt_objs()[rt_id]
    vm = {
        'rt_id': rt_id,
        'hostname': vm_obj['name'],
        'clustername': vm_obj['container_name'],
        'osname': get_rt_attr(attrs, 'SW Type'),
        'cores': get_rt_attr(attrs, 'CPU cores, No.'),
        'datastore': get_rt_attr(attrs, 'Datastore'),
        'ip_addresses': {},
        }
    for network in networks.itervalues():
        vm['ip_addresses'][network['osif']] = \
            network['addrinfo']['ip']
    vvprint("Retrieved racktables VM record: %r" % vm)

    return vm


def get_racktables_list():
    rt_ids = {}
    rt_list = {}
    pool = ThreadPool(processes=4)
    vmids = get_rt_objs().keys()
    t0 = time.time()
    vms = pool.map(get_rt_vm, vmids)
    vvprint('Gathering RT list took %s seconds' % (time.time() - t0))
    for vm in vms:
        hostname = vm.pop('hostname')
        rt_id = vm.pop('rt_id')
        rt_list[hostname] = vm
        rt_ids[hostname] = rt_id
    pool.close()

    return (rt_ids, rt_list)


def get_vmw_vm(vmpath):
    cur_vm = vsphere().get_vm_by_path(vmpath)
    hostname = cur_vm.get_property('hostname')
    if not hostname:
        hostname = cur_vm.get_property('name')
    vm = {
        'path': vmpath,
        'hostname': hostname,
        'clustername': get_vmw_cluster(vmpath),
        'osname': get_vmw_osname(cur_vm),
        'cores': str(cur_vm.get_property('num_cpu')),
        'datastore': get_vmw_datastore(cur_vm),
        'ip_addresses': {}
    }
    networks = cur_vm.get_property('net')
    if networks:
        for eth, net in enumerate(networks):
            # We only care about mac addresses that are mapped
            # to vmnics; not dummy networks. Looking at you app5!
            if net['network']:
                for num, ip in enumerate(net['ip_addresses']):
                    try:
                        socket.inet_aton(ip)
                    except socket.error:
                        continue
                    eth_string = 'eth%s' % eth
                    if eth_string in vm['ip_addresses']:
                        vm['ip_addresses']['eth%s:%s' % (eth, num)] = ip
                    else:
                        vm['ip_addresses'][eth_string] = ip
    vvprint("Retrieved VMWare VM record for %r\n" % vm)
    return vm


def get_vmw_list():
    vmw_list = {}
    vmw_paths = {}
    pool = ThreadPool(processes=6)
    vmpaths = vsphere().get_registered_vms()
    get_vmw_cluster('')
    t0 = time.time()
    vms = pool.map(get_vmw_vm, vmpaths)
    vvprint('Gathering VMW list took %s seconds' % (time.time() - t0))
    for vm in vms:
        hostname = vm.pop('hostname')
        path = vm.pop('path')
        vmw_list[hostname] = vm
        vmw_paths[hostname] = path
    pool.close()
    return vmw_list, vmw_paths


def get_vmw_cluster(vmpath):
    if not hasattr(get_vmw_cluster, 'cluster_map'):
        vprint("Initializing cluster maps...")
        get_vmw_cluster.cluster_map = {}
        for cluster in vsphere().get_clusters().values():
            vvprint("    Generating cluster map for cluster %s..." % cluster)
            for i in vsphere().get_registered_vms(cluster=cluster):
                get_vmw_cluster.cluster_map[i] = cluster
    try:
        return get_vmw_cluster.cluster_map[vmpath]
    except KeyError:
        return ''


def get_cluster_id(clustername):
    if not hasattr(get_cluster_id, 'cluster_map'):
        vprint("Initializing cluster ID map...")
        get_cluster_id.cluster_map = {}
        clusters = racktables().get_objects(type_filter=1505)
        for cluster in clusters:
            get_cluster_id.cluster_map[clusters[cluster]['name']] = cluster
    try:
        return get_cluster_id.cluster_map[clustername]
    except KeyError:
        return None


def get_os_id(osname):
    if not hasattr(get_os_id, 'os_map'):
        vprint("Initializing OS ID map...")
        get_os_id.os_map = {v: k for k, v in
                            racktables().get_chapter(13).items()}
    try:
        return get_os_id.os_map[osname]
    except KeyError:
        return None


def add_to_cluster(rt_id, vm_props):
    clusterid = get_cluster_id(vm_props['clustername'])
    # link_entities function returns {} for a 'success' and '' if the objects
    # were already linked. It DOES allow you to link to non-existant IDs,
    # which will break the child object in the web UI
    racktables().link_entities(rt_id, clusterid)
    return None


def generate_attrs(vm, vm_props):
    # Attr IDs:
    #      3: FQDN
    #      4: OS Type
    #     17: RAM (GB)
    #  10018: CPU cores, No

    attrs = {
        3: vm,
        10018: vm_props['cores'],
        10022: vm_props['datastore']
    }
    if vm_props['osname']:
        attrs[4] = get_os_id(vm_props['osname'])
    return attrs


def replace_ip_addresses(rt_id, vm_props):
    #Remove current IPs first
    old_rt_ips = racktables().get_object(rt_id)['ipv4']
    for rec in old_rt_ips:
        ip = old_rt_ips[rec]['addrinfo']['ip']
        try:
            racktables().delete_object_ipv4_address(rt_id, ip)
        except InvalidURL:
            # This happens when the IP address was deleted successfully
            pass
        except ValueError:
            # This happens (occasionally) when an IP address is deleted.
            # It is still probably successful
            pass

    for dev, ip in vm_props['ip_addresses'].iteritems():
        try:
            racktables().add_object_ipv4_address(rt_id, ip, dev)
        except InvalidURL:
            # This happens when the IP address was added successfully
            pass
        except TypeError:
            # This happens when the IP address already exists on this device,
            # or an invalid IP address is given
            pass
        except ValueError:
            # This happens (occasionally) when an IP address is added.
            # It is still probably successful
            pass
    return None


def remove_racktables_obj(vm, rt_id, vm_props):
    vvprint("Object removal for %s (ID: %s) started. %r"
            % (vm, rt_id, vm_props))
    try:
        racktables().delete_object(rt_id)
    except InvalidURL:
        # This happens when an object is deleted
        # or didn't exist in the first place
        pass
    except ValueError:
        # This happens occasionally when an object is deleted.
        # It is still probably successful
        pass
    return None


def create_racktables_obj(vm, vm_props):
    vvprint("Object creation for %s started. %r" % (vm, vm_props))

    try:
        racktables().add_object(vm, object_type_id=1504)
    except InvalidURL:
        # This happens when an object is created successfully
        pass
    except ValueError:
        # This happens (occasionally) when an object
        # is created (still successfully)
        pass
    except TypeError:
        # This happens when an object already exists,
        # we also want to ignore this
        pass

    rt_id = get_rt_vm_by_name(vm)

    if rt_id:
        try:
            racktables().update_object_tags(rt_id, generate_tags(vm_props))
        except client.RacktablesClientException:
            print("The specified tags could not be found. Tags on %s (ID %s) "
                  "will not be updated" % (vm, rt_id))
        add_to_cluster(rt_id, vm_props)
        replace_ip_addresses(rt_id, vm_props)
        try:
            ret = racktables().edit_object(
                rt_id,
                object_name=vm,
                object_type_id=1504,
                attrs=generate_attrs(vm, vm_props))
            if ret == '':
                print("An error has occurred while updating the properties "
                      "for vm %s (ID %s)" % (vm, rt_id))
        except InvalidURL:
            # This happens when it is successful
            pass
        except ValueError:
            # This sometimes also happens, but appears
            # to always be successful anyway.
            pass
    else:
        print("An error has occurred while creating %s" % vm)
    return None


def simple_check():
    # Get current machine list
    outfile = '/tmp/.vmware-to-racktables-list'
    new_list = vsphere().get_registered_vms()
    # Check if file already exists
    if os.path.isfile(outfile):
        # Load file
        with open(outfile) as f:
            # Compare against current list
            old_list = json.load(f)
        if new_list == old_list:
            return True
    with open(outfile, 'w') as f:
        json.dump(new_list, f, indent=2)
    return False


def vm_powered_on(vm_path):
    vm = vsphere().get_vm_by_path(vm_path)
    return vm.is_powered_on()


def main(args):
    if args.simple:
        if simple_check():
            exit(0)

    if args.dryrun:
        print("Dry-run mode enabled!")
        args.verbose = 2

    # Read in list of VMs from Racktables
    vprint("Retrieving Racktables VM list...")
    rt_ids, rt_list = get_racktables_list()

    # Read in list of VMs from VMWare
    vvprint("\n")
    vprint("Retrieving VSphere VM list...")
    vmw_list, vmw_paths = get_vmw_list()

    # Find differences between the data recorded
    # in Racktables compared to VMWare's
    diff = DictDiffer(vmw_list, rt_list)

    vprint("Updating changed objects...")
    for vm in diff.changed():
        if vm_powered_on(vmw_paths[vm]):
            vprint("VM %s has changed. Creating new object in racktables..."
                   % vm)
            vvprint("Racktables entry: %r" % rt_list[vm])
            vvprint("vSphere entry: %r" % vmw_list[vm])
            if not args.dryrun:
                create_racktables_obj(vm, vmw_list[vm])

    vvprint("\n")
    vprint("Adding new objects...")
    for vm in diff.added():
        vprint("VM %s has been added. Creating object in racktables..." % vm)
        if not args.dryrun:
            create_racktables_obj(vm, vmw_list[vm])

    vvprint("\n")
    vprint("Deleting old objects...")
    for vm in diff.removed():
        vprint("VM %s has been removed. Deleting object in racktables..." % vm)
        if not args.dryrun:
            remove_racktables_obj(vm, rt_ids[vm], rt_list[vm])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        help='Increase verbosity of output',
                        action='count')
    parser.add_argument('-s', '--simple', help='Only perform a quick check '
                        'for new VMs, and not changed/deleted VMs',
                        action='store_true')
    parser.add_argument('-d', '--dryrun', help='Do not apply changes to'
                        'Racktables. Implies very verbose.',
                        action='store_true')

    args = parser.parse_args()

    main(args)
