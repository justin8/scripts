#!/usr/bin/env python2

from __future__ import print_function
from socket import inet_aton
from racktables import client
import argparse
import os
import pysphere
import re


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
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        return self.set_current - self.intersect
    def removed(self):
        return self.set_past - self.intersect
    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

def vprint(message):
    if args.verbose > 0:
        print(message)

def vvprint(message):
    if args.verbose > 1:
        print(message)

def read_password_file(pw_file):
    import json
    passwords = {}
    with open(pw_file) as f:
        passwords=json.load(f)
    return passwords

def connect_racktables():
    rt = client.RacktablesClient('http://racktables.wotifgroup.com/api.php', passwords['rtusername'], passwords['rtpassword'])
    return rt

def connect_vsphere():
    vmwserver = pysphere.VIServer()
    vmwserver.connect("vcenter.core.wotifgroup.com", passwords['vmwusername'], passwords['vmwpassword'])
    return vmwserver

def generate_tags(vm_props):
    tags=[]
    if re.search('BNE2', vm_props['clustername']):
        tags.append('Eagle Farm')
    elif re.search('SYD2|UAT', vm_props['clustername']):
        tags.append('Global Switch')
    return tags

def get_rt_vm_by_name(rt, name):
    rt_objs = rt.get_objects(type_filter=1504)
    for vm in rt_objs:
        if rt_objs[vm]['name'] == name:
            return vm
    return None

def get_rt_osname(rt, rt_id):
    try:
        return rt.get_object(rt_id, get_attrs=True)['attrs']['SW type']['a_value']
    except:
        # TODO: Change this to only catch key errors
        return None

def get_vmw_osname(vm):
    os_translations = {
            'win2000AdvServGuest': 'Windows  2000',
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
            'rhel5_64Guest': 'RHEL V5',
            'rhel6_64Guest': 'RHEL V6'
            }
    os_id = vm.get_property('guest_id')
    if os_id in os_translations:
        return os_translations[os_id]
    else:
        return None

def get_racktables_list(rt):
    rt_objs = rt.get_objects(type_filter=1504)
    rt_ids = {}
    rt_list = {}

    for i in rt_objs:
        hostname = rt_objs[i]['name']
        rt_ids[hostname] = i
        vvprint("Name: %s\nID: %s\n" % ( hostname, i ))
        rt_list[hostname] = {
                'clustername': rt_objs[i]['container_name'],
                'osname': get_rt_osname(rt, i),
                'ip_addresses': {}
                }

        networks = rt.get_object(i)['ipv4']
        for net in networks:
            rt_list[hostname]['ip_addresses'][networks[net]['osif']] = networks[net]['addrinfo']['ip']
        vvprint("Retrieved racktables VM record for %s: %r" % ( hostname, rt_list[hostname] ))

    return ( rt_ids, rt_list )

def get_vmw_list(vmwserver):
    vmw_list = {}

    #for cluster in vmwserver.get_clusters().values():
    for cluster in [ 'SYD2 Prod AMD' ]:
        vprint("Retrieving VMs from cluster %s..." % cluster)
        for i in vmwserver.get_registered_vms(cluster=cluster):
            # This is the slow bit:
            cur_vm = vmwserver.get_vm_by_path(i)
            hostname = cur_vm.get_property('hostname')
            if not hostname:
                hostname = cur_vm.get_property('name')
            vmw_list[hostname] = {
                    'clustername': cluster,
                    'osname': get_vmw_osname(cur_vm),
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
                                inet_aton(ip)
                                if 'eth%s' % eth in vmw_list[hostname]['ip_addresses']:
                                    vmw_list[hostname]['ip_addresses']['eth%s:%s' % ( eth, num )] = ip
                                else:
                                    vmw_list[hostname]['ip_addresses']['eth%s' % eth] = ip
                            except:
                                #TODO: Make this only catch specific exceptions
                                pass

            vvprint("Retrieved VMWare VM record for %s: %r" % ( hostname, vmw_list[hostname] ))
        vprint("\n")
    return vmw_list

def get_cluster_id(rt, clustername):
    clusters = rt.get_objects(type_filter=1505)
    for cluster in clusters:
        if clusters[cluster]['name'] == clustername:
            return cluster
    return None

def get_os_id(rt, osname):
    oses = rt.get_chapter(13)
    for os in oses:
        if oses[os] == osname:
            return os
    return None

def add_to_cluster(rt, rt_id, vm_props):
    clusterid = get_cluster_id(rt, vm_props['clustername'])
    # link_entities function returns {} for a 'success' and '' if the objects
    # were already linked. It does allow you to link to non-existant IDs,
    # which will break the child object in the web UI
    rt.link_entities(rt_id, clusterid) 
    return None

def generate_attrs(rt, vm, vm_props):
    # Attr IDs:
    #      3: FQDN
    #      4: OS Type
    #     17: RAM (GB)
    #  10018: CPU cores, No

    attrs = {
            3: vm
            }
    # TODO: 4: if get_os_id(rt, vm_props['osname']) then add it. Otherwise do not add the OS if it is not matched
    if vm_props['osname']:
        attrs[4] = get_os_id(rt, vm_props['osname'])
    return attrs

def add_ip_addresses(rt, rt_id, vm_props):
    for dev, ip in vm_props['ip_addresses'].iteritems():
        try:
            rt.add_object_ipv4_address(rt_id, ip, dev)
        except:
            #TODO: Make this only catch specific exceptions
            pass
    return None

def remove_racktables_obj(rt, vm, rt_id, vm_props):
    vvprint("Object removal for %s (ID: %s) started. %r" % ( vm, rt_id, vm_props ))
    try:
        rt.delete_object(rt_id)
    except:
        #TODO: Make this only catch specific exceptions
        pass
    return None

def create_racktables_obj(rt, vm, vm_props):
    vvprint("Object creation for %s started. %r" % ( vm, vm_props ))

    try:
        # This throws exceptions if it is successful or not. :(
        # It will also silently fail if the object already exists,
        # allowing for updates of objects with rest of this function
        rt.add_object(vm, object_type_id=1504)
    except:
        #TODO: Make this only catch specific exceptions
        pass

    rt_id = get_rt_vm_by_name(rt, vm)

    if rt_id:
        try:
            rt.update_object_tags(rt_id, generate_tags(vm_props))
        except:
            #TODO: Make this only catch specific exceptions
            print("Caught an error while updating the tags for %s (ID %s)" % ( vm, rt_id))
        add_to_cluster(rt, rt_id, vm_props)
        add_ip_addresses(rt, rt_id, vm_props)
        try:
            # This throws exceptions if it is successful or not. :(
            rt.edit_object(rt_id, object_name=vm, object_type_id=1504, attrs=generate_attrs(rt, vm, vm_props))
        except:
            #TODO: Make this only catch specific exceptions
            pass
    else:
        print("An error has occurred while creating %s" % vm)
    return None

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Increase verbosity of output', action='count')
args = parser.parse_args()

passwords = read_password_file(os.getenv('HOME')+'/.vmwrtpw')
rt = connect_racktables()
vmwserver = connect_vsphere()

# TODO: Save out racktables global object list for VMs and vSphere's vm list
# then do a quick diff on next run to avoid the expensive queries to check each
# individual machine

# Read in list of VMs from Racktables
vprint("Retrieving Racktables VM list...")
rt_ids, rt_list = get_racktables_list(rt)

# Read in list of VMs from VMWare
vprint("\nRetrieving VMWare VM list...")
vmw_list = get_vmw_list(vmwserver)

# Find differences between the data recorded in Racktables compared to VMWare's
diff = DictDiffer(vmw_list, rt_list)

vprint("Updating changed objects...")
for vm in diff.changed():
# It does not appear to be necessary to delete the object before creating. It silently fails to create, then pushes any updates to the machine.
#    vvprint("VM %s has changed. Deleting old object in racktables..." % vm)
#    remove_racktables_obj(rt, vm, rt_ids[vm], vmw_list[vm])
    vprint("VM %s has changed. Creating new object in racktables..." % vm)
    vvprint("Racktables entry: %r" % rt_list[vm])
    vvprint("vSphere entry: %r" % vmw_list[vm])
    create_racktables_obj(rt, vm, vmw_list[vm])

vprint("\nAdding new objects...")
for vm in diff.added():
    vprint("VM %s has been added. Creating object in racktables..." % vm)
    create_racktables_obj(rt, vm, vmw_list[vm])

vprint("\nDeleting old objects...")
for vm in diff.removed():
    vprint("VM %s has been removed. Deleting object in racktables..." % vm)
    remove_racktables_obj(rt, vm, rt_ids[vm], rt_list[vm])
