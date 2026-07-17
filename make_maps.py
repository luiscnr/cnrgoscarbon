import argparse,os

import numpy as np
import matplotlib.pyplot as plt
import common_functions as cf
from options.options_manager import OptionsManager
from datetime import timedelta
from netCDF4 import Dataset
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
import matplotlib as mpl
from matplotlib.colors import LogNorm
from matplotlib.colors import BoundaryNorm

class OptionsMaps:

    def __init__(self,config_file):
        file_opt = os.path.join(os.path.dirname(__file__),'options/map_options.ini')
        self.cmanager = OptionsManager(file_opt,None)
        self.omanager = OptionsManager(config_file,None)
        self.VALID = True
        if not self.cmanager.is_valid():
            print(f'[ERROR] Problem retrieving options from {file_opt}')
            self.VALID = False
        if not self.omanager.is_valid():
            print(f'[ERROR] Problem retrieving options from the configuration file {config_file}')
            self.VALID = False

    def get_options_as_dict(self,section):
        if not self.VALID:
            return None
        try:
            poptions,required_list = self.cmanager.get_retrieve_options(section)
            options_dict = self.omanager.get_options_as_dict(section,poptions,required_list)
        except Exception as ex:
            print(f'[ERROR] Error getting options: {ex}')
            return None
        return options_dict


    def get_general_map_options(self):
        return self.get_options_as_dict('MAP_GENERAL')


    def get_specific_map_options(self,section):
        if not self.VALID:
            return None
        poptions,required_list = self.cmanager.get_retrieve_options('MAP_SPECIFIC')
        options_dict = self.omanager.get_options_as_dict(section,poptions,required_list)

        return options_dict

    def get_specific_map_options_for_dataset(self,map_options,dataset):
        if not self.VALID:
            return None
        if  map_options is None:
            map_options = self.get_general_map_options()


        key = f'{dataset}_options'
        section_specific = self.omanager.get_value_param('MAP_GENERAL',key,None,'str')
        map_options['variable'] = None
        if section_specific is not None and self.omanager.has_section(section_specific):
            map_specific_options = self.get_specific_map_options(section_specific)
            for key in map_specific_options:
                if map_specific_options[key] is not None:
                    map_options[key] = map_specific_options[key]

        if map_options['variable'] is None:
            if map_options['type_product']=='DOC':
                default_variables = map_options['default_doc_variables']
            elif map_options['type_product']=='POC':
                default_variables = map_options['default_poc_variables']

            if dataset in default_variables:
                map_options['variable'] = default_variables[dataset]
            else:
                print(f'[ERROR] Default variable for dataset {dataset} is not available. Please add a MAP_SPECIFIC section (indicated in {key} in MAP_GENERAL) with the variable option')
                return None
        return map_options

class Mapper:
    def __init__(self,options,options_maps):
        self.options = options
        self.options_maps = options_maps


    def create_maps(self,work_date,datasets):
        if self.options_maps['maps']=='ALL':
            datasets_here = datasets.copy()
        else:
            dhere = self.options_maps['maps']
            if not dhere in datasets:
                print(f'[ERROR] Dataset {dhere} is not in the list of given datasets: {list(datasets.keys())} Skipping...')
                return
            datasets_here = {dhere:datasets[dhere]}

        for dataset in datasets_here:
            print(f'[INFO] Working with dataset: {dataset}')
            map_options = self.options.get_specific_map_options_for_dataset(self.options_maps.copy(),dataset)
            if isinstance(datasets[dataset],list):
                input_file = datasets[dataset][0]
            else:
                input_file = datasets[dataset]
            if dataset.endswith('-1w'):
                real_date = work_date - timedelta(days=8)
            elif dataset.endswith('-2w'):
                real_date = work_date - timedelta(days=16)
            else:
                real_date = work_date
            self.create_map_impl(map_options,input_file,dataset,work_date,real_date)

    def create_map_impl(self,maps_options,input_file,dataset,work_date,real_date):
        name_var = maps_options['variable']
        if not os.path.isfile(input_file):
            print(f'[WARNING] Input file {input_file} is not available. Skipping....')
            return
        try:
            dset = Dataset(input_file)
            data_array = np.squeeze(dset.variables[name_var][:])
            lat_array = dset.variables['lat'][:]
            lon_array = dset.variables['lon'][:]
            dset.close()
        except Exception as ex:
            print(f'[ERROR] Error getting variables from input file {input_file}. Exception: {ex}')
            return
        output_file_path,file_format = self.get_output_file(maps_options,name_var,work_date,real_date)
        if output_file_path is None:
            return

        fig,ax = self.start_map(maps_options,lat_array,lon_array)
        self.plot_data(maps_options,ax,lat_array,lon_array,data_array)
        self.set_title(maps_options,dataset,work_date,real_date)
        self.save_map(fig,output_file_path,file_format)
        print(f'[INFO] Map saved to file: {output_file_path}')

    def get_output_file(self,map_options,name_var,input_date, real_date):
        file_format = map_options['output_format']
        output_file = map_options['output_file']
        if file_format is None:
            if  output_file is None:
                file_format = 'png'
            else:
                try:
                    file_format = output_file[output_file.rindex('.')+1:]
                except Exception as ex:
                    print(f'[ERROR] Output file format could not be retrieved from output file name {output_file}. Exception {ex}')
                    return [None]*2
        if output_file is not None:
            if not output_file.endswith(file_format):
                print(f'[ERROR] Output file {output_file} does not match with file format {file_format}')
                return [None]*2
        else:
            output_file = f'{name_var}_map_$DATE$.{file_format}'


        output_path = cf.get_input_file(map_options['output_path'],output_file,map_options['output_file_format'],input_date,name_var,
                                        none_if_not_exists=False,create_sub_dirs=True,real_date=real_date,folder_format=map_options['output_path_organization'])

        if output_path is None:
            return [None]*2

        if not os.path.isdir(os.path.dirname(output_path)):
            print(f'[ERROR] Directory for the output file {output_path} does not exist and could not be created. Please review permissions')
            return [None]*2

        print(f'[INFO] Expected output path: {output_path}. Format: {file_format}')

        return output_path, file_format

    def plot_data(self,map_options,ax,lat_array,lon_array,data_array):

        if map_options['min_v'] is not None:
            vmin = map_options['min_v']
        elif map_options['min_p'] is not None and 0 < map_options['min_p'] < 100:
            vmin = np.percentile(data_array.compressed(),map_options['min_p'])
        else:
            vmin = np.ma.min(data_array)

        if map_options['max_v'] is not None:
            vmax = map_options['max_v']
        elif map_options['max_p'] is not None and 0 < map_options['max_p'] < 100:
            vmax = np.percentile(data_array.compressed(),map_options['max_p'])
        else:
            vmax = np.ma.min(data_array)


        colormap = map_options['colormap']
        shading = map_options['shading']
        if map_options['log_scale']:
            data_array = np.ma.masked_less_equal(data_array,0)
            h = ax.pcolormesh(lon_array, lat_array, data_array, shading=shading, norm=LogNorm(vmin=vmin, vmax=vmax), cmap=mpl.colormaps[colormap],
                              transform=ccrs.PlateCarree())
            #img = ax.imshow(data, transform=crs, extent=crs.bounds, origin='upper', norm=LogNorm(vmin=0.001, vmax=100))
        elif map_options['boundary_norm'] is not None:
            bounds = map_options['boundary_norm']
            norm = BoundaryNorm(boundaries=bounds, ncolors=len(bounds) + 1)
            cmap_r = mpl.colormaps[colormap].resampled(len(bounds) + 1)
            h = ax.pcolormesh(lon_array, lat_array, data_array, shading=shading,norm=norm,cmap=cmap_r,transform=ccrs.PlateCarree())
        else:
            h = ax.pcolormesh(lon_array, lat_array, data_array, shading=shading,vmin=vmin, vmax=vmax, cmap=mpl.colormaps[colormap],transform=ccrs.PlateCarree())

        if map_options['colorbar']:
            kwargs_cb = {}
            for key in map_options:
                if key.startswith('cb_') and map_options[key] is not None:
                    key_cb = key.split('_')[1]
                    kwargs_cb[key_cb] = map_options[key]

            plt.colorbar(h, ax=ax, cax=None,use_gridspec = map_options['colorbar_use_gridspec'],**kwargs_cb)



    def set_title(self,map_options,dataset,work_date,real_date):
        if map_options['show_title']:
            if map_options['title'] is None:
                if work_date==real_date:
                    title = f'$DATASET$ - $DATE1$'
                else:
                    title = f'$DATASET$ - $DATE1$. Processing data: $DATE2$'
            else:
                title = map_options['title']
            title = title.replace('$DATASET$',dataset)
            title = title.replace('$DATE$', work_date.strftime('%Y-%m-%d'))
            title = title.replace('$DATE1$',work_date.strftime('%Y-%m-%d'))
            title = title.replace('$DATE2$', real_date.strftime('%Y-%m-%d'))
            plt.title(title)

    def save_map(self,fig,file_out,format):
        if format=='tif' or format=='tiff':
            fig.savefig(file_out, dpi=300, bbox_inches='tight', pil_kwargs={"compression": "tiff_lzw"})
        else:
            fig.savefig(file_out, dpi=300, bbox_inches='tight')


    def start_map(self,map_options,lat_array,lon_array):
        # start figure and axes
        fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()))
        fig.set_figwidth(15)
        fig.set_figheight(10)
        # ax = plt.axes(projection=ccrs.Miller())

        ##set extent
        extent = [np.min(lon_array),np.max(lon_array),np.min(lat_array),np.max(lat_array)]
        ax.set_extent(extent, crs=ccrs.PlateCarree())

        #add land
        land_50m = cfeature.NaturalEarthFeature('physical', 'land', '10m', edgecolor='black',facecolor=cfeature.COLORS['land'])
        ax.add_feature(land_50m)

        #add costline
        # ax.add_feature(cartopy.feature.LAND, zorder=0, edgecolor='black', linewidth=0.5)
        # ax.coastlines(resolution='10m')

        # grid lines
        gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False, linewidth=0.5, linestyle='dotted')
        # gl.xlocator = mticker.FixedLocator([5, 10, 15, 20, 25, 30])

        #lat_labels
        if map_options['lat_labels'] is not None:
            lat_labels = map_options['lat_labels']
        else:
            lat_min,lat_max = np.min(lat_array), np.max(lat_array)
            lat_space = map_options['lat_space']
            if lat_space is None:
                lat_space_options = np.array([0.25,0.5,1,2,3,5,10,15])
                lat_interval = (lat_max-lat_min)/4
                lat_space = lat_space_options[int(np.argmin(np.abs(lat_space_options-lat_interval)))]
            all_intervals = np.arange(0,90,lat_space)
            lat_labels = all_intervals[(all_intervals>=lat_min) & (all_intervals<=lat_max)]

        #lon_labels
        if map_options['lon_labels'] is not None:
            lon_labels = map_options['lon_labels']
        else:
            lon_min,lon_max = np.min(lon_array), np.max(lon_array)
            lon_space = map_options['lon_space']
            if lon_space is None:
                lon_space_options = np.array([0.25,0.5,1,2,3,5,10,15])
                lon_interval = (lon_max-lon_min)/4
                lon_space = lon_space_options[int(np.argmin(np.abs(lon_space_options-lon_interval)))]
            all_intervals = np.arange(0,90,lon_space)
            lon_labels = all_intervals[(all_intervals>=lon_min) & (all_intervals<=lon_max)]

        gl.xlocator = mticker.FixedLocator(lon_labels)
        gl.ylocator = mticker.FixedLocator(lat_labels)



        gl.right_labels = False
        gl.left_labels = True
        gl.bottom_labels = True
        gl.top_labels = False
        showLonLabels = map_options['show_lon_labels']
        showLatLabels = map_options['show_lat_labels']
        color_lon = 'k' if showLonLabels is True else 'w'
        size_lon = 12 if showLonLabels is True else 0
        gl.xlabel_style = {'size': size_lon, 'color': color_lon}
        color_lat = 'k' if showLatLabels is True else 'w'
        size_lat = 12 if showLatLabels is True else 0
        gl.ylabel_style = {'size': size_lat, 'color': color_lat}

        return fig, ax


def main(args_d):
    start_date = cf.get_date_arg(args_d['start_date'])
    if start_date is None:
        return

    end_date = cf.get_date_arg(args_d['end_date'])
    if end_date is None:
        end_date = start_date

    options = OptionsMaps(args_d['config_file'])
    if not options.VALID:
        return

    options_maps = options.get_general_map_options()
    if options_maps is None:
        return

    mapper = Mapper(options,options_maps)

    if options_maps['type_product']=='DOC':
        print('[INFO] Type product for map generation: DOC')
        from make_doc import OptionsDOC
        import make_doc as md
        options_doc = OptionsDOC(args_d['config_file'])
        general_model_options = options_doc.get_general_model_options()

        work_date =  start_date
        while work_date <= end_date:
            print(f'[INFO] --------------------------------------------------------------------------------------------')
            print(f'[INFO] Work date for map generation: {work_date.strftime("%Y-%m-%d")}')
            datasets = md.get_datasets(general_model_options,work_date)
            datasets['DOC'] = cf.get_input_file(general_model_options['output_path'], general_model_options['output_file'], '%Y%j', work_date,create_sub_dirs=False,none_if_not_exists=False)
            mapper.create_maps(work_date,datasets)
            work_date += timedelta(days=1)

    if options_maps['type_product']=='POC':
        print('[INFO] Type product for map generation: POC')
        from make_poc import OptionsPOC

        options_poc = OptionsPOC(args_d['config_file'])
        poc_options = options_poc.get_poc_options()

        work_date =  start_date
        while work_date <= end_date:
            print(f'[INFO] --------------------------------------------------------------------------------------------')
            print(f'[INFO] Work date for map generation: {work_date.strftime("%Y-%m-%d")}')
            file_out = cf.get_input_file(poc_options['output_path'], poc_options['output_file'], '%Y%j', work_date,create_sub_dirs=False, none_if_not_exists=False)
            if not os.path.isfile(file_out):
                print(f'[WARNING] Output file {file_out} does not exist! Skipping date: {work_date.strftime("%Y-%m-%d")}')
                work_date += timedelta(days=1)
                continue
            datasets = {x: file_out for x in options_maps['default_poc_variables'].keys()}
            mapper.create_maps(work_date,datasets)
            work_date += timedelta(days=1)






if __name__ == "__main__":
    print(f'[INFO] Started CNR-GOS Carbon tool!')
    print(f'[INFO] This is the script to product maps for CDOM, DOC and POC products.')
    parser = argparse.ArgumentParser(description="CNR-GOS Carbon Tool: Map generation")
    parser.add_argument("-v", "--verbose", help="Verbose mode.", action="store_true")
    parser.add_argument('-c', "--config_file", help="Config File.")
    parser.add_argument('-sd', "--start_date",help="Start Date: YYYY-mm-dd")
    parser.add_argument('-ed', "--end_date", help="End Date: YYYY-mm-dd")
    args = parser.parse_args()
    args_dict = vars(args)
    main(args_dict)