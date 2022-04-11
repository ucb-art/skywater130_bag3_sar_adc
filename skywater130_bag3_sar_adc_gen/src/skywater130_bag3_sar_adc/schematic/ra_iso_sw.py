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

from typing import Dict, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__ra_iso_sw(Module):
    """Module for library skywater130_bag3_sar_adc cell ra_iso_sw.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ra_iso_sw.yaml')))

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
            seg_dict='',
            w_dict='',
            th_dict='',
            out_cm='',
            in_cmos_cm='',
            out_cmos_cm='',
        )

    def design(self, lch, seg_dict, w_dict, th_dict, out_cm, in_cmos_cm, out_cmos_cm) -> None:
        self.instances['XSW_NN'].design(l=lch, w=w_dict['sw_n'], nf=seg_dict['sw_n'], intent=th_dict['sw_n'])
        self.instances['XSW_PN'].design(l=lch, w=w_dict['sw_n'], nf=seg_dict['sw_n'], intent=th_dict['sw_n'])
        self.instances['XSW_NP'].design(l=lch, w=w_dict['sw_p'], nf=seg_dict['sw_p'], intent=th_dict['sw_p'])
        self.instances['XSW_PP'].design(l=lch, w=w_dict['sw_p'], nf=seg_dict['sw_p'], intent=th_dict['sw_p'])

        # self.instances['XCM_INL'].design(l=lch, w=w_dict['sw_mid'], nf=seg_dict['sw_mid'], intent=th_dict['sw_mid'])
        # self.instances['XCM_INR'].design(l=lch, w=w_dict['sw_mid'], nf=seg_dict['sw_mid'], intent=th_dict['sw_mid'])
        # self.instances['XCM_INN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
        # self.instances['XCM_INP'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])

        if out_cm and out_cmos_cm:
            self.instances['XCM_OUT_NN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            self.instances['XCM_OUT_NP'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            self.instances['XCM_OUT_PN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            self.instances['XCM_OUT_PP'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
        elif out_cm:
            self.instances['XCM_OUT_NN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            self.instances['XCM_OUT_PN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            for inst in ['XCM_OUT_NP', 'XCM_OUT_PP']:
                self.remove_instance(inst)
        else:
            for inst in ['XCM_OUT_NN', 'XCM_OUT_NP', 'XCM_OUT_PP', 'XCM_OUT_PN']:
                self.remove_instance(inst)

        self.instances['XCM_IN_NN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
        self.instances['XCM_IN_PN'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
        if in_cmos_cm:
            self.instances['XCM_IN_NP'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
            self.instances['XCM_IN_PP'].design(l=lch, w=w_dict['sw_cm'], nf=seg_dict['sw_cm'], intent=th_dict['sw_cm'])
        else:
            for inst in ['XCM_IN_NP', 'XCM_IN_PP']:
                self.remove_instance(inst)

        if not in_cmos_cm and not out_cmos_cm:
            self.remove_pin('phi2_b')

