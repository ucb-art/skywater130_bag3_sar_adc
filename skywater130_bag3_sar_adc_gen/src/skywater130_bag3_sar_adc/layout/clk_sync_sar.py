from typing import Any, Optional, Type, Dict

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.layout.routing import TrackID
from bag.layout.template import TemplateDB
from bag.util.immutable import Param
from skywater130_bag3_sar_adc.layout.digital import InvChainCore
from skywater130_bag3_sar_adc.layout.util_orig import fill_tap, export_xm_sup
from skywater130_bag3_sar_adc.layout.vco_cnter_dec import CnterAsync
from pybag.enum import RoundMode, MinLenMode
from xbase.layout.enum import SubPortMode, MOSWireType
from xbase.layout.mos.base import MOSBasePlaceInfo, MOSBase
from xbase.layout.mos.placement.data import TilePatternElement, TilePattern


class SyncClkGen(MOSBase):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'sar_sync_clk')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            seg_dict='Number of segments.',
            w_n='nmos width',
            w_p='pmos width',
            ridx_n='index for nmos row',
            ridx_p='index for pmos row',
            cnter_params='Ring parameters',
            pinfo='Pinfo for unit row strongArm flop',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_n=4,
            w_p=4,
            ridx_n=0,
            ridx_p=-1
        )

    def draw_layout(self) -> None:
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        cnter_params: Param = self.params['cnter_params']
        seg_dict: Dict[str, Any] = self.params['seg_dict']
        w_n, w_p = self.params['w_n'], self.params['w_p']
        ridx_n, ridx_p = self.params['ridx_n'], self.params['ridx_p']

        cnter_master: MOSBase = self.new_template(CnterAsync, params=cnter_params.copy(
            append=(dict(pinfo=pinfo, export_output=True))))
        cnter_nrows = cnter_master.num_tile_rows
        tile_ele = []
        for idx in range(cnter_nrows + 4):
            tile_ele.append(cnter_master.get_tile_subpattern(0, 1, flip=bool(idx & 1)))
        tile_ele = TilePatternElement(TilePattern(tile_ele))
        self.draw_base((tile_ele, cnter_master.draw_base_info[1]))

        pg0_tidx = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-1, tile_idx=0)
        pg1_tidx = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-2, tile_idx=0)
        seg_buf_in, seg_buf_out, seg_buf_comp_clk = seg_dict['buf_in'], seg_dict['buf_out'], seg_dict['buf_comp_clk']
        buf_in_params = dict(pinfo=pinfo, seg_list=seg_buf_in, w_p=w_p, w_n=w_n, ridx_n=ridx_n, ridx_p=ridx_p,
                             vertical_sup=False, dual_output=True, sig_locs={})
        buf_out_params = dict(pinfo=pinfo, seg_list=seg_buf_out, w_p=w_p, w_n=w_n, ridx_n=ridx_n, ridx_p=ridx_p,
                              vertical_sup=False, dual_output=False, sig_locs={})
        buf_comp_clk_params = dict(pinfo=pinfo, seg_list=seg_buf_comp_clk, w_p=w_p, w_n=w_n,
                                   ridx_n=ridx_n, ridx_p=ridx_p, vertical_sup=False, dual_output=True,
                                   sig_locs={'nin0': pg0_tidx, 'nin1': pg1_tidx})

        buf_in_master: MOSBase = self.new_template(InvChainCore, params=buf_in_params)
        buf_out_master: MOSBase = self.new_template(InvChainCore, params=buf_out_params)
        buf_comp_clk_master: MOSBase = self.new_template(InvChainCore, params=buf_comp_clk_params)

        cnter_ncol = cnter_master.num_cols
        nrows = cnter_master.num_tile_rows

        # Floorplan:
        # in buffer
        # comp clk buffer
        #
        # divider
        #
        # out buffer

        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        ym_layer = xm_layer + 1
        xm1_layer = ym_layer + 1
        ym1_layer = xm1_layer + 1
        min_sep = self.min_sep_col

        tile_height = self.get_tile_pinfo(0).height

        # Get track info
        cur_loc = 0
        cnter_col = max(cnter_master.mid_col, buf_in_master.num_cols) - cnter_master.mid_col
        cnter_col += cnter_col & 1

        cnter = self.add_tile(cnter_master, 2, cnter_col)
        tap_sep = self.min_sep_col
        tap_sep += tap_sep & 1
        min_tap_ncols = self.tech_cls.min_sub_col + 2 * tap_sep + 4

        cur_loc += int(not (cur_loc & 1))
        cnter_mid_col = max(cnter_col + cnter_master.mid_col + min_sep // 2 + min_sep,
                            cur_loc + buf_in_master.num_cols + min_tap_ncols)
        cnter_mid_col += int(not (cnter_mid_col & 1))

        # Add buffers
        buf_out = self.add_tile(buf_out_master, 1, cnter_mid_col)
        buf_comp_clk = self.add_tile(buf_comp_clk_master, cnter_master.num_tile_rows + 2, cnter_mid_col)
        buf_in = self.add_tile(buf_in_master, cnter_master.num_tile_rows + 2, cur_loc)
        tot_cols = max(cnter_col+cnter_master.num_cols+min_sep,
                       cnter_mid_col + buf_comp_clk_master.num_cols + min_sep)
        self.set_mos_size(tot_cols)

        # Clock in
        tr_manager = self.tr_manager
        tr_w_sig_vm = tr_manager.get_width(vm_layer, 'sig')
        clk_in_vm_tidx = self.grid.coord_to_track(vm_layer, buf_in.bound_box.xl, RoundMode.NEAREST)
        clk_in_vm = self.connect_to_tracks(buf_in.get_pin('nin'), TrackID(vm_layer, clk_in_vm_tidx-1, tr_w_sig_vm),
                                           min_len_mode=MinLenMode.MIDDLE)

        self.connect_to_track_wires([buf_in.get_pin('nout'), buf_in.get_pin('pout')], cnter.get_pin('clkp'))
        self.connect_to_track_wires([buf_in.get_pin('noutb'), buf_in.get_pin('poutb')], cnter.get_pin('clkn'))
        
        for idx in range(1, self.num_tile_rows):
            r0_hm, r1_hm = fill_tap(self, idx, extra_margin=(idx == self.num_tile_rows - 1), port_mode=SubPortMode.ODD)
            self.extend_wires(r0_hm + r1_hm, lower=self.bound_box.xl, upper=self.bound_box.xh)

        self.connect_to_track_wires(buf_in.get_pin('outb'), buf_comp_clk.get_pin('nin'))
        self.connect_to_track_wires(cnter.get_pin('final_outp'), buf_out.get_pin('nin'))

        vdd_xm_list, vss_xm_list = [], []
        # _b, _t = export_xm_sup(self, 0, export_bot=True, export_top=True)
        # vdd_xm_list.append(_t)
        # vss_xm_list.append(_b)
        # _, _t = export_xm_sup(self, self.num_tile_rows - 1, export_top=True)
        # vdd_xm_list.append(_t)
        vdd_xm_list.extend(cnter.get_all_port_pins('VDD_xm'))
        vss_xm_list.extend(cnter.get_all_port_pins('VSS_xm'))
        # vdd_xm_list = self.extend_wires(vdd_xm_list, lower=self.bound_box.xl, upper=self.bound_box.xh)
        # vss_xm_list = self.extend_wires(vss_xm_list, lower=self.bound_box.xl, upper=self.bound_box.xh)

        self.add_pin('VDD', vdd_xm_list, show=self.show_pins, connect=True)
        self.add_pin('VSS', vss_xm_list, show=self.show_pins, connect=True)
        self.add_pin('VDD', buf_in.get_all_port_pins('VDD'), show=self.show_pins, connect=True)
        self.add_pin('VSS', buf_in.get_all_port_pins('VSS'), show=self.show_pins, connect=True)
        self.add_pin('VDD', buf_out.get_all_port_pins('VDD'),show=self.show_pins,  connect=True)
        self.add_pin('VSS', buf_out.get_all_port_pins('VSS'),show=self.show_pins,  connect=True)


        self.add_pin('clk_out', buf_out.get_pin('out'))
        self.add_pin('clk_comp', buf_comp_clk.get_pin('outb'))
        self.add_pin('clk_compn', buf_comp_clk.get_pin('out'))
        self.add_pin('clk_in', clk_in_vm)

        self._sch_params = dict(
            buf_in=buf_in_master.sch_params,
            buf_out=buf_out_master.sch_params,
            buf_comp=buf_comp_clk_master.sch_params,
            div=cnter_master.sch_params,
        )
