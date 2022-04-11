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
class skywater130_bag3_sar_adc__vco_decoder(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_decoder.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_decoder.yaml')))

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
            mux_params='MUX parameters',
            xor_params='XOR parameters',
            nand_params0='nand0 parameters',
            nand_params1='nand1 parameters',
            selbuf_params='selbuffer parameters',
            buf_params='buffer parameters',
        )

    def design(self, mux_params: Param, xor_params: Param, nand_params0: Param, nand_params1: Param,
               selbuf_params: Param, buf_params: Param) -> None:
        for mux in ['XMUX0', 'XMUX1']:
            self.instances[mux].design(**mux_params)
        for xor in ['XOR0', 'XOR1', 'XOR2']:
            self.instances[xor].design(**xor_params)
        for buf in ['XBUF_MUX0', 'XBUF_MUX1', 'XBUF_NAND0', 'XBUF_NAND1', 'XBUF_D0']:
            self.instances[buf].design(**buf_params)

        self.instances['XBUF_SEL'].design(**selbuf_params)
        self.instances['XNAND0'].design(**nand_params0)
        self.instances['XNAND1'].design(**nand_params1)

