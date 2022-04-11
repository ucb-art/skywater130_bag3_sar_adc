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
class skywater130_bag3_sar_adc__sar_async_clk_core_v2(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_async_clk_core_v2.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_async_clk_core_v2.yaml')))

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
            inv_fb='Parameters for clk_out inverter',
            nor_en='Nor gate for start-up',
            nand_done='Nand gate for stop',
            nand_en='Nand gate for stop',
            buf='Clock output buffer',
            lch='channel length.',
            w_p='PMOS width.',
            w_n='NMOS width.',
            th_p='PMOS threshold.',
            th_n='NMOS threshold.',
            seg_dict='Dictionary of other transistors segment',
        )

    def design(self, buf: Param, inv_fb: Param, nor_en: Param, nand_done: Param, nand_en: Param,
               lch: int, w_p: int, w_n: int, th_p: str, th_n: str, seg_dict: Dict[str, int]) -> None:
        self.instances['XINV_FB'].design(**inv_fb)
        self.instances['XBUF_OUT'].design(**buf)
        self.instances['XNOR_EN'].design(**nor_en)
        self.instances['XNAND_DONE'].design(**nand_done)
        self.instances['XNAND_EN'].design(**nand_en)

        self.instances['XN_FB'].design(w=w_n, l=lch, nf=seg_dict['fb_n'], intent=th_n)
        self.instances['XN_TAIL'].design(w=w_n, l=lch, nf=seg_dict['tail_n'], intent=th_n)
        self.instances['XN_CLK'].design(w=w_n, l=lch, nf=seg_dict['clk_n'], intent=th_n)

        self.instances['XP_FB'].design(w=w_p, l=lch, nf=seg_dict['fb_p'], intent=th_p)
        self.instances['XP_INN'].design(w=w_p, l=lch, nf=seg_dict['in_p'], intent=th_p)
        self.instances['XP_INP'].design(w=w_p, l=lch, nf=seg_dict['in_p'], intent=th_p)
        self.remove_pin('sel')

