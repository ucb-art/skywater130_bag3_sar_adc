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

from typing import Dict, Any, List

import pkg_resources
from pathlib import Path

from pybag.enum import TermType

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__cdac_array(Module):
    """Module for library skywater130_bag3_sar_adc cell cdac_array.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'cdac_array.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)
        self._has_bot = False

    def export_bot(self):
        return self._has_bot

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            cm='Number of unit common-mode capacitor',
            m_list='multiplier list of cap unit',
            sw_list='multiplier list of sw unit',
            unit_params='Parameters of unit capacitor + drv',
            bot_probe='True to export cap unit bottom plate',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            cm=1,
            bot_probe=False,
            sw_list=[]
        )

    def design(self, cm: int, m_list: List[int], sw_list: List[int], unit_params: Param, bot_probe: bool) -> None:
        nbits = len(m_list)
        inst_term_list = []
        unit_params_list = []

        # Remove pins first to avoid bus and scalar name conflict
        self.rename_pin('vref', 'vref<2:0>')
        for pname in ['ctrl_n', 'ctrl_p', 'ctrl_m']:
            self.rename_pin(pname, f"{pname}<{nbits - 1}:0>")

        if bot_probe:
            self.add_pin(f"bot<{nbits-1}:0>", TermType.inout)
            self._has_bot = True

        # List inst name and term connection
        for idx, m in enumerate(m_list):
            _name = f"XB{idx}"
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('vref<2:0>', 'vref<2:0>'),
                     ('bot', f"bot<{idx}>"), ('top', 'top'),
                     ('ctrl<2:0>', f"ctrl_n<{idx}>,ctrl_m<{idx}>,ctrl_p<{idx}>")]
            inst_term_list.append((_name, _term))
            if sw_list:
                unit_params_list.append(unit_params.copy(append=dict(m=m, sw=sw_list[idx])))
            else:
                unit_params_list.append(unit_params.copy(append=dict(m=m)))

        # Design sar_sch array
        self.array_instance('XUNIT', inst_term_list=inst_term_list, dx=2*self.instances['XUNIT'].width)
        for idx, (name, _) in enumerate(inst_term_list):
            self.instances[name].design(**unit_params_list[idx])

        # Design cm cap
        cm_cap_params = unit_params['cap']
        cm_name = f"<XCM{cm - 1}:0>" if cm > 1 else f"XCM"
        self.instances['XCM'].design(**cm_cap_params)
        if cm > 1:
            self.rename_instance('XCM', f'XCM{cm-1:0}')
        self.reconnect_instance_terminal(cm_name, 'minus', 'vref<1>')

