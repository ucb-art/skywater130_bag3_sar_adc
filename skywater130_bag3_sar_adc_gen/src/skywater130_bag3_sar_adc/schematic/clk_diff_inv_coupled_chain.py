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

from typing import Mapping, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__clk_diff_inv_coupled_chain(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_diff_inv_coupled_chain.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_diff_inv_coupled_chain.yaml')))

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
            inv_list='',
            export_mid=''
        )

    @classmethod
    def get_default_param_values(cls) -> Mapping[str, Any]:
        return dict(
            export_mid=False,
        )

    def design(self, inv_list, export_mid) -> None:
        nstage=len(inv_list)
        name_term_list = []
        for idx in range(nstage):
            inn_name = 'inn' if idx == 0 else f'midn<{idx-1}>'
            inp_name = 'inp' if idx == 0 else f'midp<{idx-1}>'
            outn_name = 'outn' if idx == nstage-1 else f'midn<{idx}>'
            outp_name = 'outp' if idx == nstage-1 else f'midp<{idx}>'

            term = [('VDD', 'VDD'), ('VSS', 'VSS'),
                    ('inp', inn_name if idx & 1 else inp_name),
                    ('inn', inp_name if idx & 1 else inn_name),
                    ('outp', outn_name if idx & 1 else outp_name),
                    ('outn', outp_name if idx & 1 else outn_name)]
            name_term_list.append((f'XINV{idx}', term))
        self.array_instance('XINV', inst_term_list=name_term_list)
        for idx in range(nstage):
            self.instances[f'XINV{idx}'].design(**inv_list[idx])

        if export_mid:
            self.rename_pin('midn', f'midn<{nstage - 2}:0>' if nstage > 2 else f'midn<0>')
            self.rename_pin('midp', f'midp<{nstage - 2}:0>' if nstage > 2 else f'midp<0>')
        else:
            self.remove_pin('midn')
            self.remove_pin('midp')

