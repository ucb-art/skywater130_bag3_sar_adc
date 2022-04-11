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
class skywater130_bag3_sar_adc__clk_delay_binary(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_delay_binary.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_delay_binary.yaml')))

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
            buf_list='',
            unit_list='',
            nlsb='',
            nmsb='',
        )

    def design(self, buf_list, unit_list, nlsb, nmsb) -> None:
        nbits = nlsb + nmsb
        unit_name_term_list = []
        buf_name_term_list = []
        for idx in range(nbits):
            unit_name = f'XUNIT{idx}' if idx <= nlsb else f'XUNIT{idx}<{2 ** (idx - nlsb) - 1}:0>'
            buf_name = f'XBUF{idx}' if idx <= nlsb else f'XBUF{idx}<{2 ** (idx - nlsb) - 1}:0>'
            if idx < nlsb:
                in_name = f'in<{idx}>'
            elif idx == nlsb:
                in_name = 'mid0'
            else:
                in_name = f'mid{idx-nlsb}<{2 ** (idx - nlsb) - 1}:0>'

            unit_name_term_list.append((unit_name, [('VDD', 'VDD'), ('VSS', 'VSS'),
                                                    ('in', in_name), ('outn', 'outn'), ('outp', 'outp')]))
            if idx >= nlsb:
                buf_name_term_list.append((buf_name, [('VDD', 'VDD'), ('VSS', 'VSS'),
                                                      ('in', f'in<{idx}>'), ('out', in_name)]))

        self.array_instance('XUNIT', inst_term_list=unit_name_term_list, dx=self.instances['XUNIT'].width)
        self.array_instance('XBUF', inst_term_list=buf_name_term_list, dx=self.instances['XBUF'].width)

        for idx, _unit in enumerate(unit_name_term_list):
            self.instances[_unit[0]].design(**unit_list[idx])
        for idx, _buf in enumerate(buf_name_term_list):
            self.instances[_buf[0]].design(**buf_list[idx])

        self.rename_pin('in', f'in<{nbits - 1}:0>')
