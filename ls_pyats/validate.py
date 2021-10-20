#!/usr/bin/env python

"""
Author: Nick Russo (njrusmc.net@gmail.com)
Purpose: Demonstrate pyATS in a leaf/spine network using aetest
to validate OSPF and BGP topological information.
"""

from argparse import ArgumentParser
from pyats import aetest, topology
from test_project import common, ospf_test, bgp_test

# Setup, test cases, and cleanup must be explicitly subclassed
# so that aetest can process them; importing alone does nothing
class LocalLeafSpineCommonSetup(common.LeafSpineCommonSetup):
    pass

class LocalOSPFTestcase(ospf_test.OSPFTestcase):
    pass

class LocalBGPTestcase(bgp_test.BGPTestcase):
    pass

class LocalLeafSpineCommonCleanup(common.LeafSpineCommonCleanup):
    pass


if __name__ == "__main__":

    # Process arguments from CLI
    parser = ArgumentParser()
    parser.add_argument("-t", "--testbed", type=str, help="testbed YAML path")
    args = parser.parse_args()

    # Load topology from testbed file and execute test plan
    result = aetest.main(testbed=topology.loader.load(args.testbed))
    aetest.exit_cli_code(result)
