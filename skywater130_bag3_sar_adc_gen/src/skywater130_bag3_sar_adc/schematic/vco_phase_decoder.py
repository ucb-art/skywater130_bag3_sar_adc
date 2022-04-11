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
from typing import Dict, Any

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__vco_phase_decoder(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_phase_decoder.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_phase_decoder.yaml')))

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
            mux_params='Mux parameters',
            buf_params='Mux parameters',
            nbits='Number of bits'
        )

    def design(self, mux_params, buf_params, nbits) -> None:
        instance_width_max = max(self.instances['XBUF'].width, self.instances['XMUX'].width)
        buf_name_list, buf_term_list = [], []
        mux_name_list, mux_term_list = [], []
        self.rename_pin('in', f'in<{2 ** nbits - 1}:1>')
        self.rename_pin('out', f'bit<{nbits - 1}:0>')
        for idx in range(nbits-1):
            buf_name_list.append(f'XBUF{idx}')
            buf_in = f'bit<{nbits - 1 - idx}>' if idx else f'in<{2 ** (nbits - 1)}>'
            buf_out = f'sel{idx}' if idx else f'bit<{nbits-1}>'
            buf_outb = f'selb{idx}' if idx else f'bitb<{nbits-1}>'
            buf_term_list.append({'in': buf_in, 'out': buf_out, 'outb': buf_outb,
                                  'VDD': 'VDD', 'VSS': 'VSS'})
            nmux = 2 ** (nbits - idx - 1) - 1
            nmux_prev = 2 ** (nbits - idx) - 1
            mux_name_list.append(f'XMUX{idx}<{nmux-1}:0>')
            mux_in = ','.join([f'mid{idx-1}<{jdx}>,mid{idx-1}<{nmux_prev - nmux + jdx}>' for jdx in range(0, nmux)]) \
                if idx else ','.join([f'in<{jdx}>,in<{jdx + nmux + 1}>' for jdx in range(1, nmux+1)])
            if idx < nbits - 2 and nmux//2>1:
                mux_out = ','.join([f'mid{idx}<0:{nmux // 2-1}>']) + f',bit<{nbits - idx - 2}>,' + \
                          ','.join([f'mid{idx}<{nmux // 2 + 1}:{nmux - 1}>'])
            elif idx < nbits-2 and nmux//2<=1:
                mux_out = f'mid{idx}<0>' + f',bit<{nbits - idx - 2}>,' + f'mid{idx}<{nmux-1}>'
            else:
                mux_out = 'bit<0>'

            mux_term_list.append({'sel': buf_out, 'selb': buf_outb, 'in<1:0>': mux_in, 'out': mux_out,
                                  'VDD': 'VDD', 'VSS': 'VSS'})

        self.array_instance('XBUF', buf_name_list, buf_term_list, dx=instance_width_max)
        self.array_instance('XMUX', mux_name_list, mux_term_list, dx=instance_width_max)
        for idx in range(nbits-1):
            nmux = 2 ** (nbits - idx - 1) - 1
            self.instances[f'XBUF{idx}'].design(**buf_params)
            self.instances[f'XMUX{idx}<{nmux-1}:0>'].design(**mux_params)
