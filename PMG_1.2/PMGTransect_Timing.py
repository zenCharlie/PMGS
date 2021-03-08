import sys 
import os
import json
import numpy as np
import sys
import pandas as pd
import csv
import re
from datetime import datetime
import pandas as pd
import calendar
from PMG_Data import * 
import traceback 
from PMGTransect_NETCDF import Transect_NetCDF
from PMGTransect_Output import ReportType, ProcessData, CSVOutput

class Timing_Data:
	def __init__(self, start_date, end_date, data_dict, distance_walls, watermover_dict, walls, nodes , transect):
		self.start_date = start_date
		self.end_date = end_date
		self.distance_walls = distance_walls
		self.main_data_array = data_dict
		self.watermover_dict = watermover_dict
		self.walls = walls
		self.nodes = nodes
		self.transect_distance = transect

class Transect_Timing_Process:
	@staticmethod
	def process( netcdf, data) -> list:
		report_type = ReportType()
		start_date = netcdf.getStartDate()
		end_date = netcdf.getEndDate()
		list_timing_data = list()
		for key, value in data.items():
			nodes = value['nodelist']['node']
			walls = value['nodelist']['node_pair']
			watermover_name = sorted(value['nodelist']['watermover_names'].keys())
			watermovers = sorted(value['nodelist']['watermovers'].keys())
			years = sorted(value['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort))
			data_dict = dict()
			data_dict["DATE"] = list()
			for wm in watermovers:
				data_dict[wm] = list()
			total_name = 'TOTAL (%s)' % netcdf._watermovervolume_units
			data_dict[total_name] = list()
			
			for year in years:
				months = sorted(value['years'][year]['months'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort))
				for month in months:
					date_t = '%d/%d ' % (month, year)
					data_list = data_dict["DATE"]
					date = datetime(year, month, 1)
					data_list.append(date)
					data_dict["DATE"] = data_list
					for wm in watermovers:
						temp_list = data_dict[wm] 
						if wm in value['years'][year]['months'][month]['values']:
							temp_list.append(sum(value['years'][year]['months'][month]['values'][wm]))
						data_dict[wm] = temp_list
					total_list = data_dict[total_name] 
					total_list.append(np.sum(value['years'][year]['months'][month]['all']))
					data_dict[total_name] = total_list
			distance_walls = dict()
			total_distance = 0
			if len(netcdf.coordinates.keys()) != 0:
				total_distance = 0
				for nodepair in value['nodelist']['node_pair']:
					distance = ProcessData.get_distance(netcdf, nodepair)
					total_distance = total_distance + distance
					distance_walls[distance] = nodepair
			list_timing_data.append(Timing_Data(start_date, end_date, data_dict, distance_walls, watermover_name, walls, nodes, total_distance))
		return list_timing_data

	@staticmethod
	def convert_watermover_list(input_list):
		return_list = [[input_list[i],input_list[i + 1]] for i in range(0, len(input_list), 2)]
		return return_list
	
	@staticmethod
	def create_timing_data(target_data, data):
		print(target_data.main_data_array["TOTAL (ft^3)"][400])
		target_df = pd.DataFrame(target_data.main_data_array )
		target_df["DATE"] = pd.to_datetime(target_df.DATE, format='%Y-%m-%d')
		target_df["WaterYear"] = target_df["DATE"].dt.year.where(target_df["DATE"].dt.month < 11, target_df["DATE"].dt.year + 1)
		target_watery = target_df["WaterYear"].drop_duplicates()
		target_list_water_years = target_watery.tolist()
		target_list_water_years = [int(water_year) for water_year in target_list_water_years if water_year != 1965 ]
		water_years_target_sum = dict()
		for water_year in target_list_water_years:
			water_year_data = target_df[target_df["WaterYear"] == water_year]["TOTAL (ft^3)"]
			if len(water_year_data) == 12:
				total_accum = water_year_data.sum()
				proportion_t = [accum/total_accum for accum in water_year_data]
				target_sum = np.cumsum(proportion_t)
				water_years_target_sum[water_year] = np.asarray(proportion_t, dtype=np.float32)
		df = pd.DataFrame(data.main_data_array)
		df["DATE"] = pd.to_datetime(df.DATE, format='%Y-%m-%d')
		df["WaterYear"] = df["DATE"].dt.year.where(df["DATE"].dt.month < 11, df["DATE"].dt.year + 1)
		annual_mean_discharge_rate = df.groupby('WaterYear')[['TOTAL (FT^3)']].mean()
		check = df[df["WaterYear"] == 1966]
		watery = df["WaterYear"].drop_duplicates()
		list_water_years = watery.tolist()
		list_water_years = [int(water_year) for water_year in list_water_years if water_year != 1965 ]
		deviation_data = dict()
		for water_year in list_water_years:
			water_year_data = df[df["WaterYear"] == water_year]['TOTAL (FT^3)']
			if len(water_year_data) == 12:
				total_accum = water_year_data.sum()
				proportion = [accum/total_accum for accum in water_year_data]
				sum_data = np.cumsum(proportion)
				if len(water_years_target_sum) > 0:
					target_deviation = list(proportion - water_years_target_sum[water_year])
					sub_transect_dev_sum = np.cumsum([abs(d) for d in target_deviation])
					index = 1 - sub_transect_dev_sum[-1]
					target_deviation.append(index)
					deviation_data[water_year] = target_deviation
		return deviation_data

	@staticmethod
	def build_data_for_printing(deviation_data, field_names, transect):
		print_arrray = list()
		print_arrray.append(field_names)
		for wy, data in deviation_data.items():
			temp_list = list()
			temp_list.append("%d" % wy)
			temp_list.append(transect)
			for d in data:
				value = "%.3f" % d
				temp_list.append(value)
			print_arrray.append(temp_list)
		return print_arrray

	@staticmethod
	def build_data_for_dataframe(deviation_data, field_names, transect):
		print_arrray = list()
		print_arrray.append(field_names)
		for wy, data in deviation_data.items():
			temp_list = list()
			temp_list.append(wy)
			temp_list.append(transect)
			for d in data:
				temp_list.append(d)
			print_arrray.append(temp_list)
		return print_arrray
	
	@staticmethod
	def process_data_pdf_report(deviation_data):
		field_names = ["Water Year", "Transect", str(calendar.month_name[11]), str(calendar.month_name[12]), str(calendar.month_name[1]), str(calendar.month_name[2]),\
			str(calendar.month_name[3]), str(calendar.month_name[4]), str(calendar.month_name[5]), str(calendar.month_name[6]), str(calendar.month_name[7]), str(calendar.month_name[8]), \
				str(calendar.month_name[9]), str(calendar.month_name[10]), "Index"]
		temp_data = Transect_Timing_Process.build_data_for_dataframe(deviation_data,field_names, "t7")
		print_data = Transect_Timing_Process.build_data_for_printing(deviation_data,field_names, "t7")
		test = pd.DataFrame(temp_data[1:], columns= temp_data[0])
		test.set_index("Water Year")
		boxplot_data_dict = dict()
		transect = 't7'
		average_list = ['Average', transect]
		minimum_list = ['Minimum', transect]
		ten_percent_list = ['0.10', transect]
		twenty_five_percent_list = ['0.25', transect]
		fifty_percent_list = ['0.50', transect]
		seventy_five_percent_list = ['0.75', transect]
		ninety_percent_list = ['.90', transect]
		maximum_list = ['Maximum', transect]
		for column in test.columns[2:]:
			index = field_names.index(column)
			describe = test[column].describe(percentiles=[.10, .25, .5, .75, .90])
			average_list.insert(index, "%.3f" % describe['mean'])
			minimum_list.insert(index, "%.3f" % describe['min'])
			ten_percent_list.insert(index, "%.3f" % describe['10%'])
			twenty_five_percent_list.insert(index, "%.3f" % describe['25%'])
			fifty_percent_list.insert(index, "%.3f" % describe['50%'])
			seventy_five_percent_list.insert(index, "%.3f" % describe['75%'])
			ninety_percent_list.insert(index, "%.3f" % describe['90%'])
			maximum_list.insert(index, "%.3f" % describe['max'])
			if column != "Index":
				boxplot_data_dict[column] = [describe['10%'], describe['25%'], describe['50%'], describe['75%'], describe['90%']]
		print_data.append(average_list)
		print_data.append(minimum_list)
		print_data.append(ten_percent_list)
		print_data.append(twenty_five_percent_list)
		print_data.append(fifty_percent_list)
		print_data.append(ninety_percent_list)
		print_data.append(maximum_list)
		return print_data, boxplot_data_dict

	@staticmethod
	def read_csv_file(read_file) -> Timing_Data:
		with open(read_file, newline='') as csvfile:
			field_names = list()
			reader = csv.reader(csvfile, delimiter=',', quotechar='|')
			firstline = reader.__next__()
			pattern='(?:[0-9]{2}/){2}[0-9]{4}'
			pattern_2 = '(?:[0-9]{2}/)[0-9]{4}'
			data_dict = dict()
			if "Monthly Totals"in firstline[0]:
				for list_row in reader:
					if "Timeperiod" in list_row[0]:
						Timeperiod_temp = list_row[0].split('-')
						start_date_string = Timeperiod_temp[0]
						match_start_date = re.search(pattern, start_date_string)
						start_date = datetime.strptime(match_start_date.group(), '%m/%d/%Y').date() 
						end_date_string = Timeperiod_temp[1]
						match_end_date = re.search(pattern, end_date_string)
						end_date = datetime.strptime(match_end_date.group(), '%m/%d/%Y').date() 
					elif "Wall" in list_row[0]:
						temp = list_row[0].replace("Wall", "").replace("[", "").replace("]", "")
						temp_arry = [row.replace("(", "") for row in temp.split(")") ]
						walls = list()
						for tmp_wall in temp_arry:
							wall = [ int(wall_s) for wall_s in tmp_wall.split(" ") if wall_s != ""]
							if wall:
								walls.append(wall)
					elif "Watermovers" in list_row[0]:
						watermover_string = list_row[0].split("[")[1].replace("]", "")
						watermover_list = watermover_string.split(" ")
						if "-" in watermover_list:
							watermover_dict = Transect_Timing_Process.convert_watermover_list(watermover_list)
						else:
							watermover_dict = [wm.replace('"', '') for wm in watermover_list]
					elif "Distance" in list_row[0]:
						distance_walls = dict()
						for row in list_row:
							if "Transect" in row:
								try:
									transect = int(row.split("=")[1])
								except:
									transect = float(row.split("=")[1])
							else:
								distance = row.split("=")[1]
								wall_string = row.split("=")[0].replace("Distance(", "").replace(")","")
								try:
									wall = [int(w) for w in wall_string.split(" ") if w != ""]
								except:
									wall = [float(w) for w in wall_string.split(" ") if w != ""]
								distance_walls[distance] = wall
					elif "list of nodes" in list_row[0]:
						temp_l = list_row[0].split("=")
						temp_nodes = temp_l[1].replace("[", "").replace("]", "")
						nodes_string = temp_nodes.split(" ")
						nodes = [int(n) for n in nodes_string if n != ""]
					elif "Date".upper() in list_row[0].upper():
						field_names = list_row
						field_names = [ field.strip() for field in field_names]
						for field in field_names:
							if field not in data_dict.keys():
								new_list1  = list()
								data_dict[field.strip()] = new_list1
					elif "Timeperiod" not in list_row[0]:
						match = re.search(pattern, list_row[0])
						match_2 = re.search(pattern_2, list_row[0])
						if match:
							date = datetime.strptime(match.group(), '%m/%d/%Y').date()
						if match_2:
							try:
								date = datetime.strptime(match_2.group(), '%m/%Y').date()
								field_names = list(data_dict.keys())
								for field in field_names:
									new_list = data_dict[field]
									index = field_names.index(field)
									if index == 0:
										new_list.append(date)
									else:
										new_list.append(float(list_row[index]))
									data_dict[field] = new_list
							except:
								pass
			if start_date:
				t_data = Timing_Data(start_date, end_date, data_dict, distance_walls, watermover_dict, walls, nodes, transect)
		return t_data

if __name__ == "__main__":
	
	pass