from itertools import chain
from typing import Any, Dict, Type, Optional, Tuple
from typing import Mapping, Union

from bag.design.database import ModuleDB
from bag.design.module import Module
from bag.layout.routing.base import TrackID, TrackManager
from bag.layout.template import TemplateDB
from bag.util.immutable import ImmutableSortedDict
from bag.util.immutable import Param
from bag.util.math import HalfInt
from skywater130_bag3_sar_adc.layout.util.util import fill_conn_layer_intv
from skywater130_bag3_sar_adc.layout.vco_ring_osc import RingOscUnit
from pybag.enum import RoundMode, MinLenMode, Direction
from xbase.layout.enum import MOSWireType
from xbase.layout.mos.base import MOSBasePlaceInfo, MOSBase

""" 
Generators for StrongArm flops used in VCO-based ADC

- Because the VCO is arrayed vertically, all flops are 
designed to match VCO height (1 PMOS and 1 NMOS row)
- Schematic generators reuse preamp and dynamic latch in 
SAR comparator
"""


class PreAmpDigHalf(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg_dict='segments dictionary.',
            w_dict='widths dictionary.',
            ridx_n='bottom nmos row index.',
            ridx_p='pmos row index.',
            vertical_out='True to connect outputs to vm_layer.',
            vertical_sup='True to connect outputs to vm_layer.',
            sig_locs='Optional dictionary of user defined signal locations',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_dict={},
            sig_locs={},
            ridx_n=0,
            ridx_p=-1,
            vertical_out=True,
            vertical_sup=True,
        )

    def draw_layout(self):
        place_info = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(place_info)

        seg_dict: ImmutableSortedDict[str, int] = self.params['seg_dict']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']
        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']
        vertical_sup: bool = self.params['vertical_sup']

        w_dict, th_dict = self._get_w_th_dict(ridx_n, ridx_p)

        seg_in = seg_dict['in']
        seg_tail = seg_dict['tail']
        seg_load = seg_dict['load']

        w_in = w_dict['in']
        w_tail = w_dict['tail']
        w_load = w_dict['load']

        if seg_in & 1 or (seg_tail % 4 != 0) or seg_load & 1:
            raise ValueError('in, tail, nfb, or pfb must have even number of segments')
        seg_tail = seg_tail // 2
        seg_in = seg_in
        seg_load = seg_load

        # placement
        m_tail = self.add_mos(ridx_n, 1, seg_tail, w=w_tail)
        m_in = self.add_mos(ridx_n, 1 + seg_tail, seg_in, w=w_in)
        m_load = self.add_mos(ridx_p, 0, seg_load, w=w_load, g_on_s=True)
        tail_conn = [m_tail.s, m_in.s]
        clk_conn = m_tail.g

        nclk_tid = self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0)
        tail_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig')
        pclk_tid = self.get_track_id(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-1)
        nout_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig', wire_idx=-1)
        pout_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sig', wire_idx=-1)

        supply_shield_tid = [self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=-2),
                             self.get_track_id(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=1)]

        # NOTE: force even number of columns to make sure VDD conn_layer wires are on even columns.
        ncol_tot = self.num_cols
        self.set_mos_size(num_cols=ncol_tot + (ncol_tot & 1))

        # routing
        conn_layer = self.conn_layer
        hm_layer = conn_layer + 1
        vm_layer = conn_layer + 2
        clk_vm_w = self.tr_manager.get_width(vm_layer, 'clk')
        sig_vm_w = self.tr_manager.get_width(vm_layer, 'sig')

        tail = self.connect_to_tracks(tail_conn, tail_tid)
        if vertical_sup:
            vdd = m_load.s
            vss = m_tail.d
        else:
            vdd_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sup')
            vdd = self.connect_to_tracks([m_load.s], vdd_tid)
            vss_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sup')
            vss = self.connect_to_tracks(m_tail.d, vss_tid)

        # -- Connect middle node --
        # self.connect_to_tracks(mid_conn, mid_tid)

        nclk = self.connect_to_tracks(clk_conn, pclk_tid)
        pclk = self.connect_to_tracks(m_load.g, pclk_tid)
        nout = self.connect_to_tracks(m_in.d, nout_tid, min_len_mode=MinLenMode.UPPER)
        pout = self.connect_to_tracks(m_load.d, pout_tid, min_len_mode=MinLenMode.UPPER)

        clk_vm_tidx = self.arr_info.col_to_track(vm_layer, 0, mode=RoundMode.NEAREST)
        clk_vm_tidx = sig_locs.get('clk', clk_vm_tidx)
        clk_vm = self.connect_to_tracks([nclk, pclk], TrackID(vm_layer, clk_vm_tidx, width=clk_vm_w))

        out_vm_tidx = self.arr_info.col_to_track(vm_layer, seg_tail + seg_in // 2, mode=RoundMode.NEAREST)
        out_vm_tidx = sig_locs.get('out', out_vm_tidx)
        out_vm = self.connect_to_tracks([nout, pout], TrackID(vm_layer, out_vm_tidx, width=sig_vm_w))

        # Shield output
        conn_layer_shiled_tidx = self.arr_info.col_to_track(conn_layer, self.num_cols, mode=RoundMode.NEAREST)
        conn_layer_shield = self.connect_to_tracks(vdd, TrackID(conn_layer, conn_layer_shiled_tidx))
        self.connect_to_tracks(conn_layer_shield, supply_shield_tid[0], track_lower=self.bound_box.xl)
        self.connect_to_tracks(conn_layer_shield, supply_shield_tid[1], track_lower=self.bound_box.xl)

        self.add_pin('clk_vm', clk_vm)
        self.add_pin('tail', tail)
        self.add_pin('clk', clk_vm)
        self.add_pin('in', m_in.g)
        self.add_pin('pout', pout)
        self.add_pin('nout', nout)
        self.add_pin('out', out_vm)

        self.add_pin('VSS', vss)
        self.add_pin('VDD', vdd, connect=True)

        self.sch_params = dict(
            lch=self.arr_info.lch,
            seg_dict=seg_dict,
            w_dict=w_dict,
            th_dict=th_dict,
            has_cas=False
        )

    def _get_w_th_dict(self, ridx_n: int, ridx_p: int, ) \
            -> Tuple[ImmutableSortedDict[str, int], ImmutableSortedDict[str, str]]:
        w_dict: Mapping[str, int] = self.params['w_dict']

        w_ans = {}
        th_ans = {}
        for name, row_idx in [('tail', ridx_n), ('in', ridx_n), ('load', ridx_p)]:
            rinfo = self.get_row_info(row_idx, 0)
            w = w_dict.get(name, 0)
            if w == 0:
                w = rinfo.width
            w_ans[name] = w
            th_ans[name] = rinfo.threshold

        return ImmutableSortedDict(w_ans), ImmutableSortedDict(th_ans)


class PreAmpDig(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'comp_preamp')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        ans = PreAmpDigHalf.get_params_info()
        ans['even_center'] = 'True to force center column to be even.'
        ans['flip_preamp_io'] = 'True to flip preamp input output, easy to connect to cnter'
        return ans

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = PreAmpDigHalf.get_default_param_values()
        ans['even_center'] = False
        ans['flip_preamp_io'] = False
        return ans

    def draw_layout(self):
        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']

        master: PreAmpDigHalf = self.new_template(PreAmpDigHalf, params=self.params)
        self.draw_base(master.draw_base_info)

        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1

        # placement
        nsep = 0
        nhalf = master.num_cols
        corel = self.add_tile(master, 0, nhalf, flip_lr=True)
        corer = self.add_tile(master, 0, nhalf + nsep)
        self.set_mos_size(num_cols=nsep + 2 * nhalf)

        # Routing
        # -- Get track index --
        inn_tidx, hm_w = self.get_track_info(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0)
        inp_tidx = self.get_track_index(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0)
        outn_tidx = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=0)
        outp_tidx = self.get_track_index(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=-1)

        if self.params['flip_preamp_io']:
            inn_tidx, inp_tidx, outn_tidx, outp_tidx = outn_tidx, outp_tidx, inn_tidx, inp_tidx

        inp_hm = self.connect_to_tracks(corel.get_pin('in'), TrackID(hm_layer, inp_tidx, hm_w),
                                     min_len_mode=MinLenMode.MIDDLE)
        inn_hm = self.connect_to_tracks(corer.get_pin('in'), TrackID(hm_layer, inn_tidx, hm_w),
                                     min_len_mode=MinLenMode.MIDDLE)

        outp, outn = self.connect_differential_tracks(corer.get_pin('out'), corel.get_pin('out'),
                                                      hm_layer, outn_tidx, outp_tidx, width=hm_w)
        inp_vm_tidx = tr_manager.get_next_track(vm_layer, corel.get_pin('out').track_id.base_index,
                                                'sig', 'sig', up=True)
        inn_vm_tidx = tr_manager.get_next_track(vm_layer, corer.get_pin('out').track_id.base_index,
                                                'sig', 'sig', up=False)

        tr_w_sig_vm = tr_manager.get_width(vm_layer, 'sig')
        inp_vm = self.connect_to_tracks(inp_hm, TrackID(vm_layer, inp_vm_tidx, tr_w_sig_vm),
                                        min_len_mode=MinLenMode.MIDDLE)
        inn_vm = self.connect_to_tracks(inn_hm, TrackID(vm_layer, inn_vm_tidx, tr_w_sig_vm),
                                        min_len_mode=MinLenMode.MIDDLE)

        self.connect_wires([corel.get_pin('tail'), corer.get_pin('tail')])

        self.add_pin('inp', inp_vm)
        self.add_pin('inn', inn_vm)

        self.add_pin('outp', outp)
        self.add_pin('outn', outn)

        self.add_pin('VDD', self.connect_wires([corel.get_pin('VDD'), corer.get_pin('VDD')]))
        self.add_pin('VSS', self.connect_wires([corel.get_pin('VSS'), corer.get_pin('VSS')]))
        self.reexport(corel.get_port('clk'))
        self.sch_params = master.sch_params


class DynLatchDigHalf(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg_dict='segments dictionary.',
            w_dict='widths dictionary.',
            ridx_n='bottom nmos row index.',
            ridx_p='pmos row index.',
            sig_locs='Optional dictionary of user defined signal locations',
            flip_np='True to flip nmos and pmos',
            has_rst='True to add reset devices and connect tail to output of previous stage',
            vertical_sup='True to connect outputs to vm_layer.',
            vertical_out='True to connect outputs to vm_layer.',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_dict={},
            ridx_n=0,
            ridx_p=-1,
            sig_locs={},
            has_rst=False,
            flip_np=False,
            vertical_out=True,
            vertical_sup=True,
        )

    def draw_layout(self):
        place_info = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(place_info)

        seg_dict: ImmutableSortedDict[str, int] = self.params['seg_dict']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']
        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']
        flip_np: bool = self.params['flip_np']
        vertical_out: bool = self.params['vertical_out']
        vertical_sup: bool = self.params['vertical_sup']

        ridx_tail = ridx_p if flip_np else ridx_n
        ridx_nfb = ridx_n
        ridx_pfb = ridx_p
        ridx_in = ridx_n if flip_np else ridx_p

        w_dict, th_dict = self._get_w_th_dict(ridx_tail, ridx_nfb, ridx_pfb, ridx_in)
        seg_in = seg_dict['in']
        seg_nfb = seg_dict['nfb']
        seg_pfb = seg_dict['pfb']
        seg_tail = seg_dict['tail']
        w_in = w_dict['in']
        w_tail = w_dict['tail']
        w_nfb = w_dict['nfb']
        w_pfb = w_dict['pfb']

        tr_manager = self.tr_manager

        if seg_in & 1 or (seg_tail % 2 != 0) or seg_nfb & 1 or seg_pfb & 1:
            raise ValueError('in, tail, nfb, or pfb must have even number of segments')
        seg_tail = seg_tail

        # placement
        m_nfb = self.add_mos(ridx_nfb, 0 if flip_np else 0, seg_nfb, g_on_s=not flip_np, w=w_nfb)
        m_pfb = self.add_mos(ridx_pfb, 0 if flip_np else 0, seg_pfb, g_on_s=not flip_np, w=w_pfb)
        m_tail = self.add_mos(ridx_tail, seg_pfb if flip_np else seg_nfb + 1, seg_tail, w=w_tail)
        m_in = self.add_mos(ridx_in, seg_nfb if flip_np else seg_pfb, seg_in, g_on_s=not flip_np, w=w_in)

        nout_tid = self.get_track_id(ridx_nfb, MOSWireType.DS, wire_name='sig', wire_idx=0)
        pout_tid = self.get_track_id(ridx_pfb, MOSWireType.DS, wire_name='sig', wire_idx=-1)

        clk_tid = self.get_track_id(ridx_tail, MOSWireType.G, wire_name='sig', wire_idx=-1 if flip_np else 0)
        tail_tid = self.get_track_id(ridx_pfb if flip_np else ridx_nfb, MOSWireType.DS, wire_name='sig',
                                     wire_idx=0 if flip_np else -1)

        clk_conn = m_tail.g

        # NOTE: force even number of columns to make sure VDD conn_layer wires are on even columns.
        ncol_tot = self.num_cols
        self.set_mos_size(num_cols=ncol_tot + (ncol_tot & 1))
        #
        # routing
        conn_layer = self.conn_layer
        vm_layer = conn_layer + 2
        sig_vm_w = self.tr_manager.get_width(vm_layer, 'sig')

        clk = self.connect_to_tracks(clk_conn, clk_tid)
        out = self.connect_wires([m_nfb.g, m_pfb.g])
        nout = self.connect_to_tracks([m_in.d, m_nfb.d] if flip_np else [m_nfb.d], nout_tid)
        pout = self.connect_to_tracks([m_pfb.d] if flip_np else [m_in.d, m_pfb.d], pout_tid,
                                      min_len_mode=MinLenMode.UPPER)
        tail = self.connect_to_tracks([m_tail.s, m_pfb.s] if flip_np else [m_tail.s, m_nfb.s], tail_tid)
        if flip_np:
            vdd_conn = m_tail.d
            vss_conn = [m_nfb.s, m_in.s]
        else:
            vdd_conn = [m_pfb.s, m_in.s]
            vss_conn = m_tail.d
        if vertical_sup:
            vss=vss_conn
            vdd=vdd_conn
        else:
            vdd_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sup')
            vdd = self.connect_to_tracks(vdd_conn, vdd_tid)
            vss_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sup')
            vss = self.connect_to_tracks(vss_conn, vss_tid)

        if vertical_out:
            vm_tidx = self.arr_info.col_to_track(vm_layer, 2, mode=RoundMode.NEAREST)
            vm_tidx = sig_locs.get('out', vm_tidx)
            out_vm = self.connect_to_tracks([nout, pout], TrackID(vm_layer, vm_tidx, width=sig_vm_w))
            self.add_pin('out_vm', out_vm)
        else:
            self.add_pin('pout', pout)
            self.add_pin('nout', nout)

        self.add_pin('VSS', vss)
        self.add_pin('VDD', vdd)
        self.add_pin('tail', tail)
        self.add_pin('clk', clk)
        self.add_pin('in', m_in.g)
        self.add_pin('out', out)

        self.sch_params = dict(
            lch=self.arr_info.lch,
            seg_dict=seg_dict,
            w_dict=w_dict,
            th_dict=th_dict,
            flip_np=flip_np,
        )

    def _get_w_th_dict(self, ridx_tail: int, ridx_nfb: int, ridx_pfb: int, ridx_in: int) \
            -> Tuple[ImmutableSortedDict[str, int], ImmutableSortedDict[str, str]]:
        w_dict: Mapping[str, int] = self.params['w_dict']
        has_rst: bool = self.params['has_rst']

        w_ans = {}
        th_ans = {}
        for name, row_idx in [('nfb', ridx_nfb), ('in', ridx_in), ('pfb', ridx_pfb), ('tail', ridx_tail)]:
            rinfo = self.get_row_info(row_idx, 0)
            w = w_dict.get(name, 0)
            if w == 0:
                w = rinfo.width
            w_ans[name] = w
            th_ans[name] = rinfo.threshold

        if has_rst:
            rinfo = self.get_row_info(ridx_in, 0)
            w = w_dict.get('rst', 0)
            if w == 0:
                w = rinfo.width
            w_ans['rst'] = w
            th_ans['rst'] = rinfo.threshold

        return ImmutableSortedDict(w_ans), ImmutableSortedDict(th_ans)


class DynLatchDig(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'comp_dyn_latch')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        ans = DynLatchDigHalf.get_params_info()
        ans['even_center'] = 'True to force center column to be even.'
        return ans

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DynLatchDigHalf.get_default_param_values()
        ans['even_center'] = False
        return ans

    def draw_layout(self):
        master: DynLatchDigHalf = self.new_template(DynLatchDigHalf, params=self.params)
        self.draw_base(master.draw_base_info)
        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1

        out_vm_tidx = self.arr_info.col_to_track(vm_layer, 2, mode=RoundMode.NEAREST)
        half_params = self.params.copy(append=dict(sig_locs={'out': out_vm_tidx}))
        master: DynLatchDigHalf = self.new_template(DynLatchDigHalf, params=half_params)

        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']
        vertical_out: bool = self.params['vertical_out']
        vertical_sup: bool = self.params['vertical_sup']
        even_center: bool = self.params['even_center']
        flip_np: bool = self.params['flip_np']

        # placement
        # nsep = self.min_sep_col
        # nsep += (nsep & 1)
        # if even_center and nsep % 4 == 2:
        #     nsep += 2

        nhalf = master.num_cols
        corel = self.add_tile(master, 0, nhalf, flip_lr=True)
        corer = self.add_tile(master, 0, nhalf)
        self.set_mos_size(num_cols=2 * nhalf)

        # routing
        ridx_nfb = ridx_n
        ridx_pfb = ridx_p
        inn_tidx, hm_w = \
            self.get_track_info(ridx_nfb if flip_np else ridx_pfb, MOSWireType.G, wire_name='sig', wire_idx=-1)
        inp_tidx = self.get_track_index(ridx_pfb if flip_np else ridx_nfb, MOSWireType.G, wire_name='sig',
                                        wire_idx=0 if flip_np else -1)
        outn_tidx = self.get_track_index(ridx_nfb if flip_np else ridx_pfb,
                                         MOSWireType.G, wire_name='sig', wire_idx=1 if flip_np else -3)
        outp_tidx = self.get_track_index(ridx_nfb if flip_np else ridx_pfb,
                                         MOSWireType.G, wire_name='sig', wire_idx=2 if flip_np else -2)
        #
        hm_layer = self.conn_layer + 1
        inp, inn = self.connect_differential_tracks(corel.get_pin('in'), corer.get_pin('in'),
                                                    hm_layer, inp_tidx, inn_tidx, width=hm_w)
        outp, outn = self.connect_differential_tracks(corer.get_all_port_pins('out'),
                                                      corel.get_all_port_pins('out'),
                                                      hm_layer, outp_tidx, outn_tidx, width=hm_w)
        if vertical_out:
            outp_vm = corel.get_pin('out_vm')
            outn_vm = corer.get_pin('out_vm')
            self.connect_to_track_wires(outp, outp_vm)
            self.connect_to_track_wires(outn, outn_vm)
            self.add_pin('outn', outp)
            self.add_pin('outp', outn)
            self.add_pin('outn', outp_vm)
            self.add_pin('outp', outn_vm)
        else:
            self.add_pin('outp', [corel.get_pin('pout'), corel.get_pin('nout'), outp], connect=True)
            self.add_pin('outn', [corer.get_pin('pout'), corer.get_pin('nout'), outn], connect=True)

        if vertical_sup:
            vss = list(chain(corel.get_all_port_pins('VSS', layer=self.conn_layer),
                             corer.get_all_port_pins('VSS', layer=self.conn_layer)))
            vdd = list(chain(corel.get_all_port_pins('VDD', layer=self.conn_layer),
                             corer.get_all_port_pins('VDD', layer=self.conn_layer)))
        else:
            vss = self.connect_wires(list(chain(corel.get_all_port_pins('VSS'), corer.get_all_port_pins('VSS'))))
            vdd = self.connect_wires(list(chain(corel.get_all_port_pins('VDD'), corer.get_all_port_pins('VDD'))))

        clk_vm_tidx = self.arr_info.col_to_track(vm_layer, self.num_cols // 2, mode=RoundMode.NEAREST)
        clk_vm = self.connect_to_tracks([corel.get_pin('clk'), corer.get_pin('clk')],
                                        TrackID(vm_layer, clk_vm_tidx, tr_manager.get_width(vm_layer, 'clk')))

        self.connect_wires([corel.get_pin('tail'), corer.get_pin('tail')])
        self.add_pin('VDD', vdd)
        self.add_pin('VSS', vss)
        self.add_pin('inp', inp)
        self.add_pin('inn', inn)
        self.add_pin('clk', clk_vm)

        self.sch_params = master.sch_params


class CnterLatchHalf(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg_dict='segments dictionary.',
            w_dict='widths dictionary.',
            ridx_n='bottom nmos row index.',
            ridx_p='pmos row index.',
            sig_locs='Optional dictionary of user defined signal locations',
            vertical_sup='True to connect outputs to vm_layer.',
            vertical_out='True to connect outputs to vm_layer.',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_dict={},
            ridx_n=0,
            ridx_p=-1,
            sig_locs={},
            vertical_out=True,
            vertical_sup=False,
        )

    def draw_layout(self):
        place_info = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(place_info)

        seg_dict: ImmutableSortedDict[str, int] = self.params['seg_dict']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']
        vertical_out: bool = self.params['vertical_out']
        vertical_sup: bool = self.params['vertical_sup']
        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']

        tr_manager = self.tr_manager

        w_dict, th_dict = self._get_w_th_dict(ridx_n, ridx_p)
        seg_nin = seg_dict['nin']
        seg_pin = seg_dict['pin']
        seg_nfb = seg_dict['nfb']
        seg_pfb = seg_dict['pfb']
        seg_ptail = seg_dict['ptail']
        seg_ntail = seg_dict['ntail']
        w_nin = w_dict['nin']
        w_pin = w_dict['pin']
        w_ntail = w_dict['ntail']
        w_ptail = w_dict['ptail']
        w_nfb = w_dict['nfb']
        w_pfb = w_dict['pfb']

        if seg_nin & 1 or seg_pin & 1:
        # if seg_nin & 1 or seg_pin & 1 or (seg_ntail % 4 != 0) or (seg_ptail % 4 != 0):
                raise ValueError('in, tail, nfb, or pfb must have even number of segments')
        seg_ptail = seg_ptail // 2
        seg_ntail = seg_ntail // 2

        # placement
        min_sep = self.min_sep_col
        m_ntail = self.add_mos(ridx_n, 0, seg_ntail, w=w_ntail, g_on_s=bool(seg_ntail & 1))
        m_ptail = self.add_mos(ridx_p, 0, seg_ptail, w=w_ptail, g_on_s=bool(seg_ptail & 1))
        m_nin = self.add_mos(ridx_n, seg_ntail, seg_nin, w=w_nin)
        m_pin = self.add_mos(ridx_p, seg_ptail, seg_pin, w=w_pin)

        m_nfb = self.add_mos(ridx_n, seg_nin+seg_ntail+min_sep, seg_nfb, w=w_nfb, g_on_s=bool(seg_nfb & 1))
        m_pfb = self.add_mos(ridx_p, seg_pin+seg_ptail+min_sep, seg_pfb, w=w_pfb, g_on_s=bool(seg_pfb & 1))

        nout_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig', wire_idx=0)
        pout_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sig', wire_idx=-1)
        nclk_tid = self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0+sig_locs.get('clk', 0))
        pclk_tid = self.get_track_id(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=0+sig_locs.get('clk', 0))
        ntail_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig', wire_idx=1)
        ptail_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sig', wire_idx=-2)
        in_tid = self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=3)

        # # NOTE: force even number of columns to make sure VDD conn_layer wires are on even columns.
        ncol_tot = self.num_cols
        ncol_tot += 1  # left some space for clock signal routing
        # self.set_mos_size(num_cols=ncol_tot + (ncol_tot & 1))
        self.set_mos_size(ncol_tot)
        # routing
        conn_layer = self.conn_layer
        vm_layer = conn_layer + 2
        sig_vm_w = self.tr_manager.get_width(vm_layer, 'sig')

        nclk = self.connect_to_tracks([m_ntail.g], nclk_tid)
        pclk = self.connect_to_tracks([m_ptail.g], pclk_tid)
        out = self.connect_wires([m_nfb.g, m_pfb.g])
        nout = self.connect_to_tracks([m_nin.d, m_nfb.s], nout_tid)
        pout = self.connect_to_tracks([m_pin.d, m_pfb.s], pout_tid)
        ntail = self.connect_to_tracks([m_nin.s, m_ntail.d] if seg_ntail & 1 else [m_nin.s, m_ntail.s], ntail_tid)
        ptail = self.connect_to_tracks([m_pin.s, m_ptail.d] if seg_ptail & 1 else [m_pin.s, m_ptail.s], ptail_tid)
        fb_g = self.connect_wires([m_nfb.g, m_pfb.g])
        in_g = self.connect_wires([m_nin.g, m_pin.g])
        in_hm = self.connect_to_tracks(in_g, in_tid)

        vdd_conn = [m_pfb.d, m_ptail.s] if seg_ptail & 1 else [m_pfb.d, m_ptail.d]
        vss_conn = [m_nfb.d, m_ntail.s] if seg_ntail & 1 else [m_nfb.d, m_ntail.d]
        if vertical_sup:
            tr_w_sup_vm = tr_manager.get_width(vm_layer, 'sup')
            vdd_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sup')
            vdd_hm = self.connect_to_tracks(vdd_conn, vdd_tid)
            vss_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sup')
            vss_hm = self.connect_to_tracks(vss_conn, vss_tid)
            # export to vm
            sup_vm_tidx = self.arr_info.col_to_track(vm_layer, self.num_cols, mode=RoundMode.NEAREST)
            sup_vm_tidx = tr_manager.get_next_track(vm_layer, sup_vm_tidx, 'clk', 'clk', up=False)
            sup_vm_tidx = tr_manager.get_next_track(vm_layer, sup_vm_tidx, 'clk', 'sup', up=False)
            vdd = [self.connect_to_tracks(vdd_hm, TrackID(vm_layer, sup_vm_tidx, tr_w_sup_vm))]
            vss = [self.connect_to_tracks(vss_hm, TrackID(vm_layer, sup_vm_tidx, tr_w_sup_vm))]
            # sup_vm_tidx = self.arr_info.col_to_track(vm_layer, 0, mode=RoundMode.NEAREST)
            # vdd.append(self.connect_to_tracks(vdd_hm, TrackID(vm_layer, sup_vm_tidx, tr_w_sup_vm)))
            # vss.append(self.connect_to_tracks(vss_hm, TrackID(vm_layer, sup_vm_tidx, tr_w_sup_vm)))

        else:
            vdd_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sup')
            vdd = self.connect_to_tracks(vdd_conn, vdd_tid)
            vss_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sup')
            vss = self.connect_to_tracks(vss_conn, vss_tid)

        if vertical_out:
            vm_tidx = self.arr_info.col_to_track(vm_layer, 0, mode=RoundMode.NEAREST)
            vm_tidx = sig_locs.get('out', vm_tidx)
            out_vm = self.connect_to_tracks([nout, pout], TrackID(vm_layer, vm_tidx, width=sig_vm_w))
            vm_tidx = self.arr_info.col_to_track(vm_layer, 1, mode=RoundMode.NEAREST)
            vm_tidx = sig_locs.get('in', vm_tidx)
            in_vm = self.connect_to_tracks(in_hm, TrackID(vm_layer, vm_tidx, width=sig_vm_w))
            self.add_pin('out_vm', out_vm)
            self.add_pin('in_vm', in_vm)
        else:
            self.add_pin('in', in_hm)
            self.add_pin('pout', pout)
            self.add_pin('nout', nout)

        self.add_pin('VSS', vss)
        self.add_pin('VDD', vdd)
        self.add_pin('ntail', ntail)
        self.add_pin('ptail', ptail)

        #extend clk
        clk_ext_x = self.arr_info.col_to_coord(max(seg_ptail, seg_ntail)+max(seg_nin, seg_pin)//2)
        nclk = self.extend_wires(nclk, upper=clk_ext_x)
        pclk = self.extend_wires(pclk, upper=clk_ext_x)

        self.add_pin('nclk', nclk)
        self.add_pin('pclk', pclk)
        self.add_pin('out', out)
        self.add_pin('fb_in', fb_g)

        self.sch_params = dict(
            lch=self.arr_info.lch,
            seg_dict=seg_dict,
            w_dict=w_dict,
            th_dict=th_dict,
        )

    def _get_w_th_dict(self, ridx_n: int, ridx_p: int)\
            -> Tuple[ImmutableSortedDict[str, int], ImmutableSortedDict[str, str]]:
        w_dict: Mapping[str, int] = self.params['w_dict']

        w_ans = {}
        th_ans = {}
        for name, row_idx in [('nfb', ridx_n), ('nin', ridx_n), ('pfb', ridx_p), ('pin', ridx_p), ('ntail', ridx_n),
                              ('ptail', ridx_p)]:
            rinfo = self.get_row_info(row_idx, 0)
            w = w_dict.get(name, 0)
            if w == 0:
                w = rinfo.width
            w_ans[name] = w
            th_ans[name] = rinfo.threshold

        return ImmutableSortedDict(w_ans), ImmutableSortedDict(th_ans)


class CnterLatch(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'vco_cnter_latch')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        ans = CnterLatchHalf.get_params_info()
        ans['even_center'] = 'True to force center column to be even.'
        ans['flip_io'] = 'True to flip input/output, easier for inter-connection'
        ans['vertical_clk'] = 'True to add vertical clock signals'
        return ans

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = CnterLatchHalf.get_default_param_values()
        ans['even_center'] = False
        ans['flip_io'] = False
        ans['vertical_clk'] = False
        return ans

    def draw_layout(self):
        master: CnterLatchHalf = self.new_template(CnterLatchHalf, params=self.params)
        self.draw_base(master.draw_base_info)

        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1

        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']
        flip_io: bool = self.params['flip_io']
        vertical_out: bool = self.params['vertical_out']
        vertical_sup: bool = self.params['vertical_sup']
        vertical_clk: bool = self.params['vertical_clk']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']
        # placement
        nsep = self.min_sep_col if vertical_clk else 0
        nsep += nsep & 1
        nhalf = master.num_cols
        out_vm_tidx = self.arr_info.col_to_track(vm_layer, 1)
        in_vm_tidx = self.arr_info.col_to_track(vm_layer, 2)
        sig_locs_new = {'out': sig_locs.get('out', out_vm_tidx), 'in': sig_locs.get('in', in_vm_tidx)}

        # shift hm clk idx
        if flip_io:
            sig_locs_new['clk'] = 1
        master_params = self.params.copy(append=dict(sig_locs=sig_locs_new))
        master: CnterLatchHalf = self.new_template(CnterLatchHalf, params=master_params)
        corel = self.add_tile(master, 0, nhalf, flip_lr=True)
        corer = self.add_tile(master, 0, nhalf + nsep)
        self.set_mos_size(num_cols=nsep + 2 * nhalf)

        # routing
        # in_tidx, hm_w = self.get_track_info(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=3)
        hm_w = tr_manager.get_width(hm_layer, 'sig')
        # inp_tidx = self.get_track_index(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=-2)
        outn_tidx = self.get_track_index(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=2)
        outp_tidx = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=2)
        # if flip_io:
        #     inn_tidx, inp_tidx, outn_tidx, outp_tidx = outp_tidx, outn_tidx, inp_tidx, inn_tidx
        #
        # inp = self.connect_to_tracks(corel.get_pin('in'), TrackID(hm_layer, in_tidx, hm_w))
        # inn = self.connect_to_tracks(corer.get_pin('in'), TrackID(hm_layer, in_tidx, hm_w))
        outp, outn = self.connect_differential_tracks(corer.get_all_port_pins('out'),
                                                      corel.get_all_port_pins('out'),
                                                      hm_layer, outp_tidx, outn_tidx, width=hm_w)
        if vertical_out:
            outp_vm = corel.get_pin('out_vm')
            outn_vm = corer.get_pin('out_vm')
            inp_vm = corel.get_pin('in_vm')
            inn_vm = corer.get_pin('in_vm')
            outp, outn = self.connect_differential_wires(outp_vm, outn_vm, outp, outn)

            inp_vm = self.extend_wires(inp_vm, upper=outp_vm.upper, lower=outp_vm.lower)
            inn_vm = self.extend_wires(inn_vm, upper=outp_vm.upper, lower=outp_vm.lower)

            self.add_pin('d', inp_vm)
            self.add_pin('dn', inn_vm)

            self.add_pin('outn', outp)
            self.add_pin('outp', outn)
            self.add_pin('outn', outp_vm)
            self.add_pin('outp', outn_vm)
        else:
            self.reexport(corel.get_port('in'), net_name='d')
            self.reexport(corer.get_port('in'), net_name='dn')
            self.add_pin('outp', [corel.get_pin('pout'), corel.get_pin('nout'), outp], connect=True)
            self.add_pin('outn', [corer.get_pin('pout'), corer.get_pin('nout'), outn], connect=True)

        if vertical_sup:
            vss = list(chain(corel.get_all_port_pins('VSS'), corer.get_all_port_pins('VSS')))
            vdd = list(chain(corel.get_all_port_pins('VDD'), corer.get_all_port_pins('VDD')))
            vdd_hm_tid = self.grid.coord_to_track(hm_layer, vdd[0].middle, mode=RoundMode.NEAREST)
            vss_hm_tid = self.grid.coord_to_track(hm_layer, vss[0].middle, mode=RoundMode.NEAREST)
            tr_w_sup_hm = tr_manager.get_width(hm_layer, 'sup')
            vdd_hm = self.connect_to_tracks(vdd, TrackID(hm_layer, vdd_hm_tid, tr_w_sup_hm))
            vss_hm = self.connect_to_tracks(vss, TrackID(hm_layer, vss_hm_tid, tr_w_sup_hm))
            self.add_pin('VDD', vdd_hm)
            self.add_pin('VSS', vss_hm)
        else:
            vss = self.connect_wires(list(chain(corel.get_all_port_pins('VSS'), corer.get_all_port_pins('VSS'))))
            vdd = self.connect_wires(list(chain(corel.get_all_port_pins('VDD'), corer.get_all_port_pins('VDD'))))
            self.add_pin('VDD', vdd)
            self.add_pin('VSS', vss)

        if vertical_clk:
            _, clk_tidxs = self.tr_manager.place_wires(vm_layer, ['clk', 'clk'],
                                                       center_coord=self.arr_info.col_to_coord(self.num_cols//2))
            clk_vm = self.connect_to_tracks([corel.get_pin('pclk'), corer.get_pin('pclk')],
                                            TrackID(vm_layer, clk_tidxs[0], tr_manager.get_width(vm_layer, 'clk')))
            nclk_vm = self.connect_to_tracks([corel.get_pin('nclk'), corer.get_pin('nclk')],
                                             TrackID(vm_layer, clk_tidxs[1], tr_manager.get_width(vm_layer, 'clk')))
            self.add_pin('clkn', clk_vm)
            self.add_pin('clkp', nclk_vm)
        else:
            self.add_pin('clkn', self.connect_wires([corel.get_pin('pclk'), corer.get_pin('pclk')]))
            self.add_pin('clkp', self.connect_wires([corel.get_pin('nclk'), corer.get_pin('nclk')]))

        self.connect_wires([corel.get_pin('ntail'), corer.get_pin('ntail')])
        self.connect_wires([corel.get_pin('ptail'), corer.get_pin('ptail')])

        self.sch_params = master.sch_params


class SRLatchSymmetricHalf(MOSBase):
    """Half of symmetric SR latch
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)
        zero = HalfInt(0)
        self._q_tr_info = (0, zero, zero)
        self._sr_hm_tr_info = self._q_tr_info
        self._sr_vm_tr_info = self._q_tr_info

    @property
    def q_tr_info(self) -> Tuple[int, HalfInt, HalfInt]:
        return self._q_tr_info

    @property
    def sr_hm_tr_info(self) -> Tuple[int, HalfInt, HalfInt]:
        return self._sr_hm_tr_info

    @property
    def sr_vm_tr_info(self) -> Tuple[int, HalfInt, HalfInt]:
        return self._sr_vm_tr_info

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg_dict='segments dictionary.',
            w_dict='widths dictionary.',
            ridx_n='bottom nmos row index.',
            ridx_p='pmos row index.',
            has_rstb='True to add rstb functionality.',
            has_outbuf='True to add output buffers.',
            has_inbuf='True to add input buffers.',
            out_pitch='output wire pitch from center.',
            sig_locs='Signal locations',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_dict={},
            ridx_n=0,
            ridx_p=-1,
            has_rstb=False,
            has_outbuf=True,
            has_inbuf=True,
            sig_locs={},
            out_pitch=0.5,
        )

    def draw_layout(self):
        place_info = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(place_info)

        seg_dict: ImmutableSortedDict[str, int] = self.params['seg_dict']
        ridx_n: int = self.params['ridx_n']
        ridx_p: int = self.params['ridx_p']
        has_rstb: bool = self.params['has_rstb']
        has_outbuf: bool = self.params['has_outbuf']
        has_inbuf: bool = self.params['has_inbuf']
        out_pitch: HalfInt = HalfInt.convert(self.params['out_pitch'])
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']

        w_dict, th_dict = self._get_w_th_dict(ridx_n, ridx_p, has_rstb)

        seg_fb = seg_dict['fb']
        seg_ps = seg_dict['ps']
        seg_nr = seg_dict['nr']
        seg_obuf = seg_dict['obuf'] if has_outbuf else 0
        seg_ibuf = seg_dict['ibuf'] if has_inbuf else 0

        w_pfb = w_dict['pfb']
        w_nfb = w_dict['nfb']
        w_ps = w_dict['ps']
        w_nr = w_dict['nr']
        w_rst = w_dict.get('pr', 0)
        w_nbuf = w_nr
        w_pbuf = w_ps

        sch_seg_dict = dict(nfb=seg_fb, pfb=seg_fb, ps=seg_ps, nr=seg_nr)
        if has_rstb:
            sch_seg_dict['pr'] = seg_rst = seg_dict['rst']
        else:
            seg_rst = 0

        if seg_ps & 1 or seg_nr & 1 or seg_rst & 1 or seg_obuf & 1:
            raise ValueError('ps, nr, rst, and buf must have even number of segments')

        # placement
        min_sep = self.min_sep_col
        # use even step size to maintain supply conn_layer wires parity.
        min_sep += (min_sep & 1)

        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        grid = self.grid
        arr_info = self.arr_info
        tr_manager = self.tr_manager
        hm_w = tr_manager.get_width(hm_layer, 'sig')
        vm_w = tr_manager.get_width(vm_layer, 'sig')
        hm_sep_col = self.get_hm_sp_le_sep_col(ntr=hm_w)
        mid_sep = max(hm_sep_col - 2, 0)
        mid_sep = (mid_sep + 1) // 2

        if has_inbuf:
            m_nibuf = self.add_mos(ridx_n, mid_sep, seg_ibuf, w=w_nbuf)
            m_pibuf = self.add_mos(ridx_p, mid_sep, seg_ibuf, w=w_pbuf)
            cur_col = mid_sep + seg_ibuf
            nsr_list = [m_pibuf.g, m_nibuf.g]
        else:
            m_nibuf = m_pibuf = None
            cur_col = mid_sep
            nsr_list = []

        nr_col = cur_col
        m_nr = self.add_mos(ridx_n, cur_col, seg_nr, w=w_nr)
        m_ps = self.add_mos(ridx_p, cur_col, seg_ps, w=w_ps)
        nsr_list.append(m_nr.g)
        pcol = cur_col + seg_ps
        if has_rstb:
            m_rst = self.add_mos(ridx_p, pcol, seg_rst, w=w_rst)
            pcol += seg_rst
        else:
            m_rst = None

        cur_col = max(cur_col + seg_nr, pcol)
        if has_outbuf:
            m_pinv = self.add_mos(ridx_p, cur_col, seg_obuf, w=w_pbuf)
            m_ninv = self.add_mos(ridx_n, cur_col, seg_obuf, w=w_nbuf)
            cur_col += seg_obuf
        else:
            m_pinv = m_ninv = None

        cur_col += min_sep
        fb_col = cur_col
        m_pfb = self.add_mos(ridx_p, cur_col, seg_fb, w=w_pfb, g_on_s=True, stack=2, sep_g=True)
        m_nfb = self.add_mos(ridx_n, cur_col, seg_fb, w=w_nfb, g_on_s=True, stack=2, sep_g=True)
        self.set_mos_size()

        # track planning
        vss_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sup')
        nbuf_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig', wire_idx=-2)
        nq_tid = self.get_track_id(ridx_n, MOSWireType.DS, wire_name='sig', wire_idx=-1)
        pq_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sig', wire_idx=0)
        pbuf_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sig', wire_idx=1)
        vdd_tid = self.get_track_id(ridx_p, MOSWireType.DS, wire_name='sup')

        nsrb_tid = self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0)
        nsr_tid = sig_locs.get('sr', self.get_track_id(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=0))
        # try to spread out gate wires to lower parasitics on differential Q wires
        pg_lower = self.get_track_index(ridx_n, MOSWireType.G, wire_name='sig', wire_idx=-1)
        pg_upper = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-1)
        # ng_upper = self.get_track_index(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-3)
        g_idx_list = tr_manager.spread_wires(hm_layer, ['sig', 'sig', 'sig', 'sig'],
                                             pg_lower, pg_upper, ('sig', 'sig'), alignment=-1)
        self._q_tr_info = (hm_w, g_idx_list[2], g_idx_list[1])
        self._sr_hm_tr_info = (hm_w, g_idx_list[3], g_idx_list[0])

        if has_rstb:
            rst_tid = self.get_track_id(ridx_p, MOSWireType.G, wire_name='sig', wire_idx=-2)
            pq_conn_list = [m_ps.d, m_rst.d, m_pfb.s]
            vdd_list = [m_ps.s, m_rst.s, m_pfb.d]
            vss_list = [m_nr.s, m_nfb.d]

            rstb = self.connect_to_tracks(m_rst.g, rst_tid, min_len_mode=MinLenMode.MIDDLE)
            rst_vm_tidx = grid.coord_to_track(vm_layer, rstb.middle, mode=RoundMode.GREATER_EQ)
            rstb_vm = self.connect_to_tracks(rstb, TrackID(vm_layer, rst_vm_tidx, width=vm_w),
                                             min_len_mode=MinLenMode.MIDDLE)
            self.add_pin('rstb', rstb_vm)
        else:
            pq_conn_list = [m_ps.d, m_pfb.s]
            vdd_list = [m_ps.s, m_pfb.d]
            vss_list = [m_nr.s, m_nfb.d]

        self.add_pin('psrb', m_ps.g)
        self.add_pin('psr', m_pfb.g[0::2])
        nq = self.connect_to_tracks([m_nr.d, m_nfb.s], nq_tid)
        pq = self.connect_to_tracks(pq_conn_list, pq_tid)
        nsr_ret_wire_list = []
        nsr = self.connect_to_tracks(nsr_list, nsr_tid, min_len_mode=MinLenMode.UPPER,
                                      ret_wire_list=nsr_ret_wire_list)
        nsrb = self.connect_to_tracks(m_nfb.g[0::2], nsrb_tid, min_len_mode=MinLenMode.LOWER)
        qb = self.connect_wires([m_nfb.g[1::2], m_pfb.g[1::2]])
        self.add_pin('qb', qb)

        if has_inbuf:
            vdd_list.append(m_pibuf.s)
            vss_list.append(m_nibuf.s)

            nbuf = self.connect_to_tracks(m_nibuf.d, nbuf_tid, min_len_mode=MinLenMode.UPPER)
            pbuf = self.connect_to_tracks(m_pibuf.d, pbuf_tid, min_len_mode=MinLenMode.UPPER)
            vm_tidx = grid.coord_to_track(vm_layer, nbuf.middle, mode=RoundMode.LESS_EQ)
            buf = self.connect_to_tracks([nbuf, pbuf], TrackID(vm_layer, vm_tidx, width=vm_w))
            self.add_pin('srb_buf', buf)

        out_p_htr = out_pitch.dbl_value
        vm_ref = grid.coord_to_track(vm_layer, 0)
        srb_vm_tidx = arr_info.col_to_track(vm_layer, nr_col + 1, mode=RoundMode.GREATER_EQ)
        if has_outbuf:
            vdd_list.append(m_pinv.s)
            vss_list.append(m_ninv.s)

            nbuf = self.connect_to_tracks(m_ninv.d, nbuf_tid, min_len_mode=MinLenMode.MIDDLE)
            pbuf = self.connect_to_tracks(m_pinv.d, pbuf_tid, min_len_mode=MinLenMode.MIDDLE)
            vm_delta = grid.coord_to_track(vm_layer, nbuf.middle, mode=RoundMode.LESS_EQ) - vm_ref
            vm_htr = -(-vm_delta.dbl_value // out_p_htr) * out_p_htr
            vm_tidx = vm_ref + HalfInt(vm_htr)
            buf = self.connect_to_tracks([nbuf, pbuf], TrackID(vm_layer, vm_tidx, width=vm_w))
            self.add_pin('buf_out', buf)
            buf_in = self.connect_wires([m_ninv.g, m_pinv.g])
            self.add_pin('buf_in', buf_in)

            q_vm_tidx = tr_manager.get_next_track(vm_layer, srb_vm_tidx, 'sig', 'sig')
        else:
            vm_delta = tr_manager.get_next_track(vm_layer, srb_vm_tidx, 'sig', 'sig') - vm_ref
            vm_htr = -(-vm_delta.dbl_value // out_p_htr) * out_p_htr
            q_vm_tidx = vm_ref + HalfInt(vm_htr)

        sr_vm_tidx = arr_info.col_to_track(vm_layer, fb_col, mode=RoundMode.LESS_EQ)
        self._sr_vm_tr_info = (vm_w, sr_vm_tidx, srb_vm_tidx)

        q_vm = self.connect_to_tracks([nq, pq], TrackID(vm_layer, q_vm_tidx, width=vm_w))
        self.add_pin('q_vm', q_vm)
        self.add_pin('nsr', nsr)
        self.add_pin('nsrb', nsrb)
        self.add_pin('nsr_conn', nsr_ret_wire_list[-1])

        self.add_pin('VDD', self.connect_to_tracks(vdd_list, vdd_tid))
        self.add_pin('VSS', self.connect_to_tracks(vss_list, vss_tid))

        lch = arr_info.lch
        buf_params = ImmutableSortedDict(dict(
            lch=lch,
            w_p=w_pbuf,
            w_n=w_nbuf,
            th_p=th_dict['ps'],
            th_n=th_dict['nr'],
            seg=seg_obuf,
        ))
        obuf_params = buf_params if has_outbuf else None
        ibuf_params = buf_params.copy(append=dict(seg=seg_ibuf)) if has_inbuf else None
        self.sch_params = dict(
            core_params=ImmutableSortedDict(dict(
                lch=lch,
                seg_dict=ImmutableSortedDict(sch_seg_dict),
                w_dict=w_dict,
                th_dict=th_dict,
            )),
            outbuf_params=obuf_params,
            inbuf_params=ibuf_params,
            has_rstb=has_rstb,
        )

    def _get_w_th_dict(self, ridx_n: int, ridx_p: int, has_rstb: bool
                       ) -> Tuple[ImmutableSortedDict[str, int], ImmutableSortedDict[str, str]]:
        w_dict: Mapping[str, int] = self.params['w_dict']

        w_ans = {}
        th_ans = {}
        for row_idx, name_list in [(ridx_n, ['nfb', 'nr']),
                                   (ridx_p, ['pfb', 'ps'])]:
            rinfo = self.get_row_info(row_idx, 0)
            for name in name_list:
                w = w_dict.get(name, 0)
                if w == 0:
                    w = rinfo.width
                w_ans[name] = w
                th_ans[name] = rinfo.threshold

        if has_rstb:
            w_ans['pr'] = w_ans['ps']
            th_ans['pr'] = th_ans['ps']

        return ImmutableSortedDict(w_ans), ImmutableSortedDict(th_ans)


class SRLatchSymmetric(MOSBase):
    """Symmetric SR latch.  Mainly designed to be used with strongarm.
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'sr_latch_symmetric')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        ans = SRLatchSymmetricHalf.get_params_info()
        ans['swap_outbuf'] = 'True to swap output buffers, so outp is on opposite side of inp.'
        return ans

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = SRLatchSymmetricHalf.get_default_param_values()
        ans['swap_outbuf'] = False
        return ans

    def draw_layout(self) -> None:
        master: SRLatchSymmetricHalf = self.new_template(SRLatchSymmetricHalf, params=self.params)
        self.draw_base(master.draw_base_info)

        swap_outbuf: bool = self.params['swap_outbuf']

        hm_w, q_tidx, qb_tidx = master.q_tr_info
        _, sr_hm_top, sr_hm_bot = master.sr_hm_tr_info
        vm_w, sr_vm_tidx, srb_vm_tidx = master.sr_vm_tr_info

        # placement
        inn_tidx = self.get_track_id(0, MOSWireType.G, 'sig', 2)
        inp_tidx = self.get_track_id(0, MOSWireType.G, 'sig', 1)
        n_master_params = self.params.copy(append={'sig_locs': {'sr': inn_tidx}})
        p_master_params = self.params.copy(append={'sig_locs': {'sr': inp_tidx}})
        n_master: SRLatchSymmetricHalf = self.new_template(SRLatchSymmetricHalf, params=n_master_params)
        p_master: SRLatchSymmetricHalf = self.new_template(SRLatchSymmetricHalf, params=p_master_params)

        nhalf = master.num_cols
        corel = self.add_tile(n_master, 0, nhalf, flip_lr=True)
        corer = self.add_tile(p_master, 0, nhalf)
        self.set_mos_size(num_cols=2 * nhalf)

        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        arr_info = self.arr_info
        vm0 = arr_info.col_to_track(vm_layer, 0)
        vmh = arr_info.col_to_track(vm_layer, nhalf)
        vmdr = vmh - vm0
        vmdl = vmh + vm0

        pr = corel.get_pin('psr')
        psb = corel.get_pin('psrb')
        nr = corel.get_pin('nsr')
        nsb = corel.get_pin('nsrb')
        ps = corer.get_pin('psr')
        prb = corer.get_pin('psrb')
        ns = corer.get_pin('nsr')
        nrb = corer.get_pin('nsrb')

        pr, psb = self.connect_differential_tracks(pr, psb, hm_layer, sr_hm_top, sr_hm_bot,
                                                   width=hm_w)
        ps, prb = self.connect_differential_tracks(ps, prb, hm_layer, sr_hm_bot, sr_hm_top,
                                                   width=hm_w)
        sb = self.connect_to_tracks([psb, nsb], TrackID(vm_layer, vmdl - sr_vm_tidx, width=vm_w))
        r = self.connect_to_tracks([pr, nr], TrackID(vm_layer, vmdl - srb_vm_tidx, width=vm_w),
                                   track_lower=sb.lower)
        s = self.connect_to_tracks([ps, ns], TrackID(vm_layer, vmdr + srb_vm_tidx, width=vm_w))
        rb = self.connect_to_tracks([prb, nrb], TrackID(vm_layer, vmdr + sr_vm_tidx, width=vm_w),
                                    track_lower=s.lower)

        if ns.track_id.base_index != nr.track_id.base_index:
            s, r = self.extend_wires([s, r], lower=min([s.lower, r.lower]), upper=max([s.upper, r.upper]))
            ns, nr = self.extend_wires([ns, nr], lower=min([ns.lower, nr.lower]),
                                         upper=max([ns.upper, nr.upper]))
            ns_conn = corel.get_pin('nsr_conn')
            nr_conn = corer.get_pin('nsr_conn')
            self.extend_wires([ns_conn, nr_conn], lower=min(ns_conn.lower, nr_conn.lower))

        self.add_pin('s', s)
        self.add_pin('r', r)
        self.add_pin('s', ns)
        self.add_pin('r', nr)
        if corel.has_port('srb_buf'):
            sbbuf = corer.get_pin('srb_buf')
            rbbuf = corel.get_pin('srb_buf')
            self.connect_to_track_wires(sbbuf, psb)
            self.connect_to_track_wires(rbbuf, prb)
        else:
            self.add_pin('sb', sb)
            self.add_pin('rb', rb)

        q_list = [corel.get_pin('q_vm'), corer.get_pin('qb')]
        qb_list = [corer.get_pin('q_vm'), corel.get_pin('qb')]
        if corel.has_port('buf_out'):
            if swap_outbuf:
                self.reexport(corel.get_port('buf_out'), net_name='qb')
                self.reexport(corer.get_port('buf_out'), net_name='q')
                q_list.append(corel.get_pin('buf_in'))
                qb_list.append(corer.get_pin('buf_in'))
            else:
                self.reexport(corel.get_port('buf_out'), net_name='q')
                self.reexport(corer.get_port('buf_out'), net_name='qb')
                q_list.append(corer.get_pin('buf_in'))
                qb_list.append(corel.get_pin('buf_in'))
        else:
            self.add_pin('q', q_list[0])
            self.add_pin('qb', qb_list[0])

        self.connect_differential_tracks(q_list, qb_list, self.conn_layer + 1,
                                         q_tidx, qb_tidx, width=hm_w)

        if corel.has_port('rstb'):
            self.reexport(corel.get_port('rstb'), net_name='rsthb')
            self.reexport(corer.get_port('rstb'), net_name='rstlb')

        self.add_pin('VDD', self.connect_wires([corel.get_pin('VDD'), corer.get_pin('VDD')]))
        self.add_pin('VSS', self.connect_wires([corel.get_pin('VSS'), corer.get_pin('VSS')]))

        self.sch_params = master.sch_params


class SAFFCore(RingOscUnit):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'vco_saff')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg_dict='segments dictionary.',
            w_dict='widths dictionary.',
            vertical_out='True to connect outputs to vm_layer.',
            even_center='True to force center column to be even.',
            signal_locs='Signal locations',
            shift_input='True to shift preamp input for easy connection with outside',
            export_sup_to_xm1=''
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w_dict={},
            vertical_out=True,
            even_center=False,
            shift_input=False,
            signal_locs={},
            export_sup_to_xm1=True,
        )

    def draw_layout(self):
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(pinfo)
        seg_dict: Dict[str, Dict] = self.params['seg_dict']
        w_dict: Dict[str, Dict] = self.params['w_dict']
        sig_locs = self.params['signal_locs']

        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        ym_layer = xm_layer + 1
        xm1_layer = ym_layer + 1
        tr_w_sig_vm = tr_manager.get_width(vm_layer, 'sig')

        # Make templates
        preamp_params = dict(pinfo=pinfo, vertical_sup=False, seg_dict=seg_dict['preamp'], w_dict=w_dict['preamp'],
                             flip_preamp_io=self.params['shift_input'])
        dyn_latch_params = dict(pinfo=pinfo, vertical_sup=False, seg_dict=seg_dict['dynlatch'],
                                w_dict=w_dict['dynlatch'], flip_np=True)
        sr_params = dict(pinfo=pinfo, seg_dict=seg_dict['sr'], w_dict=w_dict.get('sr', {}))

        preamp_master = self.new_template(PreAmpDig, params=preamp_params)
        dyn_latch_master = self.new_template(DynLatchDig, params=dyn_latch_params)
        sr_master = self.new_template(SRLatchSymmetric, params=sr_params)

        # floorplanning
        preamp_ncol = preamp_master.num_cols
        dyn_latch_ncol = dyn_latch_master.num_cols
        _sr_latch_ncol = sr_master.num_cols
        min_sep = self.min_sep_col

        # placement
        preamp = self.add_tile(preamp_master, 0, min_sep)
        dynlatch = self.add_tile(dyn_latch_master, 0, preamp_ncol + 2*min_sep)
        sr = self.add_tile(sr_master, 0, preamp_ncol + dyn_latch_ncol + 3*min_sep)

        sup_vm_cols = [min_sep//2, preamp_ncol + min_sep + min_sep//2,
                       preamp_ncol + dyn_latch_ncol + 2*min_sep+min_sep//2]    # Collect some col idx for vm supply
        vdd_list, vss_list = [], []
        tap_ncol = self.get_tap_ncol(tile_idx=0)
        tap_sep_col = self.sub_sep_col
        sup_vm_cols.append(self.num_cols + tap_sep_col//2)
        self.add_tap(self.num_cols + tap_sep_col, vdd_list, vss_list)
        sup_vm_cols.append(self.num_cols + tap_sep_col//2)
        self.set_mos_size(self.num_cols + tap_sep_col)

        preamp_o_n, preamp_o_p = preamp.get_pin('outn'), preamp.get_pin('outp')
        dynlatch_i_n, dynlatch_i_p = dynlatch.get_pin('inn'), dynlatch.get_pin('inp')
        dynlatch_o_n, dynlatch_o_p = dynlatch.get_pin('outn', layer=hm_layer), dynlatch.get_pin('outp', layer=hm_layer)
        sr_i_n, sr_i_p = sr.get_pin('r', layer=hm_layer), sr.get_pin('s', layer=hm_layer)
        # mn, mp = self.connect_differential_tracks(preamp_o_n, preamp_o_p, vm_layer, m_tidxs[1], m_tidxs[0],
        #                                           width=tr_w_sig_vm)
        self.connect_wires([preamp_o_n, preamp_o_p, dynlatch_i_n, dynlatch_i_p])
        self.connect_wires([dynlatch_o_n, sr_i_n])
        self.connect_wires([dynlatch_o_p, sr_i_p])

        # xm in/out
        _, xm_inout_tid = tr_manager.place_wires(xm_layer, ['sig']*2, center_coord=self.bound_box.h//2)

        signal_locs = self.params['signal_locs']
        xm_inout_tid[0] = sig_locs.get('inn', xm_inout_tid[0])
        xm_inout_tid[1] = sig_locs.get('inp', xm_inout_tid[1])
        tr_w_sig_xm = tr_manager.get_width(xm_layer, 'sig')

        inn, inp = self.connect_differential_tracks(preamp.get_pin('inn'), preamp.get_pin('inp'), xm_layer,
                                                    xm_inout_tid[0], xm_inout_tid[1], width=tr_w_sig_xm)
        outp, outn = self.connect_differential_tracks(sr.get_pin('q'), sr.get_pin('qb'), xm_layer,
                                                    xm_inout_tid[0], xm_inout_tid[1], width=tr_w_sig_xm)

        # Connect supplies
        # hm sup
        inst_list = [preamp, dynlatch, sr]
        vdd_hm_list, vss_hm_list = [], []
        for inst in inst_list:
            vdd_hm_list.append(inst.get_pin('VDD'))
            vss_hm_list.append(inst.get_pin('VSS'))
        vdd_hm, vss_hm = self.connect_wires(vdd_hm_list, upper=self.bound_box.xh, lower=self.bound_box.xl),\
                         self.connect_wires(vss_hm_list, upper=self.bound_box.xh, lower=self.bound_box.xl)
        self.connect_to_track_wires(vdd_list, vdd_hm)
        self.connect_to_track_wires(vss_list, vss_hm)

        # vm sup
        vdd_vm_list, vss_vm_list =[], []
        tr_w_sup_vm = tr_manager.get_width(vm_layer, 'sup')
        for c in sup_vm_cols:
            _tidx = self.arr_info.col_to_track(vm_layer, c, mode=RoundMode.NEAREST)
            vdd_vm_list.append(self.connect_to_tracks(vdd_hm, TrackID(vm_layer, _tidx, tr_w_sup_vm)))
            vss_vm_list.append(self.connect_to_tracks(vss_hm, TrackID(vm_layer, _tidx, tr_w_sup_vm)))

        # xm sup
        tr_w_sup_xm = tr_manager.get_width(xm_layer, 'sup')
        vdd_xm_coord = self.grid.track_to_coord(hm_layer, vdd_hm_list[0].track_id.base_index)
        vdd_xm_tid = self.grid.coord_to_track(xm_layer, vdd_xm_coord, RoundMode.NEAREST)
        vdd_xm = self.connect_to_tracks(vdd_vm_list, TrackID(xm_layer, vdd_xm_tid, tr_w_sup_xm),
                                             track_lower=vdd_hm_list[0].lower, track_upper=vdd_hm_list[0].upper)
        vss_xm_coord = self.grid.track_to_coord(hm_layer, vss_hm_list[0].track_id.base_index)
        vss_xm_tid = self.grid.coord_to_track(xm_layer, vss_xm_coord, RoundMode.NEAREST)
        vss_xm = self.connect_to_tracks(vss_vm_list, TrackID(xm_layer, vss_xm_tid, tr_w_sup_xm),
                                             track_lower=vss_hm_list[0].lower, track_upper=vss_hm_list[0].upper)

        # export clk to xm
        tr_w_clk_xm = tr_manager.get_width(xm_layer, 'clk')
        tr_w_clk_ym = tr_manager.get_width(ym_layer, 'clk')
        clk_xm_tidx = self.grid.coord_to_track(xm_layer, preamp.get_pin('clk').middle, mode=RoundMode.NEAREST)
        clk_xm = self.connect_to_tracks(preamp.get_pin('clk'), TrackID(xm_layer, clk_xm_tidx, tr_w_clk_xm),
                                        min_len_mode=MinLenMode.MIDDLE)
        clkb_xm = self.connect_to_tracks(dynlatch.get_pin('clk'), TrackID(xm_layer, clk_xm_tidx, tr_w_clk_xm),
                                         min_len_mode=MinLenMode.MIDDLE)
        clk_ym_tidx = self.grid.coord_to_track(ym_layer, self.grid.track_to_coord(vm_layer, preamp.get_pin('clk').track_id.base_index),
                                               RoundMode.NEAREST)
        clkb_ym_tidx = self.grid.coord_to_track(ym_layer, self.grid.track_to_coord(vm_layer, dynlatch.get_pin('clk').track_id.base_index),
                                                RoundMode.NEAREST)
        clk_ym = self.connect_to_tracks(clk_xm, TrackID(ym_layer, clk_ym_tidx, tr_w_clk_ym))
        clkb_ym = self.connect_to_tracks(clkb_xm, TrackID(ym_layer, clkb_ym_tidx, tr_w_clk_ym))
        # Connect supplies
        # ym layer
        if self.params['export_sup_to_xm1']:
            tr_w_sup_ym = tr_manager.get_width(ym_layer, 'sup')
            tr_w_sup_xm = tr_manager.get_width(xm_layer, 'sup')
            tr_w_sup_xm1 = tr_manager.get_width(xm1_layer, 'sup')
            ym_tid_l = self.arr_info.col_to_track(ym_layer, 0, mode=RoundMode.GREATER_EQ)
            ym_tid_r = self.arr_info.col_to_track(ym_layer, self.num_cols, mode=RoundMode.LESS_EQ)
            # num_ym_sup = tr_manager.get_num_wires_between(ym_layer, 'dum', ym_tid_l, 'dum', ym_tid_r, 'sup')
            # _, ym_sup_tidxs = tr_manager.place_wires(ym_layer, ['dum']+['sup']*num_ym_sup+['dum'],
            #                                          center_coord=self.bound_box.w//2)
            ym_sup_tidxs = self.get_available_tracks(ym_layer, ym_tid_l, ym_tid_r, self.bound_box.yl,
                                                     self.bound_box.yh, width = tr_w_sup_ym,
                                                     sep=tr_manager.get_sep(ym_layer, ('sup', 'sup')))

            ym_sup_tidxs = ym_sup_tidxs[1:-1]

            vdd_ym = [self.connect_to_tracks(vdd_xm, TrackID(ym_layer, tid, tr_w_sup_ym))
                           for tid in ym_sup_tidxs[::2]]
            vss_ym = [self.connect_to_tracks(vss_xm, TrackID(ym_layer, tid, tr_w_sup_ym))
                           for tid in ym_sup_tidxs[1::2]]
            xm1_tidx_list = [self.grid.coord_to_track(xm1_layer, 0, mode=RoundMode.NEAREST),
                             self.grid.coord_to_track(xm1_layer, self.bound_box.h, mode=RoundMode.NEAREST)]
            vdd_xm1 = self.connect_to_tracks(vdd_ym, TrackID(xm1_layer, xm1_tidx_list[1], tr_w_sup_xm1),
                                             track_lower=self.bound_box.xl, track_upper=self.bound_box.xh)
            vss_xm1 = self.connect_to_tracks(vss_ym, TrackID(xm1_layer, xm1_tidx_list[0], tr_w_sup_xm1),
                                             track_lower=self.bound_box.xl, track_upper=self.bound_box.xh)
            self.add_pin('VDD_ym', vdd_ym, label='VDD', show=self.show_pins)
            self.add_pin('VSS_ym', vss_ym, label='VSS', show=self.show_pins)
            self.add_pin('VDD_xm1', vdd_xm1, label='VDD', show=self.show_pins)
            self.add_pin('VSS_xm1', vss_xm1, label='VSS', show=self.show_pins)
            self.add_pin('VDD_xm', vdd_xm, label='VDD', show=self.show_pins)
            self.add_pin('VSS_xm', vss_xm, label='VSS', show=self.show_pins)
        else:
            self.add_pin('VDD', vdd_xm, label='VDD', show=self.show_pins)
            self.add_pin('VSS', vss_xm, label='VSS', show=self.show_pins)

        if self.params['shift_input']:
            match_vm_top = max(preamp.get_pin('inn').bound_box.yh, preamp.get_pin('inp').bound_box.yh)
            via_ext = self.grid.get_via_extensions(Direction.LOWER, hm_layer, 1, 1)
            # [mn, mp] = self.extend_wires([mn, mp], upper=match_vm_top+via_ext[1])

        s, d, dev_type = fill_conn_layer_intv(self, 0, 0, start_col=0, stop_col=self.num_cols, extend_to_gate=False)
        s, d, dev_type = fill_conn_layer_intv(self, 0, 1, start_col=0, stop_col=self.num_cols, extend_to_gate=False)

        # self.reexport(preamp.get_port('inn'))
        # self.reexport(preamp.get_port('inp'))
        # self.reexport(sr.get_port('q'), net_name='outp')
        # self.reexport(sr.get_port('qb'), net_name='outn')
        self.add_pin('inn', inn)
        self.add_pin('inp', inp)
        self.add_pin('outn', outn)
        self.add_pin('outp', outp)
        self.reexport(sr.get_port('r'))
        self.reexport(sr.get_port('s'))
        self.add_pin('clk', [preamp.get_pin('clk'), clk_ym])
        self.add_pin('clkb', [dynlatch.get_pin('clk'), clkb_ym])

        # Schematic params
        self.sch_params = dict(
            preamp=preamp_master.sch_params,
            dynlatch=dyn_latch_master.sch_params,
            sr=sr_master.sch_params,
        )


class SAFFCol(RingOscUnit):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            num_stages='Number of stages',
            saff_params='strongArm flops parameter',
            pinfo='Pinfo for unit row strongArm flop',
            topbot_dummy='Add empty topbot dummy row',
            signal_locs=''
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(topbot_dummy=True, signal_locs={})

    def draw_layout(self) -> None:
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        saff_params: Param = self.params['saff_params']
        num_stages: int = self.params['num_stages']
        topbot_dummy: int = self.params['topbot_dummy']
        saff_template: SAFFCore = self.new_template(SAFFCore,
                                                    params=saff_params.copy(append=dict(pinfo=pinfo,
                                                                                        signal_locs=self.params['signal_locs'])))
        self.draw_base(saff_template.draw_base_info)
        tr_manager = self.tr_manager

        tot_rows = num_stages + 2 if topbot_dummy else num_stages   # Two match bottom and top dummy of ring

        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        ym_layer = xm_layer + 1
        xm1_layer = ym_layer + 1
        min_sep = self.min_sep_col

        saff_list=[self.add_tile(saff_template, idx + 1 if topbot_dummy else idx, 0) for idx in range(num_stages)]
        self.set_mos_size(num_cols=saff_template.num_cols, num_tiles=tot_rows)

        vdd_ym_list = [w for inst in saff_list for w in inst.get_all_port_pins('VDD_ym')]
        vss_ym_list = [w for inst in saff_list for w in inst.get_all_port_pins('VSS_ym')]
        self.connect_wires(vdd_ym_list, lower=self.bound_box.yl, upper=self.bound_box.yh)
        self.connect_wires(vss_ym_list, lower=self.bound_box.yl, upper=self.bound_box.yh)

        [self.reexport(inst.get_port('VDD_xm1'), net_name='VDD') for inst in saff_list]
        [self.reexport(inst.get_port('VSS_xm1'), net_name='VSS') for inst in saff_list]

        [self.add_pin(f'inn<{idx}>', saff_list[idx].get_pin('inn')) for idx in range(num_stages)]
        [self.add_pin(f'inp<{idx}>', saff_list[idx].get_pin('inp')) for idx in range(num_stages)]

        [self.add_pin(f'outn<{idx}>', saff_list[idx].get_pin('outn')) for idx in range(num_stages)]
        [self.add_pin(f'outp<{idx}>', saff_list[idx].get_pin('outp')) for idx in range(num_stages)]

        clk_ym = self.connect_wires([inst.get_pin('clk', layer=ym_layer) for inst in saff_list])
        clkb_ym = self.connect_wires([inst.get_pin('clkb', layer=ym_layer)  for inst in saff_list])

        self.add_pin('clk', clk_ym)
        self.add_pin('clkb', clkb_ym)

        self._sch_params = saff_template.sch_params