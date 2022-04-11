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
class skywater130_bag3_sar_adc__ra(Module):
    """Module for library skywater130_bag3_sar_adc cell ra.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ra.yaml')))

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
            cap_fb_params='',
            cap_gain_params='',
            cap_sam_params='',
            sw_out_params='',
            cmfb_params='',
            pbias_params='',
            nbias_params='',
            nbits=','
        )

    def design(self, ra_params, cap_fb_params, cap_sam_params, sw_out_params, cmfb_params, pbias_params,
               cap_gain_params, nbias_params, nbits) -> None:
        self.instances['XBIASN'].design(**nbias_params)
        self.instances['XBIASP'].design(**pbias_params)
        self.instances['XCORE'].design(**ra_params)
        self.instances['XCAP_FB_N'].design(**cap_fb_params)
        self.instances['XCAP_FB_P'].design(**cap_fb_params)
        self.instances['XCAP_GAIN_N'].design(**cap_gain_params)
        self.instances['XCAP_GAIN_P'].design(**cap_gain_params)
        self.instances['XCAP_SAM_N'].design(**cap_sam_params)
        self.instances['XCAP_SAM_P'].design(**cap_sam_params)
        self.instances['XSW_OUT'].design(**sw_out_params)
        self.instances['XCMFB'].design(**cmfb_params)
        self.reconnect_instance_terminal('XBIASN', f'in<{nbits-1}:0>', f'ctrl_biasn<{nbits-1}:0>')
        self.reconnect_instance_terminal('XBIASP', f'in<{nbits-1}:0>', f'ctrl_biasp<{nbits-1}:0>')

        self.rename_pin('ctrl_biasp', f'ctrl_biasp<{nbits-1}:0>')
        self.rename_pin('ctrl_biasn', f'ctrl_biasn<{nbits-1}:0>')

        fb_cap_term_list = []
        for pin in self.instances['XCAP_FB_N'].master.pins.keys():
            if 'bit' in pin:
                fb_cap_term_list.append((pin, pin.replace('bit', 'ctrl_fb_cap')))
                self.rename_pin('ctrl_fb_cap', pin.replace('bit', 'ctrl_fb_cap'))
        self.reconnect_instance('XCAP_FB_N', fb_cap_term_list)
        self.reconnect_instance('XCAP_FB_P', fb_cap_term_list)

        gain_cap_term_list = []
        for pin in self.instances['XCAP_GAIN_N'].master.pins.keys():
            if 'bit' in pin:
                gain_cap_term_list.append((pin, pin.replace('bit', 'ctrl_cdac_gain')))
                self.rename_pin('ctrl_cdac_gain', pin.replace('bit', 'ctrl_cdac_gain'))
        self.reconnect_instance('XCAP_GAIN_N', gain_cap_term_list)
        self.reconnect_instance('XCAP_GAIN_P', gain_cap_term_list)

        self.reconnect_instance('XCAP_SAM_N', [('top', 'ra_out_n'), ('bot', 'sam_n')])
        self.reconnect_instance('XCAP_SAM_P', [('top', 'ra_out_p'), ('bot', 'sam_p')])


