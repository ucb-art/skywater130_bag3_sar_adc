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
class skywater130_bag3_sar_adc__vco_cnter_buffer(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_cnter_buffer.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_cnter_buffer.yaml')))

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
            lch='channel length',
            thn='nmos threshold',
            thp='pmos threshold',
            seg_dict='segments dictionary.',
            stack_dict='stack dictionary.',
            w_dict='width dictionary.',
        )

    def design(self, lch, thn, thp, seg_dict, stack_dict, w_dict) -> None:
        self.instances['XCAP'].design(l=lch, w=w_dict['wcap'], nf=seg_dict['cap'], intent=thn)
        self.instances['XRES'].design(lch=lch, w=w_dict['wres'], seg=seg_dict['res'], intent=thp,
                                      stack=stack_dict['res'])

        self.instances['XTIA_P'].design(l=lch, w=w_dict['wp'], nf=seg_dict['tiap'], intent=thp)
        self.instances['XTIA_N'].design(l=lch, w=w_dict['wn'], nf=seg_dict['tian'], intent=thn)
        self.instances['XBUF0_P'].design(l=lch, w=w_dict['wp_buf'], nf=seg_dict['bufp'], intent=thp)
        self.instances['XBUF0_N'].design(l=lch, w=w_dict['wn_buf'], nf=seg_dict['bufn'], intent=thn)
        self.instances['XBUF1_P'].design(l=lch, w=w_dict['wp_coupler'], nf=seg_dict['couplerp'], intent=thp)
        self.instances['XBUF1_N'].design(l=lch, w=w_dict['wn_coupler'], nf=seg_dict['couplern'], intent=thn)
