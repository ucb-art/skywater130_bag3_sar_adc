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

from pathlib import Path
from typing import Mapping, Any

import pkg_resources

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__vref(Module):
    """Module for library skywater130_bag3_sar_adc cell vref.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vref.yaml')))

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
            type='',
            dac_params='',
            buf_params='',
        )

    def design(self, dac_params, buf_params, type) -> None:
        if type == 'p':
            self.replace_instance_master('XSF', 'skywater130_bag3_sar_adc', 'super_source_follower_p')

        self.instances['XDAC'].design(**dac_params)
        self.instances['XSF'].design(**buf_params)

        dec_nbits = dac_params['dec']['nbits']
        num_dacn = len(buf_params['dacn_w_seg'])
        num_dacp = len(buf_params['dacp_w_seg'])

        self.reconnect_instance('XSF', [(f'ctrl_biasn<{num_dacn - 1}:0>', f'ctrl_biasn<{num_dacn - 1}:0>'),
                                        (f'ctrl_biasp<{num_dacp - 1}:0>', f'ctrl_biasp<{num_dacp - 1}:0>')])

        self.reconnect_instance('XDAC', [(f'bit<{dec_nbits - 1}:0>', f'ctrl_dac<{dec_nbits - 1}:0>')])

        self.rename_pin('ctrl_dac', f'ctrl_dac<{dec_nbits - 1}:0>')
        self.rename_pin('ctrl_biasn', f'ctrl_biasn<{dec_nbits - 1}:0>')
        self.rename_pin('ctrl_biasp', f'ctrl_biasp<{dec_nbits - 1}:0>')
