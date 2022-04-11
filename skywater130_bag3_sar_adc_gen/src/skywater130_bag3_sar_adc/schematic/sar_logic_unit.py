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
import copy
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_logic_unit(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_logic_unit.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_logic_unit.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            oai='Parameters for oai gate',
            oai_fb='Parameters for oai output middle inv',
            buf='Parameters for output buffers template',
            buf_seg='Segment for buffer',
            buf_ratio='BUffer chain ratio',
            nand='Parameters for nand gate',
            latch='Parameters for retimer latch',
            ret_inv='Parameters for retiemr inv',
        )
    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            buf_ratio=2
        )

    def design(self, oai: Param, oai_fb: Param, buf: Param, nand: Param,
               latch: Param, ret_inv: Param, buf_seg: int, buf_ratio: int) -> None:

        for gate_type in ['N', 'P']:
            self.instances[f"XOAI_{gate_type}"].design(**oai)
            self.instances[f"XINV_{gate_type}_MID"].design(**oai_fb)

        buf_params = buf.to_dict()
        buf_m = copy.deepcopy(buf_params)
        buf_m.update(seg=buf_seg)
        buf_out = copy.deepcopy(buf_params)
        buf_out.update(seg=buf_ratio*buf_seg)
        buf_chain = dict(
            dual_output=False,
            inv_params=[
                buf_m,
                # buf_out
            ]
        )

        self.instances['XBUF_M'].design(**buf_out)
        self.instances['XBUF_P'].design(**buf_chain)
        self.instances['XBUF_N'].design(**buf_chain)
        self.instances['XNAND'].design(**nand)
        self.instances['XINV_STATE'].design(**ret_inv)
        self.instances['XL_RET'].design(**latch)
