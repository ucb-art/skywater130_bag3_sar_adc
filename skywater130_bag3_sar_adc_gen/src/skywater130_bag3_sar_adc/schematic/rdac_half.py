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
class skywater130_bag3_sar_adc__rdac_half(Module):
    """Module for library skywater130_bag3_sar_adc cell rdac_half.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'rdac_half.yaml')))

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
            dec='',
            res='',
            res_bias='',
            res_bias_ref='',
            cap_cm='',
            cap_dm='',
            pside='',
            res_start_idx='',
            differential='',
            decap='True to use decap as different decouple cap'
        )

    def design(self, dec, res, res_bias, cap_cm, cap_dm, pside, res_start_idx, differential, decap=False,
               res_bias_ref='VSS') -> None:
        self.instances['XRES'].design(**res)
        self.instances['XDEC'].design(**dec)
        if differential:
            self.instances['XDECAP_CM'].design(**cap_cm)
        else:
            self.remove_instance('XDECAP_CM')
            [self.remove_pin(pin) for pin in ['mux_out', 'mux_out_c', 'out_c', 'top', 'bottom']]
        if decap:
            self.replace_instance_master('XDECAP_DM', 'skywater130_bag3_sar_adc', 'decap_array')
            self.reconnect_instance('XDECAP_DM', [('PLUS', 'out'), ('MINUS', 'VSS')])
        self.instances['XDECAP_DM'].design(**cap_dm)

        nbits = dec['nbits']
        nx_core = res['nx'] - res['nx_dum'] * 2
        ny_core = res['ny'] - res['ny_dum'] * 2
        ncore = nx_core * ny_core
        dec_conn = f'res_tap<{res_start_idx+2**nbits-1}:{res_start_idx}>'
        self.reconnect_instance('XDEC', [(f'bit<{nbits-1}:0>', f'bit<{nbits-1}:0>'), ('sel_cm', f'bit<{nbits}>'),
                                         ('sel_np', f'bit<{nbits+1}>'),
                                         (f'tap<{2**nbits-1}:0>',  dec_conn)])

        if differential:
            if res_start_idx > 0:
                res_conn = dec_conn+f',noConn<{res_start_idx-1}:0>'
        else:
            res_conn = f'noConn<{ncore - 1}:{res_start_idx + 2 ** nbits}>,' + dec_conn
            if res_start_idx > 0:
                res_conn += f',noConn<{res_start_idx - 1}:0>'
        self.reconnect_instance('XRES', [(f'out<{ncore-1}:0>', res_conn), ('VDD', 'VDD')])
        self.rename_pin('bit', f'bit<{nbits+1}:0>' if differential else f'bit<{nbits-1}:0>')

        if differential:
            self.reconnect_instance('XRES', [('bottom', 'VDD' if pside else 'VSS')])
        else:
            self.reconnect_instance('XRES', [('top', 'VDD'), ('bottom', 'VSS')])


        if res_bias:
            num_res_bias = (res_bias['nx'] - 2*res_bias['nx_dum'])*(res_bias['ny'] - 2*res_bias['ny_dum'])
            self.instances['XRES_BIAS'].design(**res_bias)
            if res_bias_ref == 'VSS':
                self.reconnect_instance('XRES_BIAS', [('bottom', 'VSS'), ('top', 'res_mid')])
                self.reconnect_instance('XRES', [('bottom', 'VDD'), ('top', 'res_mid')])
            else:
                self.reconnect_instance('XRES_BIAS', [('bottom', 'VDD'), ('top', 'res_mid')])
                self.reconnect_instance('XRES', [('bottom', 'VSS'), ('top', 'res_mid')])
            self.reconnect_instance('XRES_BIAS', [(f'out<{num_res_bias-1}:0>', f'noConnBias<{num_res_bias-1}:0>'),
                                                  ('VDD', 'VDD')])

        else:
            self.remove_instance('XRES_BIAS')
