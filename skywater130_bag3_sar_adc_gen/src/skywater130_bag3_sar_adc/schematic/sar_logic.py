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
class skywater130_bag3_sar_adc__sar_logic(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_logic.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_logic.yaml')))

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
            fsm='Parameters for FSM',
            clkgen='Parameters for clkgen',
            sar_logic='Parameters for sar logic and retimer',
            en_fast_bit='Enable fast mode after this bit',
        )

    def design(self, en_fast_bit: int, nbits: int, fsm: Param, sar_logic: Param, clkgen: Param) -> None:
        for pname in ['dm', 'dn', 'dp', 'data_out']:
            self.rename_pin(pname, f"{pname}<{nbits - 1}:0>")

        self.instances['XFSM'].design(**fsm)
        self.reconnect_instance_terminal('XFSM', f"state<{nbits - 1}:0>", f"state<{nbits - 1}:0>")

        logic_conn = [(f"state<{nbits - 1}:0>", f"state<{nbits - 1}:0>"),
                      (f"data_out<{nbits - 1}:0>", f"data_out<{nbits - 1}:0>"),
                      (f"dm<{nbits - 1}:0>", f"dm<{nbits - 1}:0>"),
                      (f"dn<{nbits - 1}:0>", f"dn<{nbits - 1}:0>"),
                      (f"dp<{nbits - 1}:0>", f"dp<{nbits - 1}:0>"),]
        self.instances['XLOGIC'].design(**sar_logic)
        self.rename_instance('XLOGIC', 'XLOGIC0', logic_conn)

        self.instances['XCLKGEN'].design(**clkgen)
        self.reconnect_instance_terminal('XCLKGEN', 'clk_fast_en_b', f'dm<{en_fast_bit}>')
