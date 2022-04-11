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
import copy
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_logic_ret_array(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_logic_ret_array.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_logic_ret_array.yaml')))

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
            nbits='Number of bits in SAR',
            buf_list='List of buffer segments',
            buf_clk='Parameters for clk buffer (for retimer)',
            buf_out='Parameters for clk buffer (for output)',
            logic='Parameters for sar logic unit',
            ret='Parameters for retimer unit',
        )

    def design(self, nbits: int, buf_list: List[int], buf_clk: Param, buf_out: Param, logic: Param, ret: Param) -> None:
        # Rename pins
        for pname in ['dm', 'dn', 'dp', 'state', 'data_out']:
            self.rename_pin(pname, f"{pname}<{nbits-1}:0>")

        # Design instances
        self.instances['XLOGIC'].design(**logic)
        self.instances['XBUF_CLK'].design(**buf_clk)
        self.instances['XBUF_OUT'].design(**buf_out)
        self.instances["XRET"].design(**ret)

        # Array logic units
        logic_term_list = []
        for idx, m in enumerate(buf_list):
            _name = f'XLOGIC{idx}'
            _term = [('state', f"state<{idx}>"), ('dm', f'dm<{idx}>'),
                          ('dp', f'dp<{idx}>'), ('dn', f'dn<{idx}>'),
                          ('out_ret', f"out_ret<{idx}>")]
            logic_term_list.append((_name, _term))

        self.array_instance('XLOGIC', inst_term_list=logic_term_list, dx=2*self.instances['XLOGIC'].width)

        logic_unit_params = logic.to_dict()
        for idx in range(nbits):
            _params = copy.deepcopy(logic_unit_params)
            _params.update(buf_seg=buf_list[idx])
            self.instances[f'XLOGIC{idx}'].design(**_params)

        # Array retimer units
        retimer_conn = [('in', f"out_ret<{nbits-1}:0>"), ('out', f"data_out<{nbits-1}:0>")]
        self.rename_instance('XRET', f"XRET<{nbits-1}:0>", retimer_conn)

