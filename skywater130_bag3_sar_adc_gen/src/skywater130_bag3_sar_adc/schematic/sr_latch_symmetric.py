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

from typing import Dict, Any, Optional

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sr_latch_symmetric(Module):
    """Module for library bag3_digital cell sr_latch_symmetric.

        Fill in high level description here.
        """

    yaml_file = pkg_resources.resource_filename(__name__, str(Path('netlist_info', 'sr_latch_symmetric.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            core_params='SR latch core parameters.',
            outbuf_params='output buffer parameters.',
            inbuf_params='s/r input buffer parameters.',
            has_rstb='True to enable rstb functionality.',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(outbuf_params=None, inbuf_params=None, has_rstb=False)

    def design(self, core_params: Param, outbuf_params: Optional[Param],
               inbuf_params: Optional[Param], has_rstb: bool) -> None:
        inst = self.instances['XCORE']
        inst.design(has_rstb=has_rstb, **core_params)

        if not has_rstb:
            self.remove_pin('rstlb')
            self.remove_pin('rsthb')

        if outbuf_params is None:
            self.remove_instance('XOBUF<1:0>')
            self.reconnect_instance('XCORE', [('q', 'q'), ('qb', 'qb')])
        else:
            self.instances['XOBUF<1:0>'].design(**outbuf_params)

        if inbuf_params is None:
            self.remove_instance('XIBUF<1:0>')
        else:
            self.remove_pin('sb')
            self.remove_pin('rb')
            self.instances['XIBUF<1:0>'].design(**inbuf_params)
            self.reconnect_instance_terminal('XIBUF<1:0>', 'out', 'sb,rb')
            self.reconnect_instance_terminal('XIBUF<1:0>', 'in', 's,r')
