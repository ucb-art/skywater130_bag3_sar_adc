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
from pybag.enum import TermType


class skywater130_bag3_sar_adc__vco_slice_se(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_slice_se.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_slice_se.yaml')))

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
            ro_params='Ring oscillator plus saff and decoder',
            cnter_params='Cnter plus saff and decoder',
        )

    def design(self, ro_params: Param, cnter_params: Param) -> None:
        vco_term_list, cnter_term_list = [], []
        self.instances['XVCO'].design(**ro_params)
        self.instances['XCNT'].design(**cnter_params)
        for pin in self.instances['XVCO'].master.pins.keys():
            if 'bit' not in pin and 'phi_out' not in pin:
                vco_term_list.append((pin, pin))
            elif 'phi_out' in pin:
                vco_term_list.append((pin, 'phi'))
            else:
                vco_term_list.append((pin, pin.replace('bit', 'lsb')))
                self.rename_pin('lsb', pin.replace('bit', 'lsb'))

        for pin in self.instances['XCNT'].master.pins.keys():
            if 'out' not in pin:
                cnter_term_list.append((pin, pin))
            else:
                cnter_term_list.append((pin, pin.replace('out', 'msb')))
                self.rename_pin('msb', pin.replace('out', 'msb'))

        self.reconnect_instance('XVCO', vco_term_list)
        self.reconnect_instance('XCNT', cnter_term_list)
        if 'vctrl_p' not in self.instances['XVCO'].master.pins.keys():
            self.remove_pin('vctrl_p')
        if 'vctrl_n' not in self.instances['XVCO'].master.pins.keys():
            self.remove_pin('vctrl_n')
        if 'vbot' in  self.instances['XVCO'].master.pins.keys():
            self.add_pin('vbot', TermType.inout)
        if 'vtop' in  self.instances['XVCO'].master.pins.keys():
            self.add_pin('vtop', TermType.inout)
