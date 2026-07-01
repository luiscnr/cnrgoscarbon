import math,os,re,configparser
from datetime import datetime as dt



class OptionsManager:

    def __init__(self, config_file, options):
        self.options = None
        if options is None:
            if config_file is None:
                print(f'[ERROR] No config file was provided')
            elif not os.path.exists(config_file):
                print(f'[ERROR] {config_file} does not exist')
            elif not os.path.isfile(config_file):
                print(f'[ERROR] {config_file} is not a valid file')
            else:
                try:
                    self.options = configparser.ConfigParser()
                    self.options.read(config_file)

                except Exception as ex:
                    print(f'[ERROR] Error parsing configuration file {config_file}: {ex}')
        else:
            self.options = options

    # def check_section(self,section):
    #     return self.options.has_section(section)

    def add_section(self,new_section):
        if self.options is not None:
            self.options.add_section(new_section)

    def remove_option(self,section,option):
        if self.options is not None:
            if self.options.has_option(section,option):
                self.options.remove_option(section, option)

    def add_value(self,section,option,value):
        if self.options is not None:
            if not self.options.has_section(section):
                self.options.add_section(section)
            self.options.set(section,option,value)

    def save_copy_as_file(self,file_config):
        if self.options is not None:
            with open(file_config, 'w') as configw:
                self.options.write(configw)



    def is_valid(self):
        return False if self.options is None else True

    def get_virtual_flag_list(self):
        if self.options is None:
            return None
        slist = self.options.sections()
        sfinal = []
        for flag in slist:
            if self.options.has_option(flag, 'type'):
                if self.options[flag]['type'] == 'virtual_flag':
                    sfinal.append(flag)
        if len(sfinal) == 0:
            sfinal = None
        return sfinal

    def get_section_list(self, exclude_sections):
        if self.options is None:
            return None
        slist = self.options.sections()
        if exclude_sections is not None:
            sfinal = []
            for section in slist:
                if section not in exclude_sections:
                    sfinal.append(section)
        else:
            sfinal = slist
        if len(sfinal) == 0:
            return None
        return sfinal

    def get_options_list(self,section):
        if self.options is None:
            return None
        if not self.options.has_section(section):
            print(f'[WARNING] Section {section} is not available')
            return None
        options = self.options.options(section)
        return options

    def get_point_args(self,section):
        return self.get_value_param(section,'point_args',None,'strlist')

    def get_retrieve_point_options(self,section,ref,value_list):
        slist = self.get_options_list(section)
        if slist is None:
            print(f'[ERROR] Retrieve options were not found for section {section}')
            return None
        soptions = {}
        for op in slist:
            if op.startswith(f'{ref}.'):
                list_here = self.get_value_param(section, op, None, 'strlist')

                type_param = list_here[0]
                default = None if list_here[1].upper() == 'NONE' else list_here[1]
                if default is not None:
                    default = get_value_param_impl(default, type_param, None)

                potential_values =None
                if len(list_here) == 3:
                    if type_param.startswith('str'):  ##str or strlist:
                        potential_values = get_value_param_impl(list_here[2], 'strlist', None)
                    elif type_param.startswith('int'):  ##int or intlist:
                        potential_values = get_value_param_impl(list_here[2], 'intlist', None)
                    elif type_param.startswith('float'):  ##float or floatlist:
                        potential_values = get_value_param_impl(list_here[2], 'floatlist', None)

                for val in value_list:
                    op_val = op.replace(ref,val)
                    soptions[op_val] = {
                        'type_param': type_param,
                        'default': default
                    }
                    if potential_values is not None:
                        soptions[op_va]['list_values'] = potential_values


        return soptions



    def get_required_args(self,section):
        req_args = self.get_value_param(section,'required_args',None,'dict')
        #print(req_args)
        required_args = {}

        for arg in req_args:
            val_list = [x.strip() for x in req_args[arg].split(';')]
            required_args[arg]={
                'type':val_list[0]
            }
            if len(val_list)>1:
                pvalues = val_list[1:]
                if val_list[0]=='str':
                    required_args[arg]['potential_values'] = pvalues
                elif val_list[0]=='int':
                    try:
                        required_args[arg]['potential_values'] = [int(x) for x in pvalues]
                    except:
                        print(f'[ERROR] Error getting int potential_values for argument {arg}')
                elif val_list[0]=='float':
                    try:
                        required_args[arg]['potential_values'] = [float(x) for x in pvalues]
                    except:
                        print(f'[ERROR] Error getting float potential_values for argument {arg}')



        return required_args



    def get_retrieve_options(self,section):
        slist = self.get_options_list(section)
        if slist is None:
            print(f'[ERROR] Retrieve options were not found for section {section}')
            return [None] * 2

        soptions = {}
        required_list = None

        for op in slist:
            if op == 'required':
                required_list = self.get_value_param(section, op, None, 'strlist')
            elif op == 'required_args' or op == 'point_args':
                continue
            elif op.find('.')>0:
                continue
            else:
                list_here = self.get_value_param(section, op, None, 'strlist')


                type_param = list_here[0]
                default = None if list_here[1].upper() == 'NONE' else list_here[1]
                if default is not None:
                    default = get_value_param_impl(default,type_param,None)


                soptions[op] = {
                    'type_param': type_param,
                    'default': default
                }
                if len(list_here) == 3:
                    #soptions[op]['list_values'] = [s.strip() for s in list[2].split(',')]
                    if type_param.startswith('str'):##str or strlist:
                        soptions[op]['list_values'] = get_value_param_impl(list_here[2], 'strlist', None)
                    elif type_param.startswith('int'):##int or intlist:
                        soptions[op]['list_values'] = get_value_param_impl(list_here[2], 'intlist', None)
                    elif type_param.startswith('float'):##float or floatlist:
                        soptions[op]['list_values'] = get_value_param_impl(list_here[2], 'floatlist', None)

        return soptions, required_list

    ##when type option is selected, then the rest of options are only applied if type_group=type
    ##it includes also overall options for virtual_flags
    def read_options_as_dict(self, section, poptions):
        options_dict = {}
        type = None
        use_pow2_flags = False

        if self.options.has_option(section, 'type'):
            type = self.read_option(section, 'type', 'type', poptions, -1, use_pow2_flags)

        if (type == 'virtual_flag' or type is None) and self.options.has_option(section,
                                                                                'typevirtual'):  ##typevirtual overwrites type
            type = self.read_option(section, 'typevirtual', 'typevirtual', poptions, -1, use_pow2_flags)
        if type is None:
            print(
                f'[ERROR] type (or typevirtual) are not define. Potential types: {poptions["typevirtual"]["list_values"]}')
            return None

        use_pow2_flags = self.get_value_param(section,'use_pow2_flags',False,'boolean')


        options_dict = self.assign_options(options_dict, 'type', type)
        options_dict = self.assign_options(options_dict, 'use_pow2_flags', use_pow2_flags)

        for opt in poptions:
            if opt == 'type' or opt == 'typevirtual' or opt == 'use_pow2_flags':
                continue

            if type is not None and 'type_group' in poptions[opt]:
                if type not in poptions[opt]['type_group']:
                    continue

            if not opt.find('_index') >= 0:
                if self.options.has_option(section, opt):
                    value = self.read_option(section, opt, opt, poptions, -1, use_pow2_flags)
                    options_dict = self.assign_options(options_dict, opt, value)
                else:
                    if 'default' in poptions[opt].keys():
                        options_dict[opt] = poptions[opt]['default']
            else:
                if opt.find('_indexm') >= 0:
                    idx = 0
                    has_option = True
                    while has_option:
                        inner_idx = 0
                        has_inner = True
                        while has_inner:
                            opt_here = opt.replace('_indexm', f'_{idx}_{inner_idx}')
                            # print(opt_here,idx, inner_idx)
                            if self.options.has_option(section, opt_here):
                                value = self.read_option(section, opt, opt_here, poptions, idx, use_pow2_flags)

                                options_dict = self.assign_options(options_dict, opt_here, value)
                                inner_idx = inner_idx + 1
                            else:
                                has_inner = False
                            if inner_idx == 0:
                                has_option = False
                        idx = idx + 1
                else:
                    idx = 0
                    has_option = True
                    while has_option:
                        opt_here = opt.replace('_index', f'_{idx}')
                        if self.options.has_option(section, opt_here):
                            value = self.read_option(section, opt, opt_here, poptions, idx, use_pow2_flags)
                            options_dict = self.assign_options(options_dict, opt_here, value)
                        else:
                            has_option = False
                        idx = idx + 1

        return options_dict

    def assign_options(self, options_dict, key, value):
        keys = key.split('.')
        if len(keys) == 1:
            options_dict[key] = value
        elif len(keys) == 2:
            if keys[0] in options_dict.keys():
                options_dict[keys[0]][keys[1]] = value
            else:
                options_dict[keys[0]] = {keys[1]: value}
        return options_dict

    def read_option(self, section, opt, opt_here, poptions, idx, use_pow2_flags):
        default = None
        if 'default' in poptions[opt].keys():
            default = poptions[opt]['default']
        value = self.get_value_param(section, opt_here, default, poptions[opt]['type_param'])

        if 'list_values' in poptions[opt]:
            if value not in poptions[opt]['list_values']:
                value = None

        if poptions[opt]['type_param'] == 'strlist':
            # use_pow2_vflags = poptions[opt]['user_pow2_vflags']
            value = self.get_strlist_as_dict(value, opt, idx, use_pow2_flags)

        return value

    def get_strlist_as_dict(self, values, opt, idx, use_pow2_flags):
        if opt == 'flag_spatial_index':
            return self.get_dict_flag_spatial_index(values, idx, use_pow2_flags)
        if opt.startswith('flag_ranges_index'):
            return self.get_dict_flag_ranges_index(values, idx, use_pow2_flags)
        if opt.startswith('flag_index'):
            return self.get_dict_flag_index(values,idx,use_pow2_flags)
        return values

    def get_dict_flag_ranges_index(self, values, idx, use_pow2_flags):
        if use_pow2_flags:
            fvalue = int(math.pow(2, idx))
        else:
            fvalue = int(idx + 1)
        value_dict = {
            'flag_name': values[0],
            'flag_value': fvalue,
            'condition_list': [],
        }
        for idx in range(1,len(values)):
            val_condition = values[idx]
            if val_condition.strip().startswith('[') and val_condition.strip().endswith(']'):
                conditions = val_condition.strip()[1:-1].split(';')

                if len(conditions)==2:
                    value_dict['condition_list'].append({
                        'name_var': conditions[0].strip(),
                        'name_flag': conditions[1].strip(),
                        'flag_or_range': 'flag'
                    })
            if val_condition.strip().startswith('(') and val_condition.strip().endswith(')'):
                val_condition = val_condition.strip()
                conditions = val_condition.strip()[1:-1].split(';')
                if len(conditions)==3:
                    value_dict['condition_list'].append({
                        'name_var': conditions[0].strip(),
                        'min_val': float(conditions[1].strip()) if conditions[1].strip().lower()!='none' else None,
                        'max_val': float(conditions[2].strip()) if conditions[2].strip().lower()!='none' else None,
                        'flag_or_range': 'range'
                    })


        return value_dict

    def get_dict_flag_index(self, values, idx, use_pow2_flags):
        if use_pow2_flags:
            fvalue = int(math.pow(2, idx))
        else:
            fvalue = int(idx + 1)
        value_dict = {
            'flag_name': values[0],
            'flag_value': fvalue,
            'condition_list': []
        }
        nconditions = int((len(values)-1)/2)

        for idx in range(nconditions):
            il = (2*idx)+1

            value_dict['condition_list'].append(
                {
                    'flag_var': values[il].strip()[1:],
                    'flag_list': [x.strip() for x in values[il+1].strip()[:-1].split(';')]
                }
            )


        return value_dict


    def get_dict_flag_spatial_index(self, values, idx, use_pow2_flags):
        value_dict = {}
        if use_pow2_flags:
            fvalue = int(math.pow(2, idx))
        else:
            fvalue = int(idx + 1)

        if len(values) == 2:
            value_dict = {
                'is_default': True,
                'flag_name': values[1],
                'flag_value': fvalue
            }
        if len(values) == 5:
            value_dict = {
                'is_default': False,
                'lat_min': float(values[0]),
                'lat_max': float(values[1]),
                'lon_min': float(values[2]),
                'lon_max': float(values[3]),
                'flag_name': values[4],
                'flag_value': fvalue
            }
        return value_dict


    def get_options_as_dict(self,section,poptions,required):
        if not self.is_valid():
            return None
        if poptions is None and required is None:
            soptions, required = self.get_retrieve_options(section)
            if soptions is None:
                return None
        result = {}
        if not self.options.has_section(section):
            for option in poptions:
                result[option] = poptions[option]['default']
        else:
            for option in poptions:
                print('414',option)
                if option.endswith('_'):
                    pass
                    # index = 0
                    # while self.options.has_option(section,f'{option}{index}'):
                    #     key = f'{option}{index}'
                    #     poptions_key = {key:poptions[option]}
                    #     result[key] = self.get_option(section,key,poptions_key,None,None)
                    #     index = index + 1
                else:
                    print(f'#{option}#')
                    #result[option] = self.get_option(section,option,poptions,None,None)
                    

        # if required is not None:
        #     for r in required:
        #         if not r in result:
        #             print(f'[ERROR] Option {r} is required in section {section} of the configuration file.')
        #             return None
        #         if result[r] is None:
        #             print(f'[ERROR] Option {section}/{r}  of the configuration file is required.')
        #             if poptions[r]['type_param']=='file' and self.options.has_option(section,r):
        #                 print(f'[ERROR] {section}/{r}: {self.options[section][r]} does not exist or is not a valid file')
        #             return None

        #return result
        return None
    def get_option(self,section,option,poptions,default,type_param):

        list_values = None
        if poptions is not None and option in poptions.keys():
            if default is None  and 'default' in poptions[option].keys():
                default = poptions[option]['default']
            if type_param is None and 'type_param' in poptions[option].keys():
                type_param = poptions[option]['type_param']
            if 'list_values' in poptions[option].keys():
                list_values = poptions[option]['list_values']

        if type_param is None:
            return None

        value = self.get_value_param(section, option, default, type_param)



        if list_values is not None:
            if not value in list_values:
                print(f'[WARNING] Section/option {section}/{option}: {value} is not a valid value. It should be in the list: {list_values}')
                value = None

        return value

    def get_value(self, section, key):
        value = None
        if self.options.has_option(section, key):
            value = self.options[section][key]
            value = value.strip()
        return value

    def get_value_param(self, section, key, default, type):
        value = self.get_value(section, key)
        if value is None:
            return default


        return get_value_param_impl(value,type,default)





def get_value_param_impl(value,type,default):
    if type == 'str':
        return value.strip(f'"')

    if type == 'file' or type.startswith('input_file'):
        type_check = type[11:] if type.startswith('input_file_') else None
        file = value.strip(f'"')

        if not os.path.exists(file):
            if default is not None and os.path.exists(default):
                return default
            else:
                print(f'[WARNING] Input file {file} is not a valid file.')
                return None
        else:
            if type_check is not None:
                if check_file(file,type_check):
                    return file
                else:
                    return None
            return file

    if type=='output_file' or type.startswith('output_file'):
        ext = type[12:] if type.startswith('output_file_') else None
        file = value.strip(f'"')
        check_default = False
        if ext is not None and not file.endswith(f'.{ext}'):
            print(f'[WARNING] Output file {file} does not have the correct extension, it should be {ext}')
            check_default = True
        output_dir = os.path.dirname(file)
        try:
            os.makedirs(output_dir,exist_ok=True)
        except:
            print(f'[WARNING] Output path {output_dir} does not exist and could not be created.')
            check_default = True
        if check_default:
            if default is not None:
                if ext is not None and not default.endswith(f'.{ext}'):
                    print(f'[WARNING] Output default file {default} does not have the correct extension, it should be {ext}')
                    return None
                output_dir_default = os.path.dirname(default)
                try:
                    os.makedirs(output_dir_default, exist_ok=True)
                except:
                    print(f'[WARNING] Default output path {output_dir_default} does not exist and could not be created.')
                    return None
                return default
            else:
                return None
        else:
            return file

    if type=='output_path': #type == 'directory' or
        directory = value.strip(f'"')
        try:
            os.makedirs(directory,exist_ok=True)
        except Exception as ex:
            if default is not None and os.path.isdir(default):
                print(f'[WARNING] Output path {directory} does not exist and could not be created. Using default output path: {default})')
            else:
                print(f'[WARNING] Output path {directory} does not exist and could not be created. Exception: {ex}. Please review permissions')
                return None
        return directory

    if type== 'input_path':
        input_path = value.strip(f'"')
        if not os.path.isdir(input_path):
            if default is not None and os.path.isdir(default):
                return default
            else:
                print(f'[WARNING] Input path {input_path} is not a valid directory')
                return None
        else:
            return input_path

    if type == 'int':
        return int(value.strip(f'"'))

    if type == 'float':
        return float(value.strip(f'"'))

    if type == 'boolean':
        value = value.strip(f'"')
        if value == '1' or value.upper() == 'TRUE':
            return True
        elif value == '0' or value.upper() == 'FALSE':
            return False
        else:
            return True

    if type == 'rrslist':
        #list_str = value.split(',')
        list_str = [s.strip().strip('"') for s in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', value)]
        list = []
        for vals in list_str:
            vals = vals.replace('.', '_')
            list.append(f'RRS{vals}')
        return list

    if type == 'strlist':
        list = [s.strip().strip('"') for s in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', value)]
        return list

    if type == 'floatlist':
        list_str = [s.strip().strip('"') for s in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', value)]
        list = []
        for vals in list_str:
            list.append(float(vals))
        return list

    if type == 'intlist':
        list_str = [s.strip().strip('"') for s in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', value)]
        list = []
        for vals in list_str:
            list.append(int(vals))
        return list

    if type == 'dict':
        list_str = [s.strip() for s in value.split(',')]
        dict_h = {}
        for vals in list_str:
            list_h = [s.strip().strip('"') for s in re.split(r':(?=(?:[^"]*"[^"]*")*[^"]*$)', vals)]
            if len(list_h)==2:
                dict_h[list_h[0]]=list_h[1]
            else:
                return None
        return dict_h

def get_date_list_from_file(file):
    if not os.path.exists(file):
        return None
    date_list = []
    fr = open(file,'r')
    for line in fr:
        try:
            date_list.append(dt.strptime(line.strip(),'%Y-%m-%d').strftime('%Y-%m-%d'))
        except:
            print(f'[WARNING] Error getting date list from file {file}: {line.strip()} is not in the  valid format YYYY-mm-dd. Skipping line...')
            continue
    fr.close()
    if len(date_list)==0:
        print(f'[ERROR] No date were retrieved from file {file}. Date list will not be used')
        return None
    print(f'[INFO] Date list with {len(date_list)} dates obtained from file {file}')

    return date_list

def check_file(file,type_file):
    if type_file=='nc':
        try:
            from netCDF4 import Dataset
            dset = Dataset(file)
            dset.close()
        except Exception as ex:
            print(f'[WARNING] File {file} is not a valid {type_file}. Exception: {ex}')
            return False

    if type_file=='ini':
        try:
            cp = configparser.ConfigParser()
            cp.read(file)
        except Exception as ex:
            print(f'[WARNING] File {file} is not a valid {type_file}. Exception: {ex}')
            return False

    return True