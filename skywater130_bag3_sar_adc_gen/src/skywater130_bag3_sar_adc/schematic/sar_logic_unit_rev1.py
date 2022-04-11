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

from typing import Mapping, Any, Dict, Optional

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_logic_unit_rev1(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_logic_unit_rev1.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_logic_unit_rev1.yaml')))

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
            buf='Parameters for output buffers template',
            buf_np='Parameters for output buffers template',
            latch='Parameters for retimer latch',
            inv_state='Inverter for state signal',
            inv_rst='Inverter for state signal',
            flop='Flop parameters',
            dyn_lat='Dynamic latch parameters',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
        )

    def design(self, flop: Param, inv_state: Param, inv_rst: Param,
               latch: Param, buf: Param, buf_np: Param, dyn_lat: Param) -> None:

        self.instances['XINV_STATE'].design(**inv_state)
        self.instances['XINV_RST'].design(**inv_rst)
        self.instances['XFF_STATE'].design(**flop)
        self.instances['XL_RET'].design(**latch)

        # self.instances['XINV_STATE1'].design(**buf_state[1])
        self.instances['XBUF_M'].design(**buf)
        self.instances['XBUF_P'].design(**buf_np)
        self.instances['XBUF_N'].design(**buf_np)

        self.instances['XLAT_M'].design(**dyn_lat)
        self.instances['XLAT_P'].design(**dyn_lat)
        self.instances['XLAT_N'].design(**dyn_lat)

        self.reconnect_instance('XFF_STATE', [('rstb', 'rstb')])
