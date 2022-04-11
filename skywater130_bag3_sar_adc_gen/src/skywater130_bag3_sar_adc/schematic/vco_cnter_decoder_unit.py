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
class skywater130_bag3_sar_adc__vco_cnter_decoder_unit(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_cnter_decoder_unit.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_cnter_decoder_unit.yaml')))

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
            first_dec='Is first decoder',
        )

    def design(self, mux_params: Param, xor_params: Param, nand_params0: Param, nand_params1: Param,
               selbuf_params: Param, buf_params: Param, first_dec: bool) -> None:
        for mux in ['XMUX0', 'XMUX1']:
            self.instances[mux].design(**mux_params)
        for xor in ['XOR0', 'XOR1', 'XOR2']:
            self.instances[xor].design(**xor_params)
        for buf in ['XBUF_MUX0', 'XBUF_MUX1', 'XBUF_NAND0', 'XBUF_NAND1', 'XBUF_D0']:
            self.instances[buf].design(**buf_params)

        self.instances['XBUF_SEL'].design(**selbuf_params)
        if first_dec:
            self.replace_instance_master('XNAND0', lib_name='bag3_digital', cell_name='nor', keep_connections=True)
        self.instances['XNAND0'].design(**nand_params0)
        self.instances['XNAND1'].design(**nand_params1)
