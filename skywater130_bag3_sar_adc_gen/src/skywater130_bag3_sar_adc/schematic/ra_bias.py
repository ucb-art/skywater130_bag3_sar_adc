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
class skywater130_bag3_sar_adc__ra_bias(Module):
    """Module for library skywater130_bag3_sar_adc cell ra_bias.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ra_bias.yaml')))

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
            logic_params_list='logic array schematic',
            cap_params_list='cap array schmatic',
            cap_m_list='m mult list',
        )

    def design(self, logic_params_list, cap_params_list, cap_m_list) -> None:
        # List inst name and term connection
        cap_term_list, logic_term_list = [], []
        for idx, cap_m in enumerate(cap_m_list):
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('en', 'en'),
                     ('out', f'cap<{idx}>'), ('in', f'in<{idx}>')]
            _cap_name = f'XC_DAC{idx}<{cap_m-1}:0>' if cap_m > 1 else f'XCAP{idx}'
            cap_term_list.append((_cap_name, [('plus', 'bias'), ('minus', f'cap<{idx}>')]))
            logic_term_list.append((f'XLOGIC{idx}', _term))

        # Design sar_sch array
        # self.instances['XC_CM'].design(**cap_params_list[0])
        self.remove_instance('XC_CM')
        dx_max = 2*max(self.instances['XC_DAC'].width, self.instances['XLOGIC'].width)
        self.array_instance('XC_DAC', inst_term_list=cap_term_list, dx=dx_max)
        self.array_instance('XLOGIC', inst_term_list=logic_term_list, dx=dx_max)
        for idx, (name, _) in enumerate(cap_term_list):
            self.instances[name].design(**cap_params_list[idx])
        for idx, (name, _) in enumerate(logic_term_list):
            self.instances[name].design(**logic_params_list[idx])

        self.rename_pin('in', f'in<{len(cap_m_list)-1}:0>')

