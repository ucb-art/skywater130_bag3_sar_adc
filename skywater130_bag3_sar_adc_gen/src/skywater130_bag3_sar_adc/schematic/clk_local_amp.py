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
from bag3_liberty.enum import TermType


class skywater130_bag3_sar_adc__clk_local_amp(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_local_amp.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_local_amp.yaml')))

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
            mux_params='',
            nand_params='',
            nor_params='',
            ret_params='',
            # non_overlap_params='',
            sel_params='',
            buf_params='',
            # buf_b_params='',
        )

    def design(self, mux_params, nand_params, nor_params, ret_params, sel_params, buf_params) -> None:
        self.instances['XMUX_NAND'].design(**mux_params)
        self.instances['XMUX_NOR'].design(**mux_params)
        self.instances['XNAND'].design(**nand_params)
        self.instances['XNOR'].design(**nor_params)
        self.instances['XRET'].design(**ret_params)
        # self.instances['XNONOVERLAP'].design(**non_overlap_params)
        self.instances['XSEL'].design(**sel_params)
        self.instances['XNAND_INV'].design(**sel_params)
        self.instances['XNOR_INV'].design(**sel_params)

        self.instances['XDIFFBUF'].design(**buf_params)
        # self.instances['XBUFB'].design(**buf_b_params)
        buf_term= [ ]
        for pin in self.instances['XDIFFBUF'].master.pins.keys():
            if 'mid' in pin:
                buf_term.append((pin, pin.replace('mid', 'mid_buf')))
                # self.add_pin(pin, TermType.output)

        self.reconnect_instance('XDIFFBUF', buf_term)


