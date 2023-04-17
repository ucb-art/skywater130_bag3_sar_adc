# SkyWater130 SAR ADC 
Synchronous SAR ADC generated using BAG3. 

## Inventory
This repo consists of sub-modules `bag3_sync_sar_adc` and `bag3_sync_sar_adc_data_skywater130` (inside the `data` folder). The latter consists of `yaml` files that describe the required parameters of each circuit. The former consists of BAG3 generators. Following BAG3 convention, please clone `bag3_sync_sar_adc` into your workspace, and `bag3_sync_sar_adc_data_skywater130` into the data folder of your workspace. 

Provided is a list of files with descriptions:

 - Top level ADC
	 - Generator: [sar_sync_bootstrap.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/sar_sync_bootstrap.py) 
	 - Specs (8 bit): [specs_slice_sync_bootstrap.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_slice_sync_bootstrap.yaml)
	 - Specs (4 bit): [specs_slice_sync_bootstrap_small.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_slice_sync_bootstrap_small.yaml)
 - Bootstrapped Sampler
	- Generates sampling switch
	- Generator: [sampler_top.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/sampler_top.py) 
	- Specs:  [specs_clkgen_sync_sar.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/bootstrap/specs_lay_sample_top.yaml) 
 - Synchronous Logic
	 - This block can be further split into the full 8 bit logic array with output registers, and the unit logic block for 1 bit
	 - Generator (for all blocks): [sar_logic_sync.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/sar_logic_sync.py) 
	 - Specs: 
		 - For top level: [specs_logic_sync.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_logic_sync.yaml)
		 - For array: [specs_logic_array_sync.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_logic_array_sync.yaml)
		 - For unit:  For top level: [specs_logic_unit_sync.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_logic_unit_sync.yaml)
		 - For OAI logic gate in unit: 
- MIM Cap DAC
	- This block generates an 8 bit capacitor dac of MIM caps
	- Generator (for all blocks): [sar_cdac.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/sar_cdac.py) 
	- Specs: 
		- For cap DAC: [specs_cdac_mim.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_cdac_mim.yaml)
		- For switch bank: [specs_capdrv_unit.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_capdrv_unit.yaml)
		- For single MIM capacitor:  [specs_cap_mim.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_cap_mim.yaml)
- Comparator
	- This block contains a wrapper around a comparator. A strongARM is used.
	- Generator: [sar_comp.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/sar_comp.py) 
	- Specs:  [specs_comp_sa.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_comp.yaml) 
- Clock generator
	- Divides input clock by 16 for a reset/sampling signal, provides buffering for clock signals
	- Generator: [clk_sync_sar.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/clk_sync_sar.py) 
	- Specs:  [specs_clkgen_sync_sar.yaml](https://github.com/ucb-art/bag3_sync_sar_adc_data_skywater130/blob/main/specs_gen/sar_lay/specs_clkgen_sync_sar.yaml) 
- Digital blocks
	- Contains BAG generator code for some standard logic gates (inv, nand, flip flop, latch, etc.)
	- Generator: [digital.py](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/digital.py) 
	- Does not have any dedicated yaml files
- Util Folder
	- Contains layout helper functions
	- [folder](https://github.com/ucb-art/bag3_sync_sar_adc/blob/main/src/bag3_sync_sar_adc/layout/util) 


## Setup
This generator will only work inside a BAG3 workspace ( [template repo](https://github.com/ucb-art/bag3_skywater130_workspace) ). See the ReadMe for the template repo for workplace setup instructions.

After cloning, add
 ```
 bag3_sync_sar_adc/src 
 ```
 to `.bashrc_pypath` .  

If you wish to use this generator with Virtuoso, also add 
```
bag3_sync_sar_adc/src/OA/bag3_sync_sar_adc
``` 
to your `cds.lib`

To generate a design from this repo run the following command in your workspace: 
```
./gen_cell.sh data/bag3_sync_sar_adc_data_skywater130/specs_gen/sar_lay/your_yaml.yaml
```
## Caveats
This generator has only been verified LVS and DRC clean on configurations in the provided yamls. 

## Licensing

This library is licensed under the BSD, 3-Clause license.  See [here](LICENSE) for full text of the BSD, 3-Clause license.
