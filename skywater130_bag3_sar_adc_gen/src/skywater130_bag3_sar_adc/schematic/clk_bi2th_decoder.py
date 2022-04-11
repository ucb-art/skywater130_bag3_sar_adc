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
from typing import Mapping, Any

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__clk_bi2th_decoder(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_bi2th_decoder.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_bi2th_decoder.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Mapping[str, str]:
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Mapping[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            inv='',
            buf='',
            nand='',
            nbits=''
        )

    def design(self, inv, buf, nand, nbits) -> None:
        self.instances['XBUF'].design(**buf)
        self.rename_instance('XBUF', f'XBUF<{nbits - 1}:0>',
                             conn_list=[('in', f'in<{nbits - 1}:0>'),
                                        ('out', f'bit_buf<{nbits - 1}:0>'),
                                        ('outb', f'bit_bufb<{nbits - 1}:0>')])
        # make nand connections
        nand_term_list, inv_term_list = [], []

        first_nand_in = 'bit_buf<1>,bit_buf<0>,bit_buf<1>,bit_bufb<0>,bit_bufb<1>,bit_buf<0>,bit_bufb<1>,bit_bufb<0>'
        first_inv_out = 'out<3:0>' if nbits == 2 else 'mid0<3:0>'
        nand_term_list.append(('XNAND0<3:0>', [('VDD', 'VDD'), ('VSS', 'VSS'), ('in<1:0>', first_nand_in),
                                               ('out', f'nand_out0<3:0>')]))
        inv_term_list.append(('XINV0<3:0>', [('VDD', 'VDD'), ('VSS', 'VSS'), ('in', f'nand_out0<3:0>'),
                                             ('out', first_inv_out)]))

        if nbits > 2:
            for idx in range(nbits - 2):
                # last bit
                num_inst = 2 ** (idx + 3)
                if idx == nbits - 3:
                    nand_in = ''
                    for jdx in range(num_inst//2):
                        nand_in += f'bit_buf<{idx+2}>,mid{idx}<{num_inst//2-jdx-1}>,'
                    for jdx in range(num_inst//2):
                        nand_in += f'bit_bufb<{idx+2}>,mid{idx}<{num_inst//2-jdx-1}>,'
                    nand_in = nand_in[:-1]
                    nand_term_list.append((f'XNAND{idx + 1}<{num_inst - 1}:0>',
                                           [('VDD', 'VDD'), ('VSS', 'VSS'), ('in<1:0>', nand_in),
                                            ('out', f'nand_out{idx + 1}<{num_inst - 1}:0>')]))
                    inv_term_list.append((f'XINV{idx + 1}<{num_inst - 1}:0>',
                                          [('VDD', 'VDD'), ('VSS', 'VSS'),
                                           ('in', f'nand_out{idx + 1}<{num_inst - 1}:0>'),
                                           ('out', f'out<{num_inst - 1}:0>')]))
                else:
                    nand_in = ''
                    for jdx in range(num_inst//2):
                        nand_in += f'bit_buf<{idx+2}>,mid{idx}<{num_inst//2-jdx-1}>,'
                    for jdx in range(num_inst//2):
                        nand_in += f'bit_bufb<{idx+2}>,mid{idx}<{num_inst//2-jdx-1}>,'
                    nand_in = nand_in[:-1]
                    nand_term_list.append((f'XNAND{idx + 1}<{num_inst - 1}:0>',
                                           [('VDD', 'VDD'), ('VSS', 'VSS'), ('in<1:0>', nand_in),
                                            ('out', f'nand_out{idx + 1}<{num_inst - 1}:0>')]))
                    inv_term_list.append((f'XINV{idx + 1}<{num_inst - 1}:0>',
                                          [('VDD', 'VDD'), ('VSS', 'VSS'),
                                           ('in', f'nand_out{idx + 1}<{num_inst - 1}:0>'),
                                           ('out', f'mid{idx+1}<{num_inst - 1}:0>')]))

        self.array_instance('XNAND', inst_term_list=nand_term_list, dy=-2* self.instances['XNAND'].height)
        self.array_instance('XINV', inst_term_list=inv_term_list, dy=-2* self.instances['XINV'].height)

        for _nand, _inv in zip(nand_term_list, inv_term_list):
            self.instances[_nand[0]].design(**nand)
            self.instances[_inv[0]].design(**inv)
        self.rename_pin('out', f'out<{2**nbits-1}:0>')
        self.rename_pin('in', f'in<{nbits-1}:0>')
