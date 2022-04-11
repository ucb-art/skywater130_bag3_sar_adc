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
from typing import Dict, Any

import pkg_resources

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__rst_latch(Module):
    """Module for library skywater130_bag3_sar_adc cell rst_latch.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'rst_latch.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            tin='Input tristate inverter params',
            tfb='Feedback (keeper) tristate inverter params',
            rst='Output Nor params',
            resetb='True to low reset, reset to logic 1',
            resetable='True to make restable latch',
            passgate='True to use passgate as input',
        )

    def design(self, tin: Dict[str, Any], tfb: Dict[str, Any], rst: Dict[str, Any],
               resetb: bool, passgate: bool, resetable: bool) -> None:
        self.instances['XTBUF'].design(**tin)
        self.instances['XTFB'].design(**tfb)
        self.instances['XCM'].design(nin=2)
        if resetable:
            if resetb:
                self.replace_instance_master('XNOR', 'bag3_digital', 'nand')
                self.reconnect_instance('XNOR', [('out', 'out'), ('in<1:0>', 'outb,rstb'),
                                                 ('VSS', 'VSS'), ('VDD', 'VDD')])
                self.rename_pin('rst', 'rstb')
                self.rename_instance('XNOR', 'XNAND')
            self.instances['XNAND' if resetb else 'XNOR'].design(**rst)
        else:
            self.replace_instance_master('XNOR', 'bag3_digital', 'inv')
            self.reconnect_instance('XNOR', [('out', 'out'), ('in', 'outb'),
                                             ('VSS', 'VSS'), ('VDD', 'VDD')])
            self.remove_pin('rst')
            self.rename_instance('XNOR', 'XINV')
            self.instances['XINV'].design(**rst)

        if passgate:
            self.replace_instance_master('XTBUF', 'bag3_digital', 'passgate')
            self.reconnect_instance('XTBUF', [('d', 'in'), ('s', 'inb'),
                                              ('en', 'clk'), ('enb', 'clkb'),
                                              ('VDD', 'VDD'), ('VSS', 'VSS')])
            self.rename_instance('XTBUF', 'XPG')
        self.instances['XPG' if passgate else 'XTBUF'].design(**tin)
