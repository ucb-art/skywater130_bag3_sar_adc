# SkyWater130 SAR ADC 
Synchronous 8 bit SAR ADC generated using BAG3. 

## Inventory
This repo consists of `skywater130_bag3_sar_adc_gen` and `skywater130_bag3_sar_adc_data`. The `_data` folder consists of `yaml` files that describe the required parameters of each circuit. `_gen` consists of BAG3 generators. 

Provided is a list of files with descriptions. Layout generator files are  in [`skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout`](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout) and corresponding `yaml` files (when applicable) are located in [`skywater130_bag3_sar_adc_data/specs_gen/sar_lay`](skywater130_bag3_sar_adc_data/specs_gen/sar_lay):

 - Top level ADC
	 - Generator: [sar_sync.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/sar_sync.py) 
	 - Specs: [specs_slice_sync.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_slice_sync.yaml)
 - Synchronous Logic
	 - This block can be further split into the full 8 bit logic array with output registers, and the unit logic block for 1 bit
	 - Generator (for all blocks): [sar_logic_sync.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/sar_logic_sync.py) 
	 - Specs: 
		 - For top level: [specs_logic_sync.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_logic_sync.yaml)
		 - For array: [specs_logic_array_sync.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_logic_array_sync.yaml)
		 - For unit:  For top level: [specs_logic_unit_sync.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_logic_unit_sync.yaml)
		 - For OAI logic gate in unit: 
- MIM Cap DAC
	- This block generates an 8 bit capacitor dac of MIM caps
	- Generator (for all blocks): [sar_cdac.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/sar_cdac.py) 
	- Specs: 
		- For cap DAC: [specs_cdac_mim.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_cdac_mim.yaml)
		- For switch bank: [specs_capdrv_unit.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_capdrv_unit.yaml)
		- For single MIM capacitor:  [specs_cap_mim.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_cap_mim.yaml)
- Comparator
	- This block contains a wrapper around a comparator. A strongARM is used.
	- Generator: [sar_comp.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/sar_comp.py) 
	- Specs:  [specs_comp_sa.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_comp.yaml) 
- Clock generator
	- Divides input clock by 16 for a reset/sampling signal, provides buffering for clock signals
	- Generator: [clk_sync_sar.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/clk_sync_sar.py) 
	- Specs:  [specs_clkgen_sync_sar.yaml](skywater130_bag3_sar_adc_data/specs_gen/sar_lay/specs_clkgen_sync_sar.yaml) 
- Digital blocks
	- Contains BAG generator code for some standard logic gates (inv, nand, flip flop, latch, etc.)
	- Generator: [digital.py](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/digital.py) 
	- Does not have any dedicated yaml files
- Util Folder
	- Contains layout helper functions
	- [folder](skywater130_bag3_sar_adc_gen/src/skywater130_bag3_sar_adc/layout/util) 


## Setup
This generator will only work inside a BAG3 workspace ( [template repo](https://github.com/ucb-art/bag3_skywater130_workspace) ). See the ReadMe for the template repo for workplace setup instructions.

After cloning, add
```
 skywater130_bag3_sar_adc/skywater130_bag3_sar_adc_gen/src` 
 ```
 to `.bashrc_pypath` .  

If you wish to use this generator with Virtuoso, also add 
```
skywater130_bag3_sar_adc/skywater130_bag3_sar_adc_gen/src/OA/skywater130_bag3_sar_adc
``` 
to your `cds.lib`

To generate a design from this repo run the following command in your workspace: 
```
./run_bag.sh BAG_framework/run_scripts/gen_cell.py skywater130_bag3_sar_adc/skywater130_bag3_sar_adc_data/specs_gen/sar_lay/your_yaml.yaml
```
## Caveats
The layouts included in this repo have been verified with Calibre LVS tools. However, the schematics created out of the box from this generator will not simulate or be usable for LVS. To simulate or check LVS on any designs, all of the transistors in the schematics must be swapped from the `BAG_prim` transistors generated to the respective skywater `s8phires_10` model .

This generator still contains a few non-waivable DRC errors out of the box. These should be manually fixed. 

## Licensing

This library is licensed under the BSD, 3-Clause license.  See [here](LICENSE) for full text of the BSD, 3-Clause license.
