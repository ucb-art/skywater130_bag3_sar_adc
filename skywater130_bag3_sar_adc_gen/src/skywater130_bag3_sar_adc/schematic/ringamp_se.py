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
class skywater130_bag3_sar_adc__ringamp_se(Module):
    """Module for library skywater130_bag3_sar_adc cell ringamp_se.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'ringamp_se.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            lch='channel length',
            seg_dict='transistor segments dictionary.',
            w_dict='transistor width dictionary.',
            th_dict='transistor threshold dictionary.',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict()

    def design(self, lch: int, seg_dict: Mapping[str, int], w_dict: Mapping[str, int], th_dict: Mapping[str, str])\
            -> None:
        for name in ['in', 'mid', 'out', 'dzd', 'be', 'bias']:
            uname = name.upper()
            pname = f'p{name}'
            nname = f'n{name}'
            if nname in seg_dict and pname in seg_dict:
                self.instances[f'X{uname}_P'].design(l=lch, w=w_dict[pname], nf=seg_dict[pname], intent=th_dict[pname])
                self.instances[f'X{uname}_N'].design(l=lch, w=w_dict[nname], nf=seg_dict[nname], intent=th_dict[nname])
            else:
                self.remove_instance(f'X{uname}_P')
                self.remove_instance(f'X{uname}_N')
        if 'nbe' not in seg_dict and 'pbe' not in seg_dict:
            self.reconnect_instance_terminal('XIN_N', 'D', 'mid')
            self.reconnect_instance_terminal('XIN_P', 'D', 'mid')
            self.reconnect_instance_terminal('XMID_N', 'G', 'mid')
            self.reconnect_instance_terminal('XMID_P', 'G', 'mid')
