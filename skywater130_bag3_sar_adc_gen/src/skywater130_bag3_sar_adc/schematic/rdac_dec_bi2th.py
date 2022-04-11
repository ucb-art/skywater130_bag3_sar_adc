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
class skywater130_bag3_sar_adc__rdac_dec_bi2th(Module):
    """Module for library skywater130_bag3_sar_adc cell rdac_dec_bi2th.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'rdac_dec_bi2th.yaml')))

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
            nbits='',
            buf_params='',
            unit_params='',
            has_out_buf='',
            inv_params=''
        )

    def design(self, nbits, buf_params, unit_params, inv_params, has_out_buf) -> None:
        ngates = 2 ** nbits
        buf_name_term_list, unit_name_term_list = [], []
        for idx in range(nbits):
            _name = f'XBUF{idx}'
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('in', f'in<{idx}>'), ('out', f'mid<{idx}>'),
                     ('outb', f'midb<{idx}>')]
            buf_name_term_list.append((_name, _term))

        for idx in range(ngates):
            _in_term = ''
            for jdx in range(nbits):
                if jdx < 2:
                    _in_term += f'mid<{jdx}>,' if idx & (2**jdx) else f'midb<{jdx}>,'
                elif jdx & 1:
                    _in_term += f'mid<{jdx}>,' if idx & (2**jdx) else f'midb<{jdx}>,'
                else:
                    _in_term += f'midb<{jdx}>,' if idx & (2**jdx) else f'mid<{jdx}>,'
            _in_term = _in_term[:-1]
            _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('out', f'mid_out<{idx}>' if has_out_buf else f'out<{idx}>'),
                     (f'in<{nbits - 1}:0>', _in_term)]
            _name = f'XNAND{idx}'
            unit_name_term_list.append((_name, _term))

        if has_out_buf:
            self.instances['XOUT'].design(**inv_params)
            self.rename_instance('XOUT', f'XOUT<{ngates-1}:0>', [('in', f'mid_out<{ngates-1}:0>'),
                                                                 ('out', f'out<{ngates-1}:0>')])
        else:
            self.remove_instance('XOUT')

        self.instances['XBUF'].design(**buf_params)
        self.instances['XNAND'].design(params_list=unit_params)
        self.array_instance('XBUF', inst_term_list=buf_name_term_list, dy=2*self.instances['XBUF'].height)
        self.array_instance('XNAND', inst_term_list=unit_name_term_list, dy=2*self.instances['XNAND'].height)
        self.rename_pin('in', f'in<{nbits-1}:0>')
        self.rename_pin('out', f'out<{ngates-1}:0>')
