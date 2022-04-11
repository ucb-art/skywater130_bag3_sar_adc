import math
from typing import Optional, List, Union

from bag.layout.routing.base import WireArray, TrackID
from bag.layout.template import TemplateBase
from bag.typing import TrackType
from bag.util.math import HalfInt
from pybag.core import BBox
from pybag.enum import RoundMode, MinLenMode, Direction, Orient2D
from xbase.layout.enum import MOSType, SubPortMode, MOSWireType
from xbase.layout.mos.base import MOSBase
from xbase.layout.mos.placement.data import MOSBasePlaceInfo, TilePatternElement, TilePattern


def draw_stack_wire(self: TemplateBase, wire: WireArray, top_layid: int, x0: Optional[Union[int, float]] = None,
                    y0: Optional[Union[int, float]] = None, x1: Optional[Union[int, float]] = None,
                    y1: Optional[Union[int, float]] = None, tr_list: Optional[List[Union[int, float]]] = None,
                    sp_list: Optional[List[Union[HalfInt, int]]] = None, max_mode: bool = True,
                    min_len_mode: MinLenMode = MinLenMode.NONE,
                    mode: int = 1, sep_margin: bool = False,
                    sp_margin_list: Optional[List[Union[HalfInt, int]]] = None) -> List[List[WireArray]]:
    """
        create WireArray from bot_layid to top_layid-1 within the given coordinates
    Parameters
    ----------
    self: TemplateBase
        template database.
    wire: WireArray
        wire to be connected.
    top_layid: Int
        top layer id.
    x0: Union[Int, float]
        bottom left, x coordinate.
    y0: Union[Int, float]
        bottom left, y coordinate.
    x1: Union[Int, float]
        top right, x coordinate.
    y1: Union[Int, float]
        top right, y coordinate.
    x_mode: Int
        x direction mode.
        If negative, the result wire will have width less than or equal to the given width.
        If positive, the result wire will have width greater than or equal to the given width.
    y_mode: Int
        y direction mode.
        If negative, the result wire will have width less than or equal to the given width.
        If positive, the result wire will have width greater than or equal to the given width.
    half_track: Bool
        True to get half track.
    tr_list: List[Union[Int, float]]
        Wire array track list.
    sp_list: List[Union[HalfInt]]
        Wire array track separation list.
    max_mode: Bool
        True to draw wire with max width from coordinates and tr_list
    track_mode:
        #######
    min_len_mode: Int
        Mininum length mode. See connect_to_tracks for details.
    mode: Int
        draw stack mode.
    Returns
    -------
    wire_arr_list: List[WireArray]
        stack wire list.
    """
    bot_layid = wire.layer_id
    # get wire layer
    if top_layid > bot_layid:
        layer_flip = False
    else:
        layer_flip = True

    if tr_list is not None:
        if len(tr_list) != top_layid - bot_layid:
            raise ValueError('If given tr_list, its length should same as layers(top_layid-bot_layid)')

    # get coordinate
    if x0 is None:
        x0 = wire.bound_box.xl
    if y0 is None:
        y0 = wire.bound_box.yl
    if x1 is None:
        x1 = wire.bound_box.xh
    if y1 is None:
        y1 = wire.bound_box.yh

    # check coordinates
    if x1 <= x0 or y1 <= y0:
        raise ValueError("If given coordinates,"
                         "we need left coord smaller than right coordinate\n"
                         "and bottom coordinate smaller than top coordinate")
    if bot_layid == top_layid:
        raise ValueError("Need top_layer != wire layer. It can be larger or smaller than it.")

    # draw stack wires
    wire_arr_list = [wire]
    if not layer_flip:
        swp_list = list(range(bot_layid, top_layid))
    else:
        swp_list = list(range(top_layid, bot_layid))[::-1]

    for i in swp_list:
        if self.grid.get_direction(i + 1) == Orient2D.y:
            if mode == 0:
                tr, tr_w = self.grid.interval_to_track(i + 1, (x0, x1))
                if tr_w is None:
                    tr_w = 1
                # could specify tr from outside and choose the larger one
                if tr_list is not None:
                    if tr_list[i - bot_layid] is not None:
                        if max_mode:
                            tr_w = max(tr_w, tr_list[i - bot_layid])
                        else:
                            tr_w = tr_list[i - bot_layid]

                tr_tid = TrackID(i + 1, tr, width=tr_w)
                wire_n = self.connect_to_tracks(wire_arr_list[-1], tr_tid, track_lower=y0, track_upper=y1,
                                                min_len_mode=min_len_mode)
            elif mode == 1:
                # get wire width and space
                if tr_list is not None:
                    w_ntr = tr_list[i - bot_layid]
                else:
                    w_ntr = wire.bound_box.w
                if sp_list is not None:
                    sp_ntr = sp_list[i - bot_layid]
                else:
                    sp_ntr = self.grid.get_sep_tracks(i + 1, ntr1=w_ntr, ntr2=w_ntr)
                if sp_margin_list is not None:
                    sp_margin_ntr = sp_margin_list[i - bot_layid]
                else:
                    sp_margin_ntr = sp_ntr // 2
                tid_lower = self.grid.coord_to_track(i + 1, x0, mode=RoundMode.GREATER_EQ)
                tid_upper = self.grid.coord_to_track(i + 1, x1, mode=RoundMode.LESS_EQ)
                if tid_lower == tid_upper:
                    tr_idx = [tid_upper]
                else:
                    tr_idx = self.get_available_tracks(i + 1, tid_lower, tid_upper, y0 - 170, y1 + 170, w_ntr,
                                                       sep=sp_ntr,
                                                       sep_margin=sp_margin_ntr if sep_margin else None,
                                                       include_last=True)
                    if tid_upper - tid_lower < w_ntr and len(tr_idx) > 0:
                        tr_idx = [(tid_upper + tid_lower) / 2]
                wire_n = []
                for idx in tr_idx:
                    tr_tid = TrackID(i + 1, idx, width=w_ntr)
                    wire_n.append(self.connect_to_tracks(wire_arr_list[-1], tr_tid, min_len_mode=min_len_mode))
            else:
                raise ValueError("For now, only support two modes.")
        else:
            if mode == 0:
                tr, tr_w = self.grid.interval_to_track(i + 1, (y0, y1))
                if tr_w is None:
                    tr_w = 1
                # could specify tr from outside and choose the larger one
                if tr_list is not None:
                    if tr_list[i - bot_layid] is not None:
                        if max_mode:
                            tr_w = max(tr_w, tr_list[i - bot_layid])
                        else:
                            tr_w = tr_list[i - bot_layid]
                tr_tid = TrackID(i + 1, tr, width=tr_w)
                wire_n = self.connect_to_tracks(wire_arr_list[-1], tr_tid, track_lower=x0, track_upper=x1,
                                                min_len_mode=min_len_mode)
            elif mode == 1:
                # get wire width and space
                if tr_list is not None:
                    w_ntr = tr_list[i - bot_layid]
                else:
                    w_ntr = wire.bound_box.w
                if sp_list is not None:
                    sp_ntr = sp_list[i - bot_layid]
                else:
                    sp_ntr = self.grid.get_sep_tracks(i + 1, ntr1=w_ntr, ntr2=w_ntr)
                if sp_margin_list is not None:
                    sp_margin_ntr = sp_margin_list[i - bot_layid]
                else:
                    sp_margin_ntr = sp_ntr // 2
                tid_lower = self.grid.coord_to_track(i + 1, y0, mode=RoundMode.GREATER_EQ)
                tid_upper = self.grid.coord_to_track(i + 1, y1, mode=RoundMode.LESS_EQ)
                if tid_upper == tid_lower:
                    tr_idx = [tid_lower]
                else:
                    tr_idx = self.get_available_tracks(i + 1, tid_lower, tid_upper, x0 - 150, x1 + 150, w_ntr,
                                                       sep=sp_ntr,
                                                       sep_margin=sp_margin_ntr if sep_margin else None,
                                                       include_last=True)
                    if tid_upper - tid_lower < w_ntr and len(tr_idx) > 0:
                        tr_idx = [(tid_upper + tid_lower) / 2]

                wire_n = []
                for idx in tr_idx:
                    tr_tid = TrackID(i + 1, idx, width=w_ntr)
                    wire_n.append(
                        self.connect_to_tracks(wire_arr_list[-1], tr_tid, min_len_mode=min_len_mode, track_lower=x0,
                                               track_upper=x1))
            else:
                raise ValueError("For now, only support two modes.")

        wire_arr_list.append(wire_n)

    return wire_arr_list


def max_conn_wires(self, tr_manager, wire_type, wire_list, start_coord=None, end_coord=None):
    max_coord, min_coord = 0, math.inf
    for w in wire_list:
        max_coord = max_coord if max_coord > w.upper else w.upper
        min_coord = min_coord if min_coord < w.lower else w.lower

    start_coord = start_coord if start_coord is not None else min_coord
    end_coord = end_coord if end_coord is not None else max_coord
    if end_coord < start_coord:
        raise ValueError("[Util Error:] End points smaller than start point, please check")
    conn_layer = wire_list[0].layer_id + 1
    conn_w = tr_manager.get_width(conn_layer, wire_type)
    cur_tidx = self.grid.coord_to_track(conn_layer, start_coord, mode=RoundMode.NEAREST)
    res_wire_list = []
    while self.grid.track_to_coord(conn_layer, cur_tidx) < end_coord:
        res_wire_list.append(self.connect_to_tracks(wire_list, TrackID(conn_layer, cur_tidx, conn_w)))
        cur_tidx = tr_manager.get_next_track(conn_layer, cur_tidx, wire_type, wire_type)
    if len(res_wire_list) < 1:
        raise ValueError("[Util Error:] Targeted connection have no effect")
    return res_wire_list


def fill_and_collect(mosbase, tile_idx, ret_p_list, ret_n_list, collect_all_bnd_dummies=True, extend_to_gate=False,
                     start_col=None, stop_col=None, fill_empty=False):
    nrows = mosbase.get_tile_pinfo(tile_idx).num_rows
    for _idx in range(nrows):
        _s, _d, _dev_type = fill_conn_layer_intv(mosbase, tile_idx, _idx, extend_to_gate=extend_to_gate,
                                                 start_col=start_col, stop_col=stop_col, fill_empty=fill_empty)
        if (_idx == 0 or _idx == nrows - 1) and collect_all_bnd_dummies:
            if _dev_type == MOSType.nch:
                ret_n_list.append(_s + _d)
            if _dev_type == MOSType.pch:
                ret_p_list.append(_s + _d)
        else:
            if _dev_type == MOSType.nch:
                if _d and _s:
                    ret_n_list.append([_s[0], _s[-1], _d[0], _d[-1]])
                elif _s:
                    ret_n_list.append([_s[0], _s[-1]])
                elif _d:
                    ret_n_list.append([_d[0], _d[-1]])
            elif _dev_type == MOSType.pch:
                if _d and _s:
                    ret_p_list.append([_s[0], _s[-1], _d[0], _d[-1]])
                elif _s:
                    ret_p_list.append([_s[0], _s[-1]])
                elif _d:
                    ret_p_list.append([_d[0], _d[-1]])


def connect_conn_dummy_rows(mosbase: MOSBase, dum_row_list: List[List[WireArray]], connect_to_sup: bool = False,
                            sup_coord=0, sup_dum_idx=0):
    if len(dum_row_list) == 1:
        pass
    else:
        nrow = len(dum_row_list)
        for idx in range(nrow - 1):
            mosbase.connect_wires(dum_row_list[idx] + dum_row_list[idx + 1])

    if connect_to_sup:
        if sup_dum_idx == 0:
            mosbase.extend_wires(dum_row_list[sup_dum_idx], lower=sup_coord)
        if sup_dum_idx < 0:
            mosbase.extend_wires(dum_row_list[sup_dum_idx], upper=sup_coord)


def fill_conn_layer_intv(mosbase: MOSBase, tile_idx: int, row_idx: int,
                         extend_to_gate: bool = True, export_gate: bool = False,
                         start_col=None, stop_col=None, fill_empty=False):
    if extend_to_gate & export_gate:
        raise ValueError('Cant use both extend_to_gate and export_gate')
    ncols = mosbase.num_cols
    start_col = start_col if start_col else 0
    stop_col = stop_col if stop_col else ncols
    pinfo, tile_yb, flip_tile = mosbase.used_array.get_tile_info(tile_idx)
    row_place_info = mosbase.get_tile_pinfo(tile_idx).get_row_place_info(row_idx)
    row_info = mosbase.get_row_info(row_idx, tile_idx)
    dev_type = row_info.row_type
    g_side_bnd = row_info.g_conn_y[0] if extend_to_gate else row_info.ds_conn_y[0]
    if flip_tile:
        tile_yb += pinfo.height
        if row_info.flip:
            conn_lower, conn_upper = (-row_place_info.yt_blk + tile_yb + g_side_bnd,
                                      -row_place_info.yt_blk + tile_yb + row_info.ds_conn_y[1])
        else:
            conn_lower, conn_upper = (-row_place_info.yb_blk + tile_yb - row_info.ds_conn_y[1],
                                      -row_place_info.yb_blk + tile_yb - g_side_bnd)
    else:
        if row_info.flip:
            conn_lower, conn_upper = (row_place_info.yt_blk + tile_yb - row_info.ds_conn_y[1],
                                      row_place_info.yt_blk + tile_yb - g_side_bnd)

        else:
            conn_lower, conn_upper = (row_place_info.yb_blk + tile_yb + g_side_bnd,
                                      row_place_info.yb_blk + tile_yb + row_info.ds_conn_y[1])

    if export_gate:
        tile_yb += pinfo.height
        if row_info.flip:
            g_conn_lower, g_conn_upper = (-row_place_info.yt_blk + tile_yb + row_info.g_conn_y[0],
                                          -row_place_info.yt_blk + tile_yb + row_info.g_conn_y[1])
        else:
            g_conn_lower, g_conn_upper = (-row_place_info.yb_blk + tile_yb - row_info.g_conn_y[1],
                                          -row_place_info.yb_blk + tile_yb - row_info.g_conn_y[0])
    else:
        if row_info.flip:
            g_conn_lower, g_conn_upper = (row_place_info.yt_blk + tile_yb - row_info.g_conn_y[1],
                                          row_place_info.yt_blk + tile_yb - row_info.g_conn_y[0])

        else:
            g_conn_lower, g_conn_upper = (row_place_info.yb_blk + tile_yb + row_info.g_conn_y[0],
                                          row_place_info.yb_blk + tile_yb + row_info.g_conn_y[1])

    if fill_empty:
        intv_list = [[(start_col, stop_col)]]
    else:
        try:
            intv_list = mosbase.used_array.get_complement(tile_idx, row_idx, start_col, stop_col)
        except IndexError:
            intv_list = mosbase.used_array.get_complement(tile_idx, row_idx, 0, ncols)

    s_dum_list, d_dum_list = [], []
    for intv in intv_list:
        intv_pair = intv[0]
        if intv_pair[0] > stop_col or intv_pair[1] < start_col:
            continue
        else:
            intv_pair = (intv_pair[0], min(intv_pair[1], stop_col))
            intv_pair = (max(intv_pair[0], start_col), intv_pair[1])
            ndum = intv_pair[1] - intv_pair[0]
        if ndum < 1 or (ndum == 1 and intv_pair[0] != 0 and intv_pair[1] != mosbase.num_cols):
            continue
        s_track = mosbase.arr_info.col_to_track(mosbase.conn_layer, intv_pair[0] + 2 if intv_pair[0] else 0,
                                                mode=RoundMode.NEAREST)
        d_track = mosbase.arr_info.col_to_track(mosbase.conn_layer, intv_pair[0] + 1, mode=RoundMode.NEAREST)
        s_ndum = ndum // 2 - 1 + (1 & ndum)
        d_ndum = ndum // 2
        if intv_pair[0] == 0:
            s_ndum += 1
        if intv_pair[1] == mosbase.num_cols and (not 1 & ndum):
            s_ndum += 1
        if intv_pair[1] == mosbase.num_cols and ndum == 1:
            d_ndum += 1
        if intv_pair[1] == mosbase.num_cols and (1 & ndum):
            d_ndum += 1
        if s_ndum:
            s_dum_list.append(mosbase.add_wires(mosbase.conn_layer, s_track, conn_lower, conn_upper,
                                                num=s_ndum, pitch=2))
        if d_ndum:
            d_dum_list.append(mosbase.add_wires(mosbase.conn_layer, d_track, conn_lower, conn_upper,
                                                num=d_ndum, pitch=2))
    return s_dum_list, d_dum_list, dev_type


def get_available_tracks_reverse(mosbase, layer_id: int, tid_lo: TrackType, tid_hi: TrackType,
                                 lower: int, upper: int, width: int = 1, sep: HalfInt = HalfInt(1),
                                 include_last: bool = False, sep_margin: Optional[HalfInt] = None
                                 ) -> List[HalfInt]:
    grid = mosbase.grid

    orient = grid.get_direction(layer_id)
    tr_info = grid.get_track_info(layer_id)
    if sep_margin is None:
        sep_margin = grid.get_sep_tracks(layer_id, width, 1, same_color=False)
    bl, bu = grid.get_wire_bounds_htr(layer_id, 0, width)
    tr_w2 = (bu - bl) // 2
    margin = tr_info.pitch * sep_margin - (tr_info.width // 2) - tr_w2

    sp_list = [0, 0]
    sp_list[orient.value ^ 1] = margin
    spx, spy = sp_list

    htr0 = HalfInt.convert(tid_lo).dbl_value
    htr1 = HalfInt.convert(tid_hi).dbl_value
    if include_last:
        htr0 -= 1
    htr_sep = HalfInt.convert(sep).dbl_value
    ans = []
    cur_htr = htr1
    while cur_htr > htr0:
        mid = grid.htr_to_coord(layer_id, cur_htr)
        box = BBox(orient, lower, upper, mid - tr_w2, mid + tr_w2)
        if not mosbase._layout.get_intersect(layer_id, box, spx, spy, False):
            ans.append(HalfInt(cur_htr))
            cur_htr -= htr_sep
        else:
            cur_htr -= 1

    return ans


def fill_tap_intv(mosbase, tile_idx, start_col, stop_col, port_mode=SubPortMode.EVEN) -> None:
    if stop_col - start_col < mosbase.min_sub_col:
        return
    nrow = mosbase.get_tile_info(tile_idx)[0].num_rows
    for idx in range(nrow):
        cur_row_type = mosbase.get_tile_info(tile_idx)[0].get_row_place_info(idx).row_info.row_type
        if cur_row_type is MOSType.ptap or cur_row_type is MOSType.nch:
            tap = mosbase.add_substrate_contact(idx, start_col, tile_idx=tile_idx, seg=stop_col - start_col,
                                                port_mode=port_mode)
        elif cur_row_type is MOSType.ntap or cur_row_type is MOSType.pch:
            tap = mosbase.add_substrate_contact(idx, start_col, tile_idx=tile_idx, seg=stop_col - start_col,
                                                port_mode=port_mode)
        else:
            tap = None
        if tap:
            try:
                tid = mosbase.get_track_id(idx, MOSWireType.DS, 'sup', tile_idx=tile_idx)
            except:
                tid = mosbase.get_track_id(idx, MOSWireType.G, 'sup', tile_idx=tile_idx)
            mosbase.connect_to_tracks(tap, tid)


def make_flipped_tile_pattern(grid, pinfo, ntiles, tile_name='logic_tile'):
    pinfo = MOSBasePlaceInfo.make_place_info(grid, pinfo)
    pinfo_list = [TilePatternElement(pinfo[1][tile_name], flip=not (idx & 1)) for idx in range(ntiles)]
    return TilePattern(pinfo_list), pinfo[1]


def export_xm_sup(mosbase, tile_idx, export_top=False, export_bot=False, given_locs=None, xm_only=False):
    """
    This function export top or bot supply to xm layer
    """

    # Setup routing information
    hm_layer = mosbase.conn_layer + 1
    vm_layer = hm_layer + 1
    xm_layer = vm_layer + 1

    tr_manager = mosbase.tr_manager
    tr_w_sup_vm = tr_manager.get_width(vm_layer, 'sup')
    tr_w_sup_xm = tr_manager.get_width(xm_layer, 'sup')
    tr_sp_sup_vm = tr_manager.get_sep(vm_layer, ('sup', 'sup'))

    # Get tile info, get coord and row_idx
    pinfo, tile_yb, flip_tile = mosbase.used_array.get_tile_info(tile_idx)
    bot_coord = tile_yb
    top_coord = tile_yb + pinfo.height
    bot_ridx = -1 if flip_tile else 0
    top_ridx = 0 if flip_tile else -1

    # Get track info
    vm_min_len = mosbase.grid.get_next_length(vm_layer, tr_w_sup_vm, 0, even=True)
    vm_min_le_sp = mosbase.grid.get_line_end_space(vm_layer, tr_w_sup_vm, even=True)
    xm_bnd_l, xm_bnd_u = mosbase.grid.get_wire_bounds_htr(xm_layer, 0, tr_w_sup_xm)

    xm_w = xm_bnd_u - xm_bnd_l

    # Get xm layer info, calculate margin
    sep_margin = mosbase.grid.get_sep_tracks(xm_layer, tr_w_sup_xm, 1, same_color=False)
    tr_info = mosbase.grid.get_track_info(xm_layer)
    margin = tr_info.pitch * sep_margin // 2

    via_ext_xm, via_ext_vm = mosbase.grid.get_via_extensions(Direction.LOWER, hm_layer, tr_w_sup_xm, tr_w_sup_vm)

    # Get vm layer info, calculate margin
    vm_margin = max(vm_min_len, xm_w) // 2 + 2 * vm_min_le_sp  # If not perfect align, add margin by *2
    margin = max(vm_margin, margin) + 2 * max(vm_min_le_sp, via_ext_vm)
    vm_sep_margin = mosbase.grid.get_sep_tracks(vm_layer, tr_w_sup_vm, tr_w_sup_vm, same_color=False)
    vm_tr_info = mosbase.grid.get_track_info(vm_layer)
    vm_margin = vm_tr_info.pitch * vm_sep_margin // 2

    # Get start and end track locs, avoid short with adjacent blocks
    vm_ti_lo = mosbase.grid.coord_to_track(vm_layer, mosbase.bound_box.xl + vm_margin, mode=RoundMode.GREATER_EQ)
    vm_ti_hi = mosbase.grid.coord_to_track(vm_layer, mosbase.bound_box.xh - vm_margin, mode=RoundMode.LESS_EQ)

    if export_bot:
        if not given_locs:
            bot_vm_locs = mosbase.get_available_tracks(vm_layer, vm_ti_lo, vm_ti_hi,
                                                       bot_coord - margin // 2, bot_coord + margin // 2,
                                                       width=tr_w_sup_vm, sep=tr_sp_sup_vm, include_last=False)
        else:
            bot_vm_locs = given_locs

        bot_hm_tid = mosbase.get_track_id(bot_ridx, MOSWireType.DS, 'sup', 0, tile_idx=tile_idx)
        bot_sup_hm = mosbase.add_wires(hm_layer, bot_hm_tid.base_index, mosbase.bound_box.xl, mosbase.bound_box.xh,
                                       width=bot_hm_tid.width)
        bot_sup_vm = []
        if not xm_only:
            for tid in bot_vm_locs:
                bot_sup_vm.append(mosbase.connect_to_tracks(bot_sup_hm, TrackID(vm_layer, tid, tr_w_sup_vm),
                                                            min_len_mode=MinLenMode.MIDDLE))

        xm_sup_coord = mosbase.grid.track_to_coord(hm_layer, bot_hm_tid.base_index)
        xm_sup_tid = mosbase.grid.coord_to_track(xm_layer, xm_sup_coord, mode=RoundMode.NEAREST)
        if bot_sup_vm:
            bot_sup_xm = mosbase.connect_to_tracks(bot_sup_vm, TrackID(xm_layer, xm_sup_tid, tr_w_sup_xm),
                                                   track_lower=mosbase.bound_box.xl, track_upper=mosbase.bound_box.xh)
        else:
            bot_sup_xm = mosbase.add_wires(xm_layer, xm_sup_tid, width=tr_w_sup_xm, lower=mosbase.bound_box.xl,
                                           upper=mosbase.bound_box.xh)
    else:
        bot_sup_xm = None

    if export_top:
        if not given_locs:
            top_vm_locs = mosbase.get_available_tracks(vm_layer, vm_ti_lo, vm_ti_hi,
                                                       top_coord - margin, top_coord + margin,
                                                       width=tr_w_sup_vm, sep=tr_sp_sup_vm, include_last=False)
        else:
            top_vm_locs = given_locs

        top_hm_tid = mosbase.get_track_id(top_ridx, MOSWireType.DS, 'sup', 0, tile_idx=tile_idx)
        top_sup_hm = mosbase.add_wires(hm_layer, top_hm_tid.base_index, mosbase.bound_box.xl, mosbase.bound_box.xh,
                                       width=top_hm_tid.width)
        top_sup_vm = []
        if not xm_only:
            for tid in top_vm_locs:
                top_sup_vm.append(mosbase.connect_to_tracks(top_sup_hm, TrackID(vm_layer, tid, tr_w_sup_vm),
                                                            min_len_mode=MinLenMode.MIDDLE))

        xm_sup_coord = mosbase.grid.track_to_coord(hm_layer, top_hm_tid.base_index)
        xm_sup_tid = mosbase.grid.coord_to_track(xm_layer, xm_sup_coord, mode=RoundMode.NEAREST)

        if top_sup_vm:
            top_sup_xm = mosbase.connect_to_tracks(top_sup_vm, TrackID(xm_layer, xm_sup_tid, tr_w_sup_xm),
                                                   track_lower=mosbase.bound_box.xl, track_upper=mosbase.bound_box.xh)
        else:
            top_sup_xm = mosbase.add_wires(xm_layer, xm_sup_tid, width=tr_w_sup_xm, lower=mosbase.bound_box.xl,
                                           upper=mosbase.bound_box.xh)
    else:
        top_sup_xm = None

    return bot_sup_xm, top_sup_xm


def fill_tap(mosbase, tile_idx, port_mode=SubPortMode.EVEN, extra_margin=True):
    """
    This method fill empty region with sub contact
    """

    _, _, flip_tile = mosbase.used_array.get_tile_info(tile_idx)
    intv_list = mosbase.used_array.get_complement(tile_idx, 0, 0, mosbase.num_cols)

    tap_sep = mosbase.min_sep_col
    tap_sep += tap_sep & 1
    tap_sep += 2 if extra_margin else 0
    min_fill_ncols = mosbase.tech_cls.min_sub_col + 2 * tap_sep

    def get_diff_port(pmode):
        return SubPortMode.EVEN if pmode == SubPortMode.ODD else SubPortMode.ODD

    row0_sup, row1_sup = [], []
    for intv in intv_list:
        intv_pair = intv[0]
        # if intv_pair[1] == mosbase.num_cols:
        #     min_fill_ncols -= mosbase.tech_cls.min_sep_col
        # if intv_pair[0] == mosbase.num_cols:
        #     min_fill_ncols -= mosbase.tech_cls.min_sep_col
        nspace = intv_pair[1] - intv_pair[0]
        if nspace < min_fill_ncols:
            continue
        else:
            _port_mode = get_diff_port(port_mode) if (intv_pair[0] + mosbase.min_sep_col) & 1 else port_mode
            tap0 = mosbase.add_substrate_contact(0, intv_pair[0] + tap_sep, seg=nspace - 2 * tap_sep,
                                                 tile_idx=tile_idx, port_mode=_port_mode)
        try:
            tid0 = mosbase.get_track_id(0, MOSWireType.DS, 'sup', tile_idx=tile_idx)
            row0_sup.append(mosbase.connect_to_tracks(tap0, tid0))
        except:
            row0_sup.append(tap0)
    intv_list = mosbase.used_array.get_complement(tile_idx, 1, 0, mosbase.num_cols)
    for intv in intv_list:
        intv_pair = intv[0]
        nspace = intv_pair[1] - intv_pair[0]
        if nspace < min_fill_ncols:
            continue
        else:
            _port_mode = get_diff_port(port_mode) if (intv_pair[0] + mosbase.min_sep_col) & 1 else port_mode
            tap1 = mosbase.add_substrate_contact(1, intv_pair[0] + tap_sep, seg=nspace - 2 * tap_sep,
                                                 tile_idx=tile_idx, port_mode=_port_mode)
        try:
            tid1 = mosbase.get_track_id(1, MOSWireType.DS, 'sup', tile_idx=tile_idx)
            row1_sup.append(mosbase.connect_to_tracks(tap1, tid1))
        except:
            row1_sup.append(tap1)

    return row0_sup, row1_sup

