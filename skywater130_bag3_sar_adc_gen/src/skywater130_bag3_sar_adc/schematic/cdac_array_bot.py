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
class skywater130_bag3_sar_adc__cdac_array_bot(Module):
    """Module for library skywater130_bag3_sar_adc cell cdac_array_bot.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'cdac_array_bot.yaml')))

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
            cm_sw='parameter of cm switch',
            cm_unit_params='Unit common-mode capacitor',
            sw_params_list='multiplier list of sw unit',
            unit_params_list='Parameters of unit capacitor + drv',
            bot_probe='True to export cap unit bottom plate',
            cm='Number of common-mode cap',
            sw_m_list='Number of switches',
            cap_m_list='Number of capacitor',
            remove_cap='True to remove capacitor, use it when doesnt have rmetal',
            has_cm_sw='has the common mode switch',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            bot_probe=True,
            remove_cap=False,
            has_cm_sw = True
        )

    def design(self, cm: int, cm_sw: Param, cm_unit_params: Param, sw_params_list: List[Param],
               unit_params_list: List[Param], sw_m_list: List[int], cap_m_list: List[int],
               bot_probe: bool, remove_cap: bool, has_cm_sw:bool) -> None:
        remove_cap = self.params['remove_cap']
        nbits = len(unit_params_list)
        # check length of switch params and cap params list:
        if nbits != len(sw_params_list):
            raise ValueError("[CDAC Array Schematic]: switch and cap params length don't match")
        cap_term_list = []
        sw_term_list = []

        # Remove pins first to avoid bus and scalar name conflict
        self.rename_pin('vref', 'vref<2:0>')
        for pname in ['ctrl_n', 'ctrl_p', 'ctrl_m', 'bot']:
            self.rename_pin(pname, f"{pname}<{nbits - 1}:0>")

        # List inst name and term connection
        for idx, (sw_m, cap_m) in enumerate(zip(sw_m_list, cap_m_list)):
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('vref<2:0>', 'vref<2:0>'),
                     ('out', f"bot<{idx}>"), ('ctrl<2:0>', f"ctrl_n<{idx}>,ctrl_m<{idx}>,ctrl_p<{idx}>")]
            _cap_name = f'XCAP{idx}<{cap_m-1}:0>' if cap_m > 1 else f'XCAP{idx}'
            _sw_name = f'XDRV{idx}<{sw_m-1}:0>' if sw_m > 1 else f'XDRV{idx}'
            cap_term_list.append((_cap_name, [('top', 'top'), ('bot', f'bot<{idx}>')]))
            sw_term_list.append((_sw_name, _term))

        # Design sar_sch array
        dx_max = 2*max(self.instances['XCAP'].width, self.instances['XDRV'].width)
        self.array_instance('XCAP', inst_term_list=cap_term_list, dx=dx_max)
        self.array_instance('XDRV', inst_term_list=sw_term_list, dx=dx_max)
        for idx, (name, _) in enumerate(cap_term_list):
            self.instances[name].design(**unit_params_list[idx])
            if remove_cap:
                self.remove_instance(name)
        for idx, (name, _) in enumerate(sw_term_list):
            self.instances[name].design(**sw_params_list[idx])

        # Design cm cap
        cm_name = f"<XCAP_CM{cm - 1}:0>" if cm > 1 else f"XCAP_CM"
        self.instances['XCAP_CM'].design(**cm_unit_params)
        if cm > 1:
            self.rename_instance('XCAP_CM', f'XCM{cm-1:0}')
            self.reconnect_instance_terminal(cm_name, 'bot', 'vref<1>')
            self.reconnect_instance_terminal(cm_name, 'top', 'top')
            if remove_cap:
                self.remove_instance(f'XCM{cm-1:0}')
        elif remove_cap:
            self.remove_instance('XCAP_CM')
        else:
            self.reconnect_instance_terminal(cm_name, 'bot', 'vref<1>')
            self.reconnect_instance_terminal(cm_name, 'top', 'top')

        # Design cm sw
        if has_cm_sw:
            self.rename_pin('ctrl_s', 'sam')
            self.reconnect_instance_terminal('XSW_CM', 'S', 'vref<1>')
            self.reconnect_instance_terminal('XSW_CM', 'G', 'sam')
            self.instances['XSW_CM'].design(**cm_sw)
        else:
            self.remove_instance('XSW_CM')
