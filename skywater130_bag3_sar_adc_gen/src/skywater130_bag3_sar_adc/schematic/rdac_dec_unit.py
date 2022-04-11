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
class skywater130_bag3_sar_adc__rdac_dec_unit(Module):
    """Module for library skywater130_bag3_sar_adc cell rdac_dec_unit.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'rdac_dec_unit.yaml')))

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
            params_list='',
        )

    def design(self, params_list) -> None:
        ninput = len(params_list) + 1
        name_term_list = []
        for idx in range(ninput - 1):
            _name = f'XNOR<{idx}>' if idx & 1 else f'XNAND<{idx}>'
            _in_term = f'mid<{idx}>,in<{ninput-idx-2}>' if idx else f'in<{ninput-1}:{ninput-2}>'
            if idx == ninput - 2:
                _out_term = 'out'
            else:
                _out_term = f'mid<{idx + 1}>'

            _term = [('in<1:0>', _in_term), ('out', _out_term), ('VDD', 'VDD'), ('VSS', "VSS")]
            name_term_list.append((_name, _term))
        self.array_instance('XNAND', inst_term_list=name_term_list)
        for idx, (name, _) in enumerate(name_term_list):
            if idx & 1:
                self.replace_instance_master(name, 'bag3_digital', 'nor', keep_connections=True)

            self.instances[name].design(**params_list[idx])

        self.rename_pin('in', f'in<{ninput - 1}:0>')
