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

from typing import Dict, Any, Mapping

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__ra_cmfb_dc(Module):
    """Module for library skywater130_bag3_sar_adc cell ra_cmfb_dc.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ra_cmfb_dc.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)


    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            lch='channel length',
            seg_dict='transistor segments dictionary.',
            w_dict='transistor width dictionary.',
            th_dict='transistor threshold dictionary.',
            cap_params='',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict()

    def design(self, lch: int, seg_dict: Mapping[str, int], w_dict: Mapping[str, int], th_dict: Mapping[str, str],
               cap_params: Param) -> None:
        self.instances['XINV0_P'].design(l=lch, w=w_dict['inv_p0'], nf=seg_dict['inv_p0'], intent=th_dict['inv_p0'])
        self.instances['XINV0_N'].design(l=lch, w=w_dict['inv_n0'], nf=seg_dict['inv_n0'], intent=th_dict['inv_n0'])
        self.instances['XINV1_P'].design(l=lch, w=w_dict['inv_p1'], nf=seg_dict['inv_p1'], intent=th_dict['inv_p1'])
        self.instances['XINV1_N'].design(l=lch, w=w_dict['inv_n1'], nf=seg_dict['inv_n1'], intent=th_dict['inv_n1'])
        self.instances['XAZ_N'].design(l=lch, w=w_dict['az_n'], nf=seg_dict['az_n'], intent=th_dict['az_n'])
        self.instances['XAZ_P'].design(l=lch, w=w_dict['az_p'], nf=seg_dict['az_p'], intent=th_dict['az_p'])
        self.instances['XAMP_N'].design(l=lch, w=w_dict['amp_n'], nf=seg_dict['amp_n'], intent=th_dict['amp_n'])
        self.instances['XAMP_P'].design(l=lch, w=w_dict['amp_p'], nf=seg_dict['amp_p'], intent=th_dict['amp_p'])
        self.instances['XCHARGE_N'].design(l=lch, w=w_dict['charge_n'],
                                           nf=seg_dict['charge_n'], intent=th_dict['charge_n'])
        self.instances['XCHARGE_P'].design(l=lch, w=w_dict['charge_p'],
                                           nf=seg_dict['charge_p'], intent=th_dict['charge_p'])
        self.instances['XSHARE_P'].design(l=lch, w=w_dict['share_p'], nf=seg_dict['share_p'], intent=th_dict['share_p'])
        self.instances['XSHARE_N'].design(l=lch, w=w_dict['share_n'], nf=seg_dict['share_n'], intent=th_dict['share_n'])
        self.instances['XCAP'].design(**cap_params)
