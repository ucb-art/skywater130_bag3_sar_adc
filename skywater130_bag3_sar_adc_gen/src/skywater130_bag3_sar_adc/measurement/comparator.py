from typing import Any, Union, Tuple, Optional, Mapping, cast, Dict, Type

# import matplotlib.pyplot as plt
import numpy as np
import copy

from pathlib import Path

from bag.simulation.core import TestbenchManager
from bag.simulation.cache import SimulationDB, DesignInstance, SimResults, MeasureResult
from bag.simulation.measure import MeasurementManager, MeasInfo
from bag.math.interpolate import LinearInterpolator

from bag.concurrent.util import GatherHelper

from bag3_testbenches.measurement.data.tran import EdgeType
from bag3_testbenches.measurement.tran.analog import AnalogTranTB
from bag3_testbenches.measurement.pnoise.base import PNoiseTB


class ComparatorMM(MeasurementManager):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tbm_info: Optional[Tuple[AnalogTranTB, Mapping[str, Any]]] = None

    def initialize(self, sim_db: SimulationDB, dut: DesignInstance) -> Tuple[bool, MeasInfo]:
        raise RuntimeError('Unused')

    def get_sim_info(self, sim_db: SimulationDB, dut: DesignInstance, cur_info: MeasInfo
                     ) -> Tuple[Union[Tuple[TestbenchManager, Mapping[str, Any]],
                                      MeasurementManager], bool]:
        raise RuntimeError('Unused')

    def process_output(self, cur_info: MeasInfo, sim_results: Union[SimResults, MeasureResult]
                       ) -> Tuple[bool, MeasInfo]:
        raise RuntimeError('Unused')

    def setup_tbm(self, sim_db: SimulationDB, dut: DesignInstance, analysis: Union[Type[AnalogTranTB], Type[PNoiseTB]],
                  ) -> Union[AnalogTranTB, PNoiseTB]:
        specs = self.specs
        noise_in_stimuli = specs['noise_in_stimuli']
        delay_in_stimuli = specs['delay_in_stimuli']
        tbm_specs = copy.deepcopy(dict(**specs['tbm_specs']))
        tbm_specs['dut_pins'] = list(dut.sch_master.pins.keys())
        if analysis is PNoiseTB:
            tbm_specs['stimuli_list'].extend(noise_in_stimuli)
        else:
            tbm_specs['stimuli_list'].extend(delay_in_stimuli)
            swp_info = []
            for k, v in specs.get('swp_info', dict()).items():
                if isinstance(v, list):
                    swp_info.append((k, dict(type='LIST', values=v)))
                else:
                    _type = v['type']
                    if _type == 'LIST':
                        swp_info.append((k, dict(type='LIST', values=v['val'])))
                    elif _type == 'LINEAR':
                        swp_info.append((k, dict(type='LINEAR', start=v['start'], stop=v['stop'], num=v['num'])))
                    elif _type == 'LOG':
                        swp_info.append((k, dict(type='LOG', start=v['start'], stop=v['stop'], num=v['num'])))
                    else:
                        raise RuntimeError
            tbm_specs['swp_info'] = swp_info
        tbm = cast(analysis, sim_db.make_tbm(analysis, tbm_specs))
        return tbm

    @staticmethod
    def process_output_noise(sim_results: Union[SimResults, MeasureResult]) -> MeasInfo:
        data = cast(SimResults, sim_results).data
        # -- Process pnoise --
        data.open_group('pnoise')
        freq = data['freq']
        noise = data['out']
        noise_fd = np.square(noise[0, 0, ...])
        noise_fit = LinearInterpolator([freq], noise_fd, [0])
        tot_noise = np.sqrt(noise_fit.integrate(noise_fit.input_ranges[0][0], noise_fit.input_ranges[0][1]))
        # -- Process pac --
        data.open_group('pac')
        gain = np.abs(data['outp'] - data['outn'])[0, 0, 0, :][0]
        in_referred_noise = tot_noise / gain

        return MeasInfo('done', {'noise': in_referred_noise})

    @staticmethod
    def process_output_delay(sim_results: Union[SimResults, MeasureResult], tbm: AnalogTranTB) -> MeasInfo:
        data = cast(SimResults, sim_results).data

        t_d = tbm.calc_delay(data, 'clk', 'out', EdgeType.RISE, EdgeType.CROSS, False, True, '2.25*t_per', 't_sim')
        result = dict(td=t_d)

        return MeasInfo('done', result)

    @staticmethod
    async def _run_sim(name: str, sim_db: SimulationDB, sim_dir: Path, dut: DesignInstance,
                       tbm: AnalogTranTB):
        sim_id = f'{name}'
        sim_results = await sim_db.async_simulate_tbm_obj(sim_id, sim_dir / sim_id,
                                                          dut, tbm, {}, tb_name=sim_id)

        return sim_results

    async def get_noise(self, name, sim_db: SimulationDB, dut: DesignInstance, sim_dir: Path, vcm: float):
        self.specs['tbm_specs']['sim_params']['v_cm'] = vcm
        tbm_noise = self.setup_tbm(sim_db, dut, PNoiseTB)
        noise_results = await self._run_sim(name + '_noise', sim_db, sim_dir, dut, tbm_noise)
        noise = self.process_output_noise(noise_results).prev_results
        return noise

    async def async_measure_performance(self, name: str, sim_dir: Path, sim_db: SimulationDB,
                                        dut: Optional[DesignInstance]) -> Dict[str, Any]:
        results = dict()
        if 'noise' in self.specs['analysis']:
            if 'v_cm' in self.specs['swp_info'].keys():
                vcm_swp_info = self.specs['swp_info']['v_cm']
                helper = GatherHelper()
                for vcm in list(
                        np.linspace(float(vcm_swp_info['start']), float(vcm_swp_info['stop']), vcm_swp_info['num'])):
                    helper.append(self.get_noise(name + f'_noise_vcm={vcm:.2f}', sim_db, dut, sim_dir, vcm))
                results['noise'] = await helper.gather_err()
            else:
                tbm_noise = self.setup_tbm(sim_db, dut, PNoiseTB)
                noise_results = await self._run_sim(name + '_noise', sim_db, sim_dir, dut, tbm_noise)
                results['noise'] = self.process_output_noise(noise_results).prev_results

        if 'delay' in self.specs['analysis']:
            tbm_delay = self.setup_tbm(sim_db, dut, AnalogTranTB)
            delay_results = await self._run_sim(name + '_delay', sim_db, sim_dir, dut, tbm_delay)
            results['delay'] = self.process_output_delay(delay_results, tbm_delay).prev_results

        return results


class ComparatorDelayMM(ComparatorMM):
    def commit(self) -> None:
        self.specs['analysis'] = ['delay']

    @classmethod
    def plot_sig(cls, sim_data, axis):
        time_vec = sim_data['time']
        for sig_name in ['inn', 'inp', 'clk']:
            axis[0].plot(time_vec, sim_data[sig_name], linewidth=2, label=sig_name)
        for sig_name in ['outn', 'outp']:
            axis[1].plot(time_vec, sim_data[sig_name], label=sig_name)
        [_ax.grid() for _ax in axis]
        [_ax.legend() for _ax in axis]

    @classmethod
    def plot_vcm_vdm(cls, sim_data, td, axis):
        if 'v_cm' not in sim_data.sweep_params or 'v_dm' not in sim_data.sweep_params:
            raise RuntimeError
        for idx, vcm in enumerate(sim_data['v_cm']):
            axis.plot(sim_data['v_dm'], td[0, idx, :], label=f'vcm={vcm}V')
        axis.set_xlabel('v_dm')
        axis.set_ylabel('Resolve Time')
        axis.grid()
        axis.legend()

    @staticmethod
    def plot_vcm(sim_data, td, axis, tbm: AnalogTranTB):
        if 'v_dm' in sim_data.sweep_params:
            raise RuntimeError("Only sweep vcm, vdm is also in sweep params now")
        vdm = tbm.get_sim_param_value('v_dm')
        axis.plot(sim_data['v_cm'], td[0, ...], label=f'vdm={vdm}')
        axis.set_xlabel('v_cm')
        axis.set_ylabel('Resolve Time')
        axis.grid()
        axis.legend()


class ComparatorPNoiseMM(ComparatorMM):
    def commit(self) -> None:
        self.specs['analysis'] = ['noise']
