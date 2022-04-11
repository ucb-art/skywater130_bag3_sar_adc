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

from typing import Mapping, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__clk_local_top(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_local_top.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_local_top.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Mapping[str, str]:
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Mapping[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            sam='',
            vco='',
            amp='',
            hold='',
            delay='',
            buf=''
        )

    def design(self, sam, vco, amp, hold, delay, buf) -> None:
        self.instances['XSAM'].design(**buf)
        self.instances['XHOLD'].design(**hold)
        self.instances['XRETIMER'].design(**sam)
        self.instances['XVCO_SAM'].design(**vco)
        self.instances['XRA_AMP'].design(**amp)
        self.instances['XDELAY'].design(**delay)

        delay_term_list = []
        for pin in self.instances['XDELAY'].master.pins.keys():
            if 'in' in pin:
                delay_term_list.append((pin, pin.replace('in', 'ctrl_delay')))
                self.rename_pin('ctrl_delay', pin.replace('in', 'ctrl_delay'))
        self.reconnect_instance('XDELAY', delay_term_list)

        sam_term_list = []
        for pin in self.instances['XSAM'].master.pins.keys():
            if 'mid' in pin:
                sam_term_list.append((pin, pin.replace('mid', 'mid_sam')))
        self.reconnect_instance('XSAM', sam_term_list)

        ret_term_list = []
        for pin in self.instances['XRETIMER'].master.pins.keys():
            if 'mid' in pin:
                ret_term_list.append((pin, pin.replace('mid', 'mid_ret')))
        self.reconnect_instance('XRETIMER', ret_term_list)
        self.reconnect_instance('XHOLD', [('sam', 'mid_retp<1>')])
        self.reconnect_instance('XSAM', [('midn<5:0>', 'midn_sam<3>,sam_n,midn_sam<2:0>,sam_e_n'),
                                         ('midp<5:0>', 'midp_sam<3>,sam_p,midp_sam<2:0>,sam_e_p')])
        ret_term_list = []
        for pin in self.instances['XVCO_SAM'].master.pins.keys():
            if 'mid' in pin:
                ret_term_list.append((pin, pin.replace('mid', 'mid_vco')))
        self.reconnect_instance('XVCO_SAM', ret_term_list)




