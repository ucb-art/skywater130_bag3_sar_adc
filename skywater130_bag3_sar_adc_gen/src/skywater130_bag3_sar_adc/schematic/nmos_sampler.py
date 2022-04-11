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
from typing import Any, Dict

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__nmos_sampler(Module):
    """Module for library skywater130_bag3_sar_adc cell nmos_sampler.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'nmos_sampler.yaml')))

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
            lch='',
            seg_p='',
            seg_n='',
            seg_dum_p='',
            seg_n_dum='',
            th_n='',
            th_p='',
            w_n='',
            w_p='',
            m_list='',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            seg_p=0,
            seg_n=0,
            seg_dum_p=0,
            seg_n_dum=0,
            th_n='',
            th_p='',
            w_n=4,
            w_p=4,
            m_list=[1],
        )

    def design(self, lch, w_n, w_p, th_n, th_p, seg_n, seg_p, seg_n_dum, seg_dum_p, m_list) -> None:
        if len(m_list) == 1:
            m = m_list[0]
            self.instances['XSAM'].design(l=lch, w=w_n, nf=seg_n * m, intent=th_n)
            if seg_n_dum:
                self.instances['XDUM'].design(l=lch, w=w_n, nf=seg_n_dum * m, intent=th_n)
            else:
                self.remove_instance('XDUM')
        else:
            nbits = len(m_list)
            self.rename_pin('out', f'out<{nbits - 1}:0>')
            pname_term_list = []
            [pname_term_list.append((f'XSAM<{idx}>', [('B', 'VSS'), ('S', 'in'), ('D', f'out<{idx}>'),
                                                      ('G', 'sam')])) for idx in range(nbits)]
            self.array_instance('XSAM', inst_term_list=pname_term_list)

            for idx, m in enumerate(m_list):
                self.instances[f'XSAM<{idx}>'].design(l=lch, w=w_n, nf=seg_n * m, intent=th_n)
            if seg_n_dum:
                pname_term_list = []
                [pname_term_list.append((f'XDUM<{idx}>', [('B', 'VSS'), ('S', 'in_c'), ('D', f'out<{idx}>'),
                                                          ('G', 'VSS')])) for idx in range(nbits)]
                self.array_instance('XDUM', inst_term_list=pname_term_list)
                for idx, m in enumerate(m_list):
                    self.instances[f'XDUM<{idx}>'].design(l=lch, w=w_n, nf=seg_n_dum * m, intent=th_n)
            else:
                self.remove_instance('XDUM')
