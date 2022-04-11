# BSD 3-Clause License
#
# Copyright (c) 2018, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# -*- coding: utf-8 -*-

from typing import Dict, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__ra_fb_nocla(Module):
    """Module for library skywater130_bag3_sar_adc cell ra_fb_nocla.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ra_fb_nocla.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            ra_params='',
            sw_fb_params='',
            sw_mid_params='',
            sw_out_params='',
            sw_cm_params='',
            # cap_az_params='',
            # cap_sam_params='',
            cap_cm_sense_params='',
            cap_cm_fb_params='',
            dc_cmfb_params='',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(dc_cmfb_params=None)

    def design(self, ra_params, sw_fb_params, sw_out_params, sw_mid_params, sw_cm_params,
               cap_cm_fb_params, cap_cm_sense_params, dc_cmfb_params) -> None:
        self.instances['XSW_FB_N'].design(**sw_fb_params)
        self.instances['XSW_FB_P'].design(**sw_fb_params)
        self.instances['XSW_MID'].design(**sw_mid_params)
        self.instances['XSW_OUT'].design(**sw_out_params)
        self.instances['XSW_CM'].design(**sw_cm_params)

        self.instances['XRA_N'].design(**ra_params)
        self.instances['XRA_P'].design(**ra_params)

        # self.instances['XCAP_SAM_N'].design(**cap_sam_params)
        # self.instances['XCAP_SAM_P'].design(**cap_sam_params)
        self.instances['XCAP_SS_N'].design(**cap_cm_sense_params)
        self.instances['XCAP_SS_P'].design(**cap_cm_sense_params)
        self.instances['XCAP_FB_N'].design(**cap_cm_fb_params)
        self.instances['XCAP_FB_P'].design(**cap_cm_fb_params)

        # self.instances['XCAP_AZ_N'].design(**cap_az_params)
        # self.instances['XCAP_AZ_P'].design(**cap_az_params)

        # self.reconnect_instance('XCAP_N', [('top', 'fb_in_n'), ('bot', 'fb_cap_n')])
        # self.reconnect_instance('XCAP_P', [('top', 'fb_in_p'), ('bot', 'fb_cap_p')])

        # self.reconnect_instance('XCAP_SAM_N', [('top', 'sw_mid_out_n'), ('bot', 'sw_out_in_n')])
        # self.reconnect_instance('XCAP_SAM_P', [('top', 'sw_mid_out_p'), ('bot', 'sw_out_in_p')])

        if dc_cmfb_params:
            self.instances['XCMFB_DC'].design(**dc_cmfb_params)
        else:
            self.remove_instance('XCMFB_DC')

