#!/usr/bin/env python

"""
Author: Nick Russo (njrusmc.net@gmail.com)
Purpose: Common setup/cleanup code for project.
"""

from pyats import aetest


class LeafSpineCommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect(self, testbed):
        """Connect to devices in testbed"""

        testbed.connect(log_stdout=False)


class LeafSpineCommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect(self, testbed):
        """Disonnect from devices in testbed"""

        testbed.disconnect(log_stdout=False)
