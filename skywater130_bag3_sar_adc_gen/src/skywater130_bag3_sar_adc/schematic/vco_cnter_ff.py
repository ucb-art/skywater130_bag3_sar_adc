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
class skywater130_bag3_sar_adc__vco_cnter_ff(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_cnter_ff.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_cnter_ff.yaml')))

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
            ff_params='Parameter of flops',
            cnter_params='Cnter parameters',
            buf_params_list='Buffer parameters list',
            dec_params='Decoder parameters'
        )

    def design(self, ff_params, cnter_params, buf_params_list, dec_params) -> None:
        nbit = 2**cnter_params['nbits']*cnter_params['ndivs']
        nbuf = len(buf_params_list)
        self.instances['XCNTER'].design(**cnter_params)
        if nbuf > 2:
            buf_in_term = f'phi,phi_d<{nbuf - 1}:0>'
        elif nbuf == 2:
            buf_in_term = f'phi,phi_d<0>'
        else:
            buf_in_term = 'phi'
        buf_name_list, conn_list = [], []
        for idx in range(nbuf):
            buf_name_list.append(f'XBUF<{idx}>')
            buf_in_term = 'phi' if not idx else f'phi_d<{idx-1}>'
            conn_list.append({'in': buf_in_term, 'out': f'phi_d<{idx}>',
                              'outb': f'phi_dn<{idx}>', 'VDD': 'VDD', 'VSS': 'VSS'})
        self.array_instance('XBUF', buf_name_list, conn_list)
        self.rename_instance('XCNTER', 'XCNTER0', [('clkn', f'phi_dn<{nbuf - 1}>'), ('clkp', f'phi_d<{nbuf - 1}>'),
                                                   (f'outp<{nbit-1}:0>', f'cnter_outp<{nbit-1}:0>'),
                                                   (f'outn<{nbit-1}:0>', f'cnter_outn<{nbit-1}:0>'),
                                                   ('VDD', 'VDD'), ('VSS', 'VSS')])
        saff_outp = ','.join([f'bit<{idx}>,bit_d<{idx}>' for idx in range(nbit//2-1, -1, -1)])
        saff_outn = ','.join([f'bit_n<{idx}>,bit_dn<{idx}>' for idx in range(nbit//2-1, -1, -1)])
        self.rename_instance('XFF', f'XFF<{nbit-1}:0>', [('clkb', 'clkb'), ('clk', 'clk'),
                                                                ('inp', f'cnter_outp<{nbit-1}:0>'),
                                                                ('inn', f'cnter_outn<{nbit-1}:0>'),
                                                                ('outp', saff_outp), ('outn', saff_outn),
                                                                ('VDD', 'VDD'), ('VSS', 'VSS')])
        for idx in range(nbuf):
            self.instances[f'XBUF<{idx}>'].design(**buf_params_list[idx])
        in_buf_term = 'in_buf' if nbuf == 1 else f'in_buf<{nbuf - 1}:0>'
        in_buf_n_term = 'in_buf_n' if nbuf == 1 else f'in_buf_n<{nbuf - 1}:0>'
        self.rename_instance('XFF_BUF', f'XFF_BUF<{nbuf - 1}:0>',
        [('clkb', 'clkb'), ('clk', 'clk'), ('inp', f'phi_d<{nbuf - 1}:0>'), ('inn', f'phi_dn<{nbuf - 1}:0>'),
         ('outp', in_buf_term), ('outn', in_buf_n_term), ('VDD', 'VDD'), ('VSS', 'VSS')])

        self.instances['XDEC'].design(**dec_params)
        in_term = ','.join([f'bit<{idx}>,bit_d<{idx}>' for idx in reversed((range(nbit//2)))]) + ',' + \
                  in_buf_term + ',phi_sampled'
        self.reconnect_instance('XDEC', (('VDD', 'VDD'), ('VSS', 'VSS'),
                                         (f'out<{nbit // 2-1}:0>', f'out<{nbit // 2-1}:0>'),
                                         (f'in<{nbit+2}:0>', in_term)))

        self.instances[f'XFF<{nbit-1}:0>'].design(**ff_params)
        self.instances[f'XFF_BUF<{nbuf - 1}:0>'].design(**ff_params)
        self.rename_pin('out', f'out<{nbit // 2-1}:0>')
        self.rename_pin('in_buf_n', in_buf_n_term)
        self.rename_pin('bit_n', f'bit_n<{nbit // 2-1}:0>')
        self.rename_pin('bit_dn', f'bit_dn<{nbit // 2-1}:0>')
