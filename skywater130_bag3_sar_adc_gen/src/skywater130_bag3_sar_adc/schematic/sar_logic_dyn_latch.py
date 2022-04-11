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
class skywater130_bag3_sar_adc__sar_logic_dyn_latch(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_logic_dyn_latch.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_logic_dyn_latch.yaml')))

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
            seg_pd='pull down tx size',
            seg_pu='pull pu tx size',
            seg_inv='inv seg',
            seg_inv_fb='inv seg_fb',
            w_dict='width dictionary',
            lch='channel length',
            th_n='nmos threshold',
            th_p='pmos threshold',
        )

    def design(self, seg_pd, seg_pu, seg_inv, seg_inv_fb, w_dict, lch, th_n, th_p) -> None:
        w_pd, w_pu = w_dict['pd'], w_dict['pu']
        w_inv_n, w_inv_p = w_dict['inv']['wn'], w_dict['inv']['wp']
        w_inv_fb_n, w_inv_fb_p = w_dict['inv_fb']['wn'], w_dict['inv_fb']['wp']
        self.instances['XPU'].design(l=lch, nf=seg_pu, stack=1, w=w_pu, intent=th_p)
        self.instances['XD'].design(l=lch, nf=1, stack=1, w=w_pd, intent=th_n)
        self.instances['XEN'].design(l=lch, nf=1, stack=1, w=w_pd, intent=th_n)
        self.rename_instance('XD', f'XD<{seg_pd-1}:0>', [('S', f'mid<{seg_pd-1}:0>')])
        self.rename_instance('XEN', f'XEN<{seg_pd-1}:0>', [('D', f'mid<{seg_pd-1}:0>')])

        self.instances['XP0'].design(l=lch, nf=seg_inv, stack=1, w=w_inv_p, intent=th_p)
        self.instances['XN0'].design(l=lch, nf=seg_inv, stack=1, w=w_inv_n, intent=th_n)

        self.instances['XP1'].design(l=lch, nf=seg_inv_fb, stack=1, w=w_inv_fb_p, intent=th_p)
        self.instances['XN1'].design(l=lch, nf=seg_inv_fb, stack=1, w=w_inv_fb_n, intent=th_n)
