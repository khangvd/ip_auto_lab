"""Validates the input variables in the base, fabric and services files are of the correct
format to be able to run the playbook, build a fabric and apply the services.
A pass or fail is returned to the Ansible Assert module, if it fails the full output is also
returned for the failure message. The following methods check:

-base configuration variables using base.yml:
bse.device_name: Ensures that the device names used match the correct format as that is heavily used in inventory script logic
bse.addr: Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask

-core fabric configuration variables  using fabric.yml
fbc.network_size: Ensures the number of each type of device is within the limits and constraints
fbc.ospf: Ensures that the OSPF process is present and area in dotted decimal format
fbc.bgp.as_num: Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
fbc.acast_gw_mac: Ensures the anycast virtual MAC is a valid mac address
fbc.adv.bse_intf: Ensures that the interface numbers are integrars
fbc.adv.lp: Ensures all the loopback names are unique, no duplicates
fbc.adv.mlag: Ensures all of MLAG paraemters are integers and VLANs within limit
fbc.adv.addr_incre: Ensures all of the IP address increment values used are integers and except for mlag peering are all unique

-tenants (VRFs, VNIs & VLANs) using services_tenant.yml
svc_tnt.tnt.tenant_name: Ensures all tenants have a name, are no restictions of what is in it
svc_tnt.tnt.l3_tenant: Ensures answer is boolean
svc_tnt.tnt.vlans: Ensures vlans are defined, must be at least one
svc_tnt.tnt.vlans.num: Ensures all VLANs are numbers and not conflicting
svc_tnt.tnt.vlans.name: Ensures all VLANs have a name, are no restrictions of what it is
svc_tnt.tnt.vlans.create_on_border: Ensures answer is boolean
svc_tnt.tnt.vlans.create_on_leaf: Ensures answer is boolean
svc_tnt.tnt.vlans.ipv4_bgp_redist: Ensures answer is boolean
svc_tnt.tnt.vlans.ip_addr: Ensures that the IP address is of the correct format
svc_tnt.tnt.vlans.num: Ensures all the VLAN numbers are unique, no duplicates
svc_tnt.adv.bse_vni): Ensures all values are integers
svc_tnt.adv.bgp.ipv4_redist_rm_name: Ensures that it contains both 'vrf' and 'as'

"""

import re
import ipaddress


class FilterModule(object):
    def filters(self):
        return {
            'input_bse_validate': self.base,
            'input_fbc_validate': self.fabric,
            'input_svc_tnt_validate': self.svc_tnt,
            'input_svc_intf_validate': self.svc_intf
        }

############  Validate formatting of variables within the base.yml file ############
    def base(self, device_name, addr, users):
        base_errors = ['Check the contents of base.yml for the following issues:']

        # DEVICE_NAME (bse.device_name): Ensures that the device names used match the correct format as is used to create group names
        for dvc, name in device_name.items():
            try:
                assert re.search('-[a-zA-Z0-9_]+$', name), "-bse.device_name.{} format ({}) is not correct. Anything after " \
                     "the last '-' is used for the group name so must be letters, digits or underscore".format(dvc, name)
            except AssertionError as e:
                base_errors.append(str(e))

        # ADDR (bse.addr): Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask
        for name, address in addr.items():
            try:
                ipaddress.IPv4Network(address)
            except ipaddress.AddressValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))
            except ipaddress.NetmaskValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))
            except ValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))

        # USERS (bse.users): Ensures that username is present and the password at least 25 characters to make sure is encrypted (not 100% this is correct, may need to disable)
        for user in users:
            try:
                assert user['username'] != None, "-bse.users.username one of the usernames does not have a value"
            except AssertionError as e:
                base_errors.append(str(e))
            try:
                assert re.match('^.{25,}$', user['password']), "-bse.users.password is probably not in encypted format as it is less that 25 characters long"
            except AssertionError as e:
                base_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(base_errors) == 1:
            return "'base.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return base_errors


############ Validate formatting of variables within the fabric.yml file ############
    def fabric(self, network_size, route, acast_gw_mac, bse_intf, lp, mlag, addr_incre):
        fabric_errors = ['Check the contents of fabric.yml for the following issues:']

        # 1. NETWORK_SIZE (fbc.network_size): Ensures thye are integers and the number of each type of device is within the limits and constraints
        for dev_type, net_size in network_size.items():
            try:
                assert type(net_size) == int, "-fbc.network_size.{} should be a numerical value".format(dev_type)
            except AssertionError as e:
                fabric_errors.append(str(e))

        try:
            assert re.match('[1-4]', str(network_size['num_spines'])), "-fbc.network_size.num_spines is {}, valid values are 1 to 4".format(network_size['num_spines'])
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            assert re.match('^([2468]|10)$', str(network_size['num_leafs'])), "-fbc.network_size.num_leafs is {}, valid values are 2, 4, 6, 8 and 10".format(network_size['num_leafs'])
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            assert re.match('^[024]$', str(network_size['num_borders'])), "-fbc.network_size.num_borders is {}, valid values are 0, 2 and 4".format(network_size['num_borders'])
        except AssertionError as e:
            fabric_errors.append(str(e))

        # 2. OSPF (fbc.ospf): Ensures that the OSPF process is present and area in dotted decimal format
        try:
            assert route['ospf']['pro'] != None ,"-fbc.route.ospf.pro does not have a value, this needs to be a string or integrer"
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            ipaddress.IPv4Address(route['ospf']['area'])
        except ipaddress.AddressValueError:
            fabric_errors.append("-fbc.route.ospf.area ({}) is not a valid dotted decimal area, valid values are 0.0.0.0 to 255.255.255.255".format(route['ospf']['area']))

        # 3. BGP (fbc.bgp.as_num): Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
        try:
            assert type(route['bgp']['as_num']) != None, "-fbc.route.bgp.as_num does not have a value"
        except AssertionError as e:
            fabric_errors.append(str(e))

        # 4. ACAST_GW_MAC (fbc.acast_gw_mac): Ensures the anycast virtual MAC is a valid mac address
        try:
            assert re.match(r'([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}', acast_gw_mac), \
                            "-fbc.acast_gw_mac ({}) is not a valid, can be [0-9], [a-f] or [A-F] in the format xxxx.xxxx.xxxx".format(acast_gw_mac)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # BSE_INTF (fbc.adv.bse_intf): Ensures that the interface numbers are integrars
        for name, intf in bse_intf.items():
            if '_to_' in name:
                try:
                    assert type(intf) == int, "-fbc.adv.bse_intf.{} should be a numerical value".format(name)
                except AssertionError as e:
                    fabric_errors.append(str(e))
            elif 'mlag_peer' == name:
                try:
                    assert re.match('^[0-9]{1,3}-[0-9]{1,3}$', str(intf)), "-fbc.adv.bse_intf.{} should be numerical values in the format xxx-xxx".format(name)
                except AssertionError as e:
                    fabric_errors.append(str(e))

        # LP (fbc.adv.lp): Ensures all the loopback names are unique, no duplicates
        dup_lp = []
        uniq_lp = {}
        for lp_type in lp.values():
            loopback = list(lp_type.keys())[0]
            if loopback not in uniq_lp:
                uniq_lp[loopback] = 1
            else:
                if uniq_lp[loopback] == 1:
                    dup_lp.append(loopback)
                uniq_lp[loopback] += 1
        try:
            assert len(dup_lp) == 0, "-fbc.adv.lp {} is/are duplicated, all loopbacks should be unique".format(dup_lp)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # MLAG (fbc.adv.mlag): Ensures all of MLAG paraemters are integers and VLANs within limit
        for mlag_attr, value in mlag.items():
            try:
                assert type(value) == int, "-fbc.adv.mlag.{} should be a numerical value".format(mlag_attr)
            except AssertionError as e:
                fabric_errors.append(str(e))
        try:
            assert re.match(r'^(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]),)*?(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]))$', str(mlag['peer_vlan'])), \
                            "-fbc.adv.mlag.peer_vlan ({}) is not a valid VLAN, valid values are 0 to 4096".format(mlag['peer_vlan'])
        except AssertionError as e:
            fabric_errors.append(str(e))

        # ADDR_INCRE (fbc.adv.addr_incre): Ensures all of the IP address increment values used are integers and except for mlag peering are all unique
        for incr_type, incr in addr_incre.items():
            try:
                assert type(incr) == int, "-ffbc.adv.addr_incre.{} should be a numerical value".format(incr_type)
            except AssertionError as e:
                fabric_errors.append(str(e))

        dup_incr = []
        uniq_incr = {}
        for incr_type, incr in addr_incre.items():
            if not incr_type.startswith('mlag'):
                if incr not in uniq_incr:
                    uniq_incr[incr] = 1
                else:
                    if uniq_incr[incr] == 1:
                        dup_incr.append(incr)
                    uniq_incr[incr] += 1
        try:
            assert len(dup_incr) == 0, "-fbc.adv.addr_incre {} is/are duplicated, all address increments should be unique".format(dup_incr)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(fabric_errors) == 1:
            return "'fabric.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return fabric_errors


############ Validate formatting of variables within the service_tenant.yml file ############
    def svc_tnt(self, svc_tnt, adv):
        svc_tnt_errors = ['Check the contents of services_tenant.yml for the following issues:']

        for tnt in svc_tnt:
            # TENANT_NAME (svc_tnt.tnt.tenant_name): Ensures all tenants have a name, are no restictions of what is in it
            try:
                assert tnt['tenant_name'] != None, "-svc_tnt.tnt.tenant_name, one of the tenants does not have a name"
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
            # L3_TENANT (svc_tnt.tnt.l3_tenant): Ensures answer is boolean
            try:
                assert isinstance(tnt['l3_tenant'], bool), "-svc_tnt.tnt.l3_tenant for tenant {} is not a boolean ({}), must be True or False".format(tnt['tenant_name'], tnt['l3_tenant'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

            # VLAN (svc_tnt.tnt.vlans): Ensures vlans are defined, must be at least one
            try:
                assert tnt['vlans'] != None, "-svc_tnt.tnt.vlans no VLANs in tenant {}, must be at least 1 VLAN to create the tenant ".format(tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
                return svc_tnt_errors

            # Used by duplicate VLAN check
            dup_vl = []
            uniq_vl = {}

            for vl in tnt['vlans']:
                # VLAN_NUMBER (svc_tnt.tnt.vlans.num): Ensures all VLANs are numbers and not conflicting
                try:
                    assert isinstance(vl['num'], int), "-svc_tnt.tnt.vlans.num VLAN '{}' should be a numerical value".format(vl['num'])
                except AssertionError as e:
                    svc_tnt_errors.append(str(e))

                # VLAN_NAME (svc_tnt.tnt.vlans.name): Ensures all VLANs have a name, are no restrictions of what it is
                try:
                    assert vl['name'] != None, "-svc_tnt.tnt.vlans.name VLAN{} does not have a name".format(vl['num'])
                except AssertionError as e:
                    svc_tnt_errors.append(str(e))

                # Create dummy default values if these settings arent set in the variable file
                vl.setdefault('create_on_border', False)
                vl.setdefault('create_on_leaf', True)
                vl.setdefault('ipv4_bgp_redist', True)
                vl.setdefault('ip_addr', '169.254.255.254/16')

                # CREATE_ON_BDR, CREATE_ON_LEAF, REDIST (svc_tnt.tnt.vlans): Ensures answer is boolean
                for opt in ['create_on_border', 'create_on_leaf', 'ipv4_bgp_redist']:
                    try:
                        assert isinstance(vl[opt], bool), "-svc_tnt.tnt.vlans.{} in VLAN{} is not a boolean ({}), "\
                                                      "must be True or False".format(opt, vl['num'], vl[opt])
                    except AssertionError as e:
                        svc_tnt_errors.append(str(e))

                # IP_ADDR (svc_tnt.tnt.vlans.ip_addr): Ensures that the IP address is of the correct format
                try:
                    ipaddress.IPv4Interface(vl['ip_addr']).ip
                except ipaddress.AddressValueError:
                    svc_tnt_errors.append("-svc_tnt.tnt.vlans.ip_addr ({}) is not a valid IPv4 address".format(vl['ip_addr']))

                # DUPLICATE VLANS (svc_tnt.tnt.vlans.num): Ensures all the VLAN numbers are unique, no duplicates
                if vl['num'] not in uniq_vl:
                    uniq_vl[vl['num']] = 1
                else:
                    if uniq_vl[vl['num']] == 1:
                        dup_vl.append(vl['num'])
                    uniq_vl[vl['num']] += 1
            try:
                assert len(dup_vl) == 0, "svc_tnt.tnt.vlans.num {} is/are duplicated in tenant {}, "\
                                         "all VLANs within a tenant should be unique".format(dup_vl, tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

        # BASE_VNI (svc_tnt.adv.bse_vni): Ensures all values are integers
        for opt in ['tnt_vlan', 'l3vni', 'l2vni']:
            try:
                assert isinstance(adv['bse_vni'][opt], int), "-adv.bse_vni.{} ({}) should be a numerical value".format(opt, adv['bse_vni'][opt])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

        # RM_NAME (svc_tnt.adv.bgp.ipv4_redist_rm_name): Ensures that it contains both 'vrf' and 'as'
        try:
            assert re.search(r'vrf\S*as|as\S*vrf', adv['bgp']['ipv4_redist_rm_name']), "-adv.bgp.ipv4_redist_rm_name format ({}) is not correct. " \
                                "It must contain 'vrf' and 'as' within its name".format(adv['bgp']['ipv4_redist_rm_name'])
        except AssertionError as e:
            svc_tnt_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(svc_tnt_errors) == 1:
            return "'service_tenant.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_tnt_errors


############ Validate formatting of variables within the service_interface.yml file ############
    def svc_intf(self, svc_intf, adv, hosts):
        svc_intf_errors = ['Check the contents of services_interface.yml for the following issues:']

        for homed, interfaces in svc_intf.items():
            for intf in interfaces:

                # SWITCH_NAME (svc_intf.intf.homed.switch): Ensures that it is a valid device name within inventary_hostnames and odd numbered if dual-homed
                try:
                    assert intf['switch'] in hosts, "-svc_intf.intf.homed.switch name {} is not an inventory_hostname".format(intf['switch'])
                except AssertionError as e:
                    svc_intf_errors.append(str(e))
                if homed == 'dual_homed':
                    assert intf['switch'][-2:] ==





            return svc_intf_errors
    #             # Adds homed as a dict and adds some default value dicts
    #             intf.setdefault('intf_num', None)
    #             if homed == 'single_homed':
    #                 intf['dual_homed'] = False
    #             elif homed == 'dual_homed':
    #                 intf['dual_homed'] = True
    #                 intf.setdefault('po_mode', 'active')
    #                 intf.setdefault('po_num', None)
    #             # STP dict is added based on Layer2 port type
    #             if intf['type'] == 'access':


    #             elif intf['type'] == 'stp_trunk':

    #             elif intf['type'] == 'stp_trunk_non_ba':

    #             elif intf['type'] == 'non_stp_trunk':



    # single_homed:
    #   - descr: L3 > DC1-ASAv-XFW01 eth1
    #     type: layer3
    #     tenant: RED
    #     ip_vlan: 10.255.99.1/30
    #     switch: DC1-N9K-BORDER01
    #     intf_num: 46
    #   - descr: L3 > DC1-ASAv-XFW02 eth1
    #     type: layer3
    #     tenant: RED
    #     ip_vlan: 10.255.99.5/30
    #     switch: DC1-N9K-BORDER02
    #   - descr: L3 > DC1-SRV-MON01 nic1
    #     type: layer3
    #     tenant: BLU
    #     ip_vlan: 10.100.100.21/30
    #     switch: DC1-N9K-LEAF01
    #   - descr: ACCESS > DC1-SRV-APP01 eth1
    #     type: access
    #     ip_vlan: 10
    #     switch: DC1-N9K-LEAF02
    #   - descr: UPLINK > DC1-VIOS-SW3
    #     type: stp_trunk
    #     ip_vlan: 110,120
    #     switch: DC1-N9K-LEAF01
    #   - descr: UPLINK > DC1-VIOS-SW4
    #     type: stp_trunk_non_ba
    #     ip_vlan: 90
    #     switch: DC1-N9K-LEAF01
    #   - descr: ACCESS >DC1-LTM-LB02
    #     type: non_stp_trunk
    #     ip_vlan: 30
    #     switch: DC1-N9K-LEAF02

    # dual_homed:
    #   - descr: ACCESS >DC1-SRV-APP01 eth1
    #     type: access
    #     ip_vlan: 10
    #     switch: DC1-N9K-LEAF01
    #   - descr: ACCESS >DC1-SRV-PRD01 eth1
    #     type: access
    #     ip_vlan: 20
    #     switch: DC1-N9K-LEAF01
    #     intf_num: 45
    #     po_num: 14
    #   - descr: UPLINK > DC1-VIOS-SW1
    #     type: stp_trunk
    #     ip_vlan: 110,120
    #     switch: DC1-N9K-LEAF01
    #   - descr: UPLINK > DC1-VIOS-SW2
    #     type: stp_trunk_non_ba
    #     ip_vlan: 90
    #     switch: DC1-N9K-LEAF01
    #     intf_num: 15
    #   - descr: ACCESS >DC1-LTM-LB01
    #     type: non_stp_trunk
    #     ip_vlan: 30
    #     switch: DC1-N9K-LEAF01
    #     intf_num: 25
    #   - descr: UPLINK > DC1-LTM-ESX1
    #     type: non_stp_trunk
    #     ip_vlan: 10,20,24,30,40
    #     switch: DC1-N9K-LEAF01
    #     po_num: 66
    #   - descr: UPLINK > DC1-VIOS-DMZ01
    #     type: stp_trunk_non_ba
    #     ip_vlan: 110,120
    #     switch: DC1-N9K-BORDER01


# valid IP
# Thta host is odd number host
# that the int raneg adn po range the same number of avaiable interfaces (difference)
# That the int range is not less than the number of interfaces
# Are vlans or tenants alreadyt on a switch
# What happens if dont ahve any config in services_interfaces?
# Cant be a space between vlans in trunk ports as will casue it to fail
# if no single or dual homed interfaces the header is hashed out
# Layer 3 can never be dual homed
# add check for base max_intf
