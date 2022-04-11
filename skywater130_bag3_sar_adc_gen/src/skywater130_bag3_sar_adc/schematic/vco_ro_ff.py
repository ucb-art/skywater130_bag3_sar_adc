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

import pkg_resources
from pathlib import Path
from typing import Dict, Any

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param
from pybag.enum import TermType


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__vco_ro_ff(Module):
    """Module for library skywater130_bag3_sar_adc cell vco_ro_ff.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'vco_ro_ff.yaml')))

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
            ff_params='Parameter of flops',
            vco_params='Cnter parameters',
            dec_params='Decoder parameters',
        )

    def design(self, ff_params, vco_params, dec_params) -> None:
        nstage = vco_params['ro_params']['num_stage']
        is_pctrl = vco_params['is_pctrl']
        self.instances['XRO'].design(**vco_params)
        ro_term = [(f'phi<{2 * nstage - 1}:0>', f'phi<{2 * nstage - 1}:0>'),
                   (f'phi_buf<{2 * nstage - 1}:0>', f'phi_buf<{2 * nstage - 1}:1>,phi_out'), (f'vctrl_n', f'vctrl_n'),
                   (f'vctrl_p', f'vctrl_p'), ('VDD', 'VDD'), ('VSS', 'VSS'),
                   ('vtop', 'vtop') if is_pctrl else ('vbot', 'vbot')]
        self.reconnect_instance('XRO', ro_term)

        # saff_outp = ','.join([f'ff_out<{idx}>' for idx in range(nstage - 1, -1, -1)])
        # saff_outn = ','.join([f'ff_out<{idx + nstage}>' for idx in range(nstage - 1, -1, -1)])
        self.rename_instance('XFF', f'XFF<{nstage - 1}:0>', [('clkb', 'clkb'), ('clk', 'clk'),
                                                             ('inp', f'phi_buf<{nstage - 1}:1>,phi_out'),
                                                             ('inn', f'phi_buf<{2 * nstage - 1}:{nstage}>'),
                                                             ('outp', f'ff_out<{nstage - 1}:1>,phi_sampled'),
                                                             ('outn', f'ff_out<{2 * nstage - 1}:{nstage}>'),
                                                             ('VDD', 'VDD'), ('VSS', 'VSS')])
        self.instances[f'XFF<{nstage - 1}:0>'].design(**ff_params)

        nbits = (2 * nstage - 1).bit_length()
        self.instances[f'XDEC'].design(**dec_params)
        self.reconnect_instance('XDEC', [('VDD', 'VDD'), ('VSS', 'VSS'),
                                         (f'in<{2 * nstage - 1}:1>', f'ff_out<{2 * nstage - 1}:1>'),
                                         (f'bit<{nbits - 1}:0>', f'bit<{nbits - 1}:0>')])
        self.rename_pin('bit', f'bit<{nbits - 1}:0>')
        if is_pctrl:
            self.remove_pin('vctrl_n')
            self.add_pin('vtop', TermType.inout)
        else:
            self.remove_pin('vctrl_p')
            self.add_pin('vbot', TermType.inout)
