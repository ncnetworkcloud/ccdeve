#!/usr/bin/env python

"""
Author: Nick Russo (njrusmc.net@gmail.com)
Purpose: Define OSPF-related tests.
"""

import logging
from pyats import aetest

class OSPFTestcase(aetest.Testcase):
    @aetest.setup
    def setup(self, testbed):
        """Perform setup for OSPF testing"""

        # Store the testbed object and an empty data dict for OSPF data
        self.testbed = testbed
        self.data = {}

        # Store the logger and set logging level to augment aetest logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Loop over devices and learn OSPF data from each
        for name, device in testbed.devices.items():
            self.logger.info(name)
            learned = device.learn("ospf").to_dict()
            ospf = learned["info"]["vrf"]["default"]["address_family"]["ipv4"]

            # Ensure there is exactly one OSPF PID and that the value is 1
            # This is placed in setup; test cases cannot continue otherwise
            assert len(ospf["instance"]) == 1
            inst1 = ospf["instance"].get("1")
            assert isinstance(inst1, dict)
            self.data[name] = inst1

        # Sanity check; ensure new dict contains proper number of devices
        assert len(self.data) == len(testbed.devices)

    @aetest.test
    def check_unique_rid(self):
        """Ensure each router has a unique RID in the range of 10.0.0.x"""

        rid_list = []
        for name, ospf in self.data.items():
            self.logger.info(name)
            rid = ospf.get("router_id")
            assert rid.startswith("10.0.0.")
            rid_list.append(rid)

        # Length of list and length of set must match (no duplicates)
        assert len(rid_list) == len(set(rid_list))

    @aetest.test
    def check_areas(self):
        """Ensure there is exactly one OSPF area with value of 0.0.0.0"""

        for name, ospf in self.data.items():
            self.logger.info(name)
            assert len(ospf["areas"]) == 1
            area0 = ospf["areas"].get("0.0.0.0")
            assert isinstance(area0, dict)

    @aetest.test
    def check_interfaces(self):
        """Ensure each non-Loopback interface is P2P with cost of 10"""

        for name, ospf in self.data.items():
            self.logger.info(name)
            area0 = ospf["areas"]["0.0.0.0"]
            for intf, attrs in area0["interfaces"].items():
                if not intf.startswith("Loopback"):
                    self.logger.info(intf)
                    assert attrs["cost"] == 10
                    assert attrs["interface_type"] == "point-to-point"

    @aetest.test
    def check_neighbors_state(self):
        """Ensure each non-Loopback interface has exactly 1 FULL neighbor"""

        for name, ospf in self.data.items():
            self.logger.info(name)
            area0 = ospf["areas"]["0.0.0.0"]
            for intf, attrs in area0["interfaces"].items():
                if not intf.startswith("Loopback"):
                    self.logger.info(intf)
                    assert len(attrs["neighbors"]) == 1
                    nbrs = list(attrs["neighbors"].values())
                    assert nbrs[0]["state"] == "full"

    @aetest.test
    def check_neighbors_count_nonspines(self):
        """Ensure each leaf/RR has a neighbor count equal to spine count"""

        # Use a dict comprehension to select non-spines ("leaf" or "rr")
        nonspines = {
            name: ospf
            for name, ospf in self.data.items()
            if self.testbed.devices[name].type != "spine"
        }
        self._count_neighbors(nonspines)

    @aetest.test
    def check_neighbors_count_spines(self):
        """Ensure each spine has a neighbor count equal to leaf/RR count"""

        # Use a dict comprehension to select spines
        spines = {
            name: ospf
            for name, ospf in self.data.items()
            if self.testbed.devices[name].type == "spine"
        }
        self._count_neighbors(spines)

    def _count_neighbors(self, subdict):
        """Helper function to generalize neighbor counting process"""

        # Iterate over devices in the subdict
        for name, ospf in subdict.items():
            area0 = ospf["areas"]["0.0.0.0"]

            # Count neighbors on all interfaces
            num_nbrs = 0
            for intf, attrs in area0["interfaces"].items():
                if not intf.startswith("Loopback"):
                    num_nbrs += len(attrs["neighbors"])

            # Number of uncaptured devices is the difference from the whole set
            self.logger.info("%s: %s", name, num_nbrs)
            num_desired = len(self.testbed.devices) - len(subdict)
            assert num_desired == num_nbrs

    @aetest.cleanup
    def cleanup(self):
        """Cleanup after OSPF testing"""
        del self.data
