from typing import Any, Dict, List, Mapping, Union, Type, Optional

from bag.design.database import ModuleDB, Module
from bag.layout.routing.base import TrackID, WireArray, HalfInt
from bag.layout.template import TemplateDB
from bag.util.immutable import Param
from bag3_digital.layout.stdcells.gates import InvCore
from pybag.enum import MinLenMode, RoundMode, Orient2D
from xbase.layout.enum import MOSWireType
from xbase.layout.enum import SubPortMode
from xbase.layout.mos.base import MOSBasePlaceInfo, MOSBase, SupplyColumnInfo
from xbase.layout.mos.placement.data import TilePatternElement, TilePattern
from xbase.layout.mos.primitives import MOSConn


class RingOscCoupled(MOSBase):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)
        self._col_tot = 0
        self._dum_info = []

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='The MOSBasePlaceInfo object.',
            seg_dict='Number of segments.',
            w_dict='Width',
            num_stages='Number of RO stages',
            delta='delta between ro and coupler, delta=0 means self coupled',
            out_buf='True to enable output buffers',
            self_coupled='True to couple the output from each other',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            delta=2,
            num_stage=4,
            out_buf=True,
            self_coupled=False,
        )

    def _draw_dum(self, tile_idx: int, col: int, seg: int, wn: int, wp: int, flip=False):
        # (prow, nrow) = (0, 1) if flip else (1, 0)
        prow, nrow = 1, 0
        pmos = self.add_mos(prow, col, seg, tile_idx=tile_idx, w=wp)
        nmos = self.add_mos(nrow, col, seg, tile_idx=tile_idx, w=wn)

        vdd, vss = pmos.s, nmos.s
        vdd_d, vss_d = pmos.d, nmos.d
        self.connect_wires([pmos.d, pmos.g])
        self.connect_wires([nmos.d, nmos.g])
        lch = self.arr_info.lch
        th = self.get_tile_info(tile_idx)[0].get_row_place_info(prow).row_info.threshold
        self._dum_info.append((('pch', wp, lch, th, '', ''), seg))
        self._dum_info.append((('nch', wn, lch, th, '', ''), seg))

        return vdd, vss, vdd_d, vss_d

    def _draw_inv(self, tile_idx, col, seg_n, seg_p, wn, wp, in_tidx=None, out_vm=True, in_vm=False, flip=False,
                  out_vm_offset=0, in_vm_offset=0, break_input=False, in_tid_shift=0):
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1

        max_seg = max(seg_n, seg_p)
        # (prow, nrow) = (0, 1) if flip else (1, 0)
        prow, nrow = 1, 0

        nmos = self.add_mos(nrow, col + (max_seg - seg_n) // 2, seg_n, w=wn, tile_idx=tile_idx)
        pmos = self.add_mos(prow, col + (max_seg - seg_n) // 2, seg_n, w=wp, tile_idx=tile_idx)

        # connect input
        if in_tidx is None:
            in_tid = self.get_track_id(0, MOSWireType.G, wire_name='sig', wire_idx=0, tile_idx=tile_idx)
        else:
            in_tid = self.get_track_id(in_tidx[0], MOSWireType.G, wire_name='sig', wire_idx=in_tidx[1],
                                       tile_idx=tile_idx)

        vdd, vss = pmos.s, nmos.s
        pout, nout = pmos.d, nmos.d
        pin, nin = pmos.g, nmos.g

        if break_input:
            in_tid = self.get_track_id(nrow, MOSWireType.G, wire_name='sig', wire_idx=0, tile_idx=tile_idx)
            in_warr = [self.connect_to_tracks(nin, in_tid, min_len_mode=MinLenMode.MIDDLE)]
            in_tid = self.get_track_id(prow, MOSWireType.G, wire_name='sig', wire_idx=in_tid_shift, tile_idx=tile_idx)
            in_warr.append(self.connect_to_tracks(pin, in_tid, min_len_mode=MinLenMode.MIDDLE))
        else:
            in_warr = self.connect_to_tracks([pin, nin], in_tid, min_len_mode=MinLenMode.MIDDLE)

        # # connect output
        # out_loc = tr_manager.place_wires(hm_layer, ['out'])[1][0]
        # if pout_tidx is None:
        tile_pinfo = self.get_tile_info(tile_idx)[0]
        sig_tidx = 1 if tile_pinfo.get_row_place_info(prow).row_info.flip else 0
        pout_tid = self.get_track_id(prow, MOSWireType.DS, wire_name='sig', wire_idx=sig_tidx, tile_idx=tile_idx)
        sig_tidx = 1 if tile_pinfo.get_row_place_info(nrow).row_info.flip else 0
        nout_tid = self.get_track_id(nrow, MOSWireType.DS, wire_name='sig', wire_idx=sig_tidx, tile_idx=tile_idx)

        pout_warr = self.connect_to_tracks(pout, pout_tid, min_len_mode=MinLenMode.MIDDLE)
        nout_warr = self.connect_to_tracks(nout, nout_tid, min_len_mode=MinLenMode.MIDDLE)

        # connect output
        out_tidx = self.grid.coord_to_track(vm_layer, pout_warr.middle, mode=RoundMode.NEAREST)

        tr_w_out_v = self.tr_manager.get_width(vm_layer, 'sig')
        if out_vm:
            out_tidx_shift = out_vm_offset + out_tidx
            tid = TrackID(vm_layer, out_tidx_shift, width=tr_w_out_v)
            out_warr = self.connect_to_tracks([pout_warr, nout_warr], tid)
        else:
            out_warr = [pout_warr, nout_warr]

        if in_vm:
            in_tidx = out_tidx - in_vm_offset
            tid = TrackID(vm_layer, in_tidx, width=tr_w_out_v)
            if break_input:
                in_warr_vm = self.connect_to_tracks(in_warr[0], tid)
                in_warr = [in_warr_vm, in_warr[1]]
            else:
                in_warr_vm = self.connect_to_tracks(in_warr, tid)
                in_warr = in_warr_vm
        return in_warr, out_warr, vdd, vss

    def _draw_buf_row(self, loc_list, tile_idx, flip, wn, wp, segn, segp):
        vbot_list, vss_list, vdd_list, inp_list, inn_list, outp_list, outn_list = [], [], [], [], [], [], []
        vss_d_list, vdd_d_list = [], []
        if loc_list[0] > 0:
            _vdd, _vss, _vdd_d, _vss_d = self._draw_dum(tile_idx, 0, loc_list[0] - 2, wn, wp, flip)
            vdd_list.append(_vdd)
            vss_list.append(_vss)
            vdd_d_list.append(_vdd_d)
            vss_d_list.append(_vss_d)
        loc_list.append(self.num_cols)
        for loc, loc_nxt in zip(loc_list[:-1], loc_list[1:]):
            _inp, _outp, _vdd, _vss = \
                self._draw_inv(tile_idx, loc, segn, segp, wn, wp, flip=flip, in_vm=True, out_vm_offset=-1)
            vdd_list.append(_vdd)
            vbot_list.append(_vss)
            loc += max(segn, segp)
            _inn, _outn, _vdd, _vss = \
                self._draw_inv(tile_idx, loc, segn, segp, wn, wp, flip=flip, in_vm=True, out_vm_offset=1)
            vdd_list.append(_vdd)
            vbot_list.append(_vss)
            inp_list.append(_inp)
            inn_list.append(_inn)
            outp_list.append(_outp)
            outn_list.append(_outn)
            loc += max(segn, segp)
            # if loc_nxt > loc:
            #     _vdd, _vss, _vdd_d, _vss_d = self._draw_dum(row, loc, loc_nxt - loc, wn, wp, flip)
            #     vdd_list.append(_vdd)
            #     vss_list.append(_vss)
            #     vdd_d_list.append(_vdd_d)
            #     vss_d_list.append(_vss_d)

        _vdd, _vss, _vdd_d, _vss_d = self._draw_dum(tile_idx, loc + 2, loc_list[-1] - loc - 2, wn, wp, flip)
        vdd_list.append(_vdd)
        vss_list.append(_vss)
        vdd_d_list.append(_vdd_d)
        vss_d_list.append(_vss_d)

        return vbot_list, vss_list, vdd_list, inp_list, inn_list, outp_list, outn_list, vss_d_list, vdd_d_list

    def draw_layout(self) -> None:
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(pinfo)

        seg_dict: Dict[str, int] = self.params['seg_dict']
        w_dict: Dict[str, int] = self.params['w_dict']
        num_stages: int = self.params['num_stages']
        delta: int = self.params['delta']

        self_coupled: bool = self.params['self_coupled']
        out_buf: bool = self.params['out_buf']

        seg_inv = seg_dict['inv']
        seg_buf = seg_dict['buf']
        seg_coupler = seg_dict['coupler']

        wn = w_dict['wn']
        wp = w_dict['wp']
        wn_buf = w_dict['wn_buf']
        wp_buf = w_dict['wp_buf']
        wn_coupled = w_dict['wn_coupled']
        wp_coupled = w_dict['wp_coupled']

        tr_manager = self.tr_manager
        hm_layer = self.arr_info.conn_layer + 1
        vm_layer = hm_layer + 1
        min_sep = self.min_sep_col

        # Calculate segments
        seg_tot = (num_stages + 2) * (2 * max(seg_inv, seg_coupler)) + (num_stages + 1) * min_sep

        # Add sub-contact
        ptap_tile_tidx0, ptap_tile_tidx1, ntap_tile_tidx0, ntap_tile_tidx1 = 0, 4, 2, 6
        ro_tile_tidx, couple_tile_tidx, buf_tile_tidx = 3, 1, 5
        ptap0 = self.add_substrate_contact(0, 0, seg=seg_tot, tile_idx=ptap_tile_tidx0, port_mode=SubPortMode.EVEN)
        ptap1 = self.add_substrate_contact(0, 0, seg=seg_tot, tile_idx=ptap_tile_tidx1, port_mode=SubPortMode.EVEN)
        ntap0 = self.add_substrate_contact(0, 0, seg=seg_tot, tile_idx=ntap_tile_tidx0, port_mode=SubPortMode.EVEN)
        ntap1 = self.add_substrate_contact(0, 0, seg=seg_tot, tile_idx=ntap_tile_tidx1, port_mode=SubPortMode.EVEN)

        self.set_mos_size()

        num_g_tids = 6  # Necessary tracks for coupled inverter routing
        ng_tidx_list, pg_tidx_list = list(range(num_g_tids)), list(range(num_g_tids))

        # === 1. Compute necessary infomation for RO ===

        # -- 1.1 Flip inverters, make flip n,p sides --
        flip_np_list = []
        for idx in range(num_stages // 2):
            if idx & 1:
                flip_np_list.extend([False, True])
            else:
                flip_np_list.extend([True, False])

        sig_locs_list = [{} for idx in range(num_stages)]
        sig_locs_map = [
            {'in_n': (1, ng_tidx_list[2]), 'in_p': (1, ng_tidx_list[1])},
            {'in_n': (0, pg_tidx_list[2]), 'in_p': (1, ng_tidx_list[0])},
            {'in_n': (0, pg_tidx_list[0]), 'in_p': (0, pg_tidx_list[1])}
        ]

        # -- 1.2 Compute signals' list for main ring --
        coupled_index = [1, 2, 1, 0]
        unit_idx_list = [idx * 2 for idx in range(num_stages // 2)] + [idx * 2 + 1 for idx in range(num_stages // 2)][
                                                                      ::-1]
        unit_idx_list = unit_idx_list + unit_idx_list[0:delta]
        for idx in range(num_stages):
            if idx == 0:
                sig_locs_list[idx].update(sig_locs_map[1])
            elif idx == num_stages - 1:
                _idx = idx // 2
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])
            elif idx & 1:
                _idx = (idx - 1) // 2 + 2
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])
            else:
                _idx = (idx // 2) - 1
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])

        # -- 1.3 Find coupled loop, and compute coupled loop signals locs --
        loop0, loop1 = [unit_idx_list[0]], [unit_idx_list[1]]
        _new = 2
        while unit_idx_list[_new] not in loop0:
            loop0.append(unit_idx_list[_new])
            _new += 2
        _new = 3
        while unit_idx_list[_new] not in loop1:
            loop1.append(unit_idx_list[_new])
            _new += 2
        ng_tidx_list = ng_tidx_list[::-1]
        for idx, num in enumerate(loop0):
            idxn, idxp = 2 * coupled_index[idx % 4], 2 * coupled_index[idx % 4] + 1

            sig_locs_list[num].update({'in_p_coupled': (0, ng_tidx_list[idxp]),
                                       'in_n_coupled': (0, ng_tidx_list[idxn])})
            if self.params['out_buf']:
                if idx == 0:
                    sig_locs_list[loop0[idx - 1]].update({'out_n': (0, ng_tidx_list[idxp]),
                                                          'out_p': (0, ng_tidx_list[idxn])})
                else:
                    sig_locs_list[loop0[idx - 1]].update({'out_p': (0, ng_tidx_list[idxp]),
                                                          'out_n': (0, ng_tidx_list[idxn])})

            # pdb.set_trace()
        for idx, num in enumerate(loop1):
            idxn, idxp = 2 * coupled_index[idx % 4], 2 * coupled_index[idx % 4] + 1
            sig_locs_list[num].update({'in_p_coupled': (1, pg_tidx_list[idxp]),
                                       'in_n_coupled': (1, pg_tidx_list[idxn])})
            if self.params['out_buf']:
                if idx == 0:
                    sig_locs_list[loop1[idx - 1]].update({'out_n': (1, pg_tidx_list[idxp]),
                                                          'out_p': (1, pg_tidx_list[idxn])})
                else:
                    sig_locs_list[loop1[idx - 1]].update({'out_p': (1, pg_tidx_list[idxp]),
                                                          'out_n': (1, pg_tidx_list[idxn])})

        # === 2. Place instances ===
        in_n_list, in_p_list, out_n_list, out_p_list = [], [], [], []
        inc_n_list, inc_p_list, outc_n_list, outc_p_list = [], [], [], []
        vss_list, vdd_list, vssc_list, vddc_list = [], [], [], []
        loc_list = []
        cur_loc = 0

        # -- 2.1 Dummy at left side --
        vdd_dum_l, vss_dum_l, vddd_dum_l, vssd_dum_l = \
            self._draw_dum(ro_tile_tidx, cur_loc, 2 * max(seg_dict['inv'], seg_dict['coupler']), wn, wp, flip=True)
        vddc_dum_l, vssc_dum_l, vdddc_dum_l, vssdc_dum_l = \
            self._draw_dum(couple_tile_tidx, cur_loc, 2 * max(seg_dict['inv'], seg_dict['coupler']), wn, wp, flip=False)
        cur_loc = 2 * max(seg_dict['inv'], seg_dict['coupler']) + min_sep

        # -- 2.2 Main instances --
        for idx in range(num_stages):
            _sig_locs = sig_locs_list[idx]
            _flip_np = flip_np_list[idx]
            loc_list.append(cur_loc)
            _inn, _outn, _vdd, _vss = self._draw_inv(ro_tile_tidx, cur_loc, seg_dict['inv'], seg_dict['inv'], wn, wp,
                                                     in_tidx=_sig_locs['in_p'], flip=True)
            vss_list.append(_vss)
            vdd_list.append(_vdd)
            _inp, _outp, _vdd, _vss = self._draw_inv(ro_tile_tidx, cur_loc + seg_dict['inv'], seg_dict['inv'],
                                                     seg_dict['inv'], wn, wp, in_tidx=_sig_locs['in_n'], flip=True)
            _inp_c, _outp_c, _vdd_c, _vss_c = \
                self._draw_inv(couple_tile_tidx, cur_loc, seg_dict['coupler'], seg_dict['coupler'],
                               wn_coupled, wp_coupled, in_tidx=_sig_locs['in_p_coupled'])
            vssc_list.append(_vss_c)
            vddc_list.append(_vdd_c)
            _inn_c, _outn_c, _vdd_c, _vss_c = \
                self._draw_inv(couple_tile_tidx, cur_loc + seg_dict['coupler'], seg_dict['coupler'],
                               seg_dict['coupler'], wn_coupled, wp_coupled, in_tidx=_sig_locs['in_n_coupled'])
            if _flip_np:
                _inp, _inn = _inn, _inp
                _outp, _outn = _outn, _outp
                _inn_c, _inp_c = _inp_c, _inn_c
            cur_loc += 2 * max(seg_dict['inv'], seg_dict['coupler']) + min_sep
            sig_list_list = [in_n_list, in_p_list, out_p_list, out_n_list, vss_list, vdd_list, inc_n_list, inc_p_list,
                             outc_n_list, outc_p_list, vssc_list, vddc_list]
            sig_list = [_inn, _inp, _outp, _outn, _vss, _vdd, _inn_c, _inp_c, _outn_c, _outp_c, _vss_c, _vdd_c]
            for sig, siglist in zip(sig_list, sig_list_list):
                siglist.append(sig)

        # -- 2.3 Dummy at right side --
        vdd_dum_r, vss_dum_r, vddd_dum_r, vssd_dum_r = \
            self._draw_dum(ro_tile_tidx, cur_loc, 2 * max(seg_dict['inv'], seg_dict['coupler']), wn, wp, flip=True)
        vddc_dum_r, vssc_dum_r, vdddc_dum_r, vssdc_dum_r = \
            self._draw_dum(couple_tile_tidx, cur_loc, 2 * max(seg_dict['inv'], seg_dict['coupler']), wn, wp, flip=False)
        vdd_list.extend([vdd_dum_r, vdd_dum_l])
        vddc_list.extend([vddc_dum_r, vddc_dum_l])
        self.connect_wires([vddd_dum_r, vdddc_dum_r])
        self.connect_wires([vddd_dum_l, vdddc_dum_l])

        # -- 2.4 Buffers rows at bottom and top --
        # vss_bot, vdd_bot, inp_bot_list, inn_bot_list, outp_bot_list, outn_bot_list, vssd_bot, vddd_bot = \
        #     self._draw_buf_row(loc_list[::2], buf_n_b_row, True, wn_buf, wp_buf, seg_dict['inv'], seg_dict['inv'])
        vbot_buf, vss_top, vdd_top, inp_list, inn_list, outp_list, outn_list, vssd_top, vddd_top = \
            self._draw_buf_row(loc_list.copy(), buf_tile_tidx, False, wn_buf, wp_buf, seg_dict['inv'], seg_dict['inv'])

        loc_list.append(cur_loc)

        # === 3. Connections ===

        # -- 3.1 Main connections in RO --
        for idx in range(num_stages):
            idx_prev = unit_idx_list[idx]
            idx_next = unit_idx_list[idx + 1]
            idx_next_coupled = unit_idx_list[idx + 2]
            if idx == num_stages - 1:
                self.connect_to_track_wires(in_p_list[idx_next], out_p_list[idx_prev])
                self.connect_to_track_wires(in_n_list[idx_next], out_n_list[idx_prev])
            else:
                self.connect_to_track_wires(out_n_list[idx_prev], in_p_list[idx_next])
                self.connect_to_track_wires(out_p_list[idx_prev], in_n_list[idx_next])
            if idx >= num_stages - 2:
                out_n_list[idx_prev] = self.connect_to_track_wires(inc_p_list[idx_next_coupled], out_n_list[idx_prev])
                out_p_list[idx_prev] = self.connect_to_track_wires(inc_n_list[idx_next_coupled], out_p_list[idx_prev])
            else:
                out_p_list[idx_prev] = self.connect_to_track_wires(inc_p_list[idx_next_coupled], out_p_list[idx_prev])
                out_n_list[idx_prev] = self.connect_to_track_wires(inc_n_list[idx_next_coupled], out_n_list[idx_prev])

        # -- 3.2 Make connections between buffers and ring ---
        buf_in_n_list, buf_in_p_list, buf_out_n_list, buf_out_p_list = [], [], [], []
        for idx in range(num_stages):
            # if idx & 1:
            buf_in_n_list.append(inn_list[idx] if flip_np_list[idx] else inp_list[idx])
            buf_in_p_list.append(inp_list[idx] if flip_np_list[idx] else inn_list[idx])
            buf_out_n_list.append(outn_list[idx] if flip_np_list[idx] else outp_list[idx])
            buf_out_p_list.append(outp_list[idx] if flip_np_list[idx] else outn_list[idx])
            # else:
            # buf_in_n_list.append(inn_bot_list[idx // 2] if flip_np_list[idx] else inp_bot_list[idx // 2])
            # buf_in_p_list.append(inp_bot_list[idx // 2] if flip_np_list[idx] else inn_bot_list[idx // 2])
            # buf_out_n_list.append(outn_bot_list[idx // 2] if flip_np_list[idx] else outp_bot_list[idx // 2])
            # buf_out_p_list.append(outp_bot_list[idx // 2] if flip_np_list[idx] else outn_bot_list[idx // 2])
        out_n_list = [self.connect_wires([_buf, _out]) for _buf, _out in zip(buf_in_n_list, out_n_list)]
        out_p_list = [self.connect_wires([_buf, _out]) for _buf, _out in zip(buf_in_p_list, out_p_list)]

        # -- 3.3 Vtop for RO, will connect to VDD --
        vss_hm_top, vss_hm_bot, vdd = [], [], []
        mid_vdd_tid = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=ntap_tile_tidx0)
        vtop, vbot = [], []
        vtop.append(self.connect_to_tracks([ntap0] + vdd_list + vddc_list, mid_vdd_tid))

        # -- 3.4 connect/export VSS/VDD --
        # nbuf_vdd_bot_tid0 = self.get_wire_id(buf_ntap_row0, 'ds', wire_name='sup')
        # self.extend_wires(vddd_bot, lower=nbuf_vdd_bot_tid0.get_bounds(self.grid, True)[0], unit_mode=True)
        # vdd.append(self.connect_to_tracks([ntap0_buf['VDD_s']] + vdd_bot, nbuf_vdd_bot_tid0))

        nbuf_vdd_top_tid0 = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=ntap_tile_tidx1)
        self.extend_wires(vddd_top, upper=nbuf_vdd_top_tid0.get_bounds(self.grid)[1])
        vdd.append(self.connect_to_tracks([ntap1] + vdd_top, nbuf_vdd_top_tid0))

        bot_vss_tid = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=ptap_tile_tidx0)
        self.extend_wires([vssdc_dum_l, vssdc_dum_r], lower=bot_vss_tid.get_bounds(self.grid)[1])
        vss_hm_bot.append(self.connect_to_tracks([ptap0] + [vssc_dum_l, vssc_dum_r], bot_vss_tid))
        # bot_vss_tid = self.get_track_id(0, MOSWireType.DS, wire_idx=1, wire_name='sup', tile_idx=ptap_tile_tidx0)
        # vss_hm_bot.append(self.connect_to_tracks([ptap0] + [vssc_dum_l, vssc_dum_r], bot_vss_tid))

        top_vss_tid = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=ptap_tile_tidx1)
        self.extend_wires(vssd_top, lower=top_vss_tid.get_bounds(self.grid)[0])
        self.extend_wires([vssd_dum_l, vssd_dum_r], upper=top_vss_tid.get_bounds(self.grid)[0])
        vss_hm_top.append(self.connect_to_tracks([ptap1] + vss_top + [vss_dum_l, vss_dum_r], top_vss_tid))
        vbot_top_hm = self.connect_to_tracks(vbot_buf, top_vss_tid)

        # -- 3.5 Connect to VBOT --
        vbot_bot_tid = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=couple_tile_tidx)
        vbot.append(self.connect_to_tracks(vssc_list, vbot_bot_tid))
        vbot_top_tid = self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=ro_tile_tidx)
        vbot.append(self.connect_to_tracks(vss_list, vbot_top_tid))
        vbot.append(vbot_top_hm)

        # === 4. Bring up routing to higher level ===
        vdd_vm_tidx_list, vbot_vm_tidx_list, vss_vm_tidx_list = [], [], []
        for loc in loc_list:
            _vbot_tidx0 = self.arr_info.col_to_track(vm_layer, loc)
            _vbot_tidx1 = self.arr_info.col_to_track(vm_layer, loc - min_sep)
            _vdd_tidx = self.arr_info.col_to_track(vm_layer, loc - min_sep // 2)
            vbot_vm_tidx_list.extend([_vbot_tidx0, _vbot_tidx1])
            vdd_vm_tidx_list.append(_vdd_tidx)

        num_sup_side = 2 * max(seg_dict['inv'], seg_dict['coupler'])
        temp_list = []
        for idx in range(num_sup_side):
            temp_list.append(self.arr_info.col_to_track(vm_layer, seg_tot - num_sup_side + idx + 1))
        # temp_list = temp_list[::-1]
        for idx in range(num_sup_side):
            temp_list.append(self.arr_info.col_to_track(vm_layer, num_sup_side - idx - 1))

        vdd_vm_tidx_list.extend(temp_list[::2])
        vdd_vm_list, vbot_vm_list, vss_vm_list = [], [], []

        for tidx in vbot_vm_tidx_list:
            tid = TrackID(vm_layer, tidx, tr_manager.get_width(vm_layer, 'sup'))
            vbot_vm_list.append(self.connect_to_tracks(vbot, tid))

        sup_top_coord = self.grid.track_to_coord(hm_layer, vdd[0].track_id.base_index)
        sup_bot_coord = self.grid.track_to_coord(hm_layer, vss_hm_bot[0].track_id.base_index)
        for tidx in temp_list[1::2]:
            tid = TrackID(vm_layer, tidx, tr_manager.get_width(vm_layer, 'sup'))
            vss_vm_list.append(self.connect_to_tracks(vss_hm_top + vss_hm_bot, tid, track_upper=sup_top_coord,
                                                      track_lower=sup_bot_coord))

        vss_coord_top, vss_coord_bot = vss_vm_list[0].upper, vss_vm_list[0].lower

        for tidx in vdd_vm_tidx_list:
            tid = TrackID(vm_layer, tidx, tr_manager.get_width(vm_layer, 'sup'))
            vdd_vm_list.append(self.connect_to_tracks(vdd + vtop, tid, track_upper=sup_top_coord,
                                                      track_lower=sup_bot_coord))

        # === 5. Pins ===
        _idx = 0
        pin_added_list, pin_n_added_list, buf_pin_added_list, buf_pinn_added_list = [], [], [], []
        while out_p_list[unit_idx_list[_idx]] not in pin_added_list:
            pin_added_list.append(out_p_list[unit_idx_list[_idx]])
            pin_n_added_list.append(out_n_list[unit_idx_list[_idx]])
            buf_pin_added_list.append(buf_out_p_list[unit_idx_list[_idx]])
            buf_pinn_added_list.append(buf_out_n_list[unit_idx_list[_idx]])
            _idx += 1

        for idx, (pinp, pinn) in enumerate(zip(pin_added_list, pin_n_added_list)):
            self.add_pin(f"phi<{idx}>", pinp, show=self.show_pins)
            self.add_pin(f"phi<{idx + num_stages}>", pinn, show=self.show_pins)

        for idx, (pinp, pinn) in enumerate(zip(buf_pin_added_list, buf_pinn_added_list)):
            self.add_pin(f"phi_buf<{idx}>", pinp, show=self.show_pins)
            self.add_pin(f"phi_buf<{idx + num_stages}>", pinn, show=self.show_pins)

        self.add_pin('VBOT_hm', vbot, label='VBOT:', show=False)
        self.add_pin('VDD_hm', vdd + vtop, label='VDD:', show=False)
        self.add_pin('VBOT', vbot_vm_list, label='VBOT:', show=self.show_pins)
        self.add_pin('VDD', vdd_vm_list, label='VDD:', show=self.show_pins)
        self.add_pin('VSS', vss_vm_list, label='VSS:', show=self.show_pins)

        # self._sch_params = dict(
        #     inv_params=dict(
        #         lch=self.arr_info.lch,
        #         wp=wp,
        #         wn=wn,
        #         wp_coupled=wp_coupled,
        #         wn_coupled=wn_coupled,
        #         pth=self.get_tile_info(0)[0].get_row_place_info(1).row_info.threshold,
        #         nth=self.get_tile_info(0)[0].get_row_place_info(0).row_info.threshold,
        #         seg_n=seg_inv,
        #         seg_p=seg_inv,
        #         seg_n_coupled=seg_coupler,
        #         seg_p_coupled=seg_coupler,
        #         self_coupled=False,
        #         out_buf=out_buf,
        #     ),
        #     buf_params=dict(
        #         inv_params=dict(
        #             lch=self.arr_info.lch,
        #             wp=wp_buf,
        #             wn=wn_buf,
        #             pth=self.get_tile_info(5)[0].get_row_place_info(1).row_info.threshold,
        #             nth=self.get_tile_info(5)[0].get_row_place_info(0).row_info.threshold,
        #             seg_n=seg_buf,
        #             seg_p=seg_buf,
        #         ),
        #         num_stage=num_stages,
        #     ),
        #     num_stage=num_stages,
        #     delta=delta,
        #     dum_info=self._dum_info,
        # )


class RingOscUnit(MOSBase):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)
        self._col_tot = 0
        self._dum_info = []
        self._center_col = 0

    @property
    def center_col(self) -> int:
        return self._center_col

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='The MOSBasePlaceInfo object.',
            seg_dict='Number of segments.',
            w_dict='Width',
            out_buf='True to enable output buffers',
            sig_locs='Signal locations',
            is_dum='Dummy row'
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            out_buf=True,
            self_coupled=False,
            sig_locs={},
            is_dum=False
        )

    def get_mos_conn_template(self, tile_idx: int, row_idx: int, w: int, stack: int, seg: int):
        pinfo = self.get_tile_pinfo(tile_idx)
        rpinfo = pinfo.get_row_place_info(row_idx)
        row_info = rpinfo.row_info
        w_max = row_info.width

        conn_layer = self.conn_layer
        params = dict(
            row_info=row_info,
            conn_layer=conn_layer,
            seg=seg,
            w=w_max,
            stack=stack,
            arr_options=self.arr_info.arr_options,
            g_on_s=False,
            options={},
        )
        master = self.new_template(MOSConn, params=params)
        return master

    def draw_layout(self) -> None:
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(pinfo)

        seg_dict: Dict[str, int] = self.params['seg_dict']
        w_dict: Dict[str, int] = self.params['w_dict']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']

        out_buf: bool = self.params['out_buf']
        is_dum: bool = self.params['is_dum']

        seg_inv = seg_dict['inv']
        seg_buf = seg_dict['buf']
        seg_coupler = seg_dict['coupler']

        wn = w_dict['wn']
        wp = w_dict['wp']
        wn_buf = w_dict['wn_buf']
        wp_buf = w_dict['wp_buf']
        wn_coupled = w_dict['wn_coupled']
        wp_coupled = w_dict['wp_coupled']

        tr_manager = self.tr_manager
        hm_layer = self.arr_info.conn_layer + 1
        vm_layer = hm_layer + 1
        min_sep = self.min_sep_col

        nd0 = self.get_track_index(0, MOSWireType.DS, wire_name='sig', wire_idx=0)
        nd1 = self.get_track_index(0, MOSWireType.DS, wire_name='sig', wire_idx=1)
        pd0 = self.get_track_index(1, MOSWireType.DS, wire_name='sig', wire_idx=1)
        pd1 = self.get_track_index(1, MOSWireType.DS, wire_name='sig', wire_idx=0)

        ng0 = self.get_track_index(0, MOSWireType.G, wire_name='sig', wire_idx=0)
        ng1 = self.get_track_index(0, MOSWireType.G, wire_name='sig', wire_idx=2)
        ng2 = self.get_track_index(0, MOSWireType.G, wire_name='sig', wire_idx=3)
        pg2 = self.get_track_index(1, MOSWireType.G, wire_name='sig', wire_idx=-4)
        pg1 = self.get_track_index(1, MOSWireType.G, wire_name='sig', wire_idx=-3)
        pg0 = self.get_track_index(1, MOSWireType.G, wire_name='sig', wire_idx=-1)

        # Calculate segments
        seg_tot = 2 * (seg_inv + seg_buf + seg_coupler)

        nout_vm_tidx = self.arr_info.col_to_track(vm_layer, sig_locs.get('nout', 0) + seg_inv)
        pout_vm_tidx = self.arr_info.col_to_track(vm_layer, sig_locs.get('pout', 0) + seg_inv)
        inv_n_params = dict(pinfo=pinfo, seg=seg_inv, w_p=wp, w_n=wn, vertical_out=True,
                            sig_locs={'pout': pd0, 'nout': nd0, 'nin': ng2, 'out': nout_vm_tidx})
        inv_p_params = dict(pinfo=pinfo, seg=seg_inv, w_p=wp, w_n=wn, vertical_out=True,
                            sig_locs={'pout': pd0, 'nout': nd0, 'nin': pg2, 'out': pout_vm_tidx})
        coupler_n_params = dict(pinfo=pinfo, seg=seg_coupler, w_p=wp_coupled, w_n=wn_coupled, vertical_out=False,
                                sig_locs={'pout': pd0, 'nout': nd0, 'nin': ng1})
        coupler_p_params = dict(pinfo=pinfo, seg=seg_coupler, w_p=wp_coupled, w_n=wn_coupled, vertical_out=False,
                                sig_locs={'pout': pd0, 'nout': nd0, 'nin': pg1})
        buf_n_params = dict(pinfo=pinfo, seg=seg_buf, w_p=wp_buf, w_n=wn_buf, vertical_out=not is_dum,
                            sig_locs={'pout': pd0, 'nout': nd0, 'nin': ng0})
        buf_p_params = dict(pinfo=pinfo, seg=seg_buf, w_p=wp_buf, w_n=wn_buf, vertical_out=not is_dum,
                            sig_locs={'pout': pd0, 'nout': nd0, 'nin': pg0})

        sup_info = self.get_supply_column_info(vm_layer)

        nrow_mos_conn = self.get_mos_conn_template(0, 0, wn, stack=1, seg=2)
        tap_sep_col = self.sub_sep_col
        # add taps
        lay_range = range(self.conn_layer, vm_layer + 1)
        vdd_l_table: Dict[int, List[WireArray]] = {lay: [] for lay in lay_range}
        vss_l_table: Dict[int, List[WireArray]] = {lay: [] for lay in lay_range}
        vdd_r_table: Dict[int, List[WireArray]] = {lay: [] for lay in lay_range}
        vss_r_table: Dict[int, List[WireArray]] = {lay: [] for lay in lay_range}
        self.add_supply_column(sup_info, 0, vdd_l_table, vss_l_table)

        cur_loc = sup_info.ncol + tap_sep_col
        # Make sure all vertical routings area within range
        min_half_col = sig_locs.get('half_col_min', 0)
        cur_loc += max(0, min_half_col - seg_inv - seg_coupler - min_sep)
        core_l = cur_loc

        coupler_master = self.new_template(InvCore, params=coupler_n_params)
        inv_master = self.new_template(InvCore, params=inv_n_params)
        coupler_n = self.add_tile(coupler_master, 0, cur_loc)
        inv_n = self.add_tile(inv_master, 0, cur_loc + seg_coupler + min_sep)
        cur_loc += 2 * seg_inv + seg_coupler + 2 * min_sep

        coupler_master = self.new_template(InvCore, params=coupler_p_params)
        inv_master = self.new_template(InvCore, params=inv_p_params)
        self._center_col = cur_loc - seg_inv - min_sep // 2
        inv_p = self.add_tile(inv_master, 0, cur_loc, flip_lr=True)
        coupler_p = self.add_tile(coupler_master, 0, cur_loc + seg_coupler + min_sep, flip_lr=True)

        core_r = cur_loc
        cur_loc += seg_inv + min_sep + max(0, min_half_col - seg_inv - seg_coupler - min_sep)
        cur_loc += sup_info.ncol

        self.add_supply_column(sup_info, cur_loc + tap_sep_col, vdd_r_table, vss_r_table, flip_lr=True)
        cur_loc += tap_sep_col + tap_sep_col // 2

        buf_master = self.new_template(InvCore, params=buf_n_params)
        buf_n = self.add_tile(buf_master, 0, cur_loc)
        dum_short_to_supply_col = cur_loc + seg_buf + min_sep // 2
        buf_master = self.new_template(InvCore, params=buf_p_params)
        buf_p = self.add_tile(buf_master, 0, cur_loc + 2 * seg_buf + min_sep, flip_lr=True)

        self.set_mos_size(cur_loc + 2 * seg_buf + min_sep)

        # Connect vco core supply
        core_vdd_list, core_vss_list = [], []
        for inst in [coupler_p, coupler_n, inv_p, inv_n]:
            core_vdd_list.append(inst.get_pin('VDD'))
            core_vss_list.append(inst.get_pin('VSS'))
        core_l_coord = self.arr_info.col_to_coord(core_l)
        core_r_coord = self.arr_info.col_to_coord(core_r)
        core_vdd_list = self.extend_wires(core_vdd_list, lower=core_l_coord, upper=core_r_coord)
        core_vss_list = self.extend_wires(core_vss_list, lower=core_l_coord, upper=core_r_coord)

        core_vdd_hm = self.connect_wires(core_vdd_list)
        core_vss_hm = self.connect_wires(core_vss_list)

        if is_dum:
            dum_short_to_supply_tid = self.arr_info.col_to_track(vm_layer, dum_short_to_supply_col,
                                                                 mode=RoundMode.NEAREST)
            self.connect_to_tracks([buf_n.get_pin('nin'), buf_p.get_pin('nin'), buf_n.get_pin('nout'),
                                    buf_p.get_pin('nout'), buf_n.get_pin('pout'), buf_p.get_pin('pout')]+
                                   vss_l_table[2], TrackID(vm_layer, dum_short_to_supply_tid))
            self.connect_differential_wires([inv_n.get_pin('nin'), coupler_p.get_pin('nin')],
                                            [inv_p.get_pin('nin'), coupler_n.get_pin('nin')],
                                            vss_l_table[3][0], vss_r_table[3][0])
            self.connect_to_track_wires([inv_n.get_pin('nout'), coupler_n.get_pin('nout'), coupler_n.get_pin('pout')] +
                                        core_vss_hm, inv_n.get_pin('out'))
            self.connect_to_track_wires([inv_p.get_pin('nout'), coupler_p.get_pin('nout'), coupler_p.get_pin('pout')] +
                                        core_vss_hm, inv_p.get_pin('out'))
            vss_hm = self.connect_wires(vss_l_table[2] + [buf_n.get_pin('VSS'), buf_p.get_pin('VSS')])
            self.add_pin('VSS', vss_hm)
        else:
            self.connect_differential_wires(buf_n.get_pin('nin'), buf_p.get_pin('nin'), inv_n.get_pin('out'),
                                            inv_p.get_pin('out'))

            self.connect_wires([inv_n.get_pin('nout'), coupler_n.get_pin('nout')])
            self.connect_wires([inv_p.get_pin('nout'), coupler_p.get_pin('nout')])
            self.connect_wires([inv_n.get_pin('pout'), coupler_n.get_pin('pout')])
            self.connect_wires([inv_p.get_pin('pout'), coupler_p.get_pin('pout')])

            buf_vdd_list = [buf_p.get_pin('VDD'), buf_n.get_pin('VDD')]
            buf_vss_list = [buf_p.get_pin('VSS'), buf_n.get_pin('VSS')]
            buf_vdd_hm = self.connect_wires(buf_vdd_list + vdd_r_table[2])
            buf_vss_hm = self.connect_wires(buf_vss_list + vss_r_table[2])

            inn, inp = inv_n.get_pin('nin'), inv_p.get_pin('nin')
            couplern, couplerp = coupler_n.get_pin('nin'), coupler_p.get_pin('nin')
            in_hm_max_coord = max([pin.upper for pin in [inn, inp, couplern, couplerp]])
            in_hm_min_coord = min([pin.lower for pin in [inn, inp, couplern, couplerp]])

            inn = self.extend_wires(inn, upper=in_hm_max_coord, lower=in_hm_min_coord)
            inp = self.extend_wires(inp, upper=in_hm_max_coord, lower=in_hm_min_coord)
            couplern = self.extend_wires(couplern, upper=in_hm_max_coord, lower=in_hm_min_coord)
            couplerp = self.extend_wires(couplerp, upper=in_hm_max_coord, lower=in_hm_min_coord)
            self.add_pin('inn', inn, show=self.show_pins)
            self.add_pin('inp', inp, show=self.show_pins)
            self.add_pin('couplern', couplern, show=self.show_pins)
            self.add_pin('couplerp', couplerp, show=self.show_pins)
            self.add_pin('VDD_buf', buf_vdd_hm, show=self.show_pins)
            self.add_pin('VSS_buf', buf_vss_hm, show=self.show_pins)

        self.add_pin('VDD_core', core_vdd_hm, show=self.show_pins)
        self.add_pin('VSS_core', core_vss_hm, show=self.show_pins)
        self.add_pin('VDD_l', vdd_l_table[2], show=self.show_pins, connect=True)
        self.add_pin('VSS_l', vss_l_table[2], show=self.show_pins, connect=True)
        self.add_pin('VDD_r', vdd_r_table[2], show=self.show_pins, connect=True)
        self.add_pin('VSS_r', vss_r_table[2], show=self.show_pins, connect=True)
        self.add_pin('VDD', vdd_l_table[3] + vdd_r_table[3], show=self.show_pins)
        self.add_pin('VSS', vss_l_table[3] + vss_r_table[3], show=self.show_pins)
        self.reexport(inv_n.get_port('out'), net_name='outn', show=self.show_pins)
        self.reexport(inv_p.get_port('out'), net_name='outp', show=self.show_pins)
        self.reexport(buf_n.get_port('out'), net_name='buf_outn', show=self.show_pins)
        self.reexport(buf_p.get_port('out'), net_name='buf_outp', show=self.show_pins)

        self._sch_params = dict(
            delay_params=dict(
                lch=self.arr_info.lch,
                wp=wp,
                wn=wn,
                wp_coupled=wp_coupled,
                wn_coupled=wn_coupled,
                pth=self.get_tile_info(0)[0].get_row_place_info(1).row_info.threshold,
                nth=self.get_tile_info(0)[0].get_row_place_info(0).row_info.threshold,
                seg_n=seg_inv,
                seg_p=seg_inv,
                seg_n_coupled=seg_coupler,
                seg_p_coupled=seg_coupler,
                self_coupled=False,
                out_buf=out_buf,
            ),
            buf_params=dict(
                lch=self.arr_info.lch,
                wp=wp_buf,
                wn=wn_buf,
                pth=self.get_tile_info(0)[0].get_row_place_info(1).row_info.threshold,
                nth=self.get_tile_info(0)[0].get_row_place_info(0).row_info.threshold,
                seg_n=seg_buf,
                seg_p=seg_buf,
            ),
        )

    def get_supply_column_info(self, top_layer: int, tile_idx: int = 0) -> SupplyColumnInfo:
        grid = self.grid
        ainfo = self._arr_info
        tr_manager = ainfo.tr_manager

        pinfo = self.get_tile_pinfo(tile_idx)
        if not pinfo.is_complementary:
            raise ValueError('Currently only works on complementary tiles.')

        if top_layer <= self.conn_layer:
            raise ValueError(f'top_layer must be at least {self.conn_layer + 1}')
        if grid.get_direction(top_layer) == Orient2D.x:
            top_vm_layer = top_layer - 1
        else:
            top_vm_layer = top_layer

        # get total number of columns
        num_col = self.get_tap_ncol() + self.sub_sep_col
        tr_info_list = []
        for vm_lay in range(self.conn_layer + 2, top_vm_layer + 1, 2):
            blk_ncol = ainfo.get_block_ncol(vm_lay)
            tr_w = tr_manager.get_width(vm_lay, 'sup')
            tr_sep = tr_manager.get_sep(vm_lay, ('sup', 'sup'), half_space=False)
            ntr = 2 * tr_sep
            cur_ncol = -(-ainfo.get_column_span(vm_lay, ntr) // blk_ncol) * blk_ncol
            num_col = max(num_col, cur_ncol)
            tr_info_list.append((tr_w, tr_sep))

        # make sure we can draw substrate contact
        num_col += (num_col & 1)
        return SupplyColumnInfo(ncol=num_col, top_layer=top_layer, tr_info=tr_info_list)


class RingOscCol(MOSBase):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)
        self._col_tot = 0
        self._dum_info = []
        self._center_col = 0
        self._row_idx = []

    @property
    def row_idx(self) -> List[int]:
        return self._row_idx

    @property
    def center_col(self) -> int:
        return self._center_col

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'vco_ro_diff_coupled')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='The MOSBasePlaceInfo object.',
            seg_dict='Number of segments.',
            w_dict='Width',
            num_stages='Number of RO stages',
            delta='delta between ro and coupler, delta=0 means self coupled',
            out_buf='True to enable output buffers',
            sig_locs='Signal locations',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            delta=2,
            num_stage=4,
            out_buf=True,
            self_coupled=False,
            sig_locs={},
        )

    def get_mos_conn_template(self, tile_idx: int, row_idx: int, w: int, stack: int, seg: int):
        pinfo = self.get_tile_pinfo(tile_idx)
        rpinfo = pinfo.get_row_place_info(row_idx)
        row_info = rpinfo.row_info
        w_max = row_info.width

        conn_layer = self.conn_layer
        params = dict(
            row_info=row_info,
            conn_layer=conn_layer,
            seg=seg,
            w=w_max,
            stack=stack,
            arr_options=self.arr_info.arr_options,
            g_on_s=False,
            options={},
        )
        master = self.new_template(MOSConn, params=params)
        return master

    def draw_layout(self) -> None:
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(pinfo)

        seg_dict: Dict[str, int] = self.params['seg_dict']
        w_dict: Dict[str, int] = self.params['w_dict']
        num_stages: int = self.params['num_stages']
        delta: int = self.params['delta']
        sig_locs: Mapping[str, Union[float, HalfInt]] = self.params['sig_locs']

        out_buf: bool = self.params['out_buf']
        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1

        # === 1. Compute necessary infomation for RO ===
        num_g_tids = 6  # Necessary tracks for coupled inverter routing
        ng_tidx_list, pg_tidx_list = list(range(num_g_tids)), list(range(num_g_tids))
        half_col_min = self.arr_info.track_to_col(vm_layer, max(ng_tidx_list), mode=RoundMode.GREATER_EQ)

        # -- 1.1 Flip inverters, make flip n,p sides --
        flip_np_list = []
        for idx in range(num_stages // 2):
            if idx & 1:
                flip_np_list.extend([False, True])
            else:
                flip_np_list.extend([True, False])

        sig_locs_list = [{} for idx in range(num_stages)]
        sig_locs_map = [
            {'in_n': (1, ng_tidx_list[2]), 'in_p': (1, ng_tidx_list[1])},
            {'in_n': (0, pg_tidx_list[2]), 'in_p': (1, ng_tidx_list[0])},
            {'in_n': (0, pg_tidx_list[0]), 'in_p': (0, pg_tidx_list[1])}
        ]

        # -- 1.2 Compute signals' list for main ring --
        coupled_index = [1, 2, 1, 0]
        unit_idx_list = [idx * 2 for idx in range(num_stages // 2)] + [idx * 2 + 1 for idx in range(num_stages // 2)][
                                                                      ::-1]
        unit_idx_list = unit_idx_list + unit_idx_list[0:delta]
        for idx in range(num_stages):
            if idx == 0:
                sig_locs_list[idx].update(sig_locs_map[1])
            elif idx == num_stages - 1:
                _idx = idx // 2
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])
            elif idx & 1:
                _idx = (idx - 1) // 2 + 2
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])
            else:
                _idx = (idx // 2) - 1
                sig_locs_list[idx].update(sig_locs_map[_idx % 3])

        # -- 1.3 Find coupled loop, and compute coupled loop signals locs --
        loop0, loop1 = [unit_idx_list[0]], [unit_idx_list[1]]
        _new = 2
        while unit_idx_list[_new] not in loop0:
            loop0.append(unit_idx_list[_new])
            _new += 2
        _new = 3
        while unit_idx_list[_new] not in loop1:
            loop1.append(unit_idx_list[_new])
            _new += 2
        ng_tidx_list = ng_tidx_list[::-1]
        for idx, num in enumerate(loop0):
            out_idx = coupled_index[(idx + 1) % 4]
            sig_locs_list[num].update({'pout': -ng_tidx_list[out_idx],
                                       'nout': -ng_tidx_list[out_idx],
                                       'half_col_min': half_col_min})

        for idx, num in enumerate(loop1):
            out_idx = -coupled_index[(idx + 1) % 4] - 1
            sig_locs_list[num].update({'pout': -ng_tidx_list[out_idx],
                                       'nout': -ng_tidx_list[out_idx],
                                       'half_col_min': half_col_min})

        # === 2. Place instances ===
        stage_list = []
        loc_list = []
        cur_loc = 0
        # -- 2.1 Dummy at top --

        # -- 2.2 Main instances --
        for idx in range(0, num_stages):
            _sig_locs = sig_locs_list[idx]
            _flip_np = flip_np_list[idx]
            _params = dict(pinfo=pinfo, seg_dict=seg_dict, w_dict=w_dict, sig_locs=_sig_locs)
            _template = self.new_template(RingOscUnit, params=_params)
            stage_list.append(self.add_tile(_template, col_idx=0, tile_idx=idx + 1))
        dum_params = dict(pinfo=pinfo, seg_dict=seg_dict, w_dict=w_dict, is_dum=True)
        dum_template = self.new_template(RingOscUnit, params=dum_params)
        dum_b = self.add_tile(dum_template, col_idx=0, tile_idx=0)
        dum_t = self.add_tile(dum_template, col_idx=0, tile_idx=num_stages + 1)
        self.set_mos_size()
        inc_n_list = [inst.get_pin('couplern') for inst in stage_list]
        inc_p_list = [inst.get_pin('couplerp') for inst in stage_list]
        in_n_list = [inst.get_pin('inn') for inst in stage_list]
        in_p_list = [inst.get_pin('inp') for inst in stage_list]
        out_n_list = [inst.get_pin('outn') for inst in stage_list]
        out_p_list = [inst.get_pin('outp') for inst in stage_list]
        buf_out_n_list = [inst.get_pin('buf_outn') for inst in stage_list]
        buf_out_p_list = [inst.get_pin('buf_outp') for inst in stage_list]

        # -- 2.3 Dummy at bottom --
        # === 3. Connections ===

        # -- 3.1 Main connections in RO --
        for idx in range(num_stages):
            idx_prev = unit_idx_list[idx]
            idx_next = unit_idx_list[idx + 1]
            idx_next_coupled = unit_idx_list[idx + 2]
            if idx == num_stages - 1:
                self.connect_differential_wires(in_p_list[idx_next], in_n_list[idx_next],
                                                out_p_list[idx_prev], out_n_list[idx_prev])
            else:
                self.connect_differential_wires(in_p_list[idx_next], in_n_list[idx_next],
                                                out_n_list[idx_prev], out_p_list[idx_prev])
            if idx >= num_stages - 2:
                out_p_list[idx_prev], out_n_list[idx_prev] = \
                    self.connect_differential_wires(inc_p_list[idx_next_coupled], inc_n_list[idx_next_coupled],
                                                    out_p_list[idx_prev], out_n_list[idx_prev])
            else:
                out_p_list[idx_prev], out_n_list[idx_prev] = \
                    self.connect_differential_wires(inc_n_list[idx_next_coupled], inc_p_list[idx_next_coupled],
                                                    out_p_list[idx_prev], out_n_list[idx_prev])

        # === 5. Pins ===
        _idx = 0
        pin_added_list, pin_n_added_list, buf_pin_added_list, buf_pinn_added_list = [], [], [], []
        while out_p_list[unit_idx_list[_idx]] not in pin_added_list:
            pin_added_list.append(out_p_list[unit_idx_list[_idx]])
            pin_n_added_list.append(out_n_list[unit_idx_list[_idx]])
            buf_pin_added_list.append(buf_out_p_list[unit_idx_list[_idx]])
            buf_pinn_added_list.append(buf_out_n_list[unit_idx_list[_idx]])
            _idx += 1

        for idx, (pinp, pinn) in enumerate(zip(pin_added_list, pin_n_added_list)):
            self.add_pin(f"phi<{idx}>", pinp, show=self.show_pins)
            self.add_pin(f"phi<{idx + num_stages}>", pinn, show=self.show_pins)

        for idx, (pinp, pinn) in enumerate(zip(buf_pin_added_list, buf_pinn_added_list)):
            self.add_pin(f"phi_buf<{idx}>", pinp, show=self.show_pins)
            self.add_pin(f"phi_buf<{idx + num_stages}>", pinn, show=self.show_pins)

        self.add_pin('VTOP', [inst.get_pin('VDD_core') for inst in stage_list], connect=True)
        self.add_pin('VBOT', [inst.get_pin('VSS_core') for inst in stage_list], connect=True)
        self.add_pin('VDD_buf', [inst.get_pin('VDD_buf') for inst in stage_list], label='VDD', connect=True)
        self.add_pin('VSS_buf', [inst.get_pin('VSS_buf') for inst in stage_list], label='VSS', connect=True)
        stage_list += [dum_t, dum_b]
        self.add_pin('VDD_l', [inst.get_pin('VDD_l') for inst in stage_list], label='VDD', connect=True)
        self.add_pin('VSS_l', [inst.get_pin('VSS_l') for inst in stage_list], label='VSS', connect=True)
        self.add_pin('VDD_r', [inst.get_pin('VDD_r') for inst in stage_list], label='VDD', connect=True)
        self.add_pin('VSS_r', [inst.get_pin('VSS_r') for inst in stage_list], label='VSS', connect=True)
        self.add_pin('VSS', [inst.get_pin('VSS', layer=hm_layer) for inst in [dum_t, dum_b]],
                     label='VSS', connect=True)
        vdd_vm_list, vss_vm_list = [], []
        for inst in stage_list:
            vdd_vm_list.extend(inst.get_all_port_pins('VDD', layer=vm_layer))
            vss_vm_list.extend(inst.get_all_port_pins('VSS', layer=vm_layer))
        self.add_pin('VDD', self.connect_wires(vdd_vm_list), connect=True)
        self.add_pin('VSS', self.connect_wires(vss_vm_list), connect=True)

        params = dict(pinfo=pinfo, seg_dict=seg_dict, w_dict=w_dict, sig_locs={})
        template = self.new_template(RingOscUnit, params=params)
        self._center_col = template.center_col
        self._sch_params = template.sch_params
        self._row_idx = unit_idx_list[:-1]

        self._sch_params.update(
            dict(
                num_stage=num_stages,
                ndum=2,
                delta=delta,
                dum_info=self._dum_info,
                vbot_core='VBOT',
                vtop_core='VTOP',
            )
        )


class VCOCore(MOSBase):
    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)
        self._ring_ncol = 0
        self._dum_info = []
        self._row_idx = []

    @property
    def row_idx(self) -> List[int]:
        return self._row_idx

    @property
    def ring_ncol(self) -> int:
        return self._ring_ncol

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'vco_vco')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='The MOSBasePlaceInfo object.',
            ctrl_type='Type of ctrl transistor, pch or nch',
            seg_dict='Number of segments.',
            w_dict='Width',
            num_stages='Number of RO stages',
            delta='delta between ro and coupler, delta=0 means self coupled',
            out_buf='True to enable output buffers',
            sig_locs='Signal locations',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            delta=2,
            num_stage=4,
            out_buf=True,
            self_coupled=False,
            sig_locs={},
        )

    def draw_layout(self) -> None:
        ring_master: MOSBase = self.new_template(RingOscCol, params=self.params)
        seg_dict: Dict[str, int] = self.params['seg_dict']
        w_dict: Dict[str, int] = self.params['w_dict']
        tile_ele = []
        tile_table = ring_master.draw_base_info[1]
        nrow_ctrl = 2
        nrow_ring = ring_master.num_tile_rows
        is_pctrl = self.params['ctrl_type'] == 'pch'
        for idx in range(nrow_ring):
            tile_ele.append(TilePatternElement(tile_table['ro_tile'], flip=bool(idx & 1)))
        for idx in range(nrow_ctrl + 1):
            tile_ele.append(TilePatternElement(tile_table['ctrl_tile']))
        tap_name = 'ntap_tile' if is_pctrl else 'ptap_tile'
        tile_ele.append(TilePatternElement(tile_table[tap_name]))

        self.draw_base((TilePattern(tile_ele), tile_table))

        tr_manager = self.tr_manager
        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1

        ring_mid_col = ring_master.center_col
        # space for supply at sides
        ntr, _ = tr_manager.place_wires(vm_layer, ['sup'] * 4)
        sep_ncol = self.arr_info.get_column_span(vm_layer, ntr)

        #  Add control
        ctrl_mos_list = []
        seg_ctrl_row = seg_dict['ctrl'] // nrow_ctrl
        seg_ctrl = seg_ctrl_row * nrow_ctrl
        if seg_ctrl_row > 2 * ring_mid_col:
            ctrl_col = max(0, (seg_ctrl_row - 2 * ring_mid_col) // 2 - sep_ncol)
            ring_col = max((seg_ctrl_row - 2 * ring_mid_col) // 2, sep_ncol)
        else:
            ctrl_col = ring_mid_col - seg_ctrl_row // 2
            ring_col = 0

        ring = self.add_tile(ring_master, 0, ring_col)
        ctrl_g_list, ctrl_d_list = [], []
        for idx in range(nrow_ctrl):
            ctrl_mos_list.append(self.add_mos(0, ctrl_col, seg=seg_ctrl_row, tile_idx=nrow_ring + idx + 1))
            g_tid = self.get_track_id(0, MOSWireType.G, 'sup', 0, tile_idx=nrow_ring + idx + 1)
            d_tid = self.get_track_id(0, MOSWireType.DS, 'sup', 0, tile_idx=nrow_ring + idx + 1)
            ctrl_g_list.append(self.connect_to_tracks(ctrl_mos_list[-1].g, g_tid))
            ctrl_d_list.append(self.connect_to_tracks(ctrl_mos_list[-1].d, d_tid))

        tap = self.add_substrate_contact(0, 0, seg=self.num_cols, tile_idx=nrow_ring + nrow_ctrl + 1)
        # connect ctrl to tap
        tap_tid = self.get_track_id(0, MOSWireType.DS, 'sup', 0, tile_idx=nrow_ring + nrow_ctrl + 1)
        tap_sup = self.connect_to_tracks([tap] + [tx.s for tx in ctrl_mos_list], tap_tid)

        self.set_mos_size()
        ring_vdd_l = ring.get_all_port_pins('VDD_l')
        ring_vss_l = ring.get_all_port_pins('VSS_l')
        ring_vdd_r = ring.get_all_port_pins('VDD_r')
        ring_vss_r = ring.get_all_port_pins('VSS_r')
        ring_vbot = ring.get_all_port_pins('VBOT')
        ring_vtop = ring.get_all_port_pins('VTOP')

        if is_pctrl:
            vss_ring = self.connect_wires(ring_vss_l + ring_vss_r + ring_vbot)
            self.add_pin('VSS', vss_ring, show=self.show_pins)
            self.add_pin('VDD_l', ring_vdd_l, label='VDD', connect=True)
            self.add_pin('VDD_r', ring_vdd_r, label='VDD', connect=True)
            self.add_pin('vtop', ring_vtop + ctrl_d_list, connect=True)
        else:
            vdd_ring = self.connect_wires(ring_vdd_l + ring_vdd_r + ring_vtop)
            self.add_pin('VDD', vdd_ring, show=self.show_pins)
            self.add_pin('VSS_l', ring_vss_l, label='VSS', connect=True)
            self.add_pin('VSS_r', ring_vss_r, label='VSS', connect=True)
            self.add_pin('vbot', ring_vbot + ctrl_d_list, connect=True)

        self.connect_to_track_wires(tap_sup, ring.get_all_port_pins('VDD' if is_pctrl else 'VSS', layer=vm_layer))
        self.add_pin('VDD_ctrl' if is_pctrl else 'VSS_ctrl', tap_sup, label='VDD' if is_pctrl else 'VSS',
                     show=self.show_pins, connect=True)
        self.add_pin('vctrl_p' if is_pctrl else 'vctrl_n', ctrl_g_list, show=self.show_pins, connect=True)
        self.add_pin('VDD', ring.get_all_port_pins('VDD', layer=vm_layer), show=self.show_pins)
        self.add_pin('VSS', ring.get_all_port_pins('VSS', layer=vm_layer), show=self.show_pins)
        for port in ring.port_names_iter():
            if 'phi' in port:
                self.reexport(ring.get_port(port))
        self._ring_ncol = self.num_cols
        self._row_idx = ring_master.row_idx
        self._sch_params = dict(
            ro_params=ring_master.sch_params,
            ctrl_params=dict(
                lch=self.arr_info.lch,
                intent=self.get_tile_pinfo(nrow_ring).get_row_place_info(0).row_info.threshold,
                w=self.get_tile_pinfo(nrow_ring).get_row_place_info(0).row_info.width,
                seg=seg_ctrl
            ),
            is_pctrl=is_pctrl
        )
