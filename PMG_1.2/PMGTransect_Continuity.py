import sys 
import os
import json
import numpy as np
import sys
import pandas as pd
import csv
import re
import math
import statistics
from datetime import datetime
import pandas as pd
import calendar
from PMG_Data import * 
import traceback 
from PMGTransect_NETCDF import Transect_NetCDF
from PMGTransect_Output import ReportType, ProcessData, CSVOutput

COV_THRESHOLD = 3.0

class Continuity_Data:
	def __init__(self, start_date, end_date, data_dict, distance_walls, watermover_dict, walls, nodes , transect):
		self.start_date = start_date
		self.end_date = end_date
		self.distance_walls = distance_walls
		self.main_data_array = data_dict
		self.watermover_dict = watermover_dict
		self.walls = walls
		self.nodes = nodes
		self.transect_distance = transect

class Transect_Continuity_Process:
	@staticmethod
	def process( netcdf, data) -> list:
		report_type = ReportType()
		start_date = netcdf.getStartDate()
		end_date = netcdf.getEndDate()
		list_continuity_data = list()
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
			list_continuity_data.append(Continuity_Data(start_date, end_date, data_dict, distance_walls, watermover_name, walls, nodes, total_distance))
		return list_continuity_data

	@staticmethod
	def convert_watermover_list(input_list):
		return_list = [[input_list[i],input_list[i + 1]] for i in range(0, len(input_list), 2)]
		return return_list
	
	@staticmethod
	def divide_chunks(l, n): 
		# looping till length l 
		for i in range(0, len(l), n):  
			yield l[i:i + n]

	@staticmethod
	def variance(data, ddof=0):
		n = len(data)
		mean = sum(data) / n
		return sum((x - mean) ** 2 for x in data) / (n - ddof)

	@staticmethod
	def stdev(data):
		var = Transect_Continuity_Process.variance(data)
		std_dev = math.sqrt(var)
		return std_dev

	@staticmethod
	def proccess_continuity_target(target_data, total_field_name):
		target_df = pd.DataFrame(target_data.main_data_array )
		target_df["DATE"] = pd.to_datetime(target_df.DATE, format='%Y-%m-%d')
		target_df["Years"] = target_df["DATE"].dt.year
		target_df["Months"] = target_df["DATE"].dt.month
		parent_sub_transect_names = [node for node in target_data.nodes if len(node) > 2] 
		child_sub_transect_names = [node for node in target_data.nodes if len(node) == 2]
		parent_sub_transect_names = ['_'.join([str(elem) for elem in parent_sub_transect_names[i]]) for i in range(0,len(parent_sub_transect_names))]
		child_sub_transect_names = ['_'.join([str(elem) for elem in child_sub_transect_names[i]]) for i in range(0,len(child_sub_transect_names))]
		main_dates = [ date.to_pydatetime() for date in target_df["DATE"].drop_duplicates()]
		main_dates = [ d.replace(day=calendar.monthrange(d.year, d.month)[1])  for d in main_dates ]
		main_date_strings = [ date.strftime("%m-%d-%Y") for date in main_dates]
		transect_data = [total for total in target_df[total_field_name]]
		amount_of_months = len(main_dates)
		length_total_transect_data = len(transect_data)
		data_node = dict()
		list_node_names = list()
		if length_total_transect_data/amount_of_months == len(target_data.nodes):
			transect_pre_node = list(Transect_Continuity_Process.divide_chunks(transect_data,amount_of_months))	
			data_node["Date"] = main_date_strings
			for i in range(0,len(target_data.nodes)):
				node_str = '_'.join([str(elem) for elem in target_data.nodes[i]])
				list_data = transect_pre_node[i]
				list_node_names.append(node_str)
				data_node[node_str] = list_data
		else:
			print("Error in structure")
		node_distance = dict(zip(list_node_names,target_data.transect_distance))
		for name in list_node_names:
			temp_data = data_node[name]
			distance = float(node_distance[name])
			adjusted_flows = [ t/(distance/ 5280 ) for t in temp_data]
			data_node[name] = adjusted_flows
		target_data_pd = pd.DataFrame(data_node)
		total_indexs = ["Date"] + parent_sub_transect_names + child_sub_transect_names
		target_data_pd = target_data_pd.reindex(columns=total_indexs)
		test_dict = target_data_pd.to_dict()
		pd_keys = target_data_pd.keys()
		mean_list = list()
		cov_list = list()
		standard_deviation_list = list()
		#print(parent_sub_transect_names)
		for k,v in target_data_pd.iterrows(): 
			temp_dict = v.to_dict()
			data_list = list()
			for name in child_sub_transect_names:
				if name in temp_dict:
					data_list.append(temp_dict[name])
			mean = statistics.mean(data_list)
			mean_list.append(mean)
			standard_deviation = Transect_Continuity_Process.stdev(data_list)
			cov = standard_deviation/mean
			if cov < COV_THRESHOLD:
				cov_list.append(cov)
			else:
				cov_list.append(COV_THRESHOLD)
			standard_deviation_list.append(standard_deviation)
		cov_list_100 = [c * 100 for c in cov_list]
		target_data_pd['Std-Dev'] = standard_deviation_list
		target_data_pd['Mean'] = mean_list
		target_data_pd['COV'] = cov_list
		target_data_pd['COV*100'] = cov_list_100
		#target_data_pd['Diff'] = cov_list
		return target_data_pd , parent_sub_transect_names , child_sub_transect_names

	@staticmethod
	def build_alt_data_cov(main_data_dic, parent_sub_transect_names , child_sub_transect_names):
		data_pd = pd.DataFrame(main_data_dic)
		total_indexs = ["Date"] + parent_sub_transect_names + child_sub_transect_names
		data_pd = data_pd.reindex(columns=total_indexs)
		mean_list = list()
		cov_list = list()
		standard_deviation_list = list()
		mean_list = list()
		cov_list = list()
		standard_deviation_list = list()
		for k,v in data_pd.iterrows(): 
			temp_dict = v.to_dict()
			data_list = list()
			for name in child_sub_transect_names:
				if name in temp_dict:
					data_list.append(temp_dict[name])
			mean = statistics.mean(data_list)
			mean_list.append(mean)
			standard_deviation = Transect_Continuity_Process.stdev(data_list)
			cov = standard_deviation/mean
			if cov < COV_THRESHOLD:
				cov_list.append(cov)
			else:
				cov_list.append(COV_THRESHOLD)
			standard_deviation_list.append(standard_deviation)
		cov_list_100 = [c * 100 for c in cov_list]
		data_pd['Std-Dev'] = standard_deviation_list
		data_pd['Mean'] = mean_list
		data_pd['COV'] = cov_list
		data_pd['COV*100'] = cov_list_100
		return data_pd


	@staticmethod
	def proccess_continuity(target_data, total_field_name):	
		target_df = pd.DataFrame(target_data.main_data_array )
		target_df["DATE"] = pd.to_datetime(target_df.DATE, format='%Y-%m-%d')
		target_df["Years"] = target_df["DATE"].dt.year
		target_df["Months"] = target_df["DATE"].dt.month
		node_str = '_'.join([str(elem) for elem in target_data.nodes]) 
		main_dates = [ date.to_pydatetime() for date in target_df["DATE"].drop_duplicates()]
		main_dates = [ d.replace(day=calendar.monthrange(d.year, d.month)[1])  for d in main_dates ]
		main_date_strings = [ date.strftime("%m-%d-%Y") for date in main_dates]
		transect_data = [total for total in target_df[total_field_name]]
		data_node = dict()
		data_node[node_str] = transect_data
		data_node["Date"] = main_date_strings
		temp_data = data_node[node_str]
		distance = int(math.ceil(target_data.transect_distance))
		adjusted_flows  = [ t/(distance/ 5280 ) for t in temp_data]
		data_node[node_str] = adjusted_flows
		print("%s temp_data: %s adjusted_flows %s distance %s" % (target_data.nodes, temp_data[0], adjusted_flows[0], distance))
		return data_node

	@staticmethod
	def calculate_sum_of_differences(target_data, alt_data):
		alt_cov_list = alt_data['COV']
		deviation_sum = 0
		delta_list = list()
		target_cov_list = target_data['COV']
		record_count = len(alt_cov_list)
		if record_count == len(target_cov_list):
			for i in range(0, len(alt_cov_list)):
				alt_cov = alt_cov_list[i]
				target_cov = target_cov_list[i]
				delta = abs(target_cov - alt_cov)
				deviation_sum = deviation_sum + delta
				delta_list.append(delta)
		alt_data["Diff"] = delta_list
		deviation_ave = deviation_sum / record_count
		return deviation_sum, deviation_ave, record_count

	@staticmethod
	def read_csv_file(read_file) -> Continuity_Data:
		with open(read_file, newline='') as csvfile:
			field_names = list()
			reader = csv.reader(csvfile, delimiter=',', quotechar='|')
			firstline = reader.__next__()
			pattern='(?:[0-9]{2}/){2}[0-9]{4}'
			pattern_2 = '(?:[0-9]{2}/)[0-9]{4}'
			data_dict = dict()
			nodes_list = list()
			distance_list = list()
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
						#print(end_date)
					elif "Wall" in list_row[0]:
						temp = list_row[0].replace("Wall", "").replace("[", "").replace("]", "")
						temp_arry = [row.replace("(", "") for row in temp.split(")") ]
						walls = list()
						for tmp_wall in temp_arry:
							wall = [ int(wall_s) for wall_s in tmp_wall.split(" ") if wall_s != ""]
							if wall:
								walls.append(wall)
					#	print(walls)
					elif "Watermovers" in list_row[0]:
						watermover_string = list_row[0].split("[")[1].replace("]", "")
						watermover_list = watermover_string.split(" ")
						if "-" in watermover_list:
							watermover_dict = Transect_Continuity_Process.convert_watermover_list(watermover_list)
						else:
							watermover_dict = [wm.replace('"', '') for wm in watermover_list]
						#print(watermover_dict)
					elif "Distance" in list_row[0]:
						distance_walls = dict()
						for row in list_row:
							if "Transect" in row:
								try:
									transect = int(row.split("=")[1])
								except:
									transect = float(row.split("=")[1])
								distance_list.append(transect)
							else:
								distance = row.split("=")[1]
								wall_string = row.split("=")[0].replace("Distance(", "").replace(")","")
								try:
									wall = [int(w) for w in wall_string.split(" ") if w != ""]
								except:
									wall = [float(w) for w in wall_string.split(" ") if w != ""]
								distance_walls[distance] = wall
						#print(distance_walls)
					elif "list of nodes" in list_row[0]:
						temp_l = list_row[0].split("=")
						temp_nodes = temp_l[1].replace("[", "").replace("]", "")
						nodes_string = temp_nodes.split(" ")
						nodes = [int(n) for n in nodes_string if n != ""]
						nodes_list.append(nodes)
					elif "Date".upper() in list_row[0].upper():
						field_names = list_row
						field_names = [ field.strip() for field in field_names]
						for field in field_names:
							if field not in data_dict.keys():
								new_list1  = list()
								data_dict[field.strip()] = new_list1
						#print(field_names)
					elif "Timeperiod" not in list_row[0]:
						match = re.search(pattern, list_row[0])
						match_2 = re.search(pattern_2, list_row[0])
						if match:
							date = datetime.strptime(match.group(), '%m/%d/%Y').date()
							#print(date)
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
			t_data = Continuity_Data(start_date, end_date, data_dict, distance_walls, watermover_dict, walls, nodes_list, distance_list)
			return t_data

if __name__ == "__main__":
	
	pass