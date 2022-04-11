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

from typing import Dict, List, Tuple, Any, Mapping

import warnings
import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__bootstrap_fast(Module):
    """Module for library skywater130_bag3_sar_adc cell bootstrap_fast.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__, str(Path('netlist_info', 'bootstrap_fast.yaml')))

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
            lch='channel length of transistors',
            intent='device intent',
            dev_info='devices information including nf, w and stack',
            dum_info='dummy information including nf, w and stack',
            cap_params='capacitor parameters',
            cap_aux_params='capacitor parameters',
            fast_on='True to turn-on XON_N fast',
            break_outputs='True to break output signals'
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            dum_info=[],
            cap_aux_params=None,
            cap_params=None,
            break_outputs=True,
            fast_on=True
        )

    def design(self, lch: int, intent: str, dev_info: Mapping[str, Any], dum_info: List[Tuple[Any]],
               cap_params: Mapping[str, Any], cap_aux_params: Mapping[str, Any], fast_on: bool,
               break_outputs: bool) -> None:

        if break_outputs:
            sampler_info = dev_info['XSAMPLE']
            dev_info = dev_info.copy(remove=['XSAMPLE'])
            nout = sampler_info['nf']//2
            self.rename_instance('XSAMPLE', f'XSAMPLE<{nout-1}:0>', conn_list=[('D', f'out<{nout-1}:0>')])
            self.instances[f'XSAMPLE<{nout-1}:0>'].design(l=lch, intent=sampler_info.get('intent', intent),
                                             w=sampler_info.get('w', 4), stack=sampler_info.get('stack', 1),
                                             nf=2)
            if 'XSAMPLE_DUM' in dev_info.keys():
                sampler_info = dev_info['XSAMPLE_DUM']
                dev_info = dev_info.copy(remove=['XSAMPLE_DUM'])
                nout = sampler_info['nf'] // 2
                self.rename_instance('XSAMPLE_DUM', f'XSAMPLE_DUM<{nout - 1}:0>', conn_list=[('D', f'out<{nout - 1}:0>')])
                self.instances[f'XSAMPLE_DUM<{nout - 1}:0>'].design(l=lch, intent=sampler_info.get('intent', intent),
                                                 w=sampler_info.get('w', 4), stack=sampler_info.get('stack', 1),
                                                 nf=2)
            self.rename_pin('out', f'out<{nout-1}:0>')
        else:
            if 'XSAMPLE_DUM' not in dev_info.keys():
                warnings.warn("Doesn't implement dummhy samlping sw")
                self.remove_pin('in_c')
                self.delete_instance('XSAMPLE_DUM')

        if not fast_on:
            self.delete_instance('XINV_P_VG2')
            self.delete_instance('XINV_N0_VG2')
            self.delete_instance('XINV_N1_VG2')
            self.reconnect_instance_terminal('XON_N', 'G', 'vg')
            self.remove_pin('vg2')

        if 'XSAMPLE_INVP<1>' not in dev_info.keys():
            [self.remove_instance(instname) for instname in ['XSAMPLE_INVP<1>', 'XSAMPLE_INVN<1>',
                                                             'XSAMPLE_INVP<0>', 'XSAMPLE_INVN<0>', 'XINV_N_BUF']]
            # self.reconnect_instance_terminal('XINV_N', 'G', 'sample')
            # self.reconnect_instance_terminal('XINV_N', 'S', 'cap_bot')
        if 'XPRE' not in dev_info.keys():
            self.remove_instance('XPRE')

        if 'XCAP_P_AUX' not in dev_info.keys():
            self.remove_pin('cap_top_aux')
            self.delete_instance('XCAP_P_AUX')
            self.reconnect_instance_terminal('XCAP_P', 'B', 'cap_top')
            self.reconnect_instance_terminal('XON_P', 'B', 'cap_top')
            if fast_on:
                self.reconnect_instance_terminal('XINV_P_VG2', 'B', 'cap_top')
                self.reconnect_instance_terminal('XINV_P_VG2', 'S', 'cap_top')

        for key, _info in dev_info.items():
            _w = _info.get('w', 4)
            _stack = _info.get('stack', 1)
            _intent = _info.get('intent', intent)
            self.instances[key].design(l=lch, intent=_intent, w=_w, nf=_info['nf'], stack=_stack)
        if dum_info:
            self.design_dummy_transistors(dum_info, 'X_DUMMY', 'VDD', 'VSS')
        else:
            self.delete_instance('X_DUMMY')

        if cap_params is None:
            self.delete_instance('X_CBOOT')
        else:
            self.instances['X_CBOOT'].design(**cap_params)
        if cap_aux_params is None:
            self.delete_instance('X_CAUX')
        else:
            self.instances['X_CAUX'].design(**cap_params)

