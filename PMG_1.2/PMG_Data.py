import xml.etree.ElementTree as ET
import json
import sys
import os
from PMG_Exceptions import InputErrorMessage, NetCDFErrorMessage, SingletonErrorMessage
import traceback

from datetime import * 

CELL_IDS_FIELD  = "cell_ids"
NODE_FIELD = "node"
TARGET_FIELD = "target"
RUN_NAME_FIELD = "run_name"
NAME_FIELD = "name"
RUN_PATHS_FIELD = "run_paths_files"

class SloughVegetationData:
	def __init__(self, data):
		self.title = data["title"]
		self.run_name = data["run_name"]
		self.cell_ids = data["cell_ids"]
		self.wet_targets = data["wet_targets"]
		self.dry_targets = data["dry_targets"]
		self.wet_season_targets = data["wet_season_targets"]
		self.dry_season_targets = data["dry_season_targets"]
		self.run_paths_files = data[RUN_PATHS_FIELD]

class TransectData:
	def __init__(self, data):
		self.title = data["title"]
		self.run_name = data["run_name"]
		self.start_date = data["start_date"]
		self.end_date = data["end_date"]
		self.nodes = data["nodes"]
		self.target = data["target"]
		self.run_paths_files = data[RUN_PATHS_FIELD]
		if "segments" in data:
			self.segments = data["segments"]

class PMGMainData:
	def __setup_slough_vegetation_pmg(self, root_xml_data):
		slough_vegetation = root_xml_data.find("slough_vegetation")
		irzones = root_xml_data.iter("irzone")
		irzones_data = dict()
		for irzone in irzones:
			irzone_dict = dict()
			attributes = irzone.attrib
			subs = list(irzone)
			irzone_dict[CELL_IDS_FIELD] = [float(value) for value in list(irzone.find(CELL_IDS_FIELD).text.split(","))]
			sub_names = [s.tag for s in subs]
			subs_w_subs = [s.tag for s in subs if len(s) > 0 ]
			sub_names = [name for name in sub_names if name not in subs_w_subs]
			for name in set(sub_names):
				irzone_dict[name] =[float(value) for value in list(irzone.find(name).text.split(","))]
			file_names = [ name for name in subs_w_subs if "file" in name.lower()]
			run_paths_files = list()
			if "run_paths_files" in file_names:
				for sub in list(irzone.find("run_paths_files")):
					if os.path.isfile(sub.text.strip()):
						path_dict = dict()
						path_dict["name"]= sub.attrib[NAME_FIELD]
						path_dict["file_name"] = sub.text.strip()
						run_paths_files.append(path_dict)
					else:
						raise FileNotFoundError(sub.text.strip())
			irzone_dict.update(attributes)
			irzone_dict[RUN_PATHS_FIELD] = run_paths_files
			slough_vegetation = SloughVegetationData(irzone_dict)
			irzones_data[attributes[RUN_NAME_FIELD]] = slough_vegetation
		return irzones_data

	def __create_datetime(self, date_dict):
		return datetime(year=int(date_dict["year"]), month=int(date_dict["month"]), day=int(date_dict["day"]))

	def __find_run_data(self, xml_tag_data):
		run_paths_files = list()
		for run_path in list(xml_tag_data.find(RUN_PATHS_FIELD)):
			if os.path.isfile(run_path.text.strip()):
				path_dict = dict()
				path_dict["name"]= run_path.attrib[NAME_FIELD]
				path_dict["file_name"] = run_path.text.strip()
				run_paths_files.append(path_dict)
		return run_paths_files

	def __setup_transect_timing_pmg(self, root_xml_data):
		transects_pmg_data = dict()
		transect_timing = root_xml_data.find("transect_timing")
		start_date_attrib = root_xml_data.find("start_date").attrib
		end_date_attrib = root_xml_data.find("end_date").attrib
		start_date = self.__create_datetime(start_date_attrib)
		end_date =  self.__create_datetime(end_date_attrib)
		transects = root_xml_data.iter("transect")
		for transect in transects:
			transect_pmg_data = dict()
			transect_attribs = transect.attrib
			transect_pmg_data["start_date"] = start_date
			transect_pmg_data["end_date"] = end_date
			transect_pmg_data.update(transect_attribs)
			segments = transect.iter("segment")
			segments_list = list()
			for segment in segments:
				segments_list.append(segment.text.strip())
			transect_pmg_data["segments"] = segments_list
			nodes = transect.iter(NODE_FIELD)
			nodes_list = list()
			for node in nodes:
				nodes_list.append([int(value) for value in list(node.text.split(","))])
			transect_pmg_data["nodes"] = nodes_list
			transect_pmg_data[TARGET_FIELD] = transect.find(TARGET_FIELD).text.strip()
			transect_pmg_data[RUN_PATHS_FIELD] = self.__find_run_data(transect)
			transects_pmg_data[transect_attribs[RUN_NAME_FIELD]] = TransectData(transect_pmg_data)
		return transects_pmg_data

	def __switch_pmg_types(self, pmg_type, data):
		types = {
			"PMG6":self.__setup_slough_vegetation_pmg,
			"PMG1.2.1":self.__setup_transect_timing_pmg
		}
		build_xml_data = types.get(pmg_type,\
			 lambda: InputErrorMessage("Error PMG not defined.", traceback.format_exc(), pmg_type+data))
		return build_xml_data(data)

	def __read_xml(self, input_file):
		try:
			attributes = dict()
			tree = ET.parse(input_file)
			root = tree.getroot()
			root.iter
		except Exception as error:
			raise InputErrorMessage(str(error), traceback.format_exc(), input_file) 
		pmg_type = ""
		if "logfolder" in root.attrib.keys():
			attributes["log_folder"] = root.attrib["logfolder"]
		else:
			raise InputErrorMessage("logfolder", traceback.format_exc(), input_file)
		if "title" in root.attrib.keys():
			attributes["title"] =  root.attrib["title"]
		else:
			raise InputErrorMessage("title", traceback.format_exc(), input_file)
		if "pmg_type" in root.attrib.keys():
			pmg_type = root.attrib["pmg_type"]
		else:
			raise InputErrorMessage("pmg_type", traceback.format_exc(), input_file)
		pmg_data = self.__switch_pmg_types(pmg_type, root)
		return pmg_data, attributes

	def __setup_slough_vegetation_pmg_json(self, json_data):
		irzones_data = {}
		irzones = json_data["irzones"]
		for irzone in irzones:
			slough_vegetation = SloughVegetationData(irzone)
			irzones_data[irzone[RUN_NAME_FIELD]] = slough_vegetation
		return irzones_data

	def __setup_timing_transect_pmg_json(self, json_data):
		transect_data = {}
		transects = json_data["transects"]
		for transect in transects:
			transect_info = TransectData(transect)
			transect_data[transect[RUN_NAME_FIELD]] = transect_info
		return transect_data

	def __switch_pmg_types_json(self, pmg_type, data):
		types = {
			"PMG6":self.__setup_slough_vegetation_pmg_json,
			"PMG1.2.1":self.__setup_timing_transect_pmg_json
		}
		build_xml_data = types.get(pmg_type,\
			 lambda: InputErrorMessage("Error PMG not defined.", traceback.format_exc(), pmg_type+data))
		return build_xml_data(data)

	def __read_json(self, input_file):
		attributes = {}
		with open(input_file) as input_json:
			json_data = json.load(input_json)
			if "logfolder" in json_data:
				attributes["logfolder"] = json_data["logfolder"]
			else:
				raise InputErrorMessage("logfolder", traceback.format_exc(), input_file)
			if "title" in json_data:
				attributes["title"] =  json_data["title"]
			else:
				raise InputErrorMessage("title", traceback.format_exc(), input_file)
			if "pmg_type" in json_data:
				pmg_type = json_data["pmg_type"]
			else:
				raise InputErrorMessage("pmg_type", traceback.format_exc(), input_file)
		pmg_data = self.__switch_pmg_types_json(pmg_type, json_data)
		return pmg_data, attributes

	def __switch_format(self, format_mode, input_file):
		formats = {
			"XML":self.__read_xml,
			"JSON":self.__read_json
		}
		build_data = formats.get(format_mode)
		return build_data(input_file)

	__instance = None
	@staticmethod
	def get_instance():
		if PMGMainData.__instance == None:
			raise SingletonErrorMessage("", traceback.format_exc(), "get")
		return PMGMainData.__instance

	def __init__(self, input_file, mode):
		if PMGMainData.__instance != None:
			raise SingletonErrorMessage("", traceback.format_exc(), "set")
		self.data, self.attributes = self.__switch_format(mode, input_file)
		PMGMainData.__instance = self

if __name__ == '__main__':
	try:
		pmg_data = PMGMainData(sys.argv[1], "XML")
		#pmg_data = PMGMainData(sys.argv[1], "JSON")
		print(pmg_data.attributes['log_folder'])
		keys = pmg_data.data.keys()
		print(keys)
		for key, value in pmg_data.data.items():
			print(key)
			run_names_list = []
			transect_data = value
			print(transect_data.segments)
			for netCDF_path in transect_data.run_paths_files:
				print(netCDF_path["name"])
				print(netCDF_path["file_name"])
		'''		
		import NETCDF_CLASS
		for irzone_name, irzone_data in pmg_data.data.items():
						run_names_list = []
						for netCDF_path in irzone_data.run_paths_files:
							run_id = irzone_data.run_paths_files.index(netCDF_path)
							netcdf_run_name = netCDF_path["name"]
							run_names_list.append(netcdf_run_name)
							netcdf_file_name = netCDF_path["file_name"]
							netcdf_run = NETCDF_CLASS.NETCDF_RSM(netcdf_file_name)
							n_timesteps = netcdf_run.get_timestamp_length()
							start_date = netcdf_run.get_date_stamp(0)
							end_date = netcdf_run.get_date_stamp(-1)
							time_array = [netcdf_run.get_date_stamp(time_index)for time_index  in range(0, n_timesteps)]
							print(time_array[0])
							print(time_array[-1])'''

	except NetCDFErrorMessage as e:
		print("Error message %s" % e.netcdf_message)