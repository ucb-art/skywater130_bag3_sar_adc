import copy
from logging import exception

from typing import Any, Dict, Type, Optional, List, Mapping, Union, Tuple
from xmlrpc.client import Boolean

from bag.design.database import ModuleDB, Module
from bag.env import get_tech_global_info
from bag.layout.routing.base import TrackManager, TrackID
from bag.layout.routing.base import WireArray
from bag.layout.template import TemplateDB, TemplateBase
from bag.util.immutable import Param, ImmutableSortedDict
from bag.util.math import HalfInt
from pybag.core import BBoxArray, Transform, BBox
from pybag.enum import Direction2D, Orient2D, RoundMode, Direction, PinMode, MinLenMode, Orientation
from xbase.layout.enum import MOSWireType
from xbase.layout.fill.base import DeviceFill
from xbase.layout.mos.base import MOSBasePlaceInfo, MOSBase, MOSArrayPlaceInfo
from xbase.layout.mos.placement.data import TilePatternElement, TilePattern
from xbase.layout.mos.top import GenericWrapper
from .util.util import get_available_tracks_reverse

from xbase.layout.data import LayoutInfoBuilder
from xbase.layout.cap.core import MOMCapCore
import math

class CapTap(MOSBase):

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg='segments dictionary.',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            seg=2
        )

    def draw_layout(self):
        pinfo = self.params['pinfo']
        seg = self.params['seg']
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, pinfo)
        self.draw_base(pinfo)

        tap = self.add_substrate_contact(0, 0, seg=seg, tile_idx=0)
        self.set_mos_size()
        self.add_pin('VSS', tap)


class CapUnitCore(TemplateBase):
    """MOMCap core
    Draw a layout has only metal and metal resistor in this shape:
    ----------------|
    --------------  |
    ----------------|
    Horizontal layer is "vertical_layer"
    Top and bottom is connected by "bot_layer"

    Parameters:
        top_w: width of middle horizontal layer
        bot_w: width of top/bot horizontal layer
        bot_y_w: width of vertical layer
        sp: space between top/bot and middle
        sp_le: line-end space between middle horizontal layer
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_unit')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            cap_config='MOM cap configuration.',
            width='MOM cap width, in resolution units.',
            tr_w='Track width',
            tr_sp='Track space',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DeviceFill.get_default_param_values()
        ans.update(
            cap_config={},
            width=0,
            tr_w={},
            tr_sp={},
        )
        return ans

    def draw_layout(self) -> None:
        cap_config: Dict[str, int] = self.params['cap_config']
        tr_w: Dict = self.params['tr_w']
        tr_sp: Dict = self.params['tr_sp']
        width: int = self.params['width']
        width = int(width / self.grid.resolution)

        tr_manager = TrackManager(self.grid, tr_w, tr_sp)

        grid = self.grid

        # Read cap_info
        top_layer = cap_config['top_layer']
        bot_layer = cap_config['bot_layer']
        top_w = cap_config['top_w']
        bot_w = cap_config['bot_w']
        bot_y_w = cap_config['bot_y_w']
        sp = cap_config['sp']
        sp_le = cap_config['sp_le']

        w_blk, h_blk = grid.get_block_size(max(top_layer, bot_layer), half_blk_x=True, half_blk_y=True)

        # draw cap
        if grid.get_direction(top_layer) == Orient2D.y:
            raise ValueError("Top layer need to be PGD")

        # Get tidx of top/mid/bot horizontal layer
        tidx_l = grid.find_next_track(top_layer, 0, tr_width=top_w, half_track=True)
        tidx_sp = grid.get_sep_tracks(top_layer, ntr1=top_w, ntr2=bot_w)
        tidx_sp = max(tidx_sp, HalfInt(sp))
        tidx_m = tidx_l + tidx_sp
        tidx_h = tidx_m + tidx_sp

        # Add wires
        top_l = self.add_wires(top_layer, tidx_l, 0, width, width=top_w)
        top_h = self.add_wires(top_layer, tidx_h, 0, width, width=top_w)

        height = grid.track_to_coord(top_layer, tidx_h) + grid.get_track_offset(top_layer)
        w_tot = -(-width // w_blk) * w_blk
        h_tot = -(-height // h_blk) * h_blk

        # Connect lower layer
        bot_layer_w = grid.get_track_info(bot_layer).width
        btidx = grid.coord_to_track(bot_layer, width - bot_layer_w, mode=RoundMode.NEAREST, even=True)
        bot = self.add_wires(bot_layer, btidx, 0, height, width=bot_y_w)
        self.add_via_on_grid(bot.track_id, top_l.track_id, extend=True)
        self.add_via_on_grid(bot.track_id, top_h.track_id, extend=True)

        bot_mid_coord = grid.track_to_coord(bot_layer, bot.track_id.base_index)

        top_min_l = grid.get_next_length(top_layer, bot_w, grid.get_wire_total_width(top_layer, bot_w), even=True)
        top_min_le_sp = grid.get_line_end_space(top_layer, bot_w, even=True)
        top_m_len = width - top_min_l - top_min_le_sp
        # top_m_len = grid.get_wire_bounds(bot_layer, btidx, bot_y_w)[0]
        top_m_len_unit = cap_config.get('unit', 1)
        top_m_len = int(top_m_len_unit * (top_m_len - sp_le))
        top_m = self.add_wires(top_layer, tidx_m, 0, top_m_len, width=bot_w)
        _top_m_dum = self.add_wires(top_layer, tidx_m, top_m_len + top_min_le_sp,
                                    grid.get_wire_bounds(bot_layer, btidx, bot_y_w)[1], width=bot_w)

        has_rmetal = cap_config.get('has_rmetal', True)
        if has_rmetal:
            pin_len = grid.get_next_length(top_layer, top_m.track_id.width,
                                           grid.get_wire_total_width(top_layer, top_m.track_id.width), even=True)
            res_top_box = top_m.bound_box
            res_top_box.set_interval(grid.get_direction(top_layer), top_m.bound_box.xh - pin_len,
                                     top_m.bound_box.xh - pin_len // 2)
            res_bot_box = top_l.bound_box
            res_bot_box.set_interval(grid.get_direction(top_layer), top_m.bound_box.xl + pin_len // 2,
                                     top_m.bound_box.xl + pin_len)
            
            self.add_res_metal(top_layer, res_bot_box)
            self.add_res_metal(top_layer, res_top_box)

        # set size
        bnd_box = BBox(0, 0, w_tot, h_tot)
        self.array_box = BBox(0, grid.get_track_offset(top_layer), bot_mid_coord,
                              h_tot - grid.get_track_offset(top_layer))
        self.set_size_from_bound_box(max(top_layer, bot_layer), bnd_box)

        # Fill metal dummy pattern
        for _layer in range(1, min(bot_layer, top_layer)):
            # -- Vertical layers --
            if _layer & 1:
                _tidx_l = self.grid.coord_to_track(_layer, self.array_box.xl, mode=RoundMode.GREATER_EQ)
                _tidx_h = self.grid.coord_to_track(_layer, self.array_box.xh, mode=RoundMode.LESS_EQ)
                _num_dum = tr_manager.get_num_wires_between(_layer, 'dum', _tidx_l, 'dum', _tidx_h, 'dum')
                _tr_w_dum = tr_manager.get_width(_layer, 'dum')
                _, _dum_locs = tr_manager.place_wires(_layer, ['dum'] * _num_dum,
                                                      center_coord=(self.array_box.xh + self.array_box.xl) // 2)
                [self.add_wires(_layer, tidx, self.array_box.yl, self.array_box.yh, width=_tr_w_dum) for tidx in
                 _dum_locs]
            # -- Horizontal layers --
            else:
                _tidx_l = self.grid.coord_to_track(_layer, self.array_box.yl, mode=RoundMode.GREATER_EQ)
                _tidx_h = self.grid.coord_to_track(_layer, self.array_box.yh, mode=RoundMode.LESS_EQ)
                _num_dum = tr_manager.get_num_wires_between(_layer, 'dum', _tidx_l, 'dum', _tidx_h, 'dum')
                _tr_w_dum = tr_manager.get_width(_layer, 'dum')
                _, _dum_locs = tr_manager.place_wires(_layer, ['dum'] * _num_dum,
                                                      center_coord=(self.array_box.yh + self.array_box.yl) // 2)
                [self.add_wires(_layer, tidx, self.array_box.xl, self.array_box.xh, width=_tr_w_dum) for tidx in
                 _dum_locs]

        self.add_pin('minus', bot)
        self.add_pin('plus', top_m, mode=PinMode.LOWER)

        if 'cap' in cap_config and has_rmetal:
            self.sch_params = dict(
                res_plus=dict(layer=top_layer, w=res_top_box.h, l=res_top_box.w),
                res_minus=dict(layer=top_layer, w=res_bot_box.h, l=res_bot_box.w),
                cap=top_m_len_unit * cap_config['cap']
            )
        elif 'cap' in cap_config:
            self.sch_params = dict(cap=top_m_len_unit * cap_config['cap'])
        elif has_rmetal:
            self.sch_params = dict(
                res_plus=dict(layer=top_layer, w=res_top_box.h, l=res_top_box.w),
                res_minus=dict(layer=top_layer, w=res_bot_box.h, l=res_bot_box.w),
            )
        else:
            self.sch_params = dict(
                res_plus=None,
                res_minus=None,
            )


class CapColCore(TemplateBase):
    """MOMCap core
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_unit')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            ny='number of unit cap in column',
            ratio='ratio of unit cell',
            cap_config='MOM cap configuration.',
            width='MOM cap width, in resolution units.',
            pin_tr_w='Width for top-plate pin',
            add_tap='Add tap to provides substrate',
            options='Other options, for use in ringamp'
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DeviceFill.get_default_param_values()
        ans.update(
            cap_config={},
            width=0,
            pin_tr_w=1,
            ratio=4,
            add_tap=False,
            options={},
        )
        return ans

    def draw_layout(self) -> None:
        cap_config: ImmutableSortedDict[str, Union[int, float]] = self.params['cap_config']
        options: ImmutableSortedDict[str, Any] = self.params['options']
        width: int = self.params['width']
        ratio: int = self.params['ratio']
        ny: int = self.params['ny']

        if ny & 1:
            raise ValueError("Number of cell must be even number")

        grid = self.grid
        unit_pin_layer = options.get('pin_layer', cap_config['top_layer'] - 1)
        add_tap = options.get('add_tap', False)
        unit_pin_tidx = grid.find_next_track(unit_pin_layer, 0, tr_width=cap_config['top_w'], half_track=True)
        pin_conn_sep = grid.get_sep_tracks(unit_pin_layer, ntr1=cap_config['top_w'], ntr2=1)

        
        #print(cap_config)
        if (cap_config['ismim'] == True):
            cap_config_copy = copy.deepcopy(cap_config.to_dict())
            cap_config_copy['unit'] = 1
            unit_master = self.new_template(CapMIMCore,
                            params=dict(cap_config=cap_config_copy, width=width))
            
            mimcap_master = self.new_template(CapMIMCore,
                            params=dict(cap_config=cap_config, width=width))
            lay_top_layer = max(unit_pin_layer, mimcap_master.top_layer)
            w_blk, h_blk = grid.get_block_size(lay_top_layer, half_blk_x=True, half_blk_y=True)
    
            unit_x = grid.track_to_coord(unit_pin_layer, unit_pin_tidx + pin_conn_sep)
            unit_x = -(-unit_x // w_blk) * w_blk

            mimcap = self.add_instance(mimcap_master, xform=Transform(unit_x, 0))
            bbox = mimcap.bound_box.extend(x=0, y=0)
            #print(bbox)
            cap_bot = mimcap.get_pin('minus') #just get the minus pin
            cap_top_list = mimcap.get_pin('plus')#just get plus pin
            #array_bbox = mimcap.array_box #should just have one box
            ideal_cap = unit_master.sch_params.get('cap', 0)
            self.top_pin_idx = mimcap_master.top_pin_idx
            m = 1 #TODO: the multiple in the schematic - have to edit in schematic

        else:
            cap_half_config = copy.deepcopy(cap_config.to_dict())
            cap_none_config = copy.deepcopy(cap_config.to_dict())
            cap_half_config['unit'] = 0.5
            cap_none_config['unit'] = 0
            unit_master: TemplateBase = self.new_template(CapUnitCore,
                                                          params=dict(cap_config=cap_config, width=width))
            unit_half_master: TemplateBase = self.new_template(CapUnitCore,
                                                               params=dict(cap_config=cap_half_config, width=width))
            unit_none_master: TemplateBase = self.new_template(CapUnitCore,
                                                               params=dict(cap_config=cap_none_config, width=width))

            lay_top_layer = max(unit_pin_layer, unit_master.top_layer)
            w_blk, h_blk = grid.get_block_size(lay_top_layer, half_blk_x=True, half_blk_y=True)

            unit_x = grid.track_to_coord(unit_pin_layer, unit_pin_tidx + pin_conn_sep)
            unit_x = -(-unit_x // w_blk) * w_blk

            if ratio & 8:
                cdac = [self.add_instance(unit_master, xform=Transform(unit_x, unit_master.array_box.h * idx))
                        for idx in range(ny)]
                bbox = cdac[-1].bound_box.extend(x=0, y=0)
                cap_bot = self.connect_wires([c.get_pin('minus') for c in cdac])
                cap_top_list = [c.get_pin('plus') for c in cdac]
                array_bbox = cdac[0].array_box.merge(cdac[-1].array_box)
                ideal_cap = unit_master.sch_params.get('cap', 0)
                m = 4
            elif ratio & 4:
                cdac = [self.add_instance(unit_half_master, xform=Transform(unit_x, unit_half_master.array_box.h * idx))
                        for idx in range(ny)]
                bbox = cdac[-1].bound_box.extend(x=0, y=0)
                cap_bot = self.connect_wires([c.get_pin('minus') for c in cdac])
                cap_top_list = [c.get_pin('plus') for c in cdac]
                array_bbox = cdac[0].array_box.merge(cdac[-1].array_box)
                ideal_cap = unit_half_master.sch_params.get('cap', 0)
                m = 4
            elif ratio & 2:
                cdac = [self.add_instance(unit_half_master, xform=Transform(unit_x, unit_half_master.array_box.h * idx))
                        for idx in range(2)] + \
                       [self.add_instance(unit_none_master, xform=Transform(unit_x, unit_none_master.array_box.h * idx))
                        for idx in range(2, 4)]
                bbox = cdac[-1].bound_box.extend(x=0, y=0)
                cap_bot = self.connect_wires([c.get_pin('minus') for c in cdac])
                cap_top_list = [c.get_pin('plus') for c in cdac]
                array_bbox = cdac[0].array_box.merge(cdac[-1].array_box)
                ideal_cap = unit_half_master.sch_params.get('cap', 0)
                m = 2
            elif ratio & 1:
                cdac = [self.add_instance(unit_half_master, xform=Transform(unit_x, 0))] + \
                       [self.add_instance(unit_none_master, xform=Transform(unit_x, unit_half_master.array_box.h * idx))
                        for idx in range(1, 4)]
                bbox = cdac[-1].bound_box.extend(x=0, y=0)
                cap_bot = self.connect_wires([c.get_pin('minus') for c in cdac])
                cap_top_list = [c.get_pin('plus') for c in cdac]
                array_bbox = cdac[0].array_box.merge(cdac[-1].array_box)
                ideal_cap = unit_half_master.sch_params.get('cap', 0)
                m = 1
            else:
                raise ValueError("Unit is wrong")

        if add_tap:
            tech_global = get_tech_global_info('bag3_digital')
            pinfo = dict(
                lch=tech_global['lch_min'],
                top_layer=MOSArrayPlaceInfo.get_conn_layer(self.grid.tech_info, tech_global['lch_min']) + 1,
                tr_widths={},
                tr_spaces={},
                row_specs=[dict(mos_type='ptap', width=tech_global['w_minn'], threshold='standard',
                                bot_wires=['sup'], top_wires=[])]
            )
            tap_master = self.new_template(CapTap, params=dict(pinfo=pinfo))
            tap = self.add_instance(tap_master, xform=Transform(-tap_master.bound_box.w, 0, Orientation.MY))
            self.reexport(tap.get_port('VSS'))

        self.set_size_from_bound_box(max(cap_config['top_layer'], cap_config['bot_layer']), bbox)
        self.array_box = bbox #array_bbox

        top_pin_list = []
        #mim modify
        if (cap_config['ismim'] == True):
            #if ((cap_config['top_layer'] - 1 ) == unit_pin_layer):
            #    _pin = self.connect_to_tracks(cap_top_list[0],
             #                                 TrackID(unit_pin_layer, unit_pin_tidx, cap_config['top_w']))
            #else:
            #    _pin = self.add_wires(unit_pin_layer, unit_pin_tidx, )
            for idx in range(0, ny, 4):
                top_pin_list.append(cap_top_list[0])
                self.add_pin(f'top_xm', cap_top_list[0], hide=True)

        else:
            for idx in range(0, ny, 4):
                _pin = self.connect_to_tracks(cap_top_list[idx: idx + 4],
                                              TrackID(unit_pin_layer, unit_pin_tidx, cap_config['top_w']))
                top_pin_list.append(_pin)
                self.add_pin(f'top_xm', cap_top_list[idx: idx + 4], hide=True)

        connect_top = options.get('connect_top', True)
        if connect_top:
            self.add_pin('top', self.connect_wires(top_pin_list))
        else:
            [self.add_pin(f'top', _pin) for _pin in top_pin_list]
        array_box_l = self.grid.track_to_coord(top_pin_list[0].layer_id, top_pin_list[0].track_id.base_index)
        self.array_box.extend(x=array_box_l)

        self.add_pin('bot', cap_bot)
        new_sch_params = dict(m=m, plus_term='top', minus_term='bot')
        if ideal_cap:
            new_sch_params['cap'] = ideal_cap
        self.sch_params = \
            unit_master.sch_params.copy(append=new_sch_params)


class CapDrvCore(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_drv')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            min_height='Height to match capdac',
            pinfo='placement information object.',
            seg='segments dictionary.',
            sp='dummy seperation',
            w='widths.',
            ny='number of rows',
            dum_row_idx='Index of dummy rows',
            sw_type='Type of switch',
            nx='number of columns',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w=4,
            sp=2,
            ny=5,
            min_height=0,
            dum_row_idx=[],
            nx=3,
            sw_type='nch',
        )

    def draw_layout(self):
        min_height: int = self.params['min_height']
        sw_type: str = self.params['sw_type']
        ny: int = self.params['ny']
        nx: int = self.params['nx']
        w: int = self.params['w']
        pinfo_dict = self.params['pinfo'].to_yaml()

        if min_height > 0:
            pinfo_dict['tile_specs']['place_info']['drv_tile']['min_height'] = min_height
        pinfo_dict['tile_specs']['place_info']['drv_tile']['row_specs'][0]['mos_type'] = sw_type
        pinfo_dict['tile_specs']['place_info']['drv_tile']['row_specs'][0]['width'] = w
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, pinfo_dict)
        pinfo0 = [TilePatternElement(pinfo[1]['drv_tile'])] * ny
        self.draw_base((TilePattern(pinfo0), pinfo[1]))

        dum_row_idx: List[int] = self.params['dum_row_idx']
        seg: int = self.params['seg']
        sp: int = self.params['sp']
        w: int = self.params['w']

        tr_manager = self.tr_manager
        conn_layer = self.conn_layer
        hm_layer = conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        ym_layer = xm_layer + 1
        tr_sup_vm_w = tr_manager.get_width(vm_layer, 'sup')
        tr_sup_xm_w = tr_manager.get_width(xm_layer, 'sup')
        tr_sup_ym_w = tr_manager.get_width(ym_layer, 'sup')

        sw_list_list, ctrl_list_list, vref_list_list = [], [], []
        cap_bot_list = []

        pin_lower = self.arr_info.col_to_coord(0)
        vdd_list, vss_list = [], []
        sup_bot_tid_list = []
        xm_tid_list = []
        tap_ncol = self.get_tap_ncol(tile_idx=0)
        tap_sep_col = self.sub_sep_col
        tap_ncol += tap_sep_col
        tile_height = self.get_tile_info(0)[0].height
        num_xm_per_tile = tr_manager.get_num_wires_between(xm_layer, 'sup',
                                                           self.grid.coord_to_track(xm_layer, 0, RoundMode.NEAREST),
                                                           'sup',
                                                           self.grid.coord_to_track(xm_layer, tile_height,
                                                                                    RoundMode.NEAREST),
                                                           'sup')
        if not num_xm_per_tile & 1:
            num_xm_per_tile += 1
        for idx in range(ny):
            if dum_row_idx and idx in dum_row_idx:
                continue
            self.add_tap(0, vdd_list, vss_list, tile_idx=idx)
            sw_list, ctrl_list, vref_list = [], [], []
            tid_bot = self.get_track_id(0, MOSWireType.DS, wire_name='sig', wire_idx=1, tile_idx=idx)
            tid_ref = self.get_track_id(0, MOSWireType.DS, wire_name='sig', wire_idx=0, tile_idx=idx)
            sw_col = tap_ncol

            # if nx != 2:
            tid_list = []
            for jdx in range(nx):
                sw_list.append(self.add_mos(0, sw_col, seg, w=w, tile_idx=idx))
                sw_col += seg + sp
                tid_list.append(self.get_track_index(0, MOSWireType.G, wire_name='sig',
                                                     wire_idx=-jdx - 1 if nx != 2 else jdx, tile_idx=idx))
                vref_list.append(self.connect_to_tracks(sw_list[-1].d, tid_ref, min_len_mode=MinLenMode.MIDDLE))

            ctrl_list.extend(self.connect_matching_tracks([sw.g for sw in sw_list], hm_layer,
                                                          tid_list, track_lower=pin_lower,
                                                          min_len_mode=MinLenMode.MIDDLE))
            cap_bot_list.append(self.connect_to_tracks([sw.s for sw in sw_list], tid_bot))

            self.add_tap(sw_col - sp + tap_ncol, vdd_list, vss_list, tile_idx=idx, flip_lr=True)

            # supply_hm
            sup_bot_tid_list.append(self.get_track_id(0, MOSWireType.G, wire_name='sup', tile_idx=idx))
            sup_bot_tid_list.append(self.get_track_id(0, MOSWireType.DS, wire_name='sup', tile_idx=idx))
            sup_bot_tid_list.append(self.get_track_id(0, MOSWireType.DS, wire_name='sup', wire_idx=-1, tile_idx=idx))
            sw_list_list.append(sw_list)
            ctrl_list_list.append(ctrl_list)
            vref_list_list.append(vref_list)

        self.set_mos_size()
        for idx in range(ny):
            tile_info, yb, _ = self.get_tile_info(idx)
            xm_locs = self.get_available_tracks(xm_layer, self.grid.coord_to_track(xm_layer, yb, RoundMode.NEAREST),
                                                self.grid.coord_to_track(xm_layer, yb + tile_height, RoundMode.NEAREST),
                                                self.bound_box.xl, self.bound_box.xh, tr_sup_xm_w,
                                                tr_manager.get_sep(xm_layer, ('sup', 'sup')), False)
            if not len(xm_locs) & 1:
                xm_locs.pop(-1)
            xm_tid_list.append(xm_locs)
        sup_hm_list = []
        for tid in sup_bot_tid_list:
            sup_conn_list = vdd_list if sw_type == 'pch' else vss_list
            sup_hm_list.append(self.connect_to_tracks(sup_conn_list, tid))

        vref_vm_list = []
        for idx in range(nx):
            vref_vm_tidx = self.grid.coord_to_track(vm_layer, vref_list_list[0][idx].middle,
                                                    mode=RoundMode.LESS if seg & 1 else RoundMode.NEAREST)
            vref_vm_list.append(self.connect_to_tracks([vref_list[idx] for vref_list in vref_list_list],
                                                       TrackID(vm_layer, vref_vm_tidx, tr_sup_vm_w),
                                                       track_upper=self.bound_box.yh, track_lower=self.bound_box.yl))

        sup_vm_locs = self.get_available_tracks(vm_layer,
                                                self.arr_info.col_to_track(vm_layer, 0),
                                                self.arr_info.col_to_track(vm_layer, tap_ncol),
                                                self.bound_box.yl, self.bound_box.yh,
                                                tr_manager.get_width(vm_layer, 'sup'),
                                                tr_manager.get_sep(vm_layer, ('sup', 'sup')),
                                                include_last=True)[::2]
        sup_vm_locs += get_available_tracks_reverse(self, vm_layer,
                                                    self.arr_info.col_to_track(vm_layer, self.num_cols - tap_ncol,
                                                                               RoundMode.NEAREST),
                                                    self.arr_info.col_to_track(vm_layer, self.num_cols,
                                                                               RoundMode.NEAREST),
                                                    self.bound_box.yl, self.bound_box.yh,
                                                    tr_manager.get_width(vm_layer, 'sup'),
                                                    tr_manager.get_sep(vm_layer, ('sup', 'sup')),
                                                    include_last=True)[::2]

        sup_vm_list = []
        for tid in sup_vm_locs:
            sup_vm_list.append(self.connect_to_tracks(sup_hm_list, TrackID(vm_layer, tid, tr_sup_vm_w)))
        
        sup_xm_list = []
        for tid_list in xm_tid_list:
            mid_tid = tid_list[num_xm_per_tile // 2]
            for idx, vref in enumerate(vref_vm_list):
                #self.connect_to_tracks(vref, TrackID(xm_layer, mid_tid, tr_sup_xm_w))
                self.add_pin(f'vref{idx}_xm', vref_vm_list[idx]) #self.connect_to_tracks(vref, TrackID(xm_layer, mid_tid, tr_sup_xm_w)))
            tid_list.pop(num_xm_per_tile // 2)

        if sw_type == 'nch':
            for tid_list in xm_tid_list:
                for tid in tid_list[::2]:
                    sup_xm_list.append(self.connect_to_tracks(sup_vm_list, TrackID(xm_layer, tid, tr_sup_xm_w)))
            self.add_pin('VSS_xm', sup_xm_list)
        else:
            for tid_list in xm_tid_list:
                for tid in tid_list[1::2]:
                    sup_xm_list.append(self.connect_to_tracks(sup_vm_list, TrackID(xm_layer, tid, tr_sup_xm_w)))
            self.add_pin('VDD_xm', sup_xm_list)

        for idx in range(nx):
            self.add_pin(f'vref{idx}', vref_vm_list[idx])
            self.add_pin(f'ctrl{idx}', [ctrl_list[idx] for ctrl_list in ctrl_list_list])

        if vdd_list:
            self.add_pin('VDD', sup_vm_list)
        if vss_list:
            self.add_pin('VSS', sup_vm_list)
        self.add_pin(f'bot', cap_bot_list, mode=PinMode.UPPER)
        self.sch_params = dict(
            lch=self.arr_info.lch,
            w=w,
            seg=seg,
            intent=self.get_row_info(0, 0).threshold
        )


class CMSwitch(MOSBase):
    """A inverter with only transistors drawn, no metal connections
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        MOSBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            pinfo='placement information object.',
            seg='segments dictionary.',
            w='widths.',
            ncols_tot='Total number of fingersa',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        return dict(
            w=4,
            ncols_tot=0,
        )

    def draw_layout(self):
        pinfo = MOSBasePlaceInfo.make_place_info(self.grid, self.params['pinfo'])
        self.draw_base(pinfo)
        tr_manager = self.tr_manager

        hm_layer = self.conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1

        seg: int = self.params['seg']
        w: int = self.params['w']
        tap_ncol = self.get_tap_ncol(tile_idx=0)
        tap_sep_col = self.sub_sep_col
        tap_ncol += tap_sep_col

        vdd_list, vss_list = [], []
        tot_cols = max(self.params['ncols_tot'], seg + 2 * tap_ncol)
        self.add_tap(0, vdd_list, vss_list, tile_idx=0)
        sw = self.add_mos(0, (tot_cols - seg) // 2, seg, w=w)
        self.add_tap(tot_cols, vdd_list, vss_list, tile_idx=0, flip_lr=True)
        self.set_mos_size()

        tid_g = self.get_track_id(0, MOSWireType.G, wire_name='sig', wire_idx=0)
        tid_sig = self.get_track_id(0, MOSWireType.DS, wire_name='sig', wire_idx=1)
        tid_ref = self.get_track_id(0, MOSWireType.DS, wire_name='sig', wire_idx=0)

        sam_hm = self.connect_to_tracks(sw.g, tid_g)
        ref_hm = self.connect_to_tracks(sw.d, tid_ref)
        sig_hm = self.connect_to_tracks(sw.s, tid_sig)

        # get middle track for sample signal
        mid_vm_tidx = self.arr_info.col_to_track(vm_layer, tot_cols // 2, RoundMode.NEAREST)
        sam_vm = self.connect_to_tracks(sam_hm, TrackID(vm_layer, mid_vm_tidx, tr_manager.get_width(vm_layer, 'ctrl')))
        tid_l = self.arr_info.col_to_track(vm_layer, tap_ncol, mode=RoundMode.NEAREST)
        tid_r = self.arr_info.col_to_track(vm_layer, self.num_cols - tap_ncol, mode=RoundMode.NEAREST)

        tr_w_sup_vm = tr_manager.get_width(vm_layer, 'sup')
        tr_w_sig_vm = tr_manager.get_width(vm_layer, 'sig')
        vref_vm_locs = self.get_available_tracks(vm_layer, tid_l, mid_vm_tidx, self.bound_box.yl, self.bound_box.yh,
                                                 tr_manager.get_width(vm_layer, 'sup'),
                                                 tr_manager.get_sep(vm_layer, ('sup', 'sup')))
        sig_vm_locs = get_available_tracks_reverse(self, vm_layer, mid_vm_tidx, tid_r, self.bound_box.yl,
                                                   self.bound_box.yh, tr_manager.get_width(vm_layer, 'sig'),
                                                   tr_manager.get_sep(vm_layer, ('sig', 'sig')))
        vref_vm = [self.connect_to_tracks(ref_hm, TrackID(vm_layer, _tid, tr_w_sup_vm)) for _tid in vref_vm_locs]
        sig_vm = [self.connect_to_tracks(sig_hm, TrackID(vm_layer, _tid, tr_w_sig_vm)) for _tid in sig_vm_locs]
        vm_warrs = vref_vm + sig_vm
        vm_warrs_max_coord, vm_warrs_min_coord = max([v.upper for v in vm_warrs]), min([v.lower for v in vm_warrs])
        vref_vm = self.extend_wires(vref_vm, upper=vm_warrs_max_coord, lower=vm_warrs_min_coord)
        sig_vm = self.extend_wires(sig_vm, upper=vm_warrs_max_coord, lower=vm_warrs_min_coord)

        tr_w_sup_xm = tr_manager.get_width(xm_layer, 'sup')
        tr_w_sig_xm = tr_manager.get_width(xm_layer, 'sig')

        # Connect supplies
        tr_sup_hm_w = tr_manager.get_width(hm_layer, 'sup')
        tr_sup_vm_w = tr_manager.get_width(vm_layer, 'sup')
        tr_sup_xm_w = tr_manager.get_width(xm_layer, 'sup')
        sup_hm_tids = [self.get_track_id(0, MOSWireType.G, wire_name='sup'),
                       self.get_track_id(0, MOSWireType.DS, wire_name='sup')]

        sup_hm_list = []
        for tid in sup_hm_tids:
            sup_hm_list.append(self.connect_to_tracks(vss_list, tid))

        sup_vm_locs = self.get_available_tracks(vm_layer,
                                                self.arr_info.col_to_track(vm_layer, 0),
                                                self.arr_info.col_to_track(vm_layer, tap_ncol),
                                                self.bound_box.yl, self.bound_box.yh,
                                                tr_manager.get_width(vm_layer, 'sup'),
                                                tr_manager.get_sep(vm_layer, ('sup', 'sup')),
                                                include_last=True)[::2]
        sup_vm_locs += get_available_tracks_reverse(self, vm_layer,
                                                    self.arr_info.col_to_track(vm_layer, self.num_cols - tap_ncol,
                                                                               RoundMode.NEAREST),
                                                    self.arr_info.col_to_track(vm_layer, self.num_cols,
                                                                               RoundMode.NEAREST),
                                                    self.bound_box.yl, self.bound_box.yh,
                                                    tr_manager.get_width(vm_layer, 'sup'),
                                                    tr_manager.get_sep(vm_layer, ('sup', 'sup')),
                                                    include_last=True)[::2]

        sup_vm_list = []
        for tid in sup_vm_locs:
            sup_vm_list.append(self.connect_to_tracks(sup_hm_list, TrackID(vm_layer, tid, tr_sup_vm_w)))

        tile_info, yb, _ = self.get_tile_info(0)
        tile_height = tile_info.height
        xm_locs = self.get_available_tracks(xm_layer, self.grid.coord_to_track(xm_layer, yb, RoundMode.NEAREST),
                                            self.grid.coord_to_track(xm_layer, yb + tile_height, RoundMode.NEAREST),
                                            self.bound_box.xl, self.bound_box.xh, tr_sup_xm_w,
                                            tr_manager.get_sep(xm_layer, ('sup', 'sup')), False)
        if not len(xm_locs):
            xm_locs = xm_locs[:-1]
        # y_mid_coord = (self.bound_box.yl + self.bound_box.yh) // 2
        # xm_mid_tidx = self.grid.coord_to_track(xm_layer, y_mid_coord, mode=RoundMode.NEAREST)
        vref_xm = self.connect_to_tracks(vref_vm, TrackID(xm_layer, xm_locs[len(xm_locs)//2], tr_w_sup_xm))
        sig_xm = self.connect_to_tracks(sig_vm, TrackID(xm_layer, xm_locs[len(xm_locs)//2], tr_w_sup_xm))
        xm_locs.pop(len(xm_locs)//2)
        sup_xm_list = []
        for tid in xm_locs[::2]:
            sup_xm_list.append(self.connect_to_tracks(sup_vm_list, TrackID(xm_layer, tid, tr_sup_xm_w)))
        self.add_pin('sam', sam_vm)
        self.add_pin('ref', vref_xm)
        self.add_pin('sig', sig_xm)
        self.add_pin('VSS', sup_xm_list)

        self.sch_params = dict(
            l=self.arr_info.lch,
            nf=seg,
            w=w,
            intent=self.place_info.get_row_place_info(0).row_info.threshold,
        )


class CapDacColCore(TemplateBase):
    """MOMCap core
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)
        self._actual_width = 0

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cdac_array_bot')

    @property
    def actual_width(self) -> int:
        return self._actual_width

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            nbits='Number of bits',
            ny_list='list of ny',
            ratio_list='list of ratio',
            sw_type='switch type list',
            diff_idx='differential cap index',
            seg='segments dictionary.',
            seg_cm='segments dictionary.',
            sp='segments dictionary.',
            w_n='widths dictionary.',
            w_p='widths dictionary.',
            w_cm='widths dictionary.',
            cap_config='MOM cap configuration.',
            width='MOM cap width, in resolution units.',
            pinfo='placement information object.',
            pinfo_cm='placement information object.',
            remove_cap='True to remove capacitor, use it when doesnt have rmetal',
            lower_layer_routing='only use up to m4',
            tr_widths='Track width dictionary',
            tr_spaces='Track space dictionary',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DeviceFill.get_default_param_values()
        ans.update(
            cap_config={},
            width=0,
            w_n=4,
            w_p=4,
            w=4,
            remove_cap=False,
        )
        return ans

    def draw_layout(self) -> None:
        cap_config: ImmutableSortedDict[str, int] = self.params['cap_config']
        width: int = self.params['width']
        nbits: int = self.params['nbits']
        seg: int = self.params['seg']
        sp: int = self.params['sp']
        w_p: int = self.params['w_p']
        w_n: int = self.params['w_p']
        seg_cm: int = self.params['seg_cm']
        w_cm: int = self.params['w_cm']
        diff_idx: int = self.params['diff_idx']
        ny_list: List[int] = self.params['ny_list'].to_list()
        ratio_list: List[int] = self.params['ratio_list'].to_list()
        sw_type: List[str] = self.params['sw_type'].to_list()
        tr_widths: Dict[str, Any] = self.params['tr_widths']
        tr_spaces: Mapping[Tuple[str, str], Mapping[int, Union[float, HalfInt]]] = self.params['tr_spaces']
        grid = self.grid
        tr_manager = TrackManager(self.grid, tr_widths, tr_spaces)
        has_cm_sw = True

        if nbits < 3:
            raise ValueError("[CDAC layout]: Less than 3-bit is not supported")

        # organize the cap ratios and placement
        # diff_idx: index from which need 2 of the cap (differential on top and bot)
        # ny: number of unit components in each cap/4
        # ratio: units come in full, half, none flavors
        
        # complete full ny list with differential caps (ny[5:end] flipped + ny)
        ny_list = ny_list[diff_idx:][::-1] + ny_list
        #do same to ratio list
        ratio_list = ratio_list[diff_idx:][::-1] + ratio_list
        
        #bit list lists out which cap belongs to which total cap ratio (ex from 0 to 8)
        bit_list = [1, 0, 2, 3] + list(range(diff_idx - 1, nbits + 1))
        bit_list = bit_list[diff_idx:][::-1] + bit_list
        
        #compute the units
        if (cap_config['ismim']==True):
            h_list = []
            w_list = []
            h_idx = 0
            for idx in range(0, max(bit_list)+1):
                if (idx==0):
                    h_list.append(cap_config['height'])
                    w_list.append(cap_config['unit_width'])
                else: 
                    if (width/(2**(idx-1)) >= cap_config['unit_width']):
                        if ((idx-1)>=h_idx):
                            h_idx = idx-1
                        w_list.append(cap_config['unit_width']*(2**(idx-1)))
                        h_list.append(cap_config['height'])
                    else:
                        w_list.append(cap_config['unit_width']*(2**h_idx))
                        h_list.append(cap_config['height']*(2**(idx-h_idx-1)))
                if (idx >= diff_idx):
                    h_list[-1] = h_list[-1]/2
        
            height_list = h_list[diff_idx:][::-1] + \
                            [h_list[1], h_list[0]] + h_list[2:diff_idx] + h_list[diff_idx:]
            width_list = w_list[diff_idx:][::-1] + \
                            [w_list[1], w_list[0]]+ w_list[2:diff_idx] + w_list[diff_idx:]

        # Place control signals
        conn_layer = MOSArrayPlaceInfo.get_conn_layer(self.grid.tech_info,
                                                      self.params['pinfo']['tile_specs']['arr_info']['lch'])
        hm_layer = conn_layer + 1
        vm_layer = hm_layer + 1
        xm_layer = vm_layer + 1
        ym_layer = xm_layer + 1

        tr_w_sup_ym = tr_manager.get_width(ym_layer, 'sup')

        # -- first track --
        tr_w_ctrl_vm = tr_manager.get_width(vm_layer, 'ctrl')

        ctrl_tidx_start = grid.find_next_track(vm_layer, 0, tr_width=tr_w_ctrl_vm)
        ctrl_tidx_used, ctrl_tidx_locs = \
            tr_manager.place_wires(vm_layer, ['ctrl'] * (3 * nbits + 1), align_idx=0, align_track=ctrl_tidx_start)
        sw_x = self.grid.track_to_coord(vm_layer, ctrl_tidx_used)
        routing_bnd = sw_x

        # Setup templates for size calculation
        height_orig = cap_config['height']
        if (cap_config['ismim'] == True):
            cap_config_mim = copy.deepcopy(cap_config.to_dict())
            cap_config_mim['total_width'] = self.params['width']
            cap_config_mim['height'] = sum(height_list) #+sum(bit_list)*cap_config['cap_sp']
            cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config_mim, width=width_list[-1], ny=4 * sum(ny_list)))
            cap_config_mim['height'] = height_orig + cap_config_mim['cap_sp']
            unit_cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config_mim, width=width_list[-1], ny=4))
        else:
            cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config, width=width, ny=4 * sum(ny_list)))
            unit_cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config, width=width, ny=4))
        
        unit_cap_height = unit_cap_master.array_box.h
        w_cap, h_cap = cap_master.bound_box.w, cap_master.bound_box.h

        sw_params = dict(
            cls_name=CapDrvCore.get_qualified_name(),
            params=dict(pinfo=self.params['pinfo'], seg=seg, ny=sum(ny_list), w=w_n, sp=sp,
                        dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
        )
        sw_master = self.new_template(GenericWrapper, params=sw_params)
        top_layer = max(cap_master.top_layer, sw_master.top_layer)
        w_blk, h_blk = self.grid.get_block_size(top_layer)

        cm_sw_params = dict(pinfo=self.params['pinfo_cm'], seg=seg_cm, w=w_cm)
        cm_sw_dum_master = self.new_template(CMSwitch, params=cm_sw_params)
        w_master = cm_sw_dum_master.bound_box.w
        w_edge = cm_sw_dum_master.tech_cls.get_edge_width(w_master, w_blk)
        ncols_tot = (cap_master.bound_box.w - 2 * w_edge) // cm_sw_dum_master.sd_pitch
        cm_sw_gen_params = dict(
            cls_name=CMSwitch.get_qualified_name(),
            params=dict(pinfo=self.params['pinfo_cm'], seg=seg_cm, w=w_cm,
                        ncols_tot=ncols_tot - (ncols_tot & 1))
        )
        cm_sw_master = self.new_template(GenericWrapper, params=cm_sw_gen_params)
        y_cm_sw_top = -(-cm_sw_master.bound_box.h // h_blk) * h_blk

        capmim_y = []
        if (cap_config['ismim']):
            if sw_type.count('n') == 3:
                w_sw, h_sw = sw_master.bound_box.w, sw_master.bound_box.h
                sw_y = y_cm_sw_top if has_cm_sw else 0
                cap_y = sw_y + (h_sw - h_cap) // 2
                sw_x = -(-sw_x // w_blk) * w_blk
                sw = self.add_instance(sw_master, inst_name='XSW', xform=Transform(sw_x, sw_y))
                # Get sorted ctrl pins
                sw_ctrl_n: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl0')
                sw_ctrl_m: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl1')
                sw_ctrl_p: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl2')
                sw_bot: List[Union[WireArray, None]] = sw.get_all_port_pins('bot')
                self.reexport(sw.get_port('vref0'), net_name='vref<2>')
                self.reexport(sw.get_port('vref1'), net_name='vref<1>')
                self.reexport(sw.get_port('vref2'), net_name='vref<1>')
                vrefm, vrefm_pin = sw.get_port('vref1'), sw.get_pin('vref1')
                sw_right_coord = sw.bound_box.xh
                sw_params_list = [sw_master.sch_params for _ in range(nbits)]
                sw_vss_bbox: List[BBox] = sw.get_all_port_pins('VSS')
            elif sw_type.count('n') == 2:
                sw_n_params = dict(
                    cls_name=CapDrvCore.get_qualified_name(),
                    draw_taps=True,
                    params=dict(pinfo=self.params['pinfo'], seg=seg, ny=sum(ny_list), w=w_n, sp=sp, nx=2, sw_type='nch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                )
                sw_p_params = dict(
                    cls_name=CapDrvCore.get_qualified_name(),
                    draw_taps=True,
                    params=dict(pinfo=self.params['pinfo'], seg=seg, ny=sum(ny_list), w=w_p, sp=sp, nx=1, sw_type='pch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                )
                sw_n_master = self.new_template(GenericWrapper, params=sw_n_params)
                sw_p_master = self.new_template(GenericWrapper, params=sw_p_params)
                top_layer = max(cap_master.top_layer, sw_n_master.top_layer, sw_p_master.top_layer)
                w_blk, h_blk = self.grid.get_block_size(top_layer)
                w_sw_p, h_sw = sw_p_master.bound_box.w, sw_p_master.bound_box.h
                w_sw_n, h_sw = sw_n_master.bound_box.w, sw_n_master.bound_box.h 
                #I don't think h_sw is actually used anywhere else?
                sw_y = (y_cm_sw_top + h_blk) if has_cm_sw else 0
                cap_y = sw_y #+ (h_sw - h_cap) // 2
                capmim_y.append(cap_y)
                sw_x = -(-sw_x // w_blk) * w_blk

                sw_type_dict = dict(
                    XN=sw_type[0],
                    XM=sw_type[1],
                    XP=sw_type[2],
                )
                sw_params_list = [sw_n_master.sch_params.copy(append=dict(sw_type_dict=sw_type_dict)) for _ in range(nbits)]
                
                #modify these lines
                #sw_p = self.add_instance(sw_p_master, inst_name='XSWP', xform=Transform(sw_x, sw_y))
                swn_x = -(-(sw_x + w_sw_p) // w_blk) * w_blk
                #sw_n = self.add_instance(sw_n_master, inst_name='XSWN', xform=Transform(swn_x, sw_y))


                # Get sorted ctrl pins
                sw_ctrl_m: List[Union[WireArray, None]] = [] #sw_n.get_all_port_pins('ctrl0')
                sw_ctrl_n: List[Union[WireArray, None]] = [] #sw_n.get_all_port_pins('ctrl1')
                sw_ctrl_p: List[Union[WireArray, None]] = [] #sw_p.get_all_port_pins('ctrl0')
                sw_bot = [] # List[Union[WireArray, None]] = []
                vref0_xm = []
                vref1_xm = []
                vref2_xm = []
                vrefm_single, vrefm_pin_single = [], []
                vdd_xm, vss_xm = [], []
                vdd_vm, vss_vm = [], []

                cap_config_dum = copy.deepcopy(cap_config.to_dict()) 
                for idx, (ny, h, bit) in enumerate(zip(ny_list, height_list, bit_list)):
                    cap_config_dum['height'] = height_list[idx]
                    cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config_dum, width=width_list[idx], ny=4,
                                                                       ratio=1))
                    unit_cap_height = cap_master.array_box.yh // ny #int(h/self.grid.resolution) // ny
                    sw_n_params = dict(
                    cls_name=CapDrvCore.get_qualified_name(),
                    draw_taps=True,
                    params=dict(pinfo=self.params['pinfo'], seg=seg, ny=ny, w=w_n, sp=sp, nx=2, sw_type='nch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                    )
                    sw_p_params = dict(
                        cls_name=CapDrvCore.get_qualified_name(),
                        draw_taps=True,
                        params=dict(pinfo=self.params['pinfo'], seg=seg, ny=ny, w=w_p, sp=sp, nx=1, sw_type='pch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                    )
                    sw_n_master = self.new_template(GenericWrapper, params=sw_n_params)
                    sw_p_master = self.new_template(GenericWrapper, params=sw_p_params)

                    unit_drv = 0
                    if(bit>0):
                        sw_p = self.add_instance(sw_p_master, inst_name='XSWP', xform=Transform(sw_x, sw_y))
                        sw_n = self.add_instance(sw_n_master, inst_name='XSWN', xform=Transform(swn_x, sw_y))

                        sw_ctrl_m = sw_ctrl_m + sw_n.get_all_port_pins('ctrl0')
                        sw_ctrl_n = sw_ctrl_n + sw_n.get_all_port_pins('ctrl1')
                        sw_ctrl_p = sw_ctrl_p + sw_p.get_all_port_pins('ctrl0')

                        self.reexport(sw_n.get_port('vref0'), net_name='vref<1>')
                        self.reexport(sw_n.get_port('vref1'), net_name='vref<0>')
                        self.reexport(sw_p.get_port('vref0'), net_name='vref<2>')

                        vref0_xm = vref0_xm + sw_n.get_all_port_pins('vref0_xm')
                        vref1_xm = vref1_xm + sw_n.get_all_port_pins('vref1_xm')
                        vref2_xm = vref2_xm + sw_p.get_all_port_pins('vref0_xm')

                        sw_right_coord = sw_n.bound_box.xh
                    
                        for botn, botp in zip(sw_n.get_all_port_pins('bot'), sw_p.get_all_port_pins('bot')):
                            sw_bot.append(self.connect_wires([botn, botp])[0])

                        vrefm_single.append(sw_n.get_port('vref0'))
                        vrefm_pin_single.append(sw_n.get_pin('vref0'))
                        #vrefm_single.append(sw_n.get_pin('vref0'))

                        self.reexport(sw_p.get_port('VDD'), connect=True)
                        self.reexport(sw_n.get_port('VSS'), connect=True)
                        vdd_vm = vdd_vm + sw_p.get_all_port_pins('VDD')
                        vss_vm = vss_vm + sw_n.get_all_port_pins('VSS')
                        vdd_xm_ = sw_p.get_all_port_pins('VDD_xm')
                        vss_xm_ = sw_n.get_all_port_pins('VSS_xm')
                        vdd_xm = vdd_xm + vdd_xm_#self.extend_wires(vdd_xm_, upper=vss_xm_[0].upper)
                        #vss_xm = vss_xm + self.extend_wires(vss_xm_, lower=vdd_xm_[0].lower)
                        if (bit==1):
                            unit_drv = sw_n.bound_box.yh-sw_n.bound_box.yl

                    sw_y = int(sw_y + max( (sw_n.bound_box.yh-sw_n.bound_box.yl), unit_drv,
                                    int(cap_master.array_box.yh) + cap_config['cap_sp']/self.grid.resolution))
                    sw_y = -(-sw_y//h_blk)*h_blk
                    capmim_y.append(sw_y)
                
                #might be a bit hacky, have to connect with boxes because of the ports returned
                self.add_rect_array((f'met{vm_layer}', 'drawing'), BBox(vref0_xm[0].xl, vref0_xm[0].yl, vref0_xm[-1].xh, vref0_xm[-1].yh))
                self.add_rect_array((f'met{vm_layer}', 'drawing'), BBox(vref1_xm[0].xl, vref1_xm[0].yl, vref1_xm[-1].xh, vref1_xm[-1].yh))
                self.add_rect_array((f'met{vm_layer}', 'drawing'), BBox(vref2_xm[0].xl, vref2_xm[0].yl, vref2_xm[-1].xh, vref2_xm[-1].yh))

                for n in range(4):  #always have 4 columns of VSS and 4 columns of VDD
                    self.add_rect_array((f'met{vm_layer}', 'drawing'), BBox(vss_vm[n].xl, vss_vm[n].yl, 
                                                            vss_vm[len(vss_vm)-4+n].xh, vss_vm[len(vss_vm)-4+n].yh))
                    self.add_rect_array((f'met{vm_layer}', 'drawing'), BBox(vdd_vm[n].xl, vdd_vm[n].yl, 
                                                            vdd_vm[len(vdd_vm)-4+n].xh, vdd_vm[len(vdd_vm)-4+n].yh))
                

                if not self.params['lower_layer_routing']:
                    vref_ym_list = []
                    for vref in [vref0_xm, vref1_xm, vref2_xm]:
                        mid_coord = vref[0].middle
                        tid = self.grid.coord_to_track(ym_layer, mid_coord, RoundMode.NEAREST)
                        vref_ym_list.append(self.connect_to_tracks(vref, TrackID(ym_layer, tid, tr_w_sup_ym)))
                    ym_sup_locs = self.get_available_tracks(ym_layer, self.grid.coord_to_track(ym_layer, sw_p.bound_box.xl,
                                                                                               RoundMode.NEAREST),
                                                            self.grid.coord_to_track(ym_layer, sw_n.bound_box.xh,
                                                                                     RoundMode.LESS_EQ),
                                                            upper=sw_n.bound_box.yh, lower=sw_n.bound_box.yl,
                                                            width=tr_w_sup_ym,
                                                            sep=tr_manager.get_sep(ym_layer, ('sup', 'sup')))
                    vdd_ym_list, vss_ym_list = [], []
                    xm_vdd_ret_list, xm_vss_ret_list = [], []
                    for tid in ym_sup_locs[::2]:
                        vdd_ym_list.append(
                            self.connect_to_tracks(vdd_xm, TrackID(ym_layer, tid, tr_w_sup_ym), ret_wire_list=xm_vdd_ret_list))
                    for tid in ym_sup_locs[1::2]:
                        vss_ym_list.append(
                            self.connect_to_tracks(vss_xm, TrackID(ym_layer, tid, tr_w_sup_ym), ret_wire_list=xm_vss_ret_list))

                    xm_sup_list = xm_vdd_ret_list + xm_vss_ret_list
                    xm_sup_max_coord, xm_sup_min_coord = max([x.upper for x in xm_sup_list]), \
                                                         min([x.lower for x in xm_sup_list])
                    self.extend_wires(xm_sup_list, upper=xm_sup_max_coord, lower=xm_sup_min_coord)
                    ym_sup_list = vdd_ym_list + vss_ym_list
                    ym_sup_max_coord, ym_sup_min_coord = max([y.upper for y in ym_sup_list]), 0

                    vdd_ym_list = self.extend_wires(vdd_ym_list, upper=ym_sup_max_coord, lower=ym_sup_min_coord)
                    vss_ym_list = self.extend_wires(vss_ym_list, upper=ym_sup_max_coord, lower=ym_sup_min_coord)
            else:
                sw_n, sw_p = None, None
                raise NotImplementedError
        else:
            if sw_type.count('n') == 3:
                w_sw, h_sw = sw_master.bound_box.w, sw_master.bound_box.h
                sw_y = y_cm_sw_top if has_cm_sw else 0
                cap_y = sw_y + (h_sw - h_cap) // 2
                sw_x = -(-sw_x // w_blk) * w_blk
                sw = self.add_instance(sw_master, inst_name='XSW', xform=Transform(sw_x, sw_y))
                # Get sorted ctrl pins
                sw_ctrl_n: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl0')
                sw_ctrl_m: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl1')
                sw_ctrl_p: List[Union[WireArray, None]] = sw.get_all_port_pins('ctrl2')
                sw_bot: List[Union[WireArray, None]] = sw.get_all_port_pins('bot')
                self.reexport(sw.get_port('vref0'), net_name='vref<2>')
                self.reexport(sw.get_port('vref1'), net_name='vref<1>')
                self.reexport(sw.get_port('vref2'), net_name='vref<1>')
                vrefm, vrefm_pin = sw.get_port('vref1'), sw.get_pin('vref1')
                sw_right_coord = sw.bound_box.xh
                sw_params_list = [sw_master.sch_params for _ in range(nbits)]
                sw_vss_bbox: List[BBox] = sw.get_all_port_pins('VSS')
            elif sw_type.count('n') == 2:
                sw_n_params = dict(
                    cls_name=CapDrvCore.get_qualified_name(),
                    draw_taps=True,
                    params=dict(pinfo=self.params['pinfo'], seg=seg, ny=sum(ny_list), w=w_n, sp=sp, nx=2, sw_type='nch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                )
                sw_p_params = dict(
                    cls_name=CapDrvCore.get_qualified_name(),
                    draw_taps=True,
                    params=dict(pinfo=self.params['pinfo'], seg=seg, ny=sum(ny_list), w=w_p, sp=sp, nx=1, sw_type='pch',
                                dum_row_idx=[sum(ny_list[:nbits - diff_idx + 1]) + 1], min_height=unit_cap_height)
                )
                sw_n_master = self.new_template(GenericWrapper, params=sw_n_params)
                sw_p_master = self.new_template(GenericWrapper, params=sw_p_params)
                top_layer = max(cap_master.top_layer, sw_n_master.top_layer, sw_p_master.top_layer)
                w_blk, h_blk = self.grid.get_block_size(top_layer)
                w_sw_p, h_sw = sw_p_master.bound_box.w, sw_p_master.bound_box.h
                w_sw_n, h_sw = sw_n_master.bound_box.w, sw_n_master.bound_box.h
                sw_y = y_cm_sw_top if has_cm_sw else 0
                cap_y = sw_y + (h_sw - h_cap) // 2
                sw_x = -(-sw_x // w_blk) * w_blk
                sw_p = self.add_instance(sw_p_master, inst_name='XSWP', xform=Transform(sw_x, sw_y))
                sw_x = -(-(sw_x + w_sw_p) // w_blk) * w_blk
                sw_n = self.add_instance(sw_n_master, inst_name='XSWN', xform=Transform(sw_x, sw_y))
                # Get sorted ctrl pins
                sw_ctrl_m: List[Union[WireArray, None]] = sw_n.get_all_port_pins('ctrl0')
                sw_ctrl_n: List[Union[WireArray, None]] = sw_n.get_all_port_pins('ctrl1')
                sw_ctrl_p: List[Union[WireArray, None]] = sw_p.get_all_port_pins('ctrl0')
                sw_bot: List[Union[WireArray, None]] = []
                for botn, botp in zip(sw_n.get_all_port_pins('bot'), sw_p.get_all_port_pins('bot')):
                    sw_bot.append(self.connect_wires([botn, botp])[0])
                self.reexport(sw_n.get_port('vref0'), net_name='vref<1>')
                self.reexport(sw_n.get_port('vref1'), net_name='vref<0>')
                self.reexport(sw_p.get_port('vref0'), net_name='vref<2>')
                vref0_xm = sw_n.get_all_port_pins('vref0_xm')
                vref1_xm = sw_n.get_all_port_pins('vref1_xm')
                vref2_xm = sw_p.get_all_port_pins('vref0_xm')

                vrefm, vrefm_pin = sw_n.get_port('vref0'), sw_n.get_pin('vref0')
                sw_right_coord = sw_n.bound_box.xh
                sw_type_dict = dict(
                    XN=sw_type[0],
                    XM=sw_type[1],
                    XP=sw_type[2],
                )
                sw_params_list = [sw_n_master.sch_params.copy(append=dict(sw_type_dict=sw_type_dict)) for _ in range(nbits)]
                self.reexport(sw_p.get_port('VDD'), connect=True)
                vdd_xm = sw_p.get_all_port_pins('VDD_xm')
                vss_xm = sw_n.get_all_port_pins('VSS_xm')
                vdd_xm = self.extend_wires(vdd_xm, upper=vss_xm[0].upper)
                vss_xm = self.extend_wires(vss_xm, lower=vdd_xm[0].lower)

                if not self.params['lower_layer_routing']:
                    vref_ym_list = []
                    for vref in [vref0_xm, vref1_xm, vref2_xm]:
                        mid_coord = vref[0].middle
                        tid = self.grid.coord_to_track(ym_layer, mid_coord, RoundMode.NEAREST)
                        vref_ym_list.append(self.connect_to_tracks(vref, TrackID(ym_layer, tid, tr_w_sup_ym)))
                    ym_sup_locs = self.get_available_tracks(ym_layer, self.grid.coord_to_track(ym_layer, sw_p.bound_box.xl,
                                                                                               RoundMode.NEAREST),
                                                            self.grid.coord_to_track(ym_layer, sw_n.bound_box.xh,
                                                                                     RoundMode.LESS_EQ),
                                                            upper=sw_n.bound_box.yh, lower=sw_n.bound_box.yl,
                                                            width=tr_w_sup_ym,
                                                            sep=tr_manager.get_sep(ym_layer, ('sup', 'sup')))
                    vdd_ym_list, vss_ym_list = [], []
                    xm_vdd_ret_list, xm_vss_ret_list = [], []
                    for tid in ym_sup_locs[::2]:
                        vdd_ym_list.append(
                            self.connect_to_tracks(vdd_xm, TrackID(ym_layer, tid, tr_w_sup_ym), ret_wire_list=xm_vdd_ret_list))
                    for tid in ym_sup_locs[1::2]:
                        vss_ym_list.append(
                            self.connect_to_tracks(vss_xm, TrackID(ym_layer, tid, tr_w_sup_ym), ret_wire_list=xm_vss_ret_list))

                    xm_sup_list = xm_vdd_ret_list + xm_vss_ret_list
                    xm_sup_max_coord, xm_sup_min_coord = max([x.upper for x in xm_sup_list]), \
                                                         min([x.lower for x in xm_sup_list])
                    self.extend_wires(xm_sup_list, upper=xm_sup_max_coord, lower=xm_sup_min_coord)
                    ym_sup_list = vdd_ym_list + vss_ym_list
                    ym_sup_max_coord, ym_sup_min_coord = max([y.upper for y in ym_sup_list]), 0

                    vdd_ym_list = self.extend_wires(vdd_ym_list, upper=ym_sup_max_coord, lower=ym_sup_min_coord)
                    vss_ym_list = self.extend_wires(vss_ym_list, upper=ym_sup_max_coord, lower=ym_sup_min_coord)
            else:
                sw_n, sw_p = None, None
                raise NotImplementedError

        # Place input signal
        tr_w_sig_vm = tr_manager.get_width(vm_layer, 'sig')
        tr_sp_sig_vm = tr_manager.get_sep(vm_layer, ('sig', 'sig'))
        sig_tidx_start = grid.find_next_track(vm_layer, sw_right_coord, tr_width=tr_w_sig_vm)
        sig_tidx_used, sig_tidx_locs = tr_manager.place_wires(vm_layer, ['sig'] * nbits, align_idx=0,
                                                              align_track=sig_tidx_start)
        print(sig_tidx_locs)
        sig_tidx_used, sig_tidx_locs = tr_manager.place_wires(vm_layer, ['sig'] * nbits + ['cap'], align_idx=0,
                                                              align_track=sig_tidx_start)
        cap_x = self.grid.track_to_coord(vm_layer, sig_tidx_locs[-1])

        cap_x = -(-cap_x // w_blk) * w_blk
        cap_config_copy = copy.deepcopy(cap_config.to_dict())

        cap_list = []
        cap_master_list = [cap_master] * (nbits + 1)

        if (cap_config['ismim'] == True):
            cap_ext_x = []
            max_pin = 0
            for idx in range(0, len(bit_list)):
                cap_config_copy['height'] = height_list[idx]
                cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config_copy, width=width_list[idx], ny=4,
                                                                       ratio=1))
                cap_master_list[bit_list[idx]] = cap_master
                if (idx ==0):
                    max_pin = cap_master.top_pin_idx 
                id_pin = cap_master.top_pin_idx 
                top_pin_lay = cap_master.top_layer if (cap_master.top_layer%2) else (cap_master.top_layer -1)
                shift = grid.track_to_coord(top_pin_lay, max_pin-id_pin-0.5)
                     #FIXME: has some rounding error #((max(width_list)-width_list[idx])/self.grid.resolution) #(max(width_list))/self.grid.resolution-(cap_master.array_box.xh)

                if (height_list[idx] == cap_config['height']):
                    cap = self.add_instance(cap_master, inst_name='XCAP', 
                                xform=Transform(cap_x + shift, -(-capmim_y[idx] // h_blk) * h_blk))
                else:    
                    cap = self.add_instance(cap_master, inst_name='XCAP', xform=Transform(cap_x, -(-capmim_y[idx] // h_blk) * h_blk))
                cap_list.append(cap)
                pin = cap.get_all_port_pins('top')
                cap_ext_x.append(cap.array_box.xl)#cap_x + int(-(-shift//w_blk)*w_blk))
                cap_y += cap_master.array_box.yh
            
            # Get cap dac pins
            cap_bot = [pin for inst in cap_list for pin in inst.get_all_port_pins('top')]

        else:
            for idx, (ny, ratio) in enumerate(zip(ny_list, ratio_list)):
                cap_master = self.new_template(CapColCore, params=dict(cap_config=cap_config_copy, width=width, ny=4 * ny,
                                                                       ratio=ratio))
                cap_master_list[bit_list[idx]] = cap_master
                cap = self.add_instance(cap_master, inst_name='XCAP', xform=Transform(cap_x, -(-cap_y // h_blk) * h_blk))
                cap_list.append(cap)
                cap_y += cap_master.array_box.h
            
            # Get cap dac pins
            cap_bot = [pin for inst in cap_list for pin in inst.get_all_port_pins('top')]

            #sort by track_id.base_index
            cap_bot.sort(key=lambda x: x.track_id.base_index)


        # cm_sw_y = -(-max(h_cap, h_sw) // h_blk) * h_blk
        ntr_margin = self.grid.get_sep_tracks(vm_layer, tr_manager.get_width(vm_layer, 'sup'),
                                              cap_list[0].get_pin('top').track_id.width)
        coord_margin = self.grid.track_to_coord(vm_layer, ntr_margin)
        if self.params['lower_layer_routing']:
            cm_sw_x = cap_x-coord_margin
            cm_sw_x = -(-cm_sw_x//w_blk)*w_blk
        else:
            cm_sw_x = cap_x

        cm_sw = self.add_instance(cm_sw_master, inst_name='XSW_CM', xform=Transform(cm_sw_x, 0))

        # left space for clock routing
        num_tr, _ = tr_manager.place_wires(vm_layer, ['cap', 'clk', 'clk'], align_idx=0)
        coord_tr = self.grid.track_to_coord(vm_layer, num_tr)

        w_tot = -(-(cap_x + w_cap + coord_tr) // w_blk) * w_blk
        h_tot = -(-max(cap.bound_box.yh, sw_n.bound_box.yh) // h_blk) * h_blk
        self.set_size_from_bound_box(top_layer, BBox(0, 0, w_tot, h_tot))

        for pin_list in [sw_ctrl_m, sw_ctrl_n, sw_ctrl_p]:
            pin_list.sort(key=lambda x: x.track_id.base_index)

        # Get sorted bottom pin
        sw_bot.sort(key=lambda x: x.track_id.base_index)

        #making the dummy cap not connectable
        for idx in [sum(ny_list[:nbits - diff_idx + 1]) + 1]:
            sw_bot.insert(idx, None)
            sw_ctrl_m.insert(idx, None)
            sw_ctrl_n.insert(idx, None)
            sw_ctrl_p.insert(idx, None)
            
        if (len(sw_bot) > len(cap_bot)):
            cap_bot_copy = cap_bot
            ext_cap = []
            for idx in range(0, len(cap_bot_copy)):
                ext_cap = ext_cap + [cap_bot_copy[idx] for n in range(0, ny_list[idx])]
            cap_bot = ext_cap
        for _sw, _cap in zip(sw_bot, cap_bot):
            if _sw and _cap:
                self.connect_to_track_wires(_sw, _cap) 
        
        # cap top    
        cap_top = self.connect_wires([pin for inst in cap_list for pin in inst.get_all_port_pins('bot')], upper=width/self.grid.resolution)
        
        # Connect to common-mode switch
        tr_w_cap_hm = tr_manager.get_width(hm_layer, 'cap')
        tr_w_cap_vm = tr_manager.get_width(vm_layer, 'cap')
        tr_w_cap_xm = tr_manager.get_width(xm_layer, 'cap')
        if (cap_config['ismim']):
            for (vrefm, vrefm_pin) in zip(vrefm_single, vrefm_pin_single):
                self.connect_bbox_to_track_wires(Direction.LOWER, (vrefm.get_single_layer(), 'drawing'),
                                         vrefm_pin, cm_sw.get_all_port_pins('ref'))
            vrefm = vrefm_single[0]
            vrefm_pin = vrefm_pin_single[0]
        else:
            self.connect_bbox_to_track_wires(Direction.LOWER, (vrefm.get_single_layer(), 'drawing'),
                                         vrefm_pin, cm_sw.get_all_port_pins('ref'))

        cap_top_vm_tidx = tr_manager.get_next_track(vm_layer, sig_tidx_locs[-1], 'sig', 'cap', up=True)
        #cap_top_vm = self.connect_to_tracks(cm_sw.get_pin('sig'),
        #                                     TrackID(vm_layer, cap_top_vm_tidx, tr_w_cap_vm),
        #                                     min_len_mode=MinLenMode.MIDDLE)
        
        #cap_top_xm_tidx = self.grid.coord_to_track(xm_layer, cap_top_vm.middle, mode=RoundMode.NEAREST)
        #cap_top_xm = self.connect_to_tracks(cap_top_vm, TrackID(xm_layer, cap_top_xm_tidx, tr_w_cap_xm))
        
        if(cap_top[0].layer_id > 4):
            pins = cm_sw.get_all_port_pins('sig')
            wire = self.add_wires(pins[0].track_id.layer_id, pins[0].track_id.base_index, lower=(cap_list[0].array_box.xh-w_blk),
                                    upper=cap_list[0].array_box.xh, width=6)
            self.extend_wires(cm_sw.get_all_port_pins('sig'), upper=cap_list[0].array_box.xh)
            self.connect_to_track_wires(wire, cap_top)
        else:
            self.connect_to_track_wires(cm_sw.get_all_port_pins('sig'), cap_top)

        # Group pins for each bit
        ctrl_bit_temp = dict(
            ctrl_m=[],
            ctrl_n=[],
            ctrl_p=[],
        )
        bit_pin_dict_list = [copy.deepcopy(ctrl_bit_temp) for _ in range(nbits)]
        bit_cap_list_list = [copy.deepcopy([]) for _ in range(nbits)]
        for idx, bit_idx in enumerate(bit_list):
            start_idx, stop_idx = sum(ny_list[:idx]), sum(ny_list[:idx + 1])
            if bit_idx:
                bit_pin_dict_list[bit_idx - 1]['ctrl_m'].extend(sw_ctrl_m[start_idx: stop_idx])
                bit_pin_dict_list[bit_idx - 1]['ctrl_n'].extend(sw_ctrl_n[start_idx: stop_idx])
                bit_pin_dict_list[bit_idx - 1]['ctrl_p'].extend(sw_ctrl_p[start_idx: stop_idx])
                bit_cap_list_list[bit_idx - 1].extend(sw_bot[start_idx: stop_idx])

        # Connect control signal to vm-layer
        ctrl_hm_ret_list = []
        ctrl_m_vm_list, ctrl_n_vm_list, ctrl_p_vm_list = [], [], []
        for idx in range(nbits):
            _bit_pins = bit_pin_dict_list[idx]
            ctrl_m_vm_list.append(self.connect_to_tracks(_bit_pins['ctrl_m'],
                                                         TrackID(vm_layer, ctrl_tidx_locs[3 * idx], tr_w_ctrl_vm),
                                                         track_lower=self.bound_box.yl, ret_wire_list=ctrl_hm_ret_list))
            ctrl_n_vm_list.append(self.connect_to_tracks(_bit_pins['ctrl_n'],
                                                         TrackID(vm_layer, ctrl_tidx_locs[3 * idx + 1], tr_w_ctrl_vm),
                                                         track_lower=self.bound_box.yl, ret_wire_list=ctrl_hm_ret_list))
            ctrl_p_vm_list.append(self.connect_to_tracks(_bit_pins['ctrl_p'],
                                                         TrackID(vm_layer, ctrl_tidx_locs[3 * idx + 2], tr_w_ctrl_vm),
                                                         track_lower=self.bound_box.yl, ret_wire_list=ctrl_hm_ret_list))
        ctrl_hm_ret_min_coord, ctrl_hm_ret_max_coord = min([x.lower for x in ctrl_hm_ret_list]), \
                                                       max([x.upper for x in ctrl_hm_ret_list])
        self.extend_wires(ctrl_hm_ret_list, lower=ctrl_hm_ret_min_coord, upper=ctrl_hm_ret_max_coord)

        cap_cm_list = cap_bot[sum(ny_list[:nbits - diff_idx + 1]) + 1: sum(ny_list[:nbits - diff_idx + 1]) + 2]
        for _cap_cm in cap_cm_list:
            hm_tidx = self.grid.coord_to_track(hm_layer, _cap_cm.middle, mode=RoundMode.NEAREST)
            hm_w = self.connect_to_tracks(_cap_cm, TrackID(hm_layer, hm_tidx, tr_w_cap_hm))
            self.connect_bbox_to_track_wires(Direction.UPPER, (vrefm.get_single_layer(), 'drawing'),
                                             vrefm_pin, hm_w)  #FIXME

        # connect bot pins   
        # want to space out bottom pins so less parasitic
        bot_vm_list: List[WireArray] = []
        for idx in range(nbits):
            # bot_tidx_locs = self.get_available_tracks(vm_layer, self.grid.coord_to_track(xm_layer, sw_x, RoundMode.NEAREST),
            #                   self.grid.coord_to_track(xm_layer, cap_x, RoundMode.NEAREST),
            #                   self.bound_box.yl, self.bound_box.yh, tr_w_sig_vm,
            #                   sep_margin = 3)
            bot_vm_list.append(self.connect_to_tracks(bit_cap_list_list[idx],
                                                      TrackID(vm_layer, sig_tidx_locs[idx], tr_w_sig_vm),
                                                      track_upper=self.bound_box.yh))
        bot_vm_list_bot_coord = sw_y
        if (cap_config['ismim']):
            bot_vm_list = self.extend_wires(bot_vm_list, lower=(-(-capmim_y[0] // h_blk) * h_blk))
        else:
            bot_vm_list = self.extend_wires(bot_vm_list, lower=bot_vm_list_bot_coord)
        for idx, bot_wire in enumerate(bot_vm_list):
            self.add_pin(f'bot<{idx}>', bot_wire, mode=PinMode.UPPER)

        # flip n and p control, just because comparator output and differential ...
        ctrl_top_coord = max([c.upper for c in ctrl_n_vm_list + ctrl_p_vm_list + ctrl_m_vm_list])
        ctrl_n_vm_list = self.extend_wires(ctrl_n_vm_list, upper=ctrl_top_coord)
        ctrl_p_vm_list = self.extend_wires(ctrl_p_vm_list, upper=ctrl_top_coord)
        ctrl_m_vm_list = self.extend_wires(ctrl_m_vm_list, upper=ctrl_top_coord)

        for idx, (n, m, p) in enumerate(zip(ctrl_n_vm_list, ctrl_m_vm_list, ctrl_p_vm_list)):
            self.add_pin(f'ctrl_m<{idx}>', m, mode=PinMode.LOWER)
            self.add_pin(f'ctrl_n<{idx}>', p, mode=PinMode.LOWER)
            self.add_pin(f'ctrl_p<{idx}>', n, mode=PinMode.LOWER)

        tr_sp_sig_cap_vm = tr_manager.get_sep(vm_layer, ('sig', 'cap'))
        vm_tidx_stop = self.grid.coord_to_track(vm_layer, cm_sw.bound_box.xh, mode=RoundMode.NEAREST)
        vm_tidx_start = self.grid.coord_to_track(vm_layer, cm_sw.bound_box.xl, mode=RoundMode.NEAREST)

        if not self.params['lower_layer_routing']:
            self.connect_to_track_wires(cm_sw.get_all_port_pins('VSS'), vss_ym_list)

        # TODO: fix VSS
        self.reexport(sw_n.get_port('VSS'), connect=True)
        self.reexport(cm_sw.get_port('sam'))
        # for vss_bbox in sw_vss_bbox + cm_bbox:
        #     self.add_pin_primitive('VSS', f'm{conn_layer}', vss_bbox, connect=True)

        self.add_pin('top', cap_top)

        m_list = [len(_l) for _l in bit_cap_list_list]
        sw_list = m_list
        unit_params_list = [master.sch_params for master in cap_master_list[1:]]

        self._actual_width = self.bound_box.w - routing_bnd
        self.sch_params = dict(
            sw_params_list=sw_params_list,
            unit_params_list=unit_params_list,
            cm_unit_params=cap_master_list[0].sch_params,
            bot_probe=True,
            cap_m_list=m_list,
            sw_m_list=sw_list,
            cm=ny_list[nbits - 1],
            cm_sw=cm_sw_master.sch_params,
            remove_cap=self.params['remove_cap'],
        )

class CapMIMUnitCore(TemplateBase):
    """MIMCap core
    Draw a layout has only metal and metal resistor in a rectangle
    Horizontal layer is "vertical_layer"
    Top and bottom is connected by "bot_layer"

    Parameters:
        top_w: width of middle horizontal layer
        bot_w: width of top/bot horizontal layer
        bot_y_w: width of vertical layer
        sp: space between top/bot and middle
        sp_le: line-end space between middle horizontal layer
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_unit')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            cap_config='MIM cap configuration.',
            width='MIM cap width, in resolution units.',
            tr_w='Track width',
            tr_sp='Track space',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DeviceFill.get_default_param_values()
        ans.update(
            cap_config={},
            width=0,
            tr_w={},
            tr_sp={},
        )
        return ans

    def draw_layout(self) -> None:
        cap_config: Dict[str, int] = self.params['cap_config']
        tr_w: Dict = self.params['tr_w']
        tr_sp: Dict = self.params['tr_sp']
        width: int = self.params['width']
        #width = int(width / self.grid.resolution)

        tr_manager = TrackManager(self.grid, tr_w, tr_sp)

        grid = self.grid

        # Read cap_info
        unit_cap = cap_config['unit_cap']
        top_layer = cap_config['top_layer']
        bot_layer = cap_config['bot_layer']

        w_blk, h_blk = grid.get_block_size(max(top_layer, bot_layer), half_blk_x=True, half_blk_y=True)
        height = cap_config['height']
        
        #DRC rules
        #spacing between met3,4 = 0.3, met5 =1.6
        #spacing between cap 0.84
        #cap enclosure = 0.14
        #cap min width 2
        #cap max aspect ratio 20
        #via enclosure by cap 0.14/0.2
        #spacing from cap to another via of same layer 0.14
        #spacing between multiple parallel caps 1.48
        if (min(width, height) < 2):
            raise ValueError("Dimension too small")

        lay_res = self.grid.resolution
        top_cap = max(top_layer, bot_layer)
        bot_cap = min(top_layer, bot_layer)
 
        #DRC rules
        ratio = 20 
        bot_sp = 0.48
        botm_wid = 0.3
        cap_bound = 0.15 
        via_bnd = 0.14
        topm_wid = 0.3
        cap_off = 1.5#1.48  #offset between cap blocks
        top_ext = topm_wid+cap_bound
        bot_ext = botm_wid+cap_bound

        top_metal = ('met4', 'drawing') #default
        bot_metal = ('met3', 'drawing')
        cap_lay = ('capm', 'drawing')


        if ((top_cap == 4)  and (bot_cap == 3)):
            top_metal = ('met4', 'drawing')
            bot_metal = ('met3', 'drawing')
            cap_lay = ('capm', 'drawing')

            #DRC rules
            bot_sp = 0.48
            via_bnd = 0.14
            topm_wid = 1.6#0.3
            top_ext = topm_wid+cap_bound

        elif ((top_cap == 5) and(bot_cap == 4)):
            top_metal = ('met5', 'drawing')
            bot_metal = ('met4', 'drawing')
            cap_lay = ('cap2m', 'drawing')
            #DRC rules
            bot_sp = 0.8
            via_bnd = 0.2
            topm_wid = 1.6
            top_ext = topm_wid+cap_bound
        else:
            raise ValueError("No MIM cap constructable")

        #Cap construction
        if unit_cap:
            unit_height = cap_config['unit_height']
            unit_width = cap_config['unit_width']
            width_total = cap_config['width_total']
            if (unit_height/unit_width > ratio or unit_width/unit_height>ratio): 
                raise ValueError("Unit dimensions violate DRC rules")
            num_vert = int(height/unit_height)
            num_hor = int(width_total/unit_width) #need to differentiate between total width and cap width (dumies)
            block_w = unit_width
            base_y = int((bot_sp+cap_bound)/lay_res)
            num_dum = int((width_total-width)/unit_width)
            for j in range(0, num_vert):  
                y_bot = base_y + j*(int((unit_height+cap_off)/lay_res))
                for n in range(0, num_hor):
                    self.add_rect_array(cap_lay, BBox(int((bot_ext+(n)*(block_w+cap_off))/lay_res), y_bot,
                                            int((bot_ext+(n+1)*(block_w)+(n)*cap_off)/lay_res), y_bot+int(unit_height/lay_res)))
                    self.add_via(BBox(int(((bot_ext+via_bnd)+n*(block_w+cap_off))/lay_res), y_bot + int(cap_bound/lay_res),
                                        int((bot_ext-via_bnd+(n+1)*(block_w)+n*cap_off)/lay_res), y_bot+int((unit_height-via_bnd)/lay_res)),
                                bot_metal, top_metal, 
                                bot_dir=self.grid.get_direction(top_layer), extend=False, add_layers=False)
            if (width<width_total):
                # for the actual cap
                self.add_rect_array(bot_metal, BBox(int((width_total-width+(num_dum)*cap_off)/lay_res), int(bot_sp/lay_res), 
                                    int((width_total+(num_hor-1)*cap_off+bot_ext+cap_bound)/lay_res),
                                    int((height+(num_vert-1)*cap_off+2*cap_bound+bot_sp)/lay_res)))
                self.add_rect_array(top_metal, BBox(int((width_total-width+(num_dum)*cap_off)/lay_res), int((bot_sp+cap_bound)/lay_res), 
                                    int((width_total+(num_hor-1)*cap_off+bot_ext+cap_bound)/lay_res), 
                                    int((height+(num_vert-1)*cap_off+bot_sp+cap_bound)/lay_res)))
                # for the dummy
                self.add_rect_array(bot_metal, BBox(0, int(bot_sp/lay_res), 
                                    int((width_total-width+(num_dum-1)*cap_off+bot_ext+cap_bound)/lay_res), 
                                    int((height+(num_vert-1)*cap_off+2*cap_bound+bot_sp)/lay_res)))
                self.add_rect_array(top_metal, BBox(int((cap_bound+botm_wid)/lay_res), int((bot_sp+cap_bound)/lay_res), 
                                    int((width_total-width+(num_dum-1)*cap_off+bot_ext+cap_bound)/lay_res), 
                                    int((height+(num_vert-1)*cap_off+bot_sp+cap_bound)/lay_res)))
            else: 
                self.add_rect_array(bot_metal, BBox(0, int(bot_sp/lay_res), 
                                        int((width+(num_hor-1)*cap_off+bot_ext+cap_bound)/lay_res), 
                                        int((height+(num_vert-1)*cap_off+2*cap_bound+bot_sp)/lay_res)))
                self.add_rect_array(top_metal, BBox(int((cap_bound+botm_wid)/lay_res), int((bot_sp+cap_bound)/lay_res), 
                                    int((width+(num_hor-1)*cap_off+(top_ext+bot_ext))/lay_res), 
                                    int((height+(num_vert-1)*cap_off+bot_sp+cap_bound)/lay_res)))
            # add top metal and bottom 
            w_tot = bot_ext+width_total+(num_hor-1)*cap_off +top_ext
            h_tot = bot_sp+cap_bound+height+(num_vert-1)*cap_off
            pin_boty = bot_sp
            pin_botx = (width_total-width+(num_dum)*cap_off)+botm_wid
            pin_topx = bot_ext+width_total+(num_hor-1)*cap_off+cap_bound
            pin_topy = bot_sp+cap_bound

            self.add_rect_array(top_metal, BBox(int(pin_topx//lay_res), int(pin_topy//lay_res), int(w_tot//lay_res), int(h_tot//lay_res)))
            self.add_rect_array(bot_metal, BBox(int((width_total-width+(num_dum)*cap_off-botm_wid)/lay_res), int(pin_boty//lay_res), 
                                                            int(pin_botx//lay_res), int(h_tot//lay_res)))


            self.add_pin_primitive('minus', top_layer, BBox(int(pin_topx//lay_res), int(pin_topy//lay_res), int(w_tot//lay_res), int(h_tot//lay_res)), show=False)
            self.add_pin_primitive('plus', bot_layer, BBox(int((width_total-width+(num_dum)*cap_off-botm_wid)/lay_res), int(pin_boty//lay_res), 
                                                            int(pin_botx//lay_res), int(h_tot//lay_res)), show=False)

            # set size
            bnd_box = BBox(0, 0, int(-(-(w_tot/self.grid.resolution)//w_blk)*w_blk),
                                  int(-(-(h_tot/self.grid.resolution)//h_blk)*h_blk))
            self.array_box = (BBox(0, 0, int(-(-(w_tot/self.grid.resolution)//w_blk)*w_blk),
                                  int(-(-(h_tot/self.grid.resolution)//h_blk)*h_blk)))
            self.set_size_from_bound_box(max(top_layer, bot_layer), bnd_box)

        else:
            self.add_rect_array(bot_metal, BBox(0, int(bot_sp/lay_res), 
                                        int((width+bot_ext+cap_bound)/lay_res), int((height+2*cap_bound+bot_sp)/lay_res)))
            self.add_rect_array(top_metal, BBox(int((cap_bound+botm_wid)/lay_res), int((bot_sp+cap_bound)/lay_res), 
                                    int((width+(top_ext+bot_ext))/lay_res), int((height+bot_sp+cap_bound)/lay_res)))
            if (width/height > ratio): #TODO: make it possible to have multiblock vertically
                num_blocks = int(math.ceil(max(width, height)/(20*min(width, height))))
                block_w = (width-(num_blocks-1)*cap_off)/num_blocks
                for n in range(0, num_blocks):
                    self.add_rect_array(cap_lay, BBox(int((bot_ext+(n)*(block_w+cap_off))/lay_res), int((bot_sp+cap_bound)/lay_res),
                                                            int((bot_ext+(n+1)*(block_w)+(n)*cap_off)/lay_res), int((height+cap_bound+bot_sp)/lay_res)))
                    self.add_via(  BBox(int(((bot_ext+via_bnd)+n*(block_w+cap_off))/lay_res), int((bot_sp+2*cap_bound)/lay_res),
                                        int((bot_ext-via_bnd+(n+1)*(block_w)+n*cap_off)/lay_res), int((height+cap_bound+bot_sp-via_bnd)/lay_res)),
                                bot_metal, top_metal, 
                                bot_dir=self.grid.get_direction(top_layer), extend=False, add_layers=False)
                
            else:
                self.add_rect_array(cap_lay, BBox(int(bot_ext/lay_res), int((bot_sp+cap_bound)/lay_res),
                                            int((bot_ext+width)/lay_res), int((height+cap_bound+bot_sp)/lay_res)))
                self.add_via( BBox(int((bot_ext+via_bnd)/lay_res), int((bot_sp+cap_bound+via_bnd)/lay_res),
                                    int((bot_ext+width-via_bnd)/lay_res), int((height+bot_sp)/lay_res)),
                                bot_metal, top_metal, 
                                bot_dir=self.grid.get_direction(top_layer), extend=False, add_layers=False)
            w_tot = bot_ext+width+top_ext
            h_tot = bot_sp+2*cap_bound+height
            pin_boty=bot_sp
            pin_botx=botm_wid
            pin_topx = bot_ext+width+cap_bound
            pin_topy =bot_sp

            self.add_rect_array( top_metal, BBox(int(pin_topx//lay_res), int(pin_topy//lay_res), int(w_tot//lay_res), int(h_tot//lay_res)))
            self.add_rect_array( bot_metal, BBox(int((width_total-width+(num_dum)*cap_off-botm_wid)/lay_res), int(pin_boty//lay_res), 
                                                            int(pin_botx//lay_res), int(h_tot//lay_res)))

            self.add_pin_primitive('minus', top_layer, BBox(int(pin_topx//lay_res), int(pin_topy//lay_res), int(w_tot//lay_res), int(h_tot//lay_res)), show=True)
            self.add_pin_primitive('plus', bot_layer, BBox(0, int(pin_boty//lay_res), int(pin_botx//lay_res), int(h_tot//lay_res)), show=True)
        

            # set size
            bnd_box = BBox(0, 0, int(-(-(width/self.grid.resolution)//w_blk)*w_blk), int(-(-(height/self.grid.resolution)//h_blk)*h_blk))  #not adding the boxes still
            self.array_box = (BBox(0, 0, int(-(-(w_tot/self.grid.resolution)//w_blk)*w_blk),
                                int(-(-(h_tot/self.grid.resolution)//h_blk)*h_blk)))
            self.set_size_from_bound_box(max(top_layer, bot_layer), bnd_box)

# Need another class to actually call CapMIMUnitCore as a template 
class CapMIMCore(TemplateBase):
    """MIMCap core
    Draw a layout has only metal and metal resistor in a rectangle
    Horizontal layer is "vertical_layer"
    Top and bottom is connected by "bot_layer"

    Parameters:
        top_w: width of middle horizontal layer
        bot_w: width of top/bot horizontal layer
        bot_y_w: width of vertical layer
        sp: space between top/bot and middle
        sp_le: line-end space between middle horizontal layer
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_unit')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            cap_config='MIM cap configuration.',
            width='MIM cap width, in resolution units.',
            tr_w='Track width',
            tr_sp='Track space',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        ans = DeviceFill.get_default_param_values()
        ans.update(
            cap_config={},
            width=0,
            tr_w={},
            tr_sp={},
            options={},
        )
        return ans

    def draw_layout(self) -> None:
        #options: ImmutableSortedDict[str, Any] = self.params['options']
        cap_config: ImmutableSortedDict[str, Union[int, float]] = self.params['cap_config']
        
        grid = self.grid
        
        top_layer = cap_config['top_layer']
        bot_layer = cap_config['bot_layer']
        #pin_layer either 3, 3 or 3, 5
        width: int = self.params['width']
        height = cap_config['height']

        capMIM_master: TemplateBase = self.new_template(CapMIMUnitCore, params=dict(cap_config=self.params['cap_config'], 
                                            width=width,tr_w=self.params['tr_w'], tr_sp=self.params['tr_w']))
        capMIM = self.add_instance(capMIM_master, inst_name='CMIM', xform=Transform(0, 0))
        lay_top_layer = capMIM_master.top_layer
        w_blk, h_blk = grid.get_block_size(lay_top_layer, half_blk_x=True, half_blk_y=True)

        #code to connect primitive pin to another layer
        mim_cap_top = BBoxArray(capMIM.get_pin('minus', layer=top_layer))
        mim_cap_bot = BBoxArray(capMIM.get_pin('plus', layer=bot_layer))

        #the track layer has to be odd, can be different from the mim_cap layer
        # to connect to tracks have to connect to above or below layer
       
        if (top_layer == 5):
            idx_t = grid.find_next_track(5, int(mim_cap_top.xl), tr_width=1, half_track=True, mode=RoundMode.GREATER_EQ)
            idx_b = grid.find_next_track(3, 0, tr_width=1, half_track=True, mode=RoundMode.LESS_EQ) 
            #cap_top = self.connect_bbox_to_tracks(Direction.LOWER, ('met3', 'drawing'), mim_cap_top, 
            #                                         TrackID(5, idx_t, 1)) 
            cap_top = self.add_wires(top_layer, idx_t, int(mim_cap_top.yl), int(mim_cap_top.yh), width=2)
            cap_bot = self.connect_bbox_to_tracks(Direction.UPPER, ('met4','drawing'), mim_cap_bot,
                                                     TrackID(3, idx_b, 1))
        if (top_layer == 4):
            idx_t = grid.find_next_track(3, int(mim_cap_top.xh), tr_width=1, half_track=True, mode=RoundMode.GREATER_EQ)
            idx_b = grid.find_next_track(3, int(mim_cap_bot.xh), tr_width=1, half_track=True, mode=RoundMode.LESS_EQ)
            cap_top = self.connect_bbox_to_tracks(Direction.UPPER, ('met4','drawing'), mim_cap_top,
                                                     TrackID(3, idx_t, 1))
            cap_bot = self.add_wires(bot_layer, idx_b, int(mim_cap_bot.yl+h_blk), int(mim_cap_bot.yh-h_blk), width=1)
        
        self.add_pin('plus', cap_bot, show=self.show_pins)
        self.add_pin('minus', cap_top, show=self.show_pins)
        self.top_pin_idx = idx_t

        #width = int(width/self.grid.resolution)
        #height = int((height+cap_config['cap_sp'])/self.grid.resolution)
        w_tot = capMIM.array_box.xh #-(-width // w_blk) * w_blk
        h_tot = capMIM.array_box.yh #-(-height // h_blk) * h_blk
        bbox = BBox(0, 0, int(w_tot), int(h_tot))
        self.set_size_from_bound_box(max(cap_config['top_layer'], cap_config['bot_layer']), bbox)
        self.array_box = BBox(0, 0, int(w_tot), int(h_tot))
        #schematic things
        has_rmetal = cap_config.get('has_rmetal', True)
        if has_rmetal:
            res_top_box = capMIM.get_pin('minus', layer=top_layer)
            res_bot_box = capMIM.get_pin('plus', layer=bot_layer)

        if 'cap' in cap_config and has_rmetal:
            self.sch_params = dict(
                res_plus=dict(layer=top_layer, w=res_top_box.h, l=res_top_box.w),
                res_minus=dict(layer=top_layer, w=res_bot_box.h, l=res_bot_box.w),
                cap=cap_config.get('unit', 1) * cap_config['cap']
            )
        elif 'cap' in cap_config:
            self.sch_params = dict(cap=cap_config.get('unit', 1) * cap_config['cap'])
        elif has_rmetal:
            self.sch_params = dict(
                res_plus=dict(layer=top_layer, w=res_top_box.h, l=res_top_box.w),
                res_minus=dict(layer=top_layer, w=res_bot_box.h, l=res_bot_box.w),
            )
        else:
            self.sch_params = dict(
                res_plus=None,
                res_minus=None,
            )
class CapMOMLUnit(TemplateBase):
    """xbase multilayerMOMCap core
    """

    def __init__(self, temp_db: TemplateDB, params: Param, **kwargs: Any) -> None:
        TemplateBase.__init__(self, temp_db, params, **kwargs)

    @classmethod
    def get_schematic_class(cls) -> Optional[Type[Module]]:
        # noinspection PyTypeChecker
        return ModuleDB.get_schematic_class('skywater130_bag3_sar_adc', 'cap_unit')

    @classmethod
    def get_params_info(cls) -> Dict[str, str]:
        return dict(
            mom_params='capacitor parameters',
        )

    @classmethod
    def get_default_param_values(cls) -> Dict[str, Any]:
        pass

    def draw_layout(self) -> None:
        mom_params: ImmutableSortedDict[str, Any] = self.params['mom_params']
        
        w_cap = int(mom_params['width'] / self.grid.resolution)
        cboot_params = copy.deepcopy(mom_params.to_dict())
        top_layer = cboot_params['top_layer']
        bot_layer = cboot_params['bot_layer']
        
        w_blk, h_blk = self.grid.get_block_size(top_layer)

        w_cap = -(-w_cap // w_blk) * w_blk


        h_cap_tot = 2 * mom_params['margin'] - 2 * h_blk
        cboot_height = (h_cap_tot // h_blk) * h_blk

        cboot_params['height'] = cboot_height
        cboot_params['width'] = w_cap
        cboot_master: TemplateBase = self.new_template(MOMCapCore, params=cboot_params)

        w_cap = cboot_master.bound_box.w
        w_tot = w_cap

        cboot = self.add_instance(cboot_master, inst_name='CBOOT', xform=Transform(0, 0))
        mom_cap_bot = [cboot.get_pin('minus', layer=top_layer)]
        mom_cap_top = cboot.get_pin('plus', layer=bot_layer)

        ym_tids = [TrackID(top_layer, 1, cboot_params['port_tr_w']), TrackID(bot_layer, 1, cboot_params['port_tr_w'])]
        cap_top = self.connect_to_track_wires(top_layer, self.connect_to_tracks(mom_cap_top, ym_tids[0]))
        cap_bot = self.connect_to_track_wires(bot_layer, self.connect_to_tracks(mom_cap_bot, ym_tids[1]))
        self.add_pin('cap_bot', cap_bot, show=self.show_pins)
        self.add_pin('cap_top', cap_top, show=self.show_pins)