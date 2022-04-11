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

from typing import Dict, Any, List

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__vco_cnter_decoder(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_cnter_decoder.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_cnter_decoder.yaml')))

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
            unit_params_list='List of unit parameters',
            inv_params='Buffer parameters',
            nand_params='Nand parameters',
        )

    def design(self, unit_params_list: List[Param], inv_params: Param, nand_params: Param) -> None:
        for nand in ['XNAND0', 'XNAND1']:
            self.instances[nand].design(**nand_params)
        for buf in ['XBUF_IN1', 'XBUF_IN0', 'XBUF_OUT1', 'XBUF_OUT0']:
            self.instances[buf].design(**inv_params)

        self.instances['XDEC0'].design(**unit_params_list[0])
        dec_name_list, dec_term_list = [], []
        for idx, param in enumerate(unit_params_list[1:]):
            dec_name_list.append(f'XDEC1<{idx}>')
            dec_term_list.append({'VDD': 'VDD', 'VSS': 'VSS', 'prev_in<1:0>': f'mid{idx}<1:0>',
                                  'out<1:0>': f'out<{2*(idx+1)+1}:{2*(idx+1)}>', 'mid1': f'mid{idx+1}<0>',
                                  'mux1': f'mid{idx+1}<1>', 'in<3:0>': f'in<{4*(idx+2)+2}:{4*(idx+2)-1}>',
                                  'sel': f'mid{idx}<1>'})
        self.array_instance('XDEC1', dec_name_list, dec_term_list, dx=int(1.5*self.instances['XDEC1'].width))
        for idx, param in enumerate(unit_params_list[1:]):
            self.instances[f'XDEC1<{idx}>'].design(**param)

        self.rename_pin('out<1:0>', f'out<{2*len(unit_params_list)-1}:0>')
        self.rename_pin('in<1:0>', f'in<{4*len(unit_params_list)+2}:0>')

