from typing import Any, Union, Tuple, Optional, Mapping, cast, Dict, Type

# import matplotlib.pyplot as plt
import numpy as np
import copy

from pathlib import Path

from bag.simulation.core import TestbenchManager
from bag.simulation.data import AnalysisType
from bag.simulation.cache import SimulationDB, DesignInstance, SimResults, MeasureResult
from bag.simulation.measure import MeasurementManager, MeasInfo
from bag.math.interpolate import LinearInterpolator

from bag.concurrent.util import GatherHelper
import matplotlib

from bag3_testbenches.measurement.data.tran import EdgeType
from bag3_testbenches.measurement.tran.digital import DigitalTranTB
from bag3_testbenches.measurement.pnoise.base import PNoiseTB
from bag3_testbenches.measurement.pac.base import PACTB

class ComparatorMM(MeasurementManager):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tbm_info: Optional[Tuple[DigitalTranTB, Mapping[str, Any]]] = None

    def initialize(self, sim_db: SimulationDB, dut: DesignInstance) -> Tuple[bool, MeasInfo]:
        raise RuntimeError('Unused')

    def get_sim_info(self, sim_db: SimulationDB, dut: DesignInstance, cur_info: MeasInfo
                     ) -> Tuple[Union[Tuple[TestbenchManager, Mapping[str, Any]],
                                      MeasurementManager], bool]:
        raise RuntimeError('Unused')

    def process_output(self, cur_info: MeasInfo, sim_results: Union[SimResults, MeasureResult]
                       ) -> Tuple[bool, MeasInfo]:
        raise RuntimeError('Unused')

    def setup_tbm(self, sim_db: SimulationDB, dut: DesignInstance, analysis: Union[Type[DigitalTranTB], Type[PNoiseTB]],
                  ) -> Union[DigitalTranTB, PNoiseTB]:
        specs = self.specs
        noise_in_stimuli = specs['noise_in_stimuli']
        delay_stimuli = specs['delay_stimuli']
        tbm_specs = copy.deepcopy(dict(**specs['tbm_specs']))
        tbm_specs['dut_pins'] = list(dut.sch_master.pins.keys())
        if analysis is DigitalTranTB:
            swp_info = []
            tbm_specs['src_list'] = []
            tbm_specs['pulse_list'] = list(tbm_specs['pulse_list'])
            tbm_specs['pulse_list'].extend(delay_stimuli)
            for k, v in specs.get('swp_info', dict()).items():
                if isinstance(v, list):
                    swp_info.append((k, dict(type='LIST', values=v)))
                else:
                    _type = v['type']
                    if _type == 'LIST':
                        swp_info.append((k, dict(type='LIST', values=v['values'])))
                    elif _type == 'LINEAR':
                        swp_info.append((k, dict(type='LINEAR', start=v['start'], stop=v['stop'], num=v['num'])))
                    elif _type == 'LOG':
                        swp_info.append((k, dict(type='LOG', start=v['start'], stop=v['stop'], num=v['num'])))
                    else:
                        raise RuntimeError
            tbm_specs['swp_info'] = swp_info
        else:
            tbm_specs['src_list'].extend(noise_in_stimuli)
        tbm = cast(analysis, sim_db.make_tbm(analysis, tbm_specs))
        return tbm

    @staticmethod
    def process_output_noise(noise_sim_results: Union[SimResults, MeasureResult],
                             pac_sim_results: Union[SimResults, MeasureResult]) -> MeasInfo:
        data_noise = cast(SimResults, noise_sim_results).data
        # -- Process pnoise --
        data_noise.open_group('pnoise')
        freq = data_noise['freq']
        noise = data_noise['out']
        noise_fd = np.square(noise[0])
        noise_fit = LinearInterpolator([freq], noise_fd, [0])
        tot_noise = np.sqrt(noise_fit.integrate(noise_fit.input_ranges[0][0], noise_fit.input_ranges[0][1]))
        # -- Process pac --
        data_pac = cast(SimResults, pac_sim_results).data
        data_pac.open_group('pac')
        gain = np.abs(data_pac['outp'] - data_pac['outn'])[0, 0, :][0]
        in_referred_noise = tot_noise / gain

        return MeasInfo('done', {'Output noise': tot_noise, 
                                 'Input Ref noise': in_referred_noise})

    @staticmethod
    def process_output_delay(sim_results: Union[SimResults, MeasureResult], tbm: DigitalTranTB) -> MeasInfo:
        data = cast(SimResults, sim_results).data
        t_d = tbm.calc_delay(data, 'clk', 'outn', EdgeType.RISE, EdgeType.CROSS, '2.25*t_per', 't_sim')
        result = dict(td=t_d)

        return MeasInfo('done', result)

    @staticmethod
    async def _run_sim(name: str, sim_db: SimulationDB, sim_dir: Path, dut: DesignInstance,
                       tbm: DigitalTranTB):
        sim_id = f'{name}'
        sim_results = await sim_db.async_simulate_tbm_obj(sim_id, sim_dir / sim_id,
                                                          dut, tbm, {}, tb_name=sim_id)

        return sim_results

    async def get_noise(self, name, sim_db: SimulationDB, dut: DesignInstance, sim_dir: Path, vcm: float):
        self.specs['tbm_specs']['sim_params']['v_vcm'] = vcm
        tbm_noise = self.setup_tbm(sim_db, dut, PNoiseTB)
        noise_results = await self._run_sim(name + '_noise', sim_db, sim_dir, dut, tbm_noise)
        tbm_pac = self.setup_tbm(sim_db, dut, PACTB)
        pac_results = await self._run_sim(name + '_pac', sim_db, sim_dir, dut, tbm_pac)
        noise = self.process_output_noise(noise_results, pac_results).prev_results
        return noise

    async def async_measure_performance(self, name: str, sim_dir: Path, sim_db: SimulationDB,
                                        dut: Optional[DesignInstance]) -> Dict[str, Any]:
        results = dict()
        if 'noise' in self.specs['analysis']:
            if 'v_vcm' in self.specs['swp_info'].keys():
                vcm_swp_info = self.specs['swp_info']['v_vcm']
                helper = GatherHelper()
                for vcm in list(
                        np.linspace(float(vcm_swp_info['start']), float(vcm_swp_info['stop']), vcm_swp_info['num'])):
                    helper.append(self.get_noise(name + f'_noise_vcm={vcm:.2f}', sim_db, dut, sim_dir, vcm))
                results['noise'] = await helper.gather_err()
            else:
                tbm_noise = self.setup_tbm(sim_db, dut, PNoiseTB)
                noise_results = await self._run_sim(name + '_noise', sim_db, sim_dir, dut, tbm_noise)
                tbm_pac = self.setup_tbm(sim_db, dut, PACTB)
                pac_results = await self._run_sim(name + '_pac', sim_db, sim_dir, dut, tbm_pac)
                results['noise'] = self.process_output_noise(noise_results, pac_results).prev_results

        if 'delay' in self.specs['analysis']:
            tbm_delay = self.setup_tbm(sim_db, dut, DigitalTranTB)
            delay_results = await self._run_sim(name + '_delay', sim_db, sim_dir, dut, tbm_delay)
            data = cast(SimResults, delay_results).data
            results['delay'] = self.process_output_delay(delay_results, tbm_delay).prev_results
            #cls = ComparatorDelayMM
            #cls.plot_vcm(data, results['delay']['td'], matplotlib.pyplot, tbm_delay)
        #matplotlib.pyplot.show()
        return results['delay'] #cast(SimResults, delay_results).data

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
    def plot_vcm(sim_data, td, axis, tbm: DigitalTranTB):
        if 'v_dm' in sim_data.sweep_params:
            raise RuntimeError("Only sweep vcm, vdm is also in sweep params now")
        vdm = tbm.get_sim_param_value('v_dm')
        axis.plot(sim_data['v_vcm'], td[0], label=f'vdm={vdm}')
        axis.xlabel('v_cm')
        axis.ylabel('Resolve Time')
        axis.grid()
        axis.legend()

class ComparatorPNoiseMM(ComparatorMM):
    def commit(self) -> None:
        self.specs['analysis'] = ['noise']
