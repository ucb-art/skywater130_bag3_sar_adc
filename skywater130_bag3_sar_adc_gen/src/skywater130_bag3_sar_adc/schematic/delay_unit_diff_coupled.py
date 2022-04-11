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
class skywater130_bag3_sar_adc__delay_unit_diff_coupled(Module):
    """Module for library skywater130_bag3_sar_adc cell delay_unit_diff_coupled.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__, str(Path('netlist_info', 'delay_unit_diff_coupled.yaml')))

    def __init__(self, database: ModuleDB, params: Param, **kwargs: Any) -> None:
        Module.__init__(self, self.yaml_file, database, params, **kwargs)

    @classmethod
    def get_params_info(cls):  # type: () -> Dict[str, str]
        """Returns a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : Optional[Dict[str, str]]
            dictionary from parameter names to descriptions.
        """
        return dict(
            lch='channel length',
            nth='nMOS threshold',
            pth='pMOS threshold',
            wn='nMOS width',
            wp='pMOS width',
            wp_coupled='coupled pMOS width',
            wn_coupled='coupled nMOS width',
            seg_n='nMOS number of finger',
            seg_p='pMOS number of finger',
            seg_n_coupled='coupled nMOS number of finger',
            seg_p_coupled='coupled pMOS number of finger',
            self_coupled='true to differential inverters output couple to each other',
            out_buf='True to enable output buffer',
        )

    @classmethod
    def get_default_param_values(cls):  # type: () -> Dict[str, Any]
        return dict(
            self=False,
            out_buf=False,
        )

    def design(self, lch, nth, pth, wn, wp, wp_coupled, wn_coupled, seg_n, seg_p, seg_n_coupled,
               seg_p_coupled, self_coupled, out_buf):
        self.instances['XNN'].design(l=lch, w=wn, intent=nth, nf=seg_n)
        self.instances['XPN'].design(l=lch, w=wn, intent=nth, nf=seg_n)
        self.instances['XNP'].design(l=lch, w=wp, intent=pth, nf=seg_p)
        self.instances['XPP'].design(l=lch, w=wp, intent=pth, nf=seg_p)

        wn = wn_coupled if wn_coupled is not None else wn
        wp = wp_coupled if wp_coupled is not None else wp
        self.instances['XNN_coupled'].design(l=lch, w=wn_coupled, intent=nth, nf=seg_n_coupled)
        self.instances['XPN_coupled'].design(l=lch, w=wn_coupled, intent=nth, nf=seg_n_coupled)
        self.instances['XNP_coupled'].design(l=lch, w=wp_coupled, intent=pth, nf=seg_p_coupled)
        self.instances['XPP_coupled'].design(l=lch, w=wp_coupled, intent=pth, nf=seg_p_coupled)

        if self_coupled:
            self.remove_pin('in_n_coupled')
            self.remove_pin('in_p_coupled')
            self.reconnect_instance_terminal('XNP_coupled', 'G', 'out_n')
            self.reconnect_instance_terminal('XNN_coupled', 'G', 'out_n')
            self.reconnect_instance_terminal('XPP_coupled', 'G', 'out_p')
            self.reconnect_instance_terminal('XPN_coupled', 'G', 'out_p')

