# SPDX-License-Identifier: Apache-2.0
# Copyright 2020 Blue Cheetah Analog Design Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-

from typing import Dict, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_fsm(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_fsm.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_fsm.yaml')))

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
            nbits='Number of bits',
            rst_flop='Parameters for reset flop',
            state_flop='Parameters for state flop',
            inv='Parameters for trigger buffer inverter',
        )

    def design(self, nbits: int, inv: Param, rst_flop: Param, state_flop: Param) -> None:

        self.rename_pin('state', f"state<{nbits-1}:0>")
        self.instances['XF_RST'].design(**rst_flop)
        self.instances['XINV'].design(**inv)

        # Make state flops array
        inst_term_list = []
        for idx in range(nbits):
            _in = f"state_b<{nbits-idx}>" if idx else 'trig_b'
            _name = f"XF_STATE<{idx}>"
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('clk', 'clk'),
                     ('in', _in), ('outb', f"state<{nbits-idx-1}>"), ('out', f"state_b<{nbits-idx-1}>")]
            inst_term_list.append((_name, _term))

        state_flop_params = state_flop.to_dict()
        state_flop_params.update(dual_output=True)
        self.array_instance('XF_STATE', inst_term_list=inst_term_list)
        for name, _ in inst_term_list:
            self.instances[name].design(**state_flop_params)
