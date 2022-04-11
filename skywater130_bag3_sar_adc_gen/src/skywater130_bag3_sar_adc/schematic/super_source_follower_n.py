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
class skywater130_bag3_sar_adc__super_source_follower_n(Module):
    """Module for library skywater130_bag3_sar_adc cell super_source_follower_n.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'super_source_follower_n.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Mapping[str, str]:
        return dict(
            lch='channel length.',
            seg_dict='number of segments dictionary.',
            w_dict='widths dictionary.',
            th_dict='threshold dictionary.',
            n_type='N-type source follower',
            ndecap='Number of decaps',
            dacn_w_seg='Pair of w and seg for dacn',
            dacp_w_seg='Pair of w and seg for dacp',
        )

    def design(self, lch, seg_dict, w_dict, th_dict, n_type, ndecap, dacn_w_seg, dacp_w_seg) -> None:
        self.instances['XIN'].design(l=lch, w=w_dict['in'], nf=seg_dict['in'], intent=th_dict['in'])
        self.instances['XP'].design(l=lch, w=w_dict['biasp'], nf=seg_dict['biasp'], intent=th_dict['biasp'])
        self.instances['XN'].design(l=lch, w=w_dict['biasn'], nf=seg_dict['biasn'], intent=th_dict['biasn'])
        self.instances['XFB'].design(l=lch, w=w_dict['fb'], nf=seg_dict['fb'], intent=th_dict['fb'])
        self.instances['XB'].design(l=lch, w=w_dict['b'], nf=seg_dict['b'], intent=th_dict['b'])
        self.instances['XB_P'].design(l=lch, w=w_dict['mi0'], nf=seg_dict['mi0'], intent=th_dict['mi0'])
        self.instances['XB_PM'].design(l=lch, w=w_dict['sr0'], nf=seg_dict['sr0'], intent=th_dict['sr0'])
        self.instances['XB_N'].design(l=lch, w=w_dict['mi1'], nf=seg_dict['mi1'], intent=th_dict['mi1'])
        self.instances['XB_IN'].design(l=lch, w=w_dict['mid'], nf=seg_dict['mid'], intent=th_dict['mid'])
        # self.instances['XDECAP'].design(l=lch, w=w_dict['bias'], nf=ndecap, intent=th_dict['bias'])
        num_dacn, num_dacp = len(dacn_w_seg), len(dacp_w_seg)
        dacn_inst_term_list, dacp_inst_term_list = [], []
        for idx in range(num_dacn):
            _name = f'XDAC_N<{idx}>'
            _term = [('B', 'VSS'), ('S', 'VSS'), ('G', f'ctrl_biasn<{idx}>'), ('D', 'vout')]
            dacn_inst_term_list.append((_name, _term))
        self.array_instance('XDAC_N', inst_term_list=dacn_inst_term_list)
        for idx in range(num_dacn):
            self.instances[f'XDAC_N<{idx}>'].design(l=lch, w=dacn_w_seg[idx][0], nf=dacn_w_seg[idx][1],
                                                    intent=th_dict['biasn'])

        for idx in range(num_dacp):
            _name = f'XDAC_P<{idx}>'
            _term = [('B', 'VDD'), ('S', 'VDD'), ('G', f'ctrl_biasp<{idx}>'), ('D', 'vm')]
            dacp_inst_term_list.append((_name, _term))

        self.array_instance('XDAC_P', inst_term_list=dacp_inst_term_list)
        for idx in range(num_dacn):
            self.instances[f'XDAC_P<{idx}>'].design(l=lch, w=dacp_w_seg[idx][0], nf=dacp_w_seg[idx][1],
                                                    intent=th_dict['biasn'])

        if dacn_inst_term_list:
            self.rename_pin('ctrl_biasn', f'ctrl_biasn<{num_dacn-1}:0>')
        else:
            self.remove_pin('ctrl_biasn')
        if dacp_inst_term_list:
            self.rename_pin('ctrl_biasp', f'ctrl_biasp<{num_dacp-1}:0>')
        else:
            self.remove_pin('ctrl_biasp')
        # self.instances['XDECAP'].design(l=lch, w=w_dict['bias'], nf=ndecap, intent=th_dict['bias'])
