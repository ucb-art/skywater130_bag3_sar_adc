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
from typing import Mapping, Any

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__rdac_dec(Module):
    """Module for library skywater130_bag3_sar_adc cell rdac_dec.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'rdac_dec.yaml')))

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
            dec_lsb_params='',
            dec_msb_params='',
            mux_params='',
            npmux_params='',
            pside='',
            differential='',
            pg_params='',
            buf_params='',
            off_low='',
        )

    @classmethod
    def get_default_param_values(cls) -> Mapping[str, Any]:
        return dict(
            pg_params=dict(),
            buf_params=dict(),
            off_low=True,
        )

    def design(self, dec_lsb_params, dec_msb_params, mux_params, npmux_params, pside, differential,
               pg_params, buf_params, off_low) -> None:
        nbits_tot = dec_lsb_params['nbits'] + dec_msb_params['nbits']
        self.instances['XDEC_LSB'].design(**dec_lsb_params)
        self.instances['XDEC_MSB'].design(**dec_msb_params)
        nbits_lsb = dec_lsb_params['nbits']
        nbits_msb = dec_msb_params['nbits']
        self.reconnect_instance('XDEC_LSB', [(f'in<{nbits_lsb-1}:0>', f'bit<{nbits_lsb-1}:0>'),
                                             (f'out<{2**nbits_lsb-1}:0>', f'sel0<{2**nbits_lsb-1}:0>')])
        self.reconnect_instance('XDEC_MSB', [(f'in<{nbits_msb-1}:0>', f'bit<{nbits_tot-1}:{nbits_lsb}>'),
                                             (f'out<{2**nbits_msb-1}:0>', f'sel1<{2**nbits_msb-1}:0>')])
        self.instances['XMUX'].design(**mux_params)
        mux_name_term_list = []
        for idx in range(2**nbits_lsb):
            for jdx in range(2 ** nbits_msb):
                _name = f'XMUX{idx + jdx * 2**nbits_lsb}'
                _term = [('VDD', 'VDD'), ('VSS', 'VSS'), ('in', f'in<{idx}>'),
                         ('sel0', f'sel0<{idx}>'), ('sel1', f'sel1<{jdx}>'),
                         ('in', f'tap<{idx + jdx * 2**nbits_lsb}>'),
                         ('out', 'mux_out')]
                mux_name_term_list.append((_name, _term))
        self.array_instance('XMUX', inst_term_list=mux_name_term_list)

        self.rename_pin('in', f'tap<{2**nbits_tot-1}:0>')
        self.rename_pin('bit', f'bit<{nbits_tot-1}:0>')
        if differential:
            self.remove_instance('XBUF_EN')
            self.remove_instance('XPG_EN')
            self.remove_instance('XPG_OFF')
            self.instances['XNP'].design(**npmux_params)
            if pside:
                self.reconnect_instance('XNP', [('inp', 'mux_out'), ('inn', 'mux_out_n')])
            else:
                self.reconnect_instance('XNP', [('inn', 'mux_out'), ('inp', 'mux_out_n')])
        else:
            self.instances['XPG_EN'].design(**pg_params)
            self.instances['XPG_OFF'].design(**pg_params)
            self.instances['XBUF_EN'].design(**buf_params)
            self.reconnect_instance('XPG_OFF', [('d', 'VSS' if off_low else 'VDD')])
            self.remove_instance('XNP')
            [self.remove_pin(pin) for pin in ['mux_out', 'mux_out_n', 'vcm', 'sel_cm', 'sel_np']]

