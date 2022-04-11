# -*- coding: utf-8 -*-

import pkg_resources
from pathlib import Path
from typing import Mapping, Any

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.util.immutable import Param


# noinspection PyPep8Naming
class skywater130_bag3_sar_adc__clk_global(Module):
    """Module for library skywater130_bag3_sar_adc cell clk_global.

    Fill in high level description here.
    """

    yaml_file = pkg_resources.resource_filename(__name__,
                                                str(Path('netlist_info',
                                                         'clk_global.yaml')))

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
            inv_diff='',
            div2='',
            div4='',
        )

    def design(self, inv_diff, div2, div4) -> None:
        self.instances['XPHASE_CORR'].design(**inv_diff)
        self.reconnect_instance('XDIV2', [('VDD', 'VDD'), ('VSS', 'VSS'), ('clkn', 'clkn_int'), ('clkp', 'clkp_int'),
                                          ('midn<1:0>', 'noconn_n0<1:0>'), ('midp<1:0>', 'noconn_p0<1:0>'),
                                          ('outn<1:0>', 'midn<1:0>'), ('outp<1:0>', 'midp<1:0>')])
        self.instances['XDIV2'].design(**div2)
        self.reconnect_instance('XDIV40', [('VDD', 'VDD'), ('VSS', 'VSS'), ('clkn', 'midn<1>'), ('clkp', 'midp<1>'),
                                           ('midn<1:0>', 'div40_midn<1:0>'), ('midp<1:0>', 'div40_midp<1:0>'),
                                           ('outn<1:0>', 'out<4>,out<0>'), ('outp<1:0>', 'out<6>,out<2>'),
                                           ('inn', 'div41_midp<1>'), ('inp', 'div41_midn<1>')])
        self.instances['XDIV40'].design(**div4)
        self.reconnect_instance('XDIV41', [('VDD', 'VDD'), ('VSS', 'VSS'), ('clkn', 'midn<1>'), ('clkp', 'midp<1>'),
                                           ('midn<1:0>', 'div41_midn<1:0>'), ('midp<1:0>', 'div41_midp<1:0>'),
                                           ('outn<1:0>', 'out<5>,out<1>'), ('outp<1:0>', 'out<7>,out<3>'),
                                           ('inn', 'div40_midn<1>'), ('inp', 'div40_midp<1>')])
        self.instances['XDIV41'].design(**div4)
        self.rename_pin('out', 'out<7:0>')
