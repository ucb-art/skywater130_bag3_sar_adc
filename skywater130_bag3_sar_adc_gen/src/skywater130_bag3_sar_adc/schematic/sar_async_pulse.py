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

from typing import Dict, Any

import pkg_resources
from pathlib import Path

from bag.design.module import Module
from bag.design.database import ModuleDB
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__sar_async_pulse(Module):
    """Module for library skywater130_bag3_sar_adc cell sar_async_pulse.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'sar_async_pulse.yaml')))

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
            buf='Parameters for output buffer',
            seg_rstp='segment for reset p',
            seg_rstn='segment for reset n',
            seg_nandp='segment for nand stack p',
            seg_nandn='segment for nand stack n',
            lch='channel length',
            wn='n-fet width',
            wp='p-fet width',
            intent='dev-type for tx other than buf',
        )

    def design(self, seg_nandp: int, seg_nandn: int, seg_rstp: int, seg_rstn: int, lch: int,
               wn: int, wp: int, intent: str, buf: Param) -> None:
        self.instances['XBUF'].design(**buf)
        self.instances['XP_RST'].design(l=lch, nf=seg_rstp, intent=intent, w=wp)
        self.instances['XN_RST'].design(l=lch, nf=seg_rstn, intent=intent, w=wn)
        self.instances['XP_PULSE'].design(lch=lch, seg=seg_nandp, intent=intent, w=wp, stack=1)
        self.rename_instance('XP_PULSE', 'XP_PULSE<1:0>', [('g', 'done,done_d')])
        self.instances['XN_PULSE'].design(lch=lch, seg=seg_nandn, intent=intent, w=wn, stack=2)


