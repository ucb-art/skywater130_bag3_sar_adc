# SPDX-License-Identifier: Apache-2.0
# Copyright 2020 Blue Cheetah Analog Design Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-

from typing import Dict, Any, Mapping

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__comp_dyn_latch(Module):
    """Module for library skywater130_bag3_sar_adc cell comp_dyn_latch.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'comp_dyn_latch.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            lch='channel length',
            seg_dict='transistor segments dictionary.',
            w_dict='transistor width dictionary.',
            th_dict='transistor threshold dictionary.',
            has_rst='True to add reset dev',
            flip_np='Flip NMOS and PMOS',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            has_rst=False,
            flip_np=False
        )

    def design(self, lch: int, seg_dict: Mapping[str, int], w_dict: Mapping[str, int], th_dict: Mapping[str, str],
               has_rst: bool, flip_np: bool) -> None:
        if flip_np:
            self.replace_instance_master(f'XINP', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XINN', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XINP_M', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XINN_M', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XPFBP', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XPFBN', 'BAG_prim', 'nmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XNFBP', 'BAG_prim', 'pmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XNFBN', 'BAG_prim', 'pmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XTAILP', 'BAG_prim', 'pmos4_standard', keep_connections=True)
            self.replace_instance_master(f'XTAILN', 'BAG_prim', 'pmos4_standard', keep_connections=True)
            self.rename_instance('XNFBN', 'XPFBNt')
            self.rename_instance('XNFBP', 'XPFBPt')
            self.rename_instance('XPFBN', 'XNFBN')
            self.rename_instance('XPFBP', 'XNFBP')
            self.rename_instance('XPFBNt', 'XPFBN')
            self.rename_instance('XPFBPt', 'XPFBP')

            for inst_name in ['XINP', 'XINN', 'XINP_M', 'XINN_M', 'XNFBN', 'XNFBP']:
                self.reconnect_instance(inst_name, [('B', 'VSS'), ('S', 'VSS')])
            for inst_name in ['XPFBP', 'XPFBN', 'XTAILP', 'XTAILN']:
                self.reconnect_instance(inst_name, [('B', 'VDD')])
            self.reconnect_instance('XTAILN', [('S', 'VDD')])
            self.reconnect_instance('XTAILP', [('S', 'VDD')])

        for name in ['in', 'tail', 'nfb', 'pfb']:
            uname = name.upper()
            w = w_dict[name]
            nf = seg_dict[name]
            intent = th_dict[name]
            if 'tail' in name:
                nf = nf//2
            self.instances[f'X{uname}P'].design(l=lch, w=w, nf=nf, intent=intent)
            self.instances[f'X{uname}N'].design(l=lch, w=w, nf=nf, intent=intent)
        if has_rst:
            self.instances['XINP_M'].design(l=lch, w=w_dict['rst'], nf=seg_dict['rst'], intent=th_dict['rst'])
            self.instances['XINN_M'].design(l=lch, w=w_dict['rst'], nf=seg_dict['rst'], intent=th_dict['rst'])
            self.reconnect_instance('XTAILN', [('G', 'inn_m')])
            self.reconnect_instance('XTAILP', [('G', 'inp_m')])
        else:
            self.delete_instance('XINP_M')
            self.delete_instance('XINN_M')
            self.remove_pin('inn_m')
            self.remove_pin('inp_m')
            self.reconnect_instance('XTAILN', [('D', 'tail')])
            self.reconnect_instance('XTAILP', [('D', 'tail')])
            self.reconnect_instance('XPFBN' if flip_np else 'XNFBN', [('S', 'tail')])
            self.reconnect_instance('XPFBP' if flip_np else 'XNFBP', [('S', 'tail')])
