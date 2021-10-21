#!/usr/bin/env python

"""
Author: Nick Russo (njrusmc.net@gmail.com)
Purpose: Define BGP-related tests.
"""

import logging
from pyats import aetest


class BGPTestcase(aetest.Testcase):
    @aetest.setup
    def setup(self, testbed):
        """Perform setup for BGP testing"""

        # Store the testbed object and an empty data dict for BGP data
        self.testbed = testbed
        self.data = {}
        self.orig = {}

        # Store the logger and set logging level to augment aetest logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Use a dict comprehension to select non-spines ("leaf" or "rr")
        nonspines = {
            name: device
            for name, device in self.testbed.devices.items()
            if device.type != "spine"
        }

        # Loop over devices and collect BGP summary data
        for name, device in nonspines.items():
            self.logger.info(name)

            # Retain the original "parsed" data for comparative purposes
            self.orig[name] = device.parse("show bgp ipv4 unicast summary")

            # Modify the structure; "neighbor", "local_asn", and "type" top keys
            self.data[name] = self.orig[name]["vrf"]["default"]
            self.data[name]["local_asn"] = self.orig[name]["bgp_id"]
            self.data[name]["type"] = device.type

            # Remove the unnecessary intermediate AFI/SAFI to simplify tests
            for nbr, attr in self.data[name]["neighbor"].items():
                self.data[name]["neighbor"][nbr] = attr[
                    "address_family"]["ipv4 unicast"]

            # Sanity check; ensure new subdict contains exactly 3 keys
            assert len(self.data[name]) == 3

        # Sanity check; ensure new dict contains proper number of devices
        assert len(self.data) == len(nonspines)

    @aetest.test
    def check_same_asn(self):
        """Ensure each router is in the same BGP ASN"""

        asn_set = set()
        for name, bgp in self.data.items():
            self.logger.info(name)
            asn_set.add(bgp["local_asn"])

        # Only one element in the set indicates iBGP everywhere
        assert len(asn_set) == 1

    @aetest.test
    def check_prefix_count_leaf(self):
        """Ensure each leaf learns the same number of routes from each RR"""

        for name, bgp in self.data.items():
            pfx_set = set()
            if bgp["type"] == "leaf":
                self.logger.info(name)
                for nbr, attr in bgp["neighbor"].items():
                    pfx = attr["state_pfxrcd"]
                    pfx_set.add(pfx)
                    self.logger.info("%s: %s", nbr, pfx)

                # Only one set element per device is proper RR cluster design
                assert len(pfx_set) == 1

    @aetest.test
    def check_prefix_count_rr(self):
        """Ensure the RRs learn a consistent number of routes from each leaf"""

        pfx_dict = {}
        for name, bgp in self.data.items():
            if bgp["type"] == "rr":
                self.logger.info(name)
                for nbr, attr in bgp["neighbor"].items():
                    pfx = attr["state_pfxrcd"]

                    # "nbr" key is absent on first pass; add nbr/set pair
                    if not nbr in pfx_dict:
                        pfx_dict[nbr] = set()
                    pfx_dict[nbr].add(pfx)
                    self.logger.info("%s: %s", nbr, pfx)

        # Each dict value should be a set with 1 value each
        for pfx_set in pfx_dict.values():
            assert len(pfx_set) == 1

    @aetest.test
    def check_empty_queues(self):
        """Ensure each router has no queued messages using Dq() feature"""

        # Loop over original "parsed" data (unmodified Genie output)
        for name, orig in self.orig.items():
            self.logger.info(name)

            # Query the for all input_queue values and convert to set
            inq_set = set(orig.q.get_values("input_queue"))

            # Set must have one element which is equal to 0 (no updates in InQ)
            assert len(inq_set) == 1
            assert inq_set.pop() == 0

            # Query for all output_queue values greater than 0
            outq_dq = orig.q.value_operator("output_queue", ">", 0)

            # Nothing should be returned; a positive int means updates in OutQ
            assert len(outq_dq) == 0

    @aetest.cleanup
    def cleanup(self):
        del self.data
