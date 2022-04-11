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

from typing import Mapping, Any, Dict

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_slice_bot_rev(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_slice_bot_rev.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_slice_bot_rev.yaml')))

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
            nbits='Number of bits',
            comp='Parameters of comparator',
            logic='Parameters of sar logic block',
            cdac='Parameters of cdac',
            buf='Buffer params',
            ideal_switch='True to put ideal switch in front of SAR for sch simulation',
            tri_sa='True to enable tri-tail comparator',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            ideal_switch=True,
            tri_sa=False,
        )

    def design(self, nbits: int, comp: Param, logic: Param, cdac: Param, buf: Param, ideal_switch: bool,
               tri_sa: bool) -> None:

        pipeline_sar = True
        idx = 1 if pipeline_sar else 2
        for pname in ['dm', 'dn', 'dp', 'data_out']:
            self.rename_pin(pname, f"{pname}<{nbits - 1}:0>")
        # for pname in ['bot_p', 'bot_n']:
        #     self.rename_pin(pname, f"{pname}<{nbits -idx + 1}:0>")
        self.remove_pin('bot_p')
        self.remove_pin('bot_n')
        self.rename_pin('vref', 'vref<2:0>')
        self.remove_pin('clk_sel')

        # self.replace_instance_master('XCOMP', 'skywater130_bag3_sar_adc', 'strongarm_tri')
        comp_conn = [('VDD', 'VDD'), ('VSS', 'VSS'),
                     ('inp', 'top_p'), ('inn', 'top_n'), ('osn', 'osn'), ('osp', 'osp'),
                     ('outp', 'comp_p'), ('outn', 'comp_n'), ('stop', 'state<0>'),
                     ('clk', 'comp_clk'), ]
        if tri_sa:
            comp_conn.append(('clkb', 'comp_clkb'))
        self.instances['XCOMP'].design(**comp)
        for con_pair in comp_conn:
            self.reconnect_instance_terminal('XCOMP', con_pair[0], con_pair[1])

        self.instances['XLOGIC'].design(**logic)
        [self.instances[inst].design(**cdac) for inst in ['XDACN', 'XDACP']]

        logic_conn = [(f"state<{nbits - 1}:0>", f"state<{nbits - 1}:0>"),
                      (f"data_out<{nbits - 1}:0>", f"data_out<{nbits - 1}:0>"),
                      (f"dm<{nbits - 1}:0>", f"dm<{nbits - 1}:0>"),
                      (f"dn<{nbits - 1}:0>", f"dn<{nbits - 1}:0>"),
                      (f"dp<{nbits - 1}:0>", f"dp<{nbits - 1}:0>"), ]
        self.instances['XLOGIC'].design(**logic)
        for con_pair in logic_conn:
            self.reconnect_instance_terminal('XLOGIC', con_pair[0], con_pair[1])

        # Buffer connections
        self.instances['XBUFN'].design(**buf)
        self.instances['XBUFP'].design(**buf)
        bufn_conn = [('VDD', 'VDD'), ('VSS', 'VSS'),
                     (f'din0<{nbits - 1}:0>', f'dn<{nbits - 1}:0>'),
                     (f'din1<{nbits - 1}:0>', f'dm<{nbits - 1}:0>'),
                     (f'din2<{nbits - 1}:0>', f'dp<{nbits - 1}:0>'),
                     (f'dout0<{nbits - 1}:0>', f'bufnn<{nbits - 1}:0>'),
                     (f'dout1<{nbits - 1}:0>', f'bufnm<{nbits - 1}:0>'),
                     (f'dout2<{nbits - 1}:0>', f'bufnp<{nbits - 1}:0>')]
        bufp_conn = [('VDD', 'VDD'), ('VSS', 'VSS'),
                     (f'din0<{nbits - 1}:0>', f'dp<{nbits - 1}:0>'),
                     (f'din1<{nbits - 1}:0>', f'dm<{nbits - 1}:0>'),
                     (f'din2<{nbits - 1}:0>', f'dn<{nbits - 1}:0>'),
                     (f'dout0<{nbits - 1}:0>', f'bufpn<{nbits - 1}:0>'),
                     (f'dout1<{nbits - 1}:0>', f'bufpm<{nbits - 1}:0>'),
                     (f'dout2<{nbits - 1}:0>', f'bufpp<{nbits - 1}:0>')]
        for con_pair in bufn_conn:
            self.reconnect_instance_terminal('XBUFN', con_pair[0], con_pair[1])
        for con_pair in bufp_conn:
            self.reconnect_instance_terminal('XBUFP', con_pair[0], con_pair[1])

        dac_conn_p = [(f"vref<2:0>", f"vref<2:0>"), ('sam_b', 'hold'), ('top', 'top_p'),
                      (f"ctrl_m<{nbits - idx}:0>", f"bufpm<{nbits - 1}:0>"),
                      (f"ctrl_p<{nbits - idx}:0>", f"bufpp<{nbits - 1}:0>"),
                      (f"ctrl_n<{nbits - idx}:0>", f"bufpn<{nbits - 1}:0>")]

        dac_conn_n = [(f"vref<2:0>", f"vref<2:0>"), ('sam_b', 'hold'), ('top', 'top_n'),
                      (f"ctrl_m<{nbits - idx}:0>", f"bufnm<{nbits - 1}:0>"),
                      (f"ctrl_p<{nbits - idx}:0>", f"bufnp<{nbits - 1}:0>"),
                      (f"ctrl_n<{nbits - idx}:0>", f"bufnn<{nbits - 1}:0>")]

        for pname in self.instances['XDACN'].master.pins.keys():
            if 'bot' in pname:
                dac_conn_n.append((pname, pname.replace('bot', 'bot_n')))
                dac_conn_p.append((pname, pname.replace('bot', 'bot_p')))

        for con_pair in dac_conn_n:
            self.reconnect_instance_terminal('XDACN', con_pair[0], con_pair[1])
        for con_pair in dac_conn_p:
            self.reconnect_instance_terminal('XDACP', con_pair[0], con_pair[1])

        # self.reconnect_instance_terminal('XDACN', 'sam_e', 'clk_e')
        # self.reconnect_instance_terminal('XDACP', 'sam_e', 'clk_e')
        # self.reconnect_instance_terminal('XDACN', 'sam_e_b', 'clk_e_b')
        # self.reconnect_instance_terminal('XDACP', 'sam_e_b', 'clk_e_b')
        # self.reconnect_instance_terminal('XDACN', 'sam', 'clk_b')
        # self.reconnect_instance_terminal('XDACP', 'sam', 'clk_b')
