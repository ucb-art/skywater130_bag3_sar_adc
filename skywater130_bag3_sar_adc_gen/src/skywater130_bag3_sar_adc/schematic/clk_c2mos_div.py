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

import pkg_resources
from pathlib import Path
from typing import Mapping, Any, List

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param
# noinspection PyPep8Naming
from bag3_liberty.enum import TermType


class skywater130_bag3_sar_adc__clk_c2mos_div(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_c2mos_div.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_c2mos_div.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Mapping[str, str]
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            latch_params_list='unit inverter parameters',
            buf_params='Buffer parameters',
            num_stages='number of stage in RO',
            close_loop=''
        )

    @classmethod
    def get_default_param_values(cls) -> Mapping[str, Any]:
        return dict(
            close_loop=True,
            # inv_params=None
        )

    def design(self, latch_params_list, buf_params, num_stages, close_loop):
        if not isinstance(latch_params_list, List):
            latch_params_list = [latch_params_list] * num_stages
        name_list = [f'XLATCH<{idx}>' for idx in range(num_stages)] if num_stages > 1 else 'XL'
        clkp_name = ['clkp', 'clkn'] * (num_stages // 2)
        clkn_name = ['clkn', 'clkp'] * (num_stages // 2)

        out_name = [f'midp<{idx}>' for idx in range(num_stages)]
        out_b_name = [f'midn<{idx}>' for idx in range(num_stages)]

        if close_loop:
            inp_name_shift = [f'midn<{num_stages - 1}>'] + [f'midp<{idx}>' for idx in range(num_stages - 1)]
            inn_name_shift = [f'midp<{num_stages - 1}>'] + [f'midn<{idx}>' for idx in range(num_stages - 1)]
            self.remove_pin('inn')
            self.remove_pin('inp')
        else:
            inp_name_shift = ['inp'] + [f'midp<{idx}>' for idx in range(num_stages - 1)]
            inn_name_shift = ['inn'] + [f'midn<{idx}>' for idx in range(num_stages - 1)]
        term_list = [{'outp': out_name[idx], 'outn': out_b_name[idx],
                      'dn': inn_name_shift[idx], 'd': inp_name_shift[idx],
                      'clkn': clkn_name[idx], 'clkp': clkp_name[idx]} for idx in range(num_stages)]

        self.array_instance('XLATCH', name_list, term_list, dx=2 * self.instances['XLATCH'].width)

        for idx in range(num_stages):
            self.instances[f'XLATCH<{idx}>'].design(**latch_params_list[idx])
        self.instances['XBUF'].design(**buf_params)
        self.rename_instance('XBUF', f'XBUF<{2 * num_stages - 1}:0>',
                             [('in', f'midn<{num_stages - 1}:0>,midp<{num_stages - 1}:0>'), ('VDD', 'VDD'),
                              ('VSS', 'VSS'),
                              ('outb', f'outn<{num_stages - 1}:0>,outp<{num_stages - 1}:0>')])

        self.rename_pin('midp', f'midp<{num_stages - 1}:0>')
        self.rename_pin('midn', f'midn<{num_stages - 1}:0>')
        self.rename_pin('outp', f'outp<{num_stages - 1}:0>')
        self.rename_pin('outn', f'outn<{num_stages - 1}:0>')
